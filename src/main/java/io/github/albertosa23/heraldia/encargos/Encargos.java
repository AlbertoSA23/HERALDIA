package io.github.albertosa23.heraldia.encargos;

import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.mojang.brigadier.arguments.IntegerArgumentType;
import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.arena.Arena;
import io.github.albertosa23.heraldia.caminos.Caminos;
import io.github.albertosa23.heraldia.caminos.Nombres;
import io.github.albertosa23.heraldia.caminos.Trazado;
import io.github.albertosa23.heraldia.comando.InfoCommand;
import io.github.albertosa23.heraldia.comando.Textos;
import io.github.albertosa23.heraldia.comun.Medianas;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.config.UniqueSeparation;
import io.github.albertosa23.heraldia.jefes.Fases;
import io.github.albertosa23.heraldia.minas.Minas;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.Consumer;
import java.util.stream.Collectors;
import net.fabricmc.fabric.api.attachment.v1.AttachmentRegistry;
import net.fabricmc.fabric.api.attachment.v1.AttachmentType;
import net.fabricmc.fabric.api.entity.event.v1.ServerLivingEntityEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.fabricmc.fabric.api.event.player.UseBlockCallback;
import net.minecraft.ChatFormatting;
import net.minecraft.advancements.AdvancementHolder;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.core.BlockPos;
import net.minecraft.core.HolderSet;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.chat.ClickEvent;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.HoverEvent;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.resources.Identifier;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.tags.TagKey;
import net.minecraft.util.Util;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.animal.golem.IronGolem;
import net.minecraft.world.entity.npc.villager.Villager;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.trading.MerchantOffer;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.levelgen.structure.Structure;
import net.minecraft.world.level.levelgen.structure.StructureStart;
import net.minecraft.world.phys.AABB;
import org.jspecify.annotations.Nullable;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Encargos del tablón y reputación por aldea (T38): lo que toca el juego. La lógica pura está en {@link Generador},
 * {@link Objetivos}, {@link Reputacion} y {@link Datos}.
 * <ul>
 * <li>El tablón: el atril del tablón de la plaza (el que tiene detrás al alguacil) enseña en el chat los encargos de su
 * aldea, con botones (texto clicable: vale con el cliente vanilla); y {@code /heraldia quest} desde dentro de una aldea.
 * Una aldea de Heraldia se reconoce por su estructura (la etiqueta heraldia:aldeas): también las ya generadas.</li>
 * <li>Qué hay alrededor (únicas con guardián, medianas y minas, aldeas vecinas) se busca una vez por aldea fuera del hilo
 * del servidor, con la misma búsqueda que /heraldia info nearby (no carga ni genera chunks).</li>
 * <li>Seguimiento sin trabajo por tick que recorra el mundo: la muerte de un guardián (evento), la oleada superada en la
 * arena (aviso de la arena), la llegada a un sitio (cada 2 s, solo los jugadores con un encargo de ir a un sitio) y lo
 * que se trae (al entregar).</li>
 * <li>Reputación: sube al entregar, baja al golpear o matar a un aldeano o gólem de la aldea; el descuento lo pone
 * {@code VillagerPreciosMixin} al abrir los tratos.</li>
 * </ul>
 * Todo se lee de la configuración en cada uso: encargos.activado, encargos.rotacion_dias y reputacion.activado se
 * recargan con /heraldia reload.
 */
public final class Encargos {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	public static final String ACTIVADO = "encargos.activado", ROTACION = "encargos.rotacion_dias", REPUTACION = "reputacion.activado";
	static final TagKey<Structure> ALDEAS = TagKey.create(Registries.STRUCTURE, Heraldia.id("aldeas"));
	/** El alguacil del tablón (tablon.TAG_ALGUACIL): sus tratos son fijos y no llevan descuento. */
	public static final String ALGUACIL = "heraldia_alguacil";
	/** Logros (tools/gen/encargos.py): heraldia:encargos/<id>, criterio «hecho». */
	static final String LOGRO_PRIMERO = "encargos/primero", LOGRO_DIEZ = "encargos/diez", LOGRO_AMIGO = "encargos/amigo",
			LOGRO_HEROE = "encargos/heroe";
	static final int DIEZ = 10;
	private static final Map<String, CompletableFuture<Generador.Candidatos>> CANDIDATOS = new ConcurrentHashMap<>();
	/** Tablones ya apuntados en el log (aldea y periodo), para no repetirlo en cada clic. */
	private static final Set<String> REGISTRADOS = ConcurrentHashMap.newKeySet();

	private Encargos() {
	}

	/** Los adjuntos, aparte para que los tests no registren nada al cargar la clase. */
	static final class Adjuntos {
		static final AttachmentType<Datos> JUGADOR = AttachmentRegistry.create(Heraldia.id("encargos"),
				b -> b.persistent(Datos.CODEC).copyOnDeath());
		static final AttachmentType<Mundo> MUNDO = AttachmentRegistry.create(Heraldia.id("encargos_mundo"),
				b -> b.persistent(Mundo.CODEC));

		private Adjuntos() {
		}
	}

	/** Una aldea de Heraldia: el chunk de su inicio, su estilo y su nombre. */
	record Aldea(int cx, int cz, String estilo, String nombre) {
		String clave() {
			return Reputacion.clave(cx, cz);
		}
	}

	/** Una línea en Heraldia.onInitialize. */
	public static void registrar() {
		Adjuntos.JUGADOR.identifier();
		Adjuntos.MUNDO.identifier();
		UseBlockCallback.EVENT.register((player, level, hand, hit) -> {
			if (player instanceof ServerPlayer p && level instanceof ServerLevel sl && hand == net.minecraft.world.InteractionHand.MAIN_HAND
					&& level.getBlockState(hit.getBlockPos()).is(Blocks.LECTERN)) {
				atril(p, sl, hit.getBlockPos());
			}
			return InteractionResult.PASS;     // el libro del atril se abre como siempre
		});
		ServerLivingEntityEvents.AFTER_DAMAGE.register((entity, source, base, taken, blocked) -> {
			if (taken > 0 && !entity.isDeadOrDying()) {
				ataque(entity, source, false);
			}
		});
		ServerLivingEntityEvents.AFTER_DEATH.register((entity, source) -> {
			if (Fases.esGuardian(entity.entityTags())) {
				guardianMuerto(entity, source);
			} else {
				ataque(entity, source, true);
			}
		});
		ServerTickEvents.END_SERVER_TICK.register(server -> {
			if (server.getTickCount() % Objetivos.CADA_TICKS == 0) {
				llegadas(server);
			}
		});
		ServerLifecycleEvents.SERVER_STOPPED.register(server -> {
			CANDIDATOS.clear();
			REGISTRADOS.clear();
		});
	}

	static boolean activado() {
		return HeraldiaConfig.get().getBool(ACTIVADO);
	}

	static boolean conReputacion() {
		return HeraldiaConfig.get().getBool(REPUTACION);
	}

	static Map<String, String> idioma(@Nullable ServerPlayer p) {
		return Textos.idioma(p == null ? "es_es" : p.clientInformation().language());
	}

	// --- datos ---

	public static Datos datos(Player p) {
		Datos d = p.getAttached(Adjuntos.JUGADOR);
		return d == null ? Datos.VACIO : d;
	}

	static void guardar(Player p, Datos d) {
		p.setAttached(Adjuntos.JUGADOR, d);
	}

	public static Mundo mundo(MinecraftServer server) {
		Mundo m = server.overworld().getAttached(Adjuntos.MUNDO);
		return m == null ? Mundo.VACIO : m;
	}

	static void guardarMundo(MinecraftServer server, Mundo m) {
		server.overworld().setAttached(Adjuntos.MUNDO, m);
	}

	// --- aldeas ---

	/** La aldea de Heraldia en cuya caja está la posición (solo chunks cargados; en otra dimensión, ninguna). */
	static @Nullable Aldea aldeaEn(ServerLevel level, BlockPos pos) {
		if (level.dimension() != Level.OVERWORLD || !level.isLoaded(pos)) {
			return null;
		}
		Optional<HolderSet.Named<Structure>> set = level.registryAccess().lookupOrThrow(Registries.STRUCTURE).get(ALDEAS);
		if (set.isEmpty()) {
			return null;
		}
		StructureStart start = level.structureManager().getStructureAt(pos, set.get());
		if (start == null || !start.isValid()) {
			return null;
		}
		Identifier id = level.registryAccess().lookupOrThrow(Registries.STRUCTURE).getKey(start.getStructure());
		String estilo = id == null ? "" : id.getPath();
		if (estilo.endsWith("_grande")) {
			estilo = estilo.substring(0, estilo.length() - "_grande".length());
		}
		int cx = start.getChunkPos().x(), cz = start.getChunkPos().z();
		return new Aldea(cx, cz, estilo, nombre(level.getSeed(), cx, cz));
	}

	/** Nombre de la aldea con el inicio en ese chunk: el de los carteles de los caminos ({@link Nombres}). */
	static String nombre(long seed, int cx, int cz) {
		String[] n = Nombres.de(seed, cx * 16 + 8, cz * 16 + 8);
		return n[0] + " " + n[1];
	}

	static String familia(String estilo) {
		JsonObject estilos = HeraldiaConfig.get().schema().getAsJsonObject("aldeas").getAsJsonObject("estilos");
		JsonElement f = estilos.get(estilo);
		return f == null ? "" : f.getAsString();
	}

	// --- candidatos (fuera del hilo del servidor) ---

	/** Qué hay alrededor de la aldea (sin la arena, que se mira en cada tablón): una vez por aldea y arranque. */
	private static CompletableFuture<Generador.Candidatos> candidatos(ServerLevel level, Aldea a) {
		return CANDIDATOS.computeIfAbsent(a.clave(), k -> {
			List<InfoCommand.Group> grupos = InfoCommand.groups(level);
			Set<String> conGuardian = level.getServer().getAdvancements().getAllAdvancements().stream()
					.map(h -> h.id())
					.filter(id -> id.getNamespace().equals(Heraldia.MOD_ID) && id.getPath().startsWith("unicas/") && id.getPath().endsWith("/guardian"))
					.map(id -> id.getPath().substring("unicas/".length(), id.getPath().length() - "/guardian".length()))
					.collect(Collectors.toSet());
			String familia = familia(a.estilo());
			long t0 = System.nanoTime();
			return CompletableFuture.supplyAsync(() -> buscar(level, a, grupos, conGuardian, familia), Util.backgroundExecutor())
					.whenComplete((c, e) -> {
						if (e != null) {
							LOGGER.error("Heraldia: encargos: no se pudo buscar alrededor de {}", a.nombre(), e);
							CANDIDATOS.remove(k);
						} else {
							LOGGER.info("Heraldia: encargos: alrededor de {} ({}, {}): {} guardianes, {} lugares, {} vecinas en {} ms",
									a.nombre(), a.cx(), a.cz(), c.guardianes().size(), c.lugares().size(), c.vecinas().size(),
									(System.nanoTime() - t0) / 1_000_000);
						}
					});
		});
	}

	static Generador.Candidatos buscar(ServerLevel level, Aldea a, List<InfoCommand.Group> grupos, Set<String> conGuardian, String familia) {
		BlockPos centro = new BlockPos(a.cx() * 16 + 8, 64, a.cz() * 16 + 8);
		List<InfoCommand.Group> unicas = new ArrayList<>(), otros = new ArrayList<>();
		for (InfoCommand.Group g : grupos) {
			Identifier id = g.structures().getFirst().unwrapKey().orElseThrow().identifier();
			if (UniqueSeparation.isUnique(id)) {
				unicas.add(g);
			} else if (Medianas.esMediana(id) || Minas.esMina(id)) {
				otros.add(g);
			}
		}
		List<Generador.Objetivo> guardianes = new ArrayList<>(), lugares = new ArrayList<>();
		for (InfoCommand.Found f : InfoCommand.search(level, unicas, centro, Generador.RADIO_GUARDIAN)) {
			String sid = f.structure().unwrapKey().orElseThrow().identifier().getPath().substring("unicas/".length());
			if (conGuardian.contains(sid)) {
				guardianes.add(objetivo(sid, f, centro));
			}
		}
		for (InfoCommand.Found f : InfoCommand.search(level, otros, centro, Generador.RADIO_LUGAR)) {
			lugares.add(objetivo(f.structure().unwrapKey().orElseThrow().identifier().toString(), f, centro));
		}
		List<Generador.Objetivo> vecinas = new ArrayList<>();
		for (long v : Caminos.vecinas(level, a.cx(), a.cz())) {
			int x = Trazado.px(v), z = Trazado.pz(v);
			vecinas.add(new Generador.Objetivo(nombre(level.getSeed(), Math.floorDiv(x, 16), Math.floorDiv(z, 16)), x, z,
					(int) Math.hypot(x - centro.getX(), z - centro.getZ())));
		}
		java.util.Comparator<Generador.Objetivo> cerca = java.util.Comparator.comparingInt(Generador.Objetivo::distancia);
		guardianes.sort(cerca);
		lugares.sort(cerca);
		vecinas.sort(cerca);
		return new Generador.Candidatos(familia, guardianes, lugares, vecinas, false);
	}

	private static Generador.Objetivo objetivo(String id, InfoCommand.Found f, BlockPos centro) {
		return new Generador.Objetivo(id, f.pos().getX(), f.pos().getZ(), (int) Math.sqrt(f.distanceSq()));
	}

	/** El tablón de la aldea en este periodo, cuando esté listo (en el hilo del servidor). */
	static void conTablon(ServerLevel level, Aldea a, Consumer<Component> out, Map<String, String> l, Consumer<List<Encargo>> f) {
		CompletableFuture<Generador.Candidatos> fut = candidatos(level, a);
		if (!fut.isDone()) {
			out.accept(Textos.t(l, "heraldia.encargos.preparando", a.nombre()).withStyle(ChatFormatting.GRAY));
		}
		MinecraftServer server = level.getServer();
		fut.thenAcceptAsync(c -> {
			Mundo m = mundo(server);
			int dias = HeraldiaConfig.get().getInt(ROTACION);
			long periodo = Generador.periodo(level.getGameTime(), dias);
			long inicio = Generador.inicio(periodo, dias);
			// los caídos antes de este periodo ya no salen; los que caen durante él siguen hasta que rote (ver Mundo.caidoAntes)
			List<Generador.Objetivo> vivos = c.guardianes().stream().filter(o -> !m.caidoAntes(o.id(), o.x(), o.z(), inicio)).toList();
			boolean arena = HeraldiaConfig.get().getBool("arena.activado") && Arena.centro() != null;
			Generador.Candidatos ahora = new Generador.Candidatos(c.familia(), vivos, c.lugares(), c.vecinas(), arena);
			List<Encargo> t = Generador.tablon(level.getSeed(), a.cx(), a.cz(), periodo, ahora);
			if (REGISTRADOS.add(a.clave() + "@" + periodo + "@" + t.hashCode())) {
				LOGGER.info("Heraldia: encargos: tablón de {} ({}, {}), periodo {}: {}", a.nombre(), a.cx(), a.cz(), periodo,
						t.stream().map(e -> e.hueco() + 1 + "=" + e.tipo().id() + ":" + e.objetivo() + ":" + e.cantidad() + "@" + e.x() + "," + e.z())
								.collect(Collectors.joining(" ")));
			}
			f.accept(t);
		}, server).exceptionally(e -> {
			LOGGER.error("Heraldia: encargos: tablón de {}", a.nombre(), e);
			return null;
		});
	}

	/** ¿Es de vencer a un guardián que ya ha caído? */
	static boolean caido(Mundo m, Encargo e) {
		return e.tipo() == Tipo.GUARDIAN && m.caido(e.objetivo(), e.x(), e.z());
	}

	// --- el atril del tablón ---

	/** Clic en un atril: si es el del tablón (con el alguacil detrás, dentro de una aldea), enseña el tablón en el chat. */
	static void atril(ServerPlayer p, ServerLevel level, BlockPos pos) {
		if (!activado()) {
			return;
		}
		List<Villager> alguacil = level.getEntitiesOfClass(Villager.class, new AABB(pos).inflate(2), v -> v.entityTags().contains(ALGUACIL));
		if (alguacil.isEmpty()) {
			return;
		}
		Aldea a = aldeaEn(level, pos);
		if (a != null) {
			LOGGER.info("Heraldia: encargos: {} mira el tablón de {}", p.getGameProfile().name(), a.nombre());
			Map<String, String> l = idioma(p);
			conTablon(level, a, p::sendSystemMessage, l, t -> tablon(p, a, t, p::sendSystemMessage, l));
		}
	}

	// --- textos ---

	static Component boton(Map<String, String> l, String clave, String orden, ChatFormatting color) {
		return Textos.t(l, clave).withStyle(s -> s.withColor(color).withClickEvent(new ClickEvent.RunCommand(orden))
				.withHoverEvent(new HoverEvent.ShowText(Component.literal(orden))));
	}

	static Component nivel(Map<String, String> l, Reputacion.Nivel n) {
		return Textos.t(l, "heraldia.encargos.nivel." + n.id());
	}

	/** Qué pide el encargo, con la pista del sitio vista desde (x, z): «Trae 16 × Pan», «Vence al guardián de...». */
	static MutableComponent descripcion(Map<String, String> l, Encargo e, int x, int z) {
		MutableComponent pista = e.conLugar()
				? Textos.t(l, "heraldia.encargos.pista", Textos.t(l, "heraldia.info.dir." + Objetivos.rumbo(x, z, e.x(), e.z())),
				Objetivos.aproximada(x, z, e.x(), e.z()))
				: Component.empty();
		return switch (e.tipo()) {
			case TRAER -> Textos.t(l, "heraldia.encargos.desc.traer", e.cantidad(), objeto(e.objetivo()));
			case GUARDIAN -> Textos.t(l, "heraldia.encargos.desc.guardian", Textos.t(l, "heraldia.unicas." + e.objetivo() + ".nombre"), pista);
			case EXPLORAR -> Textos.t(l, "heraldia.encargos.desc.explorar", lugar(l, e.objetivo()), pista);
			case VIAJE -> Textos.t(l, "heraldia.encargos.desc.viaje", e.objetivo(), pista);
			case ARENA -> Textos.t(l, "heraldia.encargos.desc.arena", e.cantidad());
		};
	}

	static Component objeto(String id) {
		Identifier i = Identifier.tryParse(id);
		Item it = i == null ? Items.AIR : BuiltInRegistries.ITEM.getValue(i);
		return Component.translatable(it.getDescriptionId());
	}

	/** Nombre del tipo de estructura que explorar: «posada de camino», «entrada a mina pequeña»... */
	static Component lugar(Map<String, String> l, String structureId) {
		Identifier id = Identifier.tryParse(structureId);
		if (id != null && Medianas.esMediana(id)) {
			return Textos.t(l, "heraldia.medianas." + id.getPath().split("/")[1] + ".nombre");
		}
		if (id != null && Minas.esMina(id)) {
			return Textos.t(l, "heraldia.minas." + id.getPath().split("/")[1] + ".nombre");
		}
		return Component.literal(structureId);
	}

	static Component recompensa(Map<String, String> l, Encargo e, boolean rep) {
		return rep ? Textos.t(l, "heraldia.encargos.paga", e.esmeraldas(), e.experiencia(), e.reputacion())
				: Textos.t(l, "heraldia.encargos.paga.sin_reputacion", e.esmeraldas(), e.experiencia());
	}

	/** El tablón de la aldea en el chat. */
	static void tablon(ServerPlayer p, Aldea a, List<Encargo> t, Consumer<Component> out, Map<String, String> l) {
		Datos d = datos(p);
		boolean rep = conReputacion();
		out.accept(Textos.t(l, "heraldia.encargos.tablon.titulo", a.nombre()).withStyle(ChatFormatting.GOLD));
		if (rep) {
			Reputacion.Nivel n = d.nivel(a.clave());
			out.accept(Textos.t(l, "heraldia.encargos.tablon.reputacion", nivel(l, n), d.reputacion(a.clave()))
					.withStyle(n == Reputacion.Nivel.HEROE ? ChatFormatting.LIGHT_PURPLE : ChatFormatting.YELLOW));
		}
		int x = p.getBlockX(), z = p.getBlockZ();
		Mundo m = mundo(p.level().getServer());
		for (Encargo e : t) {
			MutableComponent linea = Textos.t(l, "heraldia.encargos.linea", e.hueco() + 1, descripcion(l, e, x, z), recompensa(l, e, rep));
			linea.append(" ");
			if (d.hecho(e.id())) {
				linea.append(Textos.t(l, "heraldia.encargos.estado.entregado").withStyle(ChatFormatting.GRAY));
			} else if (d.tiene(e.id())) {
				linea.append(Textos.t(l, "heraldia.encargos.estado.aceptado").withStyle(ChatFormatting.GREEN));
			} else if (caido(m, e)) {
				linea.append(Textos.t(l, "heraldia.encargos.estado.vencido").withStyle(ChatFormatting.GRAY));
			} else {
				linea.append(boton(l, "heraldia.encargos.boton.aceptar", "/heraldia quest accept " + (e.hueco() + 1), ChatFormatting.AQUA));
			}
			out.accept(linea);
		}
		long dias = Math.max(1, (Generador.restante(p.level().getGameTime(), HeraldiaConfig.get().getInt(ROTACION)) + Generador.DIA - 1) / Generador.DIA);
		out.accept(Textos.t(l, "heraldia.encargos.tablon.rota", dias).withStyle(ChatFormatting.GRAY));
		out.accept(Component.empty().append(boton(l, "heraldia.encargos.boton.mios", "/heraldia quest list", ChatFormatting.AQUA))
				.append(" ").append(boton(l, "heraldia.encargos.boton.entregar", "/heraldia quest turnin", ChatFormatting.GREEN)));
	}

	// --- comandos: /heraldia quest [list | accept <number> | abandon <number> | turnin] ---

	public static LiteralArgumentBuilder<CommandSourceStack> nodo() {
		return Commands.literal("quest")
				.executes(ctx -> principal(ctx))
				.then(Commands.literal("list").executes(Encargos::lista))
				.then(Commands.literal("accept").then(Commands.argument("number", IntegerArgumentType.integer(1, Generador.MAX))
						.executes(ctx -> aceptar(ctx, IntegerArgumentType.getInteger(ctx, "number")))))
				.then(Commands.literal("abandon").then(Commands.argument("number", IntegerArgumentType.integer(1, Datos.MAX_ACTIVOS))
						.executes(ctx -> abandonar(ctx, IntegerArgumentType.getInteger(ctx, "number")))))
				.then(Commands.literal("turnin").executes(Encargos::entregar));
	}

	private record Uso(ServerPlayer p, ServerLevel level, Map<String, String> l, Consumer<Component> out) {
	}

	/** El jugador que ejecuta la orden (la respuesta va a la fuente: también sale en la consola con «execute as»). */
	private static @Nullable Uso uso(CommandContext<CommandSourceStack> ctx) throws CommandSyntaxException {
		CommandSourceStack src = ctx.getSource();
		ServerPlayer p = src.getPlayerOrException();
		Map<String, String> l = idioma(p);
		if (!activado()) {
			src.sendFailure(Textos.t(l, "heraldia.encargos.desactivados"));
			return null;
		}
		return new Uso(p, p.level(), l, c -> src.sendSuccess(() -> c, false));
	}

	private static @Nullable Aldea aqui(Uso u) {
		Aldea a = aldeaEn(u.level(), u.p().blockPosition());
		if (a == null) {
			u.out().accept(Textos.t(u.l(), "heraldia.encargos.fuera").withStyle(ChatFormatting.RED));
		}
		return a;
	}

	private static int principal(CommandContext<CommandSourceStack> ctx) throws CommandSyntaxException {
		Uso u = uso(ctx);
		if (u == null) {
			return 0;
		}
		Aldea a = aldeaEn(u.level(), u.p().blockPosition());
		if (a == null) {
			return lista(ctx);
		}
		conTablon(u.level(), a, u.out(), u.l(), t -> tablon(u.p(), a, t, u.out(), u.l()));
		return 1;
	}

	private static int lista(CommandContext<CommandSourceStack> ctx) throws CommandSyntaxException {
		Uso u = uso(ctx);
		if (u == null) {
			return 0;
		}
		Datos d = datos(u.p());
		Map<String, String> l = u.l();
		u.out().accept(Textos.t(l, "heraldia.encargos.mios.titulo", d.activos().size(), Datos.MAX_ACTIVOS, d.completados())
				.withStyle(ChatFormatting.GOLD));
		int x = u.p().getBlockX(), z = u.p().getBlockZ();
		long seed = u.level().getSeed();
		Mundo m = mundo(u.level().getServer());
		for (int i = 0; i < d.activos().size(); i++) {
			Datos.Activo a = d.activos().get(i);
			Encargo e = a.encargo();
			String estado = a.cumplido() ? "cumplido" : caido(m, e) ? "caido" : "en_curso";
			MutableComponent linea = Textos.t(l, "heraldia.encargos.mio", i + 1, descripcion(l, e, x, z),
					nombre(seed, e.aldeaX(), e.aldeaZ()), Textos.t(l, "heraldia.encargos.estado." + estado));
			linea.append(" ").append(boton(l, "heraldia.encargos.boton.abandonar", "/heraldia quest abandon " + (i + 1), ChatFormatting.RED));
			u.out().accept(linea);
		}
		if (d.activos().isEmpty()) {
			u.out().accept(Textos.t(l, "heraldia.encargos.mios.ninguno").withStyle(ChatFormatting.GRAY));
		}
		if (conReputacion()) {
			for (Map.Entry<String, Integer> r : d.reputacion().entrySet()) {
				int[] c = Reputacion.chunk(r.getKey());
				if (c != null && r.getValue() != 0) {
					u.out().accept(Textos.t(l, "heraldia.encargos.mios.reputacion", nombre(seed, c[0], c[1]),
							nivel(l, Reputacion.nivel(r.getValue())), r.getValue()));
				}
			}
		}
		return d.activos().size();
	}

	private static int aceptar(CommandContext<CommandSourceStack> ctx, int n) throws CommandSyntaxException {
		Uso u = uso(ctx);
		Aldea a = u == null ? null : aqui(u);
		if (a == null) {
			return 0;
		}
		conTablon(u.level(), a, u.out(), u.l(), t -> {
			if (n > t.size()) {
				u.out().accept(Textos.t(u.l(), "heraldia.encargos.no_existe", n, t.size()).withStyle(ChatFormatting.RED));
				return;
			}
			Encargo e = t.get(n - 1);
			Datos d = datos(u.p());
			String motivo = caido(mundo(u.level().getServer()), e) ? "caido" : d.noAceptable(e);
			if (motivo != null) {
				u.out().accept(Textos.t(u.l(), "heraldia.encargos.no_aceptable." + motivo, Datos.MAX_ACTIVOS).withStyle(ChatFormatting.RED));
				return;
			}
			guardar(u.p(), d.aceptar(e));
			u.out().accept(Textos.t(u.l(), "heraldia.encargos.aceptado", descripcion(u.l(), e, u.p().getBlockX(), u.p().getBlockZ()))
					.withStyle(ChatFormatting.GREEN));
			LOGGER.info("Heraldia: encargos: {} acepta {} ({} {} {} en {}, {})", u.p().getGameProfile().name(), e.id(), e.tipo().id(),
					e.objetivo(), e.cantidad(), e.x(), e.z());
		});
		return 1;
	}

	private static int abandonar(CommandContext<CommandSourceStack> ctx, int n) throws CommandSyntaxException {
		Uso u = uso(ctx);
		if (u == null) {
			return 0;
		}
		Datos d = datos(u.p());
		if (n > d.activos().size()) {
			u.out().accept(Textos.t(u.l(), "heraldia.encargos.no_existe", n, d.activos().size()).withStyle(ChatFormatting.RED));
			return 0;
		}
		Encargo e = d.activos().get(n - 1).encargo();
		guardar(u.p(), d.abandonar(n - 1));
		u.out().accept(Textos.t(u.l(), "heraldia.encargos.abandonado", descripcion(u.l(), e, u.p().getBlockX(), u.p().getBlockZ())));
		return 1;
	}

	private static int entregar(CommandContext<CommandSourceStack> ctx) throws CommandSyntaxException {
		Uso u = uso(ctx);
		Aldea a = u == null ? null : aqui(u);
		if (a == null) {
			return 0;
		}
		ServerPlayer p = u.p();
		Datos d = datos(p);
		boolean rep = conReputacion();
		int entregados = 0;
		for (Datos.Activo act : List.copyOf(d.activos())) {
			Encargo e = act.encargo();
			if (!e.aldea().equals(a.clave())) {
				continue;
			}
			Item item = e.tipo() == Tipo.TRAER ? itemDe(e.objetivo()) : null;
			int tiene = item == null ? 0 : contar(p.getInventory(), item);
			if (!Objetivos.entregable(act, tiene)) {
				if (e.tipo() == Tipo.TRAER) {
					u.out().accept(Textos.t(u.l(), "heraldia.encargos.faltan", tiene, e.cantidad(), objeto(e.objetivo())).withStyle(ChatFormatting.YELLOW));
				}
				continue;
			}
			if (item != null) {
				quitar(p.getInventory(), item, e.cantidad());
			}
			Reputacion.Nivel antes = d.nivel(a.clave());
			d = d.entregar(e.id(), rep);
			pagar(p, e);
			entregados++;
			u.out().accept(Textos.t(u.l(), "heraldia.encargos.entregado", descripcion(u.l(), e, p.getBlockX(), p.getBlockZ()),
					recompensa(u.l(), e, rep)).withStyle(ChatFormatting.GREEN));
			Reputacion.Nivel despues = d.nivel(a.clave());
			if (rep && despues != antes) {
				u.out().accept(Textos.t(u.l(), "heraldia.encargos.sube", a.nombre(), nivel(u.l(), despues)).withStyle(ChatFormatting.LIGHT_PURPLE));
			}
			LOGGER.info("Heraldia: encargos: {} entrega {} en {}: {} esmeraldas, {} de experiencia; reputación {} ({})",
					p.getGameProfile().name(), e.id(), a.nombre(), e.esmeraldas(), e.experiencia(), d.reputacion(a.clave()), despues.id());
		}
		if (entregados == 0) {
			u.out().accept(Textos.t(u.l(), "heraldia.encargos.nada").withStyle(ChatFormatting.GRAY));
			return 0;
		}
		guardar(p, d);
		MinecraftServer server = p.level().getServer();
		Mundo m = mundo(server);
		for (int i = 0; i < entregados; i++) {
			m = m.completado();
		}
		guardarMundo(server, m);
		logros(p, d);
		return entregados;
	}

	static @Nullable Item itemDe(String id) {
		Identifier i = Identifier.tryParse(id);
		return i == null ? null : BuiltInRegistries.ITEM.getOptional(i).orElse(null);
	}

	/** Cuántos de ese objeto lleva en el inventario (sin mirar el cursor ni la mesa de crafteo). */
	static int contar(Inventory inv, Item item) {
		int n = 0;
		for (int i = 0; i < inv.getContainerSize(); i++) {
			ItemStack s = inv.getItem(i);
			if (s.is(item)) {
				n += s.getCount();
			}
		}
		return n;
	}

	static void quitar(Inventory inv, Item item, int cuantos) {
		for (int i = 0; i < inv.getContainerSize() && cuantos > 0; i++) {
			ItemStack s = inv.getItem(i);
			if (s.is(item)) {
				int q = Math.min(cuantos, s.getCount());
				s.shrink(q);
				cuantos -= q;
			}
		}
		inv.setChanged();
	}

	static void pagar(ServerPlayer p, Encargo e) {
		p.getInventory().placeItemBackInInventory(new ItemStack(Items.EMERALD, e.esmeraldas()), net.minecraft.util.Prediction.SERVER_ONLY);   // al suelo si no cabe
		p.giveExperiencePoints(e.experiencia());
		io.github.albertosa23.heraldia.tesoro.Tesoro.recompensa(p);   // a veces, un fragmento de mapa del tesoro (T40)
	}

	static void logros(ServerPlayer p, Datos d) {
		if (d.completados() >= 1) {
			logro(p, LOGRO_PRIMERO);
		}
		if (d.completados() >= DIEZ) {
			logro(p, LOGRO_DIEZ);
		}
		if (d.aldeasCon(Reputacion.Nivel.AMIGO) > 0) {
			logro(p, LOGRO_AMIGO);
		}
		if (d.aldeasCon(Reputacion.Nivel.HEROE) > 0) {
			logro(p, LOGRO_HEROE);
		}
	}

	static void logro(ServerPlayer p, String ruta) {
		AdvancementHolder h = p.level().getServer().getAdvancements().get(Heraldia.id(ruta));
		if (h != null) {
			p.getAdvancements().award(h, "hecho");
		}
	}

	// --- seguimiento ---

	/** Un guardián ha muerto: se apunta y cumple los encargos de quien lo mata y de los que están cerca. */
	static void guardianMuerto(LivingEntity e, DamageSource source) {
		if (!(e.level() instanceof ServerLevel level)) {
			return;
		}
		String sid = Fases.unica(e.entityTags());
		if (sid == null) {
			return;
		}
		int x = e.getBlockX(), z = e.getBlockZ();
		MinecraftServer server = level.getServer();
		guardarMundo(server, mundo(server).cae(sid, x, z, level.getGameTime()));
		if (!activado()) {
			return;
		}
		List<ServerPlayer> quienes = new ArrayList<>(level.getEntitiesOfClass(ServerPlayer.class,
				new AABB(e.blockPosition()).inflate(Objetivos.RADIO_PARTICIPA)));
		if (source.getEntity() instanceof ServerPlayer k && !quienes.contains(k)) {
			quienes.add(k);
		}
		for (ServerPlayer p : quienes) {
			cumplir(p, en -> Objetivos.guardian(en, sid, x, z));
		}
	}

	/** Cada 2 s: los jugadores con un encargo de ir a un sitio, ¿han llegado? */
	static void llegadas(MinecraftServer server) {
		if (!activado()) {
			return;
		}
		for (ServerPlayer p : server.overworld().players()) {
			Datos d = p.getAttached(Adjuntos.JUGADOR);
			if (d != null && Objetivos.esperaLlegada(d.activos())) {
				int x = p.getBlockX(), z = p.getBlockZ();
				cumplir(p, e -> Objetivos.llegada(e, x, z));
			}
		}
	}

	/** Aviso de la arena: el jugador ha superado la oleada {@code n}. */
	public static void oleadaSuperada(ServerPlayer p, int n) {
		if (activado()) {
			cumplir(p, e -> Objetivos.oleada(e, n));
		}
	}

	static void cumplir(ServerPlayer p, java.util.function.Predicate<Encargo> cond) {
		Datos d = p.getAttached(Adjuntos.JUGADOR);
		if (d == null) {
			return;
		}
		Datos nuevo = d.cumplir(cond);
		if (nuevo == d) {
			return;
		}
		guardar(p, nuevo);
		Map<String, String> l = idioma(p);
		long seed = p.level().getSeed();
		for (int i = 0; i < nuevo.activos().size(); i++) {
			if (nuevo.activos().get(i).cumplido() && !d.activos().get(i).cumplido()) {
				Encargo e = nuevo.activos().get(i).encargo();
				p.sendSystemMessage(Textos.t(l, "heraldia.encargos.cumplido", descripcion(l, e, p.getBlockX(), p.getBlockZ()),
						nombre(seed, e.aldeaX(), e.aldeaZ())).withStyle(ChatFormatting.GREEN));
				LOGGER.info("Heraldia: encargos: {} cumple {} ({})", p.getGameProfile().name(), e.id(), e.tipo().id());
			}
		}
	}

	// --- reputación ---

	/** Un jugador golpea o mata a un aldeano o a un gólem de hierro dentro de una aldea de Heraldia: baja su reputación. */
	static void ataque(LivingEntity e, DamageSource source, boolean muerte) {
		boolean golem = e instanceof IronGolem;
		if (!(golem || e instanceof Villager) || !(source.getEntity() instanceof ServerPlayer p) || !(e.level() instanceof ServerLevel level)
				|| !conReputacion()) {
			return;
		}
		Aldea a = aldeaEn(level, e.blockPosition());
		if (a != null) {
			sumar(p, a, Reputacion.ataque(golem, muerte), (muerte ? "mata" : "golpea") + " a un " + (golem ? "gólem" : "aldeano"));
		}
	}

	// --- API para otros sistemas (p. ej. las caravanas) ---

	/**
	 * Suma (o resta) reputación del jugador con la aldea de Heraldia cuyo inicio está en el chunk (chunkX, chunkZ), sin
	 * salirse de [{@link Reputacion#MIN}, {@link Reputacion#MAX}]: avisa al jugador si cambia de nivel, concede los
	 * logros de amigo y héroe y lo apunta en el log con {@code motivo}. Sin efecto (devuelve la reputación que tenía) con
	 * reputacion.activado a false. En el hilo del servidor. Devuelve la reputación nueva.
	 */
	public static int sumarReputacion(ServerPlayer p, int chunkX, int chunkZ, int puntos, String motivo) {
		Aldea a = new Aldea(chunkX, chunkZ, "", nombre(p.level().getSeed(), chunkX, chunkZ));
		if (!conReputacion()) {
			return datos(p).reputacion(a.clave());
		}
		return sumar(p, a, puntos, motivo);
	}

	/** Como {@link #sumarReputacion(ServerPlayer, int, int, int, String)} con la aldea en cuya caja está {@code pos};
	 *  devuelve null si ahí no hay ninguna aldea de Heraldia (o el chunk no está cargado). */
	public static @Nullable Integer sumarReputacion(ServerPlayer p, ServerLevel level, BlockPos pos, int puntos, String motivo) {
		Aldea a = aldeaEn(level, pos);
		return a == null ? null : sumarReputacion(p, a.cx(), a.cz(), puntos, motivo);
	}

	/** Reputación del jugador con la aldea del chunk (chunkX, chunkZ) (0 si nunca ha tratado con ella). */
	public static int reputacion(Player p, int chunkX, int chunkZ) {
		return datos(p).reputacion(Reputacion.clave(chunkX, chunkZ));
	}

	/** El chunk del inicio de la aldea de Heraldia en cuya caja está {@code pos}, o null (para usar con lo de arriba). */
	public static net.minecraft.world.level.@Nullable ChunkPos aldea(ServerLevel level, BlockPos pos) {
		Aldea a = aldeaEn(level, pos);
		return a == null ? null : new net.minecraft.world.level.ChunkPos(a.cx(), a.cz());
	}

	static int sumar(ServerPlayer p, Aldea a, int puntos, String motivo) {
		Datos d = datos(p);
		Reputacion.Nivel antes = d.nivel(a.clave());
		Datos nuevo = d.sumarReputacion(a.clave(), puntos);
		guardar(p, nuevo);
		Reputacion.Nivel despues = nuevo.nivel(a.clave());
		if (despues != antes) {
			Map<String, String> l = idioma(p);
			p.sendSystemMessage(despues.compareTo(antes) > 0
					? Textos.t(l, "heraldia.encargos.sube", a.nombre(), nivel(l, despues)).withStyle(ChatFormatting.LIGHT_PURPLE)
					: Textos.t(l, "heraldia.encargos.baja", a.nombre(), nivel(l, despues)).withStyle(ChatFormatting.RED));
			logros(p, nuevo);
		}
		LOGGER.info("Heraldia: encargos: {} {} de {}: reputación {}", p.getGameProfile().name(), motivo, a.nombre(),
				nuevo.reputacion(a.clave()));
		return nuevo.reputacion(a.clave());
	}

	/**
	 * Lo llama VillagerPreciosMixin al final de {@code Villager.updateSpecialPrices} (al abrir los tratos): rebaja cada
	 * oferta según la reputación del jugador con la aldea del aldeano y le saluda. Sin efecto fuera de una aldea, con la
	 * reputación desactivada, con el alguacil o si el jugador ya tiene Héroe de la aldea.
	 */
	public static void precios(Villager v, Player player) {
		if (!(player instanceof ServerPlayer p) || !(v.level() instanceof ServerLevel level) || !conReputacion()
				|| v.entityTags().contains(ALGUACIL)) {
			return;
		}
		Datos d = p.getAttached(Adjuntos.JUGADOR);
		if (d == null || d.reputacion().isEmpty()) {
			return;
		}
		Aldea a = aldeaEn(level, v.blockPosition());
		if (a == null) {
			return;
		}
		Reputacion.Nivel n = d.nivel(a.clave());
		boolean heroe = p.hasEffect(MobEffects.HERO_OF_THE_VILLAGE);
		int total = 0;
		for (MerchantOffer o : v.getOffers()) {
			int r = Reputacion.rebaja(n, o.getBaseCostA().getCount(), true, heroe);
			o.addToSpecialPriceDiff(r);
			total += r;
		}
		if (n != Reputacion.Nivel.DESCONOCIDO) {
			p.sendOverlayMessage(Textos.t(idioma(p), "heraldia.encargos.saludo." + n.id(), a.nombre()).withStyle(ChatFormatting.GREEN));
			level.sendParticles(ParticleTypes.HAPPY_VILLAGER, v.getX(), v.getY() + 1.8, v.getZ(), 4, 0.3, 0.3, 0.3, 0);
			LOGGER.debug("Heraldia: encargos: {} en {}: {} ({} en total)", p.getGameProfile().name(), a.nombre(), n.id(), total);
		}
	}

	/** Para /heraldia status: entregados entre todos y por el jugador, y sus aldeas amigas y de las que es héroe. */
	public static List<Component> estado(MinecraftServer server, @Nullable ServerPlayer p) {
		List<Component> out = new ArrayList<>();
		HeraldiaConfig cfg = HeraldiaConfig.get();
		if (!cfg.getBool(ACTIVADO)) {
			out.add(Textos.t("heraldia.estado.encargos.no"));
			return out;
		}
		out.add(Textos.t("heraldia.estado.encargos", mundo(server).completados()));
		if (p != null) {
			Datos d = datos(p);
			out.add(cfg.getBool(REPUTACION)
					? Textos.t("heraldia.estado.encargos.tuyos", d.completados(), d.aldeasCon(Reputacion.Nivel.AMIGO), d.aldeasCon(Reputacion.Nivel.HEROE))
					: Textos.t("heraldia.estado.encargos.tuyos.sin_reputacion", d.completados()));
		}
		return out;
	}
}
