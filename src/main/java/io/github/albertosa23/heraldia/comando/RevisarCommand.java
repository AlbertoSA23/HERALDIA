package io.github.albertosa23.heraldia.comando;

import com.google.gson.JsonObject;
import com.mojang.brigadier.arguments.StringArgumentType;
import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.arena.Arena;
import io.github.albertosa23.heraldia.caminos.Caminos;
import io.github.albertosa23.heraldia.comando.Revision.Marca;
import io.github.albertosa23.heraldia.comando.Revision.Parada;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.dimensiones.Suelo;
import io.github.albertosa23.heraldia.costa.Costa;
import io.github.albertosa23.heraldia.config.UniqueSeparation;
import java.io.IOException;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.function.Predicate;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.minecraft.ChatFormatting;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.SharedSuggestionProvider;
import net.minecraft.commands.arguments.IdentifierArgument;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Holder;
import net.minecraft.core.SectionPos;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.chat.ClickEvent;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.HoverEvent;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.network.protocol.game.ClientboundSetSubtitleTextPacket;
import net.minecraft.network.protocol.game.ClientboundSetTitleTextPacket;
import net.minecraft.network.protocol.game.ClientboundSetTitlesAnimationPacket;
import net.minecraft.resources.Identifier;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.level.TicketType;
import net.minecraft.util.Util;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.biome.Climate;
import net.minecraft.world.level.chunk.ChunkGenerator;
import net.minecraft.world.level.levelgen.RandomState;
import net.minecraft.world.level.levelgen.densityfunction.SamplerContext;
import net.minecraft.world.level.levelgen.structure.placement.RandomSpreadStructurePlacement;
import net.minecraft.world.level.block.BaseFireBlock;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.CampfireBlock;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.chunk.LevelChunk;
import net.minecraft.world.level.chunk.storage.ChunkScanAccess;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.level.material.Fluid;
import net.minecraft.world.level.material.Fluids;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.levelgen.structure.Structure;
import net.minecraft.world.level.levelgen.structure.StructureStart;
import net.minecraft.world.level.storage.LevelResource;
import org.jspecify.annotations.Nullable;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * /heraldia review (operador, nivel 2): ruta guiada para validar en una tarde todo el contenido visual ({@link Revision}).
 * En cada parada: búsqueda fuera del hilo del servidor (la rejilla de cada tipo, como /heraldia info nearby: sin cargar
 * ni generar nada), teletransporte seguro ({@link Seguro}), un título, la lista de qué mirar y botones para marcarla.
 * <p>Busca desde el punto de aparición del mundo. Prefiere una estructura ya generada (aunque esté más lejos) a una
 * prevista; ir a una prevista genera terreno nuevo, así que antes se avisa y hace falta pulsar «Ir y generar» (goto &lt;id&gt; generate). El
 * progreso de cada jugador se guarda en heraldia_revision.json y el resumen en heraldia_revision.md (carpeta del mundo),
 * escritos fuera del hilo del servidor.
 */
public final class RevisarCommand {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	/** Radio de búsqueda (bloques desde el punto de aparición); la Atlántida, una por mundo, se busca en todo el mundo. */
	static final int RADIO = InfoCommand.MAX_RADIUS, RADIO_ATLANTIDA = 1 << 20;
	/** Puntos de la lista de cada tipo de parada (claves heraldia.revisar.mirar.&lt;tipo&gt;.&lt;n&gt;). */
	static final Map<Revision.Tipo, Integer> PUNTOS = Map.of(Revision.Tipo.ALDEA, 4, Revision.Tipo.UNICA, 4,
			Revision.Tipo.MEDIANA, 3, Revision.Tipo.MINA, 3, Revision.Tipo.COSTA, 3, Revision.Tipo.ARENA, 3, Revision.Tipo.CAMINO, 3);
	/** Únicas con un punto propio en la lista (heraldia.revisar.mirar.unica.&lt;id&gt;). */
	static final Set<String> CON_PUNTO_PROPIO = Set.of("atlantida", "isla_corsario");

	private static Revision.Registro registro = new Revision.Registro();
	private static @Nullable Path carpeta;
	private static CompletableFuture<Void> escritura = CompletableFuture.completedFuture(null);
	private static final Set<UUID> BUSCANDO = new HashSet<>();

	private RevisarCommand() {
	}

	static void registrarEventos() {
		ServerLifecycleEvents.SERVER_STARTED.register(server -> {
			carpeta = server.getWorldPath(LevelResource.ROOT);
			registro = Revision.leer(carpeta.resolve(Revision.FICHERO));
		});
		ServerLifecycleEvents.SERVER_STOPPING.register(server -> {
			escritura.join();                  // lo pendiente de escribir, antes de cerrar
			BUSCANDO.clear();
		});
	}

	static LiteralArgumentBuilder<CommandSourceStack> nodo() {
		return Commands.literal("review")
				.requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))
				.executes(ctx -> ir(ctx, null, false))
				.then(Commands.literal("next").executes(ctx -> mover(ctx, +1)))
				.then(Commands.literal("previous").executes(ctx -> mover(ctx, -1)))
				.then(Commands.literal("skip").executes(ctx -> saltar(ctx, ""))
						.then(Commands.argument("note", StringArgumentType.greedyString())
								.executes(ctx -> saltar(ctx, StringArgumentType.getString(ctx, "note")))))
				.then(Commands.literal("goto")
						.then(Commands.argument("id", IdentifierArgument.id())
								.suggests((ctx, b) -> SharedSuggestionProvider.suggest(
										ruta(ctx.getSource().getServer()).stream().map(Parada::id), b))
								.executes(ctx -> ir(ctx, IdentifierArgument.getId(ctx, "id").getPath(), false))
								.then(Commands.literal("generate")
										.executes(ctx -> ir(ctx, IdentifierArgument.getId(ctx, "id").getPath(), true)))))
				.then(Commands.literal("mark")
						.then(Commands.literal("checked").executes(ctx -> marcar(ctx, Marca.REVISADA, ""))
								.then(Commands.argument("note", StringArgumentType.greedyString())
										.executes(ctx -> marcar(ctx, Marca.REVISADA, StringArgumentType.getString(ctx, "note")))))
						.then(Commands.literal("problem").executes(ctx -> marcar(ctx, Marca.PROBLEMA, ""))
								.then(Commands.argument("note", StringArgumentType.greedyString())
										.executes(ctx -> marcar(ctx, Marca.PROBLEMA, StringArgumentType.getString(ctx, "note"))))))
				.then(Commands.literal("list").executes(RevisarCommand::lista))
				.then(Commands.literal("status").executes(RevisarCommand::estado))
				.then(Commands.literal("reset").executes(RevisarCommand::reiniciar));
	}

	// --- la ruta ---

	/** Las paradas de este mundo (del registro de estructuras y la configuración en uso). Barato: se hace cada vez. */
	static List<Parada> ruta(MinecraftServer server) {
		HeraldiaConfig cfg = HeraldiaConfig.get();
		List<String> ids = new ArrayList<>();
		server.registryAccess().lookupOrThrow(Registries.STRUCTURE).keySet().stream()
				.filter(id -> Heraldia.MOD_ID.equals(id.getNamespace())).forEach(id -> ids.add(id.getPath()));
		Map<String, String> estilos = estiloFamilia(cfg);
		Predicate<Parada> activa = p -> switch (p.tipo()) {
			case ALDEA -> estilos.entrySet().stream().anyMatch(e -> e.getValue().equals(p.sub())
					&& opcion(cfg, "aldeas.estilos." + e.getKey()) && opcion(cfg, "aldeas.familias." + p.sub()));
			case UNICA -> InfoCommand.uniqueEnabled(cfg, p.sub());
			case MEDIANA -> opcion(cfg, "medianas.activadas") && opcion(cfg, "medianas." + p.sub() + ".activada");
			case MINA -> opcion(cfg, "minas.entradas.activado");
			case COSTA -> Costa.opcion(p.sub()) == null || opcion(cfg, Costa.opcion(p.sub()) + ".activado");
			case ARENA, CAMINO -> true;
		};
		return Revision.ruta(ids, estilos, activa, cfg.getBool("arena.activado"), cfg.getBool(Caminos.ACTIVADO));
	}

	private static boolean opcion(HeraldiaConfig cfg, String key) {
		return !cfg.has(key) || cfg.getBool(key);
	}

	static Map<String, String> estiloFamilia(HeraldiaConfig cfg) {
		Map<String, String> out = new LinkedHashMap<>();
		JsonObject styles = cfg.schema().getAsJsonObject("aldeas").getAsJsonObject("estilos");
		styles.entrySet().forEach(e -> out.put(e.getKey(), e.getValue().getAsString()));
		return out;
	}

	/** Nombre traducible de una parada. */
	static MutableComponent nombre(Parada p) {
		return switch (p.tipo()) {
			case ALDEA -> Textos.t("heraldia.info.aldea", Textos.t("heraldia.familia." + p.sub()));
			case UNICA -> InfoCommand.uniqueName(p.sub());
			case MEDIANA -> InfoCommand.mediumName(p.sub());
			case MINA -> Textos.t("heraldia.minas." + p.sub() + ".nombre");
			case COSTA -> Textos.t("heraldia.costa." + p.sub() + ".nombre");
			case ARENA -> Textos.t("heraldia.revisar.parada.arena");
			case CAMINO -> Textos.t("heraldia.revisar.parada.camino");
		};
	}

	/** El mismo nombre en español, para el informe en Markdown. */
	static String nombreEs(Parada p) {
		Map<String, String> es = Textos.idioma(Textos.ES);
		return switch (p.tipo()) {
			case ALDEA -> es.getOrDefault("heraldia.info.aldea", "%s").replace("%s", es.getOrDefault("heraldia.familia." + p.sub(), p.sub()));
			case UNICA -> es.getOrDefault("heraldia.unicas." + p.sub() + ".nombre", p.sub());
			case MEDIANA -> es.getOrDefault("heraldia.medianas." + p.sub() + ".nombre", p.sub());
			case MINA -> es.getOrDefault("heraldia.minas." + p.sub() + ".nombre", p.sub());
			case COSTA -> es.getOrDefault("heraldia.costa." + p.sub() + ".nombre", p.sub());
			case ARENA -> es.getOrDefault("heraldia.revisar.parada.arena", "arena");
			case CAMINO -> es.getOrDefault("heraldia.revisar.parada.camino", "camino");
		};
	}

	/** Claves de la lista de qué mirar de una parada. */
	static List<String> puntos(Parada p) {
		String tipo = p.tipo().name().toLowerCase(Locale.ROOT);
		List<String> out = new ArrayList<>();
		for (int i = 1; i <= PUNTOS.get(p.tipo()); i++) {
			out.add("heraldia.revisar.mirar." + tipo + "." + i);
		}
		if (p.tipo() == Revision.Tipo.UNICA && CON_PUNTO_PROPIO.contains(p.sub())) {
			out.add("heraldia.revisar.mirar.unica." + p.sub());
		}
		return out;
	}

	/** ¿Es la estructura `id` (de Heraldia) de esta parada? */
	static boolean deLaParada(Parada p, Identifier id, Map<String, String> estilos) {
		if (!Heraldia.MOD_ID.equals(id.getNamespace())) {
			return false;
		}
		String path = id.getPath();
		return switch (p.tipo()) {
			case ALDEA -> {
				String estilo = path.endsWith("_grande") ? path.substring(0, path.length() - "_grande".length()) : path;
				yield p.sub().equals(estilos.get(estilo));
			}
			case UNICA -> path.equals("unicas/" + p.sub());
			case MEDIANA -> path.startsWith("medianas/" + p.sub() + "/");
			case MINA -> path.startsWith("minas/" + p.sub() + "/");
			case COSTA -> path.startsWith("costa/" + p.sub() + "/");
			case ARENA, CAMINO -> false;
		};
	}

	// --- órdenes ---

	private static ServerPlayer jugador(CommandContext<CommandSourceStack> ctx) throws CommandSyntaxException {
		return ctx.getSource().getPlayerOrException();
	}

	private static Revision.Progreso progreso(ServerPlayer p) {
		return registro.de(p.getUUID(), p.getGameProfile().name());
	}

	private static int mover(CommandContext<CommandSourceStack> ctx, int paso) throws CommandSyntaxException {
		ServerPlayer p = jugador(ctx);
		List<Parada> ruta = ruta(ctx.getSource().getServer());
		Revision.Progreso pr = progreso(p);
		pr.actual = paso > 0 ? Revision.siguiente(ruta, pr.actual) : Revision.anterior(ruta, pr.actual);
		guardar(ctx.getSource().getServer());
		return irA(ctx.getSource(), p, ruta, pr.actual, false);
	}

	private static int ir(CommandContext<CommandSourceStack> ctx, @Nullable String id, boolean generar) throws CommandSyntaxException {
		ServerPlayer p = jugador(ctx);
		List<Parada> ruta = ruta(ctx.getSource().getServer());
		Revision.Progreso pr = progreso(p);
		if (id != null) {
			int i = Revision.indice(ruta, id);
			if (i < 0) {
				ctx.getSource().sendFailure(Textos.t("heraldia.revisar.desconocida", id));
				return 0;
			}
			pr.actual = i;
			guardar(ctx.getSource().getServer());
		}
		return irA(ctx.getSource(), p, ruta, pr.actual, generar);
	}

	private static int saltar(CommandContext<CommandSourceStack> ctx, String nota) throws CommandSyntaxException {
		ServerPlayer p = jugador(ctx);
		List<Parada> ruta = ruta(ctx.getSource().getServer());
		Revision.Progreso pr = progreso(p);
		if (pr.actual < ruta.size()) {
			registro.marcar(p.getUUID(), p.getGameProfile().name(), ruta.get(pr.actual).id(), Marca.SALTADA, nota, System.currentTimeMillis());
		}
		pr.actual = Revision.siguiente(ruta, pr.actual);
		guardar(ctx.getSource().getServer());
		return irA(ctx.getSource(), p, ruta, pr.actual, false);
	}

	private static int marcar(CommandContext<CommandSourceStack> ctx, Marca m, String nota) throws CommandSyntaxException {
		ServerPlayer p = jugador(ctx);
		CommandSourceStack src = ctx.getSource();
		List<Parada> ruta = ruta(src.getServer());
		Revision.Progreso pr = progreso(p);
		if (pr.actual >= ruta.size()) {
			src.sendFailure(Textos.t("heraldia.revisar.sin_parada"));
			return 0;
		}
		Parada parada = ruta.get(pr.actual);
		registro.marcar(p.getUUID(), p.getGameProfile().name(), parada.id(), m, nota, System.currentTimeMillis());
		guardar(src.getServer());
		Revision.Nota n = pr.nota(parada.id());
		src.sendSuccess(() -> Textos.t("heraldia.revisar.marcada", nombre(parada), parada.id(), estado(m),
				n == null || n.nota().isEmpty() ? Component.empty() : Textos.t("heraldia.revisar.con_nota", n.nota())), false);
		src.sendSuccess(() -> botones(false), false);
		return 1;
	}

	private static int lista(CommandContext<CommandSourceStack> ctx) {
		CommandSourceStack src = ctx.getSource();
		List<Parada> ruta = ruta(src.getServer());
		ServerPlayer p = src.getPlayer();
		Revision.Progreso pr = p == null ? null : registro.jugadores().get(p.getUUID());
		src.sendSuccess(() -> Textos.t("heraldia.revisar.lista.titulo", ruta.size()).withStyle(ChatFormatting.GOLD), false);
		for (int i = 0; i < ruta.size(); i++) {
			Parada x = ruta.get(i);
			Revision.Nota n = pr == null ? null : pr.nota(x.id());
			boolean aqui = pr != null && pr.actual == i;
			MutableComponent l = Textos.t("heraldia.revisar.lista.linea", i + 1, nombre(x), x.id(),
					n == null ? Textos.t("heraldia.revisar.estado.pendiente") : estado(n.marca()));
			l.withStyle(s -> s.withColor(aqui ? ChatFormatting.AQUA : n == null ? ChatFormatting.WHITE
							: n.marca() == Marca.PROBLEMA ? ChatFormatting.RED : ChatFormatting.GRAY)
					.withClickEvent(new ClickEvent.RunCommand("/heraldia review goto " + x.id()))
					.withHoverEvent(new HoverEvent.ShowText(Textos.t("heraldia.revisar.boton.ir.ayuda"))));
			src.sendSuccess(() -> l, false);
		}
		return ruta.size();
	}

	private static int estado(CommandContext<CommandSourceStack> ctx) {
		CommandSourceStack src = ctx.getSource();
		List<Parada> ruta = ruta(src.getServer());
		ServerPlayer p = src.getPlayer();
		Map<UUID, Revision.Progreso> todos = p != null ? (registro.jugadores().containsKey(p.getUUID())
				? Map.of(p.getUUID(), registro.jugadores().get(p.getUUID())) : Map.of()) : registro.jugadores();
		if (todos.isEmpty()) {
			Revision.Cuenta c = Revision.cuenta(ruta, null);
			src.sendSuccess(() -> Textos.t("heraldia.revisar.resumen", "-", c.revisadas(), ruta.size(), c.problemas(), c.saltadas(),
					c.pendientes()).withStyle(ChatFormatting.GOLD), false);
		}
		for (Revision.Progreso pr : todos.values()) {
			Revision.Cuenta c = Revision.cuenta(ruta, pr);
			src.sendSuccess(() -> Textos.t("heraldia.revisar.resumen", pr.nombre(), c.revisadas(), ruta.size(), c.problemas(),
					c.saltadas(), c.pendientes()).withStyle(ChatFormatting.GOLD), false);
			for (Parada x : ruta) {
				Revision.Nota n = pr.nota(x.id());
				if (n != null && n.marca() == Marca.PROBLEMA) {
					src.sendSuccess(() -> Textos.t("heraldia.revisar.resumen.problema", nombre(x), x.id(), n.nota())
							.withStyle(ChatFormatting.RED), false);
				}
			}
		}
		Path md = carpeta == null ? null : carpeta.resolve(Revision.INFORME).normalize();
		if (md != null) {
			guardar(src.getServer());
			src.sendSuccess(() -> Textos.t("heraldia.revisar.exportado", md.toString()).withStyle(ChatFormatting.GRAY), false);
		}
		return todos.size();
	}

	private static int reiniciar(CommandContext<CommandSourceStack> ctx) throws CommandSyntaxException {
		ServerPlayer p = jugador(ctx);
		registro.reiniciar(p.getUUID());
		guardar(ctx.getSource().getServer());
		ctx.getSource().sendSuccess(() -> Textos.t("heraldia.revisar.reiniciada"), false);
		return 1;
	}

	// --- ir a una parada ---

	private record Destino(BlockPos pos, boolean generada) {
	}

	private static int irA(CommandSourceStack src, ServerPlayer p, List<Parada> ruta, int i, boolean generar) {
		if (i >= ruta.size()) {
			src.sendSuccess(() -> Textos.t("heraldia.revisar.fin").withStyle(ChatFormatting.GOLD), false);
			return 0;
		}
		if (!BUSCANDO.add(p.getUUID())) {
			src.sendFailure(Textos.t("heraldia.revisar.ocupado"));
			return 0;
		}
		Parada parada = ruta.get(i);
		MinecraftServer server = src.getServer();
		ServerLevel level = nivel(server, parada, estiloFamilia(HeraldiaConfig.get()));
		// en el Nether y el End no hay punto de reaparición: se busca desde el 0, 0
		BlockPos origen = level.dimension() == Level.OVERWORLD ? level.getRespawnData().pos() : new BlockPos(0, 64, 0);
		src.sendSuccess(() -> Textos.t("heraldia.revisar.buscando", nombre(parada)).withStyle(ChatFormatting.GRAY), false);
		long t0 = System.nanoTime();
		CompletableFuture<@Nullable Destino> busqueda;
		if (parada.tipo() == Revision.Tipo.ARENA) {
			BlockPos c = Arena.centro();
			busqueda = CompletableFuture.completedFuture(c == null ? null : new Destino(c, true));
		} else {
			Map<String, String> estilos = estiloFamilia(HeraldiaConfig.get());
			List<InfoCommand.Group> grupos = parada.tipo() == Revision.Tipo.CAMINO ? List.of() : InfoCommand.groups(level);
			busqueda = CompletableFuture.supplyAsync(() -> parada.tipo() == Revision.Tipo.CAMINO ? camino(level, origen)
					: buscar(level, grupos, h -> deLaParada(parada, h.unwrapKey().orElseThrow().identifier(), estilos), origen,
					"unica/atlantida".equals(parada.id()) ? RADIO_ATLANTIDA : RADIO), Util.backgroundExecutor());
		}
		busqueda.thenAcceptAsync(d -> {
			long ms = (System.nanoTime() - t0) / 1_000_000;
			LOGGER.info("Heraldia: /heraldia review {}: {} en {} ms", parada.id(), d == null ? "nada" : d, ms);
			Destino dest = d == null ? null : confirmar(level, parada, d, estiloFamilia(HeraldiaConfig.get()));
			if (dest == null) {
				BUSCANDO.remove(p.getUUID());
				cabecera(src, p, ruta, i, parada);
				src.sendFailure(Textos.t(parada.tipo() == Revision.Tipo.ARENA ? "heraldia.revisar.sin_arena"
						: "heraldia.revisar.no_encontrada", nombre(parada), RADIO));
				src.sendSuccess(() -> botones(true), false);
			} else if (!dest.generada() && !generar) {
				BUSCANDO.remove(p.getUUID());
				cabecera(src, p, ruta, i, parada);
				int dist = (int) Math.sqrt(dest.pos().distSqr(new BlockPos(origen.getX(), dest.pos().getY(), origen.getZ())));
				src.sendSuccess(() -> Textos.t("heraldia.revisar.prevista", InfoCommand.coordinates(dest.pos()), dist)
						.withStyle(ChatFormatting.YELLOW), false);
				src.sendSuccess(() -> boton("heraldia.revisar.boton.generar", "/heraldia review goto " + parada.id() + " generate",
						true, ChatFormatting.GOLD), false);
				src.sendSuccess(() -> botones(true), false);
			} else {
				teletransportar(src, p, level, dest, () -> {
					BUSCANDO.remove(p.getUUID());
					cabecera(src, p, ruta, i, parada);
					src.sendSuccess(() -> botones(false), false);
				});
			}
		}, server).exceptionally(e -> {
			BUSCANDO.remove(p.getUUID());
			LOGGER.error("Heraldia: /heraldia review falló", e);
			src.sendFailure(Component.literal(String.valueOf(e.getMessage())));
			return null;
		});
		return 1;
	}

	/**
	 * Fuera del hilo del servidor: la estructura de la parada más cercana a {@code origen}, recorriendo las casillas de
	 * su rejilla de la más cercana a la más lejana. Una ya generada (chunk guardado con su inicio) gana a cualquier
	 * prevista; de las previstas, la más cercana (las mismas reglas de la generación que /heraldia info nearby). No carga
	 * ni genera chunks: el disco se lee con el escáner de StructureCheck.
	 */
	static @Nullable Destino buscar(ServerLevel level, List<InfoCommand.Group> grupos, Predicate<Holder<Structure>> filtro,
									BlockPos origen, int radio) {
		ChunkScanAccess scanner = level.getChunkSource().chunkScanner();
		List<InfoCommand.Found> celdas = new ArrayList<>();
		Map<InfoCommand.Found, InfoCommand.Group> grupoDe = new LinkedHashMap<>();
		long seed = level.getChunkSource().getGeneratorState().getLevelSeed();
		int cx = SectionPos.blockToSectionCoord(origen.getX()), cz = SectionPos.blockToSectionCoord(origen.getZ());
		long radioSq = (long) radio * radio;
		for (InfoCommand.Group g0 : grupos) {
			List<Holder<Structure>> propias = g0.structures().stream().filter(filtro).toList();
			if (propias.isEmpty()) {
				continue;
			}
			InfoCommand.Group g = new InfoCommand.Group(g0.placement(), propias);
			RandomSpreadStructurePlacement pl = g.placement();
			int s = pl.spacing(), ox = UniqueSeparation.offsetX(pl), oz = UniqueSeparation.offsetZ(pl);
			int reach = (int) Math.min(radio / 16 + 1, 1L << 16);
			for (int gx = Math.floorDiv(cx - reach - ox, s), gxMax = Math.floorDiv(cx + reach - ox, s); gx <= gxMax; gx++) {
				for (int gz = Math.floorDiv(cz - reach - oz, s), gzMax = Math.floorDiv(cz + reach - oz, s); gz <= gzMax; gz++) {
					ChunkPos c = pl.getPotentialStructureChunk(seed, gx * s + ox, gz * s + oz);
					BlockPos at = pl.getLocatePos(c);
					long dx = at.getX() - origen.getX(), dz = at.getZ() - origen.getZ(), d = dx * dx + dz * dz;
					if (d <= radioSq && pl.isStructureChunk(level.getChunkSource().getGeneratorState(), c.x(), c.z())) {
						InfoCommand.Found f = new InfoCommand.Found(null, c, at, d, false);
						if (!grupoDe.containsKey(f)) {
							celdas.add(f);
							grupoDe.put(f, g);
						}
					}
				}
			}
		}
		celdas.sort((a, b) -> Long.compare(a.distanceSq(), b.distanceSq()));
		Destino prevista = null;
		Viabilidad viab = null;
		for (InfoCommand.Found celda : celdas) {
			InfoCommand.Group g = grupoDe.get(celda);
			InfoCommand.Stored stored = InfoCommand.stored(scanner, celda.chunk());
			if (stored != null) {
				for (Holder<Structure> h : g.structures()) {
					if (stored.starts().contains(h.unwrapKey().orElseThrow().identifier())) {
						return new Destino(celda.pos(), true);
					}
				}
			} else if (prevista == null) {
				if (viab == null) {
					viab = new Viabilidad(level, seed);   // como en InfoCommand.search: una vez por búsqueda (cuesta preparar)
				}
				ChunkGenerator gen = level.getChunkSource().getGenerator();
				if (InfoCommand.firstViable(g, celda.chunk(), seed, level, level.registryAccess(), gen,
						level.getChunkSource().randomState(), viab.sampler, viab.sep, viab.v) != null) {
					prevista = new Destino(celda.pos(), false);
				}
			}
		}
		return prevista;
	}

	/** Lo que la búsqueda de previstas necesita preparar una vez (muestreador de este hilo y separación de las únicas). */
	private static final class Viabilidad {
		final Climate.Sampler sampler;
		final UniqueSeparation sep;
		final UniqueSeparation.Viability v;

		Viabilidad(ServerLevel level, long seed) {
			ChunkGenerator gen = level.getChunkSource().getGenerator();
			RandomState rs = level.getChunkSource().randomState();
			sampler = rs.createClimateSampler(SamplerContext.builder().enableCaches().build());
			sep = UniqueSeparation.of(level.registryAccess());
			v = sep.viability(level.registryAccess(), gen, gen.getBiomeSource(), sampler, rs, level.getStructureTemplateManager(),
					seed, level, level.dimension());
		}
	}

	/** Fuera del hilo del servidor: el centro del tramo de camino más cercano al punto de aparición. */
	private static @Nullable Destino camino(ServerLevel level, BlockPos origen) {
		BlockPos p = Caminos.tramoCercano(level, origen.getX(), origen.getZ());
		if (p == null) {
			return null;
		}
		ChunkPos c = ChunkPos.containing(p);
		return new Destino(p, InfoCommand.stored(level.getChunkSource().chunkScanner(), c) != null);
	}

	/**
	 * Mundo de la parada: el primero (el principal, luego el Nether y el End) cuyas rejillas tienen alguna estructura de
	 * la parada (las medianas y las únicas del Nether y el End solo están en las suyas). La arena y los caminos, en el
	 * principal.
	 */
	static ServerLevel nivel(MinecraftServer server, Parada parada, Map<String, String> estilos) {
		if (parada.tipo() == Revision.Tipo.ARENA || parada.tipo() == Revision.Tipo.CAMINO) {
			return server.overworld();
		}
		for (ServerLevel l : server.getAllLevels()) {
			for (InfoCommand.Group g : InfoCommand.groups(l)) {
				for (Holder<Structure> h : g.structures()) {
					if (h.unwrapKey().map(k -> deLaParada(parada, k.identifier(), estilos)).orElse(false)) {
						return l;
					}
				}
			}
		}
		return server.overworld();
	}

	/** En el hilo del servidor: un chunk cargado (aún sin guardar) puede tener ya la estructura que el disco no tiene. */
	private static @Nullable Destino confirmar(ServerLevel level, Parada parada, Destino d, Map<String, String> estilos) {
		if (d.generada()) {
			return d;
		}
		ChunkPos c = ChunkPos.containing(d.pos());
		LevelChunk chunk = level.getChunkSource().getChunkNow(c.x(), c.z());
		if (chunk == null) {
			return d;
		}
		if (parada.tipo() == Revision.Tipo.CAMINO) {
			return new Destino(d.pos(), true);
		}
		for (Map.Entry<Structure, StructureStart> e : chunk.getAllStarts().entrySet()) {
			Identifier id = level.registryAccess().lookupOrThrow(Registries.STRUCTURE).getKey(e.getKey());
			if (id != null && e.getValue().isValid() && deLaParada(parada, id, estilos)) {
				return new Destino(d.pos(), true);
			}
		}
		return d;
	}

	/**
	 * Carga (o, si el operador lo ha pedido, genera) el chunk del destino con un ticket temporal, sin bloquear el hilo del
	 * servidor, y aparece en el sitio seguro más cercano, en el mundo de la parada ({@link #nivel}).
	 */
	private static void teletransportar(CommandSourceStack src, ServerPlayer p, ServerLevel level, Destino d, Runnable despues) {
		ChunkPos c = ChunkPos.containing(d.pos());
		src.sendSuccess(() -> Textos.t("heraldia.revisar.cargando").withStyle(ChatFormatting.GRAY), false);
		level.getChunkSource().addTicketAndLoadWithRadius(TicketType.PORTAL, c, 1).thenRunAsync(() -> {
			java.util.Optional<Seguro.Sitio> sitio = Seguro.buscar(mundo(level), d.pos().getX(), d.pos().getZ(), Seguro.RADIO);
			if (sitio.isEmpty() || p.hasDisconnected()) {
				src.sendFailure(Textos.t("heraldia.revisar.sin_sitio", InfoCommand.coordinates(d.pos())));
			} else {
				Seguro.Sitio s = sitio.get();
				p.teleportTo(level, s.x() + 0.5, s.y(), s.z() + 0.5, Set.of(), p.getYRot(), p.getXRot(), true);
				p.resetFallDistance();
				LOGGER.info("Heraldia: /heraldia review: {} a {} {} {}", p.getGameProfile().name(), s.x(), s.y(), s.z());
				src.sendSuccess(() -> Textos.t("heraldia.revisar.teletransportado", s.x(), s.y(), s.z()).withStyle(ChatFormatting.GRAY), false);
			}
			despues.run();
		}, level.getServer()).exceptionally(e -> {
			BUSCANDO.remove(p.getUUID());
			LOGGER.error("Heraldia: /heraldia review: no se pudo cargar el destino", e);
			src.sendFailure(Component.literal(String.valueOf(e.getMessage())));
			return null;
		});
	}

	/** El mundo para {@link Seguro}: solo chunks ya cargados (uno sin cargar cuenta como peligroso: no se elige). */
	private static Seguro.Mundo mundo(ServerLevel level) {
		return new Seguro.Mundo() {
			@Override
			public Seguro.Celda en(int x, int y, int z) {
				LevelChunk ch = level.getChunkSource().getChunkNow(SectionPos.blockToSectionCoord(x), SectionPos.blockToSectionCoord(z));
				if (ch == null) {
					return Seguro.Celda.PELIGRO;
				}
				BlockPos pos = new BlockPos(x, y, z);
				return celda(ch.getBlockState(pos), !ch.getBlockState(pos).getCollisionShape(level, pos).isEmpty());
			}

			@Override
			public int altura(int x, int z) {
				LevelChunk ch = level.getChunkSource().getChunkNow(SectionPos.blockToSectionCoord(x), SectionPos.blockToSectionCoord(z));
				if (ch != null && level.dimensionType().hasCeiling()) { // el Nether: bajo el techo de bedrock
					return Seguro.bajoTecho(this, x, z, Suelo.NETHER_DESDE + 8, Suelo.NETHER_HASTA - 2);
				}
				return ch == null ? level.getMinY() : ch.getHeight(Heightmap.Types.MOTION_BLOCKING_NO_LEAVES, x & 15, z & 15) + 1;
			}

			@Override
			public int minY() {
				return level.getMinY();
			}

			@Override
			public int maxY() {
				return level.getMaxY() + 1;
			}
		};
	}

	/** Clasifica un bloque para {@link Seguro}. */
	static Seguro.Celda celda(BlockState s, boolean colision) {
		// sin etiquetas (BlockTags/FluidTags): así no depende de los datos cargados
		Fluid f = s.getFluidState().getType();
		if (Fluids.LAVA.isSame(f) || s.getBlock() instanceof BaseFireBlock || s.getBlock() instanceof CampfireBlock
				|| s.is(Blocks.MAGMA_BLOCK) || s.is(Blocks.CACTUS) || s.is(Blocks.POWDER_SNOW) || s.is(Blocks.SWEET_BERRY_BUSH)
				|| s.is(Blocks.WITHER_ROSE) || s.is(Blocks.POINTED_DRIPSTONE)) {
			return Seguro.Celda.PELIGRO;
		}
		if (colision) {
			return Seguro.Celda.SOLIDO;
		}
		return Fluids.WATER.isSame(f) ? Seguro.Celda.AGUA : Seguro.Celda.LIBRE;
	}

	// --- textos ---

	/** Título en pantalla y, en el chat, el nombre de la parada y la lista de qué mirar. */
	private static void cabecera(CommandSourceStack src, ServerPlayer p, List<Parada> ruta, int i, Parada parada) {
		if (!p.hasDisconnected()) {
			p.connection.send(new ClientboundSetTitlesAnimationPacket(10, 60, 20));
			p.connection.send(new ClientboundSetSubtitleTextPacket(Textos.t("heraldia.revisar.subtitulo", i + 1, ruta.size())));
			p.connection.send(new ClientboundSetTitleTextPacket(nombre(parada).withStyle(ChatFormatting.GOLD)));
		}
		src.sendSuccess(() -> Textos.t("heraldia.revisar.titulo", i + 1, ruta.size(), nombre(parada), parada.id())
				.withStyle(ChatFormatting.GOLD), false);
		src.sendSuccess(() -> Textos.t("heraldia.revisar.mirar").withStyle(ChatFormatting.YELLOW), false);
		for (String k : puntos(parada)) {
			src.sendSuccess(() -> Textos.t("heraldia.revisar.punto", Textos.t(k)), false);
		}
		Revision.Nota n = progreso(p).nota(parada.id());
		if (n != null) {
			src.sendSuccess(() -> Textos.t("heraldia.revisar.ya_marcada", estado(n.marca()),
					n.nota().isEmpty() ? Component.empty() : Textos.t("heraldia.revisar.con_nota", n.nota())).withStyle(ChatFormatting.GRAY), false);
		}
	}

	static Component estado(Marca m) {
		return Textos.t("heraldia.revisar.estado." + m.name().toLowerCase(Locale.ROOT));
	}

	/** Botones de la parada: marcar (revisada, con nota o con problema), saltar, anterior, siguiente y lista. */
	private static Component botones(boolean sinDestino) {
		MutableComponent out = Component.empty();
		if (!sinDestino) {
			out.append(boton("heraldia.revisar.boton.revisada", "/heraldia review mark checked", true, ChatFormatting.GREEN)).append(" ");
			out.append(boton("heraldia.revisar.boton.nota", "/heraldia review mark checked ", false, ChatFormatting.DARK_GREEN)).append(" ");
			out.append(boton("heraldia.revisar.boton.problema", "/heraldia review mark problem ", false, ChatFormatting.RED)).append(" ");
		}
		out.append(boton("heraldia.revisar.boton.saltar", "/heraldia review skip", true, ChatFormatting.GRAY)).append(" ");
		out.append(boton("heraldia.revisar.boton.anterior", "/heraldia review previous", true, ChatFormatting.AQUA)).append(" ");
		out.append(boton("heraldia.revisar.boton.siguiente", "/heraldia review next", true, ChatFormatting.AQUA)).append(" ");
		out.append(boton("heraldia.revisar.boton.lista", "/heraldia review list", true, ChatFormatting.GRAY));
		return out;
	}

	/** [texto] clicable: ejecuta la orden o la deja escrita para completarla (con la ayuda «.ayuda» al pasar el ratón). */
	private static Component boton(String key, String orden, boolean ejecutar, ChatFormatting color) {
		return Textos.t(key).withStyle(s -> s.withColor(color)
				.withClickEvent(ejecutar ? new ClickEvent.RunCommand(orden) : new ClickEvent.SuggestCommand(orden))
				.withHoverEvent(new HoverEvent.ShowText(Textos.t(key + ".ayuda"))));
	}

	// --- guardar ---

	/** Escribe el progreso (JSON) y el resumen (Markdown) fuera del hilo del servidor, en orden. */
	private static void guardar(MinecraftServer server) {
		Path dir = carpeta;
		if (dir == null) {
			return;
		}
		List<Parada> ruta = ruta(server);
		Revision.Registro copia = registro.copia();
		Map<String, String> nombres = new LinkedHashMap<>();
		ruta.forEach(x -> nombres.put(x.id(), nombreEs(x)));
		long ahora = System.currentTimeMillis();
		escritura = escritura.thenRunAsync(() -> {
			try {
				Revision.escribir(dir.resolve(Revision.FICHERO), Revision.json(copia));
				Revision.escribir(dir.resolve(Revision.INFORME), Revision.markdown(ruta, copia, x -> nombres.get(x.id()), ahora));
			} catch (IOException e) {
				LOGGER.warn("Heraldia: no se pudo guardar la revisión en {} ({})", dir, e.getMessage());
			}
		}, Util.ioPool());
	}
}
