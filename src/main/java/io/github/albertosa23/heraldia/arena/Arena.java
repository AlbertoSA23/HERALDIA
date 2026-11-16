package io.github.albertosa23.heraldia.arena;

import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;
import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.comando.Textos;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import java.util.Optional;
import java.util.concurrent.CompletableFuture;
import net.fabricmc.fabric.api.command.v2.CommandRegistrationCallback;
import net.fabricmc.fabric.api.entity.event.v1.ServerLivingEntityEvents;
import net.fabricmc.fabric.api.entity.event.v1.ServerPlayerEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerEntityEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.fabricmc.fabric.api.event.player.PlayerBlockBreakEvents;
import net.fabricmc.fabric.api.event.player.UseBlockCallback;
import net.fabricmc.fabric.api.event.player.UseItemCallback;
import net.fabricmc.fabric.api.loot.v3.LootTableEvents;
import net.minecraft.ChatFormatting;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.core.BlockPos;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.chat.ClickEvent;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.permissions.Permissions;
import net.minecraft.util.Util;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.BucketItem;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.chunk.ChunkGenerator;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.level.levelgen.RandomState;
import net.minecraft.world.level.storage.loot.parameters.LootContextParams;
import org.jspecify.annotations.Nullable;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Arena de oleadas cerca del spawn (T31). Una por mundo, en el mundo principal; la colocan los operadores
 * (/heraldia arena colocar, con confirmación) o se genera sola en un mundo nuevo (arena.generar_en_mundos_nuevos).
 * <ul>
 * <li>Protección ({@link #protegido}): la caja de la plantilla, una AABB de enteros en memoria ({@link Zona}). Ningún
 * jugador que no sea operador puede romper, colocar ni usar bloques (salvo la campana), ni usar cubos cerca; las
 * explosiones, los pistones y los endermen que dejan bloques no la tocan (mixins con salida temprana barata); el fuego
 * y los endermen que cogen bloques, por diseño (sus materiales no arden ni se pueden coger).</li>
 * <li>Partidas: {@link Juego} y {@link Partida}.</li>
 * <li>Obras (colocar, mover, quitar): {@link Obras}, un chunk por tick.</li>
 * </ul>
 * Sin trabajo por tick si no hay partida, obra ni propuesta (tres comprobaciones de un campo).
 */
public final class Arena {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	/** Etiqueta (Tags) de los mobs de la arena. */
	public static final String TAG = "heraldia_arena";
	/** Un mundo es nuevo (la arena se genera sola) si al arrancar por primera vez con el mod no ha pasado este tiempo. */
	static final long MUNDO_NUEVO_TICKS = 1200;
	private static final int PROPUESTA_TICKS = 6000, CADA_PARTICULAS = 20, RADIO_CUBOS = 6;

	private static @Nullable Plano plano;
	private static volatile @Nullable Zona zona;
	private static @Nullable ServerLevel nivel;
	private static boolean activada;

	/** Un sitio propuesto que espera confirmación (o se coloca solo, en un mundo nuevo). */
	private record Propuesta(Zona zona, Sitio.Eleccion eleccion, long hasta, @Nullable ServerPlayer quien) {
	}

	private static @Nullable Propuesta propuesta;

	private Arena() {
	}

	public static void registrar() {
		plano = Plano.delJar();
		Guardada.Tipo.ARENA.identifier();   // registra los adjuntos al arrancar
		ServerLifecycleEvents.SERVER_STARTED.register(Arena::alArrancar);
		ServerLifecycleEvents.SERVER_STOPPING.register(server -> {
			Juego.alParar();
			zona = null;
			nivel = null;
			propuesta = null;
		});
		ServerTickEvents.END_SERVER_TICK.register(Arena::tick);
		ServerEntityEvents.ENTITY_LOAD.register(Juego::alCargar);
		ServerLivingEntityEvents.AFTER_DEATH.register((entity, source) -> Juego.alMorir(entity));
		ServerPlayerEvents.COPY_FROM.register(Juego::copiar);
		ServerPlayerEvents.AFTER_RESPAWN.register((viejo, nuevo, vivo) -> Juego.reaparecer(nuevo));
		PlayerBlockBreakEvents.BEFORE.register((level, player, pos, state, be) -> !protegido(level, pos, player));
		UseBlockCallback.EVENT.register(Arena::usarBloque);
		UseItemCallback.EVENT.register(Arena::usarObjeto);
		LootTableEvents.MODIFY_DROPS.register((table, context, drops) -> {
			Entity e = context.getOptional(LootContextParams.THIS_ENTITY);
			if (e != null && !drops.isEmpty() && e.entityTags().contains(TAG)) {
				drops.clear();                       // los mobs de la arena no sueltan nada
			}
		});
		CommandRegistrationCallback.EVENT.register((dispatcher, access, environment) -> dispatcher.register(comando()));
	}

	static Plano plano() {
		return plano;
	}

	static @Nullable Zona zona() {
		return zona;
	}

	static @Nullable ServerLevel nivel() {
		return nivel;
	}

	static void fijarZona(@Nullable Zona z) {
		zona = z;
	}

	/** Guarda en el mundo la arena colocada (o ninguna) y empieza (o deja) de protegerla. */
	static void guardar(ServerLevel level, @Nullable Zona z) {
		Guardada g = Optional.ofNullable(level.getAttached(Guardada.Tipo.ARENA)).orElse(Guardada.VACIA);
		level.setAttached(Guardada.Tipo.ARENA, g.conOrigen(z == null ? null : new BlockPos(z.ox(), z.oy(), z.oz())));
		nivel = level;
		zona = z;
	}

	// --- protección ---

	/** ¿Está protegido este bloque frente a quien actúa (null: explosión, pistón, enderman)? Salida temprana barata. */
	public static boolean protegido(Level level, BlockPos pos, @Nullable Player quien) {
		Zona z = zona;
		if (z == null || level != nivel || !z.contiene(pos.getX(), pos.getY(), pos.getZ())) {
			return false;
		}
		return z.protegido(pos.getX(), pos.getY(), pos.getZ(), quien != null && esOperador(quien));
	}

	public static boolean protegido(Level level, BlockPos pos) {
		return protegido(level, pos, null);
	}

	/** ¿Hay arena en este mundo? (salida temprana de los mixins) */
	public static boolean hayArena(Level level) {
		return zona != null && level == nivel;
	}

	/** Para ArenaJugadorMixin: ¿conserva el inventario al morir (cae en el ruedo durante una partida)? */
	public static boolean conservaAlMorir(Player p) {
		if (zona == null) {
			if (p.hasAttached(Guardada.Tipo.CONSERVAR)) {
				p.removeAttached(Guardada.Tipo.CONSERVAR);
			}
			return false;
		}
		return Juego.conservaAlMorir(p);
	}

	/** Para ArenaJugadorMixin: ¿está conservando (no suelta experiencia)? */
	public static boolean conservando(Player p) {
		return Juego.conservando(p);
	}

	/** Para ArenaExperienciaMixin: experiencia de un mob de la arena (arena.experiencia_porcentaje % de la vanilla). */
	public static int experiencia(int vanilla, double azar) {
		int r = Oleadas.experiencia(vanilla, Juego.experienciaPct(), azar);
		Juego.sumarExperiencia(vanilla, r);
		return r;
	}

	static boolean esOperador(Player p) {
		return p instanceof ServerPlayer sp && sp.permissions().hasPermission(Permissions.COMMANDS_GAMEMASTER);
	}

	private static InteractionResult usarBloque(Player player, Level level, net.minecraft.world.InteractionHand hand,
			net.minecraft.world.phys.BlockHitResult hit) {
		Zona z = zona;
		if (z == null || level != nivel || !(player instanceof ServerPlayer p)) {
			return InteractionResult.PASS;
		}
		BlockPos pos = hit.getBlockPos();
		BlockPos junto = pos.relative(hit.getDirection());
		boolean dentro = z.contiene(pos.getX(), pos.getY(), pos.getZ()) || z.contiene(junto.getX(), junto.getY(), junto.getZ());
		if (!dentro) {
			return InteractionResult.PASS;
		}
		if (z.esCampana(pos.getX(), pos.getY(), pos.getZ()) && !p.isSecondaryUseActive()) {
			if (activada && hand == net.minecraft.world.InteractionHand.MAIN_HAND) {
				Juego.campana(p, z);
			}
			return InteractionResult.PASS;          // y la campana suena (vanilla)
		}
		if (esOperador(p)) {
			return InteractionResult.PASS;
		}
		negar(p, "heraldia.arena.prohibido");
		return InteractionResult.FAIL;
	}

	private static InteractionResult usarObjeto(Player player, Level level, net.minecraft.world.InteractionHand hand) {
		Zona z = zona;
		if (z == null || level != nivel || !(player instanceof ServerPlayer p) || esOperador(p)) {
			return InteractionResult.PASS;
		}
		ItemStack s = p.getItemInHand(hand);
		if (s.getItem() instanceof BucketItem && z.cerca(p.getBlockX(), p.getBlockY(), p.getBlockZ(), RADIO_CUBOS)) {
			negar(p, "heraldia.arena.prohibido");
			return InteractionResult.FAIL;
		}
		if (s.is(Items.ENDER_PEARL) && Juego.partida().estado() != Partida.Estado.LIBRE && z.enRuedo(p.getX(), p.getY(), p.getZ())) {
			negar(p, "heraldia.arena.perla");
			return InteractionResult.FAIL;
		}
		return InteractionResult.PASS;
	}

	private static void negar(ServerPlayer p, String clave) {
		p.sendOverlayMessage(Textos.t(clave).withStyle(ChatFormatting.RED));
		p.inventoryMenu.sendAllDataToRemote();      // el cliente pudo dar por gastado el objeto
		LOGGER.debug("Heraldia: arena: {} para {}", clave, p.getGameProfile().name());
	}

	// --- arranque y tick ---

	private static void alArrancar(MinecraftServer server) {
		HeraldiaConfig cfg = HeraldiaConfig.get();
		activada = cfg.getBool("arena.activado");
		Juego.configurar(cfg);
		ServerLevel ow = server.overworld();
		Guardada g = Optional.ofNullable(ow.getAttached(Guardada.Tipo.ARENA)).orElse(Guardada.VACIA);
		if (!activada) {
			LOGGER.info("Heraldia: arena: desactivada (arena.activado = false)");
			return;
		}
		Marcador.objetivo(server);
		if (g.origen().isPresent()) {
			BlockPos o = g.origen().get();
			nivel = ow;
			zona = new Zona(o.getX(), o.getY(), o.getZ(), plano);
			Juego.puerta(ow, zona, false);           // por si el servidor se paró en mitad de una partida
			LOGGER.info("Heraldia: arena: en {} {} {}", zona.columnaX(), zona.sueloY(), zona.columnaZ());
		} else if (!g.decidida()) {
			boolean nuevo = ow.getGameTime() < MUNDO_NUEVO_TICKS;
			ow.setAttached(Guardada.Tipo.ARENA, g.decidir());
			if (nuevo && cfg.getBool("arena.generar_en_mundos_nuevos")) {
				LOGGER.info("Heraldia: arena: mundo nuevo: se busca sitio para la arena");
				buscar(server, null, true);
			} else {
				LOGGER.info("Heraldia: arena: mundo existente: sin arena hasta que un operador la coloque (/heraldia arena colocar)");
			}
		}
	}

	private static void tick(MinecraftServer server) {
		Obras.tick(server);
		Juego.tick(server);
		Propuesta pr = propuesta;
		if (pr != null && server.getTickCount() % CADA_PARTICULAS == 0) {
			if (server.overworld().getGameTime() > pr.hasta()) {
				propuesta = null;
			} else {
				particulas(server.overworld(), pr);
			}
		}
	}

	/** Marca el sitio propuesto: columnas de partículas en las esquinas y el centro, visibles de lejos. */
	private static void particulas(ServerLevel level, Propuesta pr) {
		Zona z = pr.zona();
		int[][] cols = {{z.minX(), z.minZ()}, {z.maxX(), z.minZ()}, {z.minX(), z.maxZ()}, {z.maxX(), z.maxZ()},
				{z.columnaX(), z.columnaZ()}};
		for (ServerPlayer p : level.players()) {
			if (!esOperador(p)) {
				continue;
			}
			for (int[] c : cols) {
				for (int y = 1; y <= 24; y += 2) {
					level.sendParticles(p, ParticleTypes.END_ROD, true, true, c[0] + 0.5, z.sueloY() + y, c[1] + 0.5, 1, 0, 0, 0, 0);
				}
			}
		}
	}

	// --- búsqueda de sitio ---

	/** Busca sitio fuera del hilo del servidor; al tenerlo, lo propone (o lo coloca, en un mundo nuevo). */
	private static void buscar(MinecraftServer server, @Nullable ServerPlayer quien, boolean colocarSolo) {
		ServerLevel ow = server.overworld();
		BlockPos spawn = ow.getRespawnData().pos();
		ChunkGenerator gen = ow.getChunkSource().getGenerator();
		RandomState rs = ow.getChunkSource().randomState();
		Sitio.Alturas alturas = new Sitio.Alturas() {
			@Override
			public int superficie(int x, int z) {
				return gen.getBaseHeight(x, z, Heightmap.Types.WORLD_SURFACE_WG, ow, rs);
			}

			@Override
			public int fondo(int x, int z) {
				return gen.getBaseHeight(x, z, Heightmap.Types.OCEAN_FLOOR_WG, ow, rs);
			}

			@Override
			public boolean ocupado(int chunkX, int chunkZ) {
				return Estructuras.ocupado(ow, chunkX, chunkZ);
			}
		};
		Plano pl = plano;
		int lado = Math.max(pl.tamano()[0], pl.tamano()[2]);
		int bajo = pl.suelo(), alto = pl.tamano()[1] - pl.suelo();
		long t0 = System.nanoTime();
		CompletableFuture.supplyAsync(() -> Sitio.elegir(spawn.getX(), spawn.getZ(), lado, bajo, alto, ow.getMinY(), ow.getMaxY(), alturas),
						Util.backgroundExecutor())
				.thenAcceptAsync(res -> {
					long ms = (System.nanoTime() - t0) / 1_000_000;
					if (res.isEmpty()) {
						LOGGER.info("Heraldia: arena: sin sitio llano a {}-{} bloques del spawn ({} ms)", Sitio.RADIO_MIN, Sitio.RADIO_MAX, ms);
						if (quien != null) {
							quien.sendSystemMessage(Textos.t("heraldia.arena.sin_sitio").withStyle(ChatFormatting.RED));
						}
						return;
					}
					Sitio.Eleccion e = res.get();
					Zona z = Zona.centrada(e.x(), e.z(), e.suelo(), pl);
					LOGGER.info("Heraldia: arena: sitio propuesto en {} {} {} (a {} bloques del spawn {} {}, desnivel {}) en {} ms",
							e.x(), e.suelo(), e.z(), e.distancia(), spawn.getX(), spawn.getZ(), e.desnivel(), ms);
					if (colocarSolo) {
						Obras.empezar(ow, null, z, null);
						return;
					}
					propuesta = new Propuesta(z, e, ow.getGameTime() + PROPUESTA_TICKS, quien);
					if (quien != null) {
						proponer(quien, e, zona != null);
					}
				}, server);
	}

	private static void proponer(ServerPlayer p, Sitio.Eleccion e, boolean mover) {
		String orden = "/heraldia arena " + (mover ? "mover" : "colocar") + " confirmar";
		p.sendSystemMessage(Textos.t("heraldia.arena.propuesta", e.x(), e.suelo() + 1, e.z(), e.distancia()).withStyle(ChatFormatting.GOLD));
		p.sendSystemMessage(Textos.t("heraldia.arena.copia").withStyle(ChatFormatting.YELLOW));
		MutableComponent cmd = Component.literal(orden).withStyle(s -> s.withColor(ChatFormatting.GREEN).withUnderlined(true)
				.withClickEvent(new ClickEvent.SuggestCommand(orden)));
		p.sendSystemMessage(Textos.t("heraldia.arena.propuesta.confirmar", cmd));
	}

	// --- comandos ---

	/** /heraldia arena [salir | colocar [confirmar] | mover [confirmar] | quitar [confirmar] | empezar | parar]. */
	static LiteralArgumentBuilder<CommandSourceStack> comando() {
		return Commands.literal("heraldia").then(Commands.literal("arena")
				.executes(Arena::info)
				.then(Commands.literal("salir").executes(ctx -> {
					ServerPlayer p = ctx.getSource().getPlayerOrException();
					if (!Juego.salir(p)) {
						ctx.getSource().sendFailure(Textos.t("heraldia.arena.salir.no"));
						return 0;
					}
					return 1;
				}))
				.then(Commands.literal("colocar").requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS)).executes(ctx -> proponerCmd(ctx, false))
						.then(Commands.literal("confirmar").executes(ctx -> confirmar(ctx, false))))
				.then(Commands.literal("mover").requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS)).executes(ctx -> proponerCmd(ctx, true))
						.then(Commands.literal("confirmar").executes(ctx -> confirmar(ctx, true))))
				.then(Commands.literal("quitar").requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS)).executes(Arena::quitarAviso)
						.then(Commands.literal("confirmar").executes(Arena::quitar)))
				.then(Commands.literal("empezar").requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS)).executes(Arena::empezarCmd))
				.then(Commands.literal("parar").requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS)).executes(ctx -> {
					if (Juego.partida().estado() == Partida.Estado.LIBRE) {
						ctx.getSource().sendFailure(Textos.t("heraldia.arena.info.libre"));
						return 0;
					}
					Juego.terminar(nivel, zona, "parada por un operador");
					ctx.getSource().sendSuccess(() -> Textos.t("heraldia.arena.parada"), true);
					return 1;
				})));
	}

	private static boolean comprobar(CommandSourceStack src, boolean libre) {
		if (!activada) {
			src.sendFailure(Textos.t("heraldia.arena.desactivada"));
			return false;
		}
		if (Obras.ocupado()) {
			src.sendFailure(Textos.t("heraldia.arena.trabajando"));
			return false;
		}
		if (libre && Juego.partida().estado() != Partida.Estado.LIBRE) {
			src.sendFailure(Textos.t("heraldia.arena.ocupada"));
			return false;
		}
		return true;
	}

	private static int info(CommandContext<CommandSourceStack> ctx) {
		CommandSourceStack src = ctx.getSource();
		Zona z = zona;
		if (z == null) {
			src.sendFailure(Textos.t(activada ? "heraldia.arena.no_existe" : "heraldia.arena.desactivada"));
			return 0;
		}
		src.sendSuccess(() -> Textos.t("heraldia.arena.info", z.columnaX(), z.sueloY() + 1, z.columnaZ()).withStyle(ChatFormatting.GOLD), false);
		Partida pa = Juego.partida();
		src.sendSuccess(() -> pa.estado() == Partida.Estado.LIBRE ? Textos.t("heraldia.arena.info.libre")
				: Textos.t("heraldia.arena.info.partida", Math.max(1, pa.oleada()), pa.participantes().size()), false);
		ServerPlayer p = src.getPlayer();
		MinecraftServer server = src.getServer();
		int propio = p == null ? 0 : Marcador.leer(server, p.getScoreboardName());
		src.sendSuccess(() -> Textos.t("heraldia.arena.info.record", propio, Marcador.record(server)), false);
		return 1;
	}

	private static int proponerCmd(CommandContext<CommandSourceStack> ctx, boolean mover) {
		CommandSourceStack src = ctx.getSource();
		if (!comprobar(src, true)) {
			return 0;
		}
		Zona z = zona;
		if (!mover && z != null) {
			src.sendFailure(Textos.t("heraldia.arena.ya_existe", z.columnaX(), z.sueloY() + 1, z.columnaZ()));
			return 0;
		}
		if (mover && z == null) {
			src.sendFailure(Textos.t("heraldia.arena.no_existe"));
			return 0;
		}
		buscar(src.getServer(), src.getPlayer(), false);
		return 1;
	}

	private static int confirmar(CommandContext<CommandSourceStack> ctx, boolean mover) {
		CommandSourceStack src = ctx.getSource();
		if (!comprobar(src, true)) {
			return 0;
		}
		Propuesta pr = propuesta;
		String orden = "/heraldia arena " + (mover ? "mover" : "colocar");
		if (pr == null) {
			src.sendFailure(Textos.t("heraldia.arena.sin_propuesta", orden));
			return 0;
		}
		Zona vieja = zona;
		if (!mover && vieja != null) {
			src.sendFailure(Textos.t("heraldia.arena.ya_existe", vieja.columnaX(), vieja.sueloY() + 1, vieja.columnaZ()));
			return 0;
		}
		if (mover && vieja == null) {
			src.sendFailure(Textos.t("heraldia.arena.no_existe"));
			return 0;
		}
		propuesta = null;
		Zona z = pr.zona();
		if (!Obras.empezar(src.getServer().overworld(), vieja, z, src.getPlayer())) {
			return 0;
		}
		src.sendSuccess(() -> Textos.t("heraldia.arena.colocando", z.columnaX(), z.sueloY() + 1, z.columnaZ()), true);
		return 1;
	}

	private static int quitarAviso(CommandContext<CommandSourceStack> ctx) {
		Zona z = zona;
		if (z == null) {
			ctx.getSource().sendFailure(Textos.t("heraldia.arena.no_existe"));
			return 0;
		}
		ctx.getSource().sendSuccess(() -> Textos.t("heraldia.arena.quitar.confirmar", z.columnaX(), z.sueloY() + 1, z.columnaZ())
				.withStyle(ChatFormatting.YELLOW), false);
		return 1;
	}

	private static int quitar(CommandContext<CommandSourceStack> ctx) {
		CommandSourceStack src = ctx.getSource();
		if (!comprobar(src, true)) {
			return 0;
		}
		Zona z = zona;
		if (z == null) {
			src.sendFailure(Textos.t("heraldia.arena.no_existe"));
			return 0;
		}
		return Obras.empezar(src.getServer().overworld(), z, null, src.getPlayer()) ? 1 : 0;
	}

	private static int empezarCmd(CommandContext<CommandSourceStack> ctx) {
		CommandSourceStack src = ctx.getSource();
		Zona z = zona;
		if (!comprobar(src, false) || z == null || nivel == null) {
			if (z == null && activada) {
				src.sendFailure(Textos.t("heraldia.arena.no_existe"));
			}
			return 0;
		}
		if (!Juego.empezar(nivel, z, src.getTextName())) {
			src.sendFailure(Textos.t("heraldia.arena.en_marcha"));
			return 0;
		}
		src.sendSuccess(() -> Textos.t("heraldia.arena.cuenta"), false);
		return 1;
	}

	/** Para los tests: identificador del adjunto. */
	static String adjunto() {
		return Heraldia.id("arena").toString();
	}
}
