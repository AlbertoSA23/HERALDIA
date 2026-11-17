package io.github.albertosa23.heraldia.caravanas;

import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;
import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.caminos.Caminos;
import io.github.albertosa23.heraldia.caminos.Nombres;
import io.github.albertosa23.heraldia.caminos.Trazado;
import io.github.albertosa23.heraldia.comando.Textos;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.dificultad.Dificultad;
import io.github.albertosa23.heraldia.encargos.Encargos;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.function.Consumer;
import net.fabricmc.fabric.api.entity.event.v1.ServerLivingEntityEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerEntityEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.fabricmc.fabric.api.loot.v3.LootTableEvents;
import net.minecraft.ChatFormatting;
import net.minecraft.advancements.AdvancementHolder;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.core.BlockPos;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.resources.Identifier;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.util.Prediction;
import net.minecraft.util.Util;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntitySpawnReason;
import net.minecraft.world.entity.EntityTypes;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.animal.equine.TraderLlama;
import net.minecraft.world.entity.animal.golem.IronGolem;
import net.minecraft.world.entity.npc.wanderingtrader.WanderingTrader;
import net.minecraft.world.entity.raid.Raider;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.level.storage.loot.parameters.LootContextParams;
import org.jspecify.annotations.Nullable;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Caravanas por los caminos entre aldeas (T39): lo que toca el juego. La lógica pura está en {@link Tramo} (qué tramo de
 * la ruta canónica recorre), {@link Viaje} (sus fases), {@link Reglas} (cuándo sale, cómo es, qué paga) y {@link Suelo}
 * (si el camino existe de verdad en el mundo).
 * <ul>
 * <li>Cada minuto, con jugadores en el mundo principal, se sortea una caravana (caravanas.frecuencia %) junto a uno de
 * ellos: la ruta más cercana a 80 bloques como mucho se busca fuera del hilo del servidor (el trazado está en memoria; no
 * carga ni genera chunks) y la caravana sale solo si su vértice de salida está en un chunk cargado con entidades y el
 * camino está ahí de verdad (en un mundo existente, no en los chunks de antes de los caminos).</li>
 * <li>Un mercader de Heraldia (vendedor ambulante) con 1-3 llamas de carga y a veces un gólem de guardia recorre unos
 * 128 bloques hacia la aldea de destino: el objetivo de IA del propio vendedor ({@code setWanderTarget}) lo lleva de
 * vértice en vértice; las llamas y el guardia lo siguen. Con caravanas.prob_asalto %, a media ruta salen de 2 a 4
 * bandidos (los del campamento de bandidos: saqueadores y un vindicador jefe, anclados y con la dificultad de Heraldia).</li>
 * <li>Al llegar, cada jugador que la acompaña cobra esmeraldas (más un objeto si la defendió de un asalto) y gana
 * reputación con la aldea de destino ({@link Encargos#sumarReputacion}); defenderla da el logro. Si el mercader muere,
 * la caravana se pierde y sus entidades no sueltan nada.</li>
 * <li>Sin trabajo por tick salvo la caravana activa (un paso por segundo). Si los jugadores se alejan, el camino se acaba o
 * pasa el tiempo, se despide y se quitan todas sus entidades. Nada se guarda: al parar el servidor se quitan las cargadas
 * y, al arrancar, cualquier entidad de caravana que se cargue se quita ({@code ENTITY_LOAD}): sin huérfanas ni duplicadas.</li>
 * </ul>
 * Las opciones caravanas.* se leen en cada uso: se recargan con /heraldia reload.
 */
public final class Caravanas {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	public static final String ACTIVADO = "caravanas.activado", FRECUENCIA = "caravanas.frecuencia", PROB_ASALTO = "caravanas.prob_asalto",
			MAX_ACTIVAS = "caravanas.max_activas";
	/** Jugadores que cuentan como cerca del mercader (los que la acompañan), y los que cobran al llegar. */
	public static final double RADIO_JUGADORES = 64, RADIO_PREMIO = 48;
	/** Logro (tools/gen/caravanas.py): heraldia:caravanas/defensa, criterio «hecho». */
	static final String LOGRO = "caravanas/defensa";
	private static final Map<Integer, Caravana> ACTIVAS = new LinkedHashMap<>();
	/** Entidad → su caravana: las que no están aquí y llevan la etiqueta sobran. */
	private static final Map<UUID, Caravana> DE = new HashMap<>();
	private static int contador, buscando, llegadas, perdidas;
	private static long ultimoFin = -Reglas.ESPERA_TICKS;

	private Caravanas() {
	}

	/** Una caravana en camino (solo en el hilo del servidor). */
	static final class Caravana {
		final int id;
		final ServerLevel level;
		final Tramo tramo;
		final Viaje viaje;
		final UUID mercader;
		final List<UUID> sequito = new ArrayList<>();      // llamas y guardia, en orden de marcha
		final List<UUID> bandidos = new ArrayList<>();
		final String origen, destino;
		final long semilla;
		/** Vértice del tramo cuyo camino ya se comprobó (para no mirarlo cada segundo). */
		int comprobado = 0;

		Caravana(int id, ServerLevel level, Tramo tramo, Viaje viaje, UUID mercader, long semilla) {
			this.id = id;
			this.level = level;
			this.tramo = tramo;
			this.viaje = viaje;
			this.mercader = mercader;
			this.semilla = semilla;
			this.origen = nombre(level, tramo.origen());
			this.destino = nombre(level, tramo.destino());
		}

		List<UUID> todas() {
			List<UUID> out = new ArrayList<>(sequito);
			out.addAll(bandidos);
			out.add(mercader);
			return out;
		}
	}

	/** Una línea en Heraldia.onInitialize. */
	public static void registrar() {
		ServerEntityEvents.ENTITY_LOAD.register(Caravanas::alCargar);
		ServerLivingEntityEvents.AFTER_DEATH.register((entity, source) -> alMorir(entity));
		LootTableEvents.MODIFY_DROPS.register((table, context, drops) -> {
			Entity e = context.getOptional(LootContextParams.THIS_ENTITY);
			if (e != null && sinBotin(e.entityTags())) {
				drops.clear();
			}
		});
		ServerTickEvents.END_SERVER_TICK.register(Caravanas::tick);
		ServerLifecycleEvents.SERVER_STOPPING.register(server -> limpiar(Viaje.Fin.LIMPIEZA));
		ServerLifecycleEvents.SERVER_STOPPED.register(server -> {
			ACTIVAS.clear();
			DE.clear();
			contador = buscando = llegadas = perdidas = 0;
			ultimoFin = -Reglas.ESPERA_TICKS;
		});
	}

	/** El mercader, las llamas y el guardia no sueltan nada (los bandidos, lo suyo). */
	static boolean sinBotin(Set<String> tags) {
		return !tags.isEmpty() && tags.contains(Reglas.TAG) && !tags.contains(Reglas.BANDIDO);
	}

	static HeraldiaConfig cfg() {
		return HeraldiaConfig.get();
	}

	static String nombre(ServerLevel level, long aldea) {
		String[] n = Nombres.de(level.getSeed(), Trazado.px(aldea), Trazado.pz(aldea));
		return n[0] + " " + n[1];
	}

	// --- entidades sobrantes ---

	private static void alCargar(Entity e, ServerLevel level) {
		if (Reglas.huerfana(e.entityTags(), e.getUUID(), DE.keySet())) {
			LOGGER.info("Heraldia: caravanas: quitada una entidad de una caravana que ya no está en camino ({} en {} {} {})",
					BuiltInRegistries.ENTITY_TYPE.getKey(e.getType()).getPath(), e.getBlockX(), e.getBlockY(), e.getBlockZ());
			e.discard();
		}
	}

	private static void alMorir(LivingEntity e) {
		Set<String> tags = e.entityTags();
		if (tags.isEmpty() || !tags.contains(Reglas.MERCADER)) {
			return;
		}
		Caravana c = DE.get(e.getUUID());
		if (c != null) {
			c.viaje.terminar(Viaje.Fin.PERDIDA);
			acabar(c);       // ya, en el mismo tick: las llamas no llegan a soltar nada
		}
	}

	// --- cada tick: solo la caravana activa y el sorteo de cada minuto ---

	private static void tick(MinecraftServer server) {
		int t = server.getTickCount();
		if (!ACTIVAS.isEmpty() && t % Viaje.CADA == 0 && !cfg().getBool(ACTIVADO)) {
			limpiar(Viaje.Fin.LIMPIEZA);      // desactivadas con /heraldia reload: se van las que había
		}
		if (!ACTIVAS.isEmpty() && t % Viaje.CADA == 0) {
			for (Caravana c : new ArrayList<>(ACTIVAS.values())) {
				actualizar(c);
			}
		}
		if (t % Reglas.SORTEO_TICKS == 0) {
			sortear(server, t);
		}
	}

	private static void sortear(MinecraftServer server, long t) {
		HeraldiaConfig cfg = cfg();
		ServerLevel level = server.overworld();
		if (!Reglas.sale(cfg.getBool(ACTIVADO), ACTIVAS.size() + buscando, cfg.getInt(MAX_ACTIVAS), t, ultimoFin, cfg.getInt(FRECUENCIA),
				level.getRandom().nextDouble())) {
			return;
		}
		List<ServerPlayer> candidatos = new ArrayList<>();
		for (ServerPlayer p : level.players()) {
			if (!p.isSpectator() && p.isAlive()) {
				candidatos.add(p);
			}
		}
		if (candidatos.isEmpty()) {
			return;
		}
		ServerPlayer p = candidatos.get(level.getRandom().nextInt(candidatos.size()));
		buscar(level, p.getBlockX(), p.getBlockZ(), null, msg -> LOGGER.debug("Heraldia: caravanas: sorteo junto a {}: {}",
				p.getGameProfile().name(), msg.getString()));
	}

	/**
	 * Busca el tramo junto a (x, z) fuera del hilo del servidor y, de vuelta en él, crea la caravana.
	 *
	 * @param asalto true/false para fijar si la asaltan (el comando); null, con caravanas.prob_asalto
	 * @param aviso  lo que se dice si no sale (o cuando sale)
	 */
	static void buscar(ServerLevel level, int x, int z, @Nullable Boolean asalto, Consumer<Component> aviso) {
		MinecraftServer server = level.getServer();
		long semilla = level.getRandom().nextLong();
		buscando++;
		CompletableFuture.supplyAsync(() -> {
					Trazado t = Caminos.trazado(level);
					if (t == null) {
						return null;
					}
					int r = Tramo.DIST_MAX;
					return Tramo.elegir(t.rutasEn(x - r, z - r, x + r, z + r), x, z, semilla);
				}, Util.backgroundExecutor())
				.whenCompleteAsync((tramo, e) -> {
					buscando--;
					if (e != null) {
						LOGGER.error("Heraldia: caravanas: no se pudo buscar el camino junto a {} {}", x, z, e);
						return;
					}
					crear(level, tramo, asalto, semilla, aviso);
				}, server);
	}

	// --- crear ---

	/** La altura del suelo en (x, z) si su chunk está cargado con entidades; si no, null (no carga nada). */
	static @Nullable BlockPos suelo(ServerLevel level, int x, int z) {
		BlockPos p = new BlockPos(x, level.getMinY(), z);
		if (!level.isPositionEntityTicking(p)) {
			return null;
		}
		return new BlockPos(x, level.getHeight(Heightmap.Types.MOTION_BLOCKING_NO_LEAVES, x, z), z);
	}

	/** ¿Hay camino de verdad en (x, z)? Solo con su 3 × 3 cargado; null si no se puede saber sin cargar chunks. */
	static @Nullable Boolean hayCamino(ServerLevel level, int x, int z) {
		int n = 0;
		for (int dx = -1; dx <= 1; dx++) {
			for (int dz = -1; dz <= 1; dz++) {
				BlockPos s = suelo(level, x + dx, z + dz);
				if (s == null) {
					return null;
				}
				n += Suelo.delCamino(level.getBlockState(s.below())) ? 1 : 0;
			}
		}
		return Suelo.hayCamino(n);
	}

	private static void crear(ServerLevel level, @Nullable Tramo tramo, @Nullable Boolean asalto, long semilla, Consumer<Component> aviso) {
		HeraldiaConfig cfg = cfg();
		if (!cfg.getBool(ACTIVADO)) {
			aviso.accept(Textos.t("heraldia.caravanas.desactivadas"));
			return;
		}
		if (ACTIVAS.size() >= cfg.getInt(MAX_ACTIVAS)) {
			aviso.accept(Textos.t("heraldia.caravanas.limite", ACTIVAS.size(), cfg.getInt(MAX_ACTIVAS)));
			return;
		}
		if (tramo == null) {
			aviso.accept(Textos.t("heraldia.caravanas.sin_camino", Tramo.DIST_MAX));
			return;
		}
		// la salida: cargada y con camino de verdad
		BlockPos salida = suelo(level, tramo.x(0), tramo.z(0));
		if (salida == null || !Boolean.TRUE.equals(hayCamino(level, tramo.x(0), tramo.z(0)))) {
			aviso.accept(Textos.t("heraldia.caravanas.sin_camino", Tramo.DIST_MAX));
			LOGGER.info("Heraldia: caravanas: sin camino en la salida {} {} ({})", tramo.x(0), tramo.z(0), salida == null ? "sin cargar" : "no hay camino");
			return;
		}
		// en un mundo existente el camino puede acabar antes: el tramo llega hasta el último vértice cargado con camino
		int hasta = tramo.vertices() - 1;
		for (int k = 1; k < tramo.vertices(); k++) {
			Boolean hay = hayCamino(level, tramo.x(k), tramo.z(k));
			if (hay == null) {
				break;              // aún sin cargar: se mira al llegar
			}
			if (!hay) {
				hasta = k - 1;
				break;
			}
		}
		if (hasta < 2) {
			aviso.accept(Textos.t("heraldia.caravanas.sin_camino", Tramo.DIST_MAX));
			LOGGER.info("Heraldia: caravanas: el camino de {} {} se acaba enseguida", tramo.x(0), tramo.z(0));
			return;
		}
		Tramo t = hasta < tramo.vertices() - 1 ? tramo.hasta(hasta) : tramo;
		java.util.Random rnd = new java.util.Random(semilla);
		boolean asaltada = asalto != null ? asalto : Reglas.asalto(cfg.getInt(PROB_ASALTO), rnd.nextDouble());
		int asaltoEn = asaltada ? Viaje.puntoDeAsalto(t.vertices(), rnd.nextDouble()) : -1;
		int llamas = Reglas.llamas(rnd.nextDouble());
		boolean guardia = Reglas.guardia(rnd.nextDouble());
		int id = ++contador;
		// rumbo: del vértice de salida al siguiente
		double dx = t.x(1) - t.x(0), dz = t.z(1) - t.z(0), len = Math.max(1e-6, Math.hypot(dx, dz));
		dx /= len;
		dz /= len;
		float yaw = (float) Math.toDegrees(Math.atan2(-dx, dz));
		WanderingTrader m = EntityTypes.WANDERING_TRADER.create(level, EntitySpawnReason.EVENT);
		if (m == null) {
			return;
		}
		m.snapTo(salida.getX() + 0.5, salida.getY(), salida.getZ() + 0.5, yaw, 0f);
		m.addTag(Reglas.TAG);
		m.addTag(Reglas.MERCADER);
		m.setCustomName(Textos.t("heraldia.caravanas.mercader").withStyle(ChatFormatting.GOLD));
		m.setCustomNameVisible(true);
		m.setPersistenceRequired();
		m.setDespawnDelay(Viaje.MAX_TICKS + 2 * Reglas.SORTEO_TICKS);   // lo quita la caravana, no el reloj del vendedor
		var vida = m.getAttribute(Attributes.MAX_HEALTH);
		if (vida != null) {
			vida.setBaseValue(MERCADER_VIDA);   // aguanta un asalto el tiempo de llegar a defenderlo
			m.setHealth((float) MERCADER_VIDA);
		}
		Viaje viaje = new Viaje(t.vertices(), asaltoEn);
		Caravana c = new Caravana(id, level, t, viaje, m.getUUID(), semilla);
		DE.put(m.getUUID(), c);
		if (!level.addFreshEntity(m)) {
			DE.remove(m.getUUID());
			return;
		}
		ACTIVAS.put(id, c);
		// las llamas detrás, en fila; el guardia a un lado
		for (int i = 1; i <= llamas; i++) {
			TraderLlama l = EntityTypes.TRADER_LLAMA.create(level, EntitySpawnReason.EVENT);
			if (l != null) {
				l.setDespawnDelay(Viaje.MAX_TICKS + 2 * Reglas.SORTEO_TICKS);
				anadir(c, l, Reglas.LLAMA, salida, -dx * 2.5 * i, -dz * 2.5 * i, yaw);
			}
		}
		if (guardia) {
			IronGolem g = EntityTypes.IRON_GOLEM.create(level, EntitySpawnReason.EVENT);
			if (g != null) {
				g.setPlayerCreated(true);       // no se vuelve contra los jugadores sin motivo
				anadir(c, g, Reglas.GUARDIA, salida, -dz * 3, dx * 3, yaw);
			}
		}
		irA(c, m);
		LOGGER.info("Heraldia: caravanas: sale la caravana {} de {} hacia {}: {} vértices ({} bloques) desde {} {} {} hasta {} {}, asalto {}, "
						+ "{} llamas, {}", id, c.origen, c.destino, t.vertices(), Math.round(t.longitud()), salida.getX(), salida.getY(), salida.getZ(),
				t.x(t.vertices() - 1), t.z(t.vertices() - 1), asaltoEn < 0 ? "no" : "en el vértice " + asaltoEn, llamas, guardia ? "con guardia" : "sin guardia");
		StringBuilder vertices = new StringBuilder();
		for (int k = 0; k < t.vertices(); k++) {
			vertices.append(k == 0 ? "" : "; ").append(t.x(k)).append(' ').append(t.z(k));
		}
		LOGGER.info("Heraldia: caravanas: vértices de la caravana {}: {}", id, vertices);   // los sigue la prueba de servidor
		aviso.accept(Textos.t("heraldia.caravanas.creada", id, c.origen, c.destino, Math.round(t.longitud())));
		avisar(c, m, "heraldia.caravanas.sale", ChatFormatting.YELLOW, c.origen, c.destino);
	}

	static final double MERCADER_VIDA = 40;

	private static void anadir(Caravana c, Mob mob, String papel, BlockPos salida, double ox, double oz, float yaw) {
		BlockPos s = suelo(c.level, (int) Math.floor(salida.getX() + 0.5 + ox), (int) Math.floor(salida.getZ() + 0.5 + oz));
		if (s == null) {
			s = salida;
		}
		mob.snapTo(s.getX() + 0.5, s.getY(), s.getZ() + 0.5, yaw, 0f);
		mob.addTag(Reglas.TAG);
		mob.addTag(papel);
		mob.setPersistenceRequired();
		DE.put(mob.getUUID(), c);
		if (c.level.addFreshEntity(mob)) {
			c.sequito.add(mob.getUUID());
		} else {
			DE.remove(mob.getUUID());
		}
	}

	// --- cada segundo, la caravana activa ---

	private static @Nullable Entity entidad(Caravana c, UUID u) {
		Entity e = c.level.getEntity(u);
		return e == null || e.isRemoved() ? null : e;
	}

	private static void actualizar(Caravana c) {
		Entity e = entidad(c, c.mercader);
		WanderingTrader m = e instanceof WanderingTrader w ? w : null;
		int k = c.viaje.siguiente();
		int tx = c.tramo.x(k), tz = c.tramo.z(k);
		boolean cargado = m != null && c.level.isPositionEntityTicking(m.blockPosition())
				&& c.level.isPositionEntityTicking(new BlockPos(tx, m.getBlockY(), tz));
		double dist = m == null ? Double.MAX_VALUE : Math.hypot(m.getX() - (tx + 0.5), m.getZ() - (tz + 0.5));
		int jugadores = m == null ? 0 : cerca(c.level, m, RADIO_JUGADORES).size();
		int bandidos = 0;
		for (UUID u : c.bandidos) {
			bandidos += entidad(c, u) instanceof LivingEntity l && l.isAlive() ? 1 : 0;
		}
		boolean camino = true;
		if (cargado && c.comprobado < k) {
			Boolean hay = hayCamino(c.level, tx, tz);
			camino = !Boolean.FALSE.equals(hay);
			if (hay != null) {
				c.comprobado = k;
			}
		}
		Viaje.Paso paso = c.viaje.paso(new Viaje.Vista(m == null || m.isAlive(), cargado, dist, jugadores, bandidos, camino));
		switch (paso) {
			case FIN -> acabar(c);
			case ASALTO -> asalto(c, m, jugadores);
			case SUPERADO -> {
				avisar(c, m, "heraldia.caravanas.superado", ChatFormatting.GREEN);
				LOGGER.info("Heraldia: caravanas: la caravana {} supera el asalto", c.id);
				irA(c, m);
			}
			default -> irA(c, m);
		}
	}

	/** El mercader hacia el vértice siguiente (con el objetivo de IA del vendedor) y su séquito detrás. */
	private static void irA(Caravana c, @Nullable WanderingTrader m) {
		if (m == null || c.viaje.fase() == Viaje.Fase.FIN) {
			return;
		}
		if (c.viaje.fase() == Viaje.Fase.CAMINO) {
			int k = c.viaje.siguiente();
			BlockPos s = suelo(c.level, c.tramo.x(k), c.tramo.z(k));
			if (s != null) {
				m.setWanderTarget(s);
			}
		}
		Entity delante = m;
		for (UUID u : c.sequito) {
			if (entidad(c, u) instanceof Mob mob) {
				boolean guardia = mob.entityTags().contains(Reglas.GUARDIA);
				Entity sigue = guardia ? m : delante;
				if (mob.getTarget() == null && mob.distanceToSqr(sigue) > (guardia ? 36 : 16)) {
					mob.getNavigation().moveTo(sigue, guardia ? 0.8 : 1.2);
				}
				if (!guardia) {
					delante = mob;
				}
			}
		}
	}

	static List<ServerPlayer> cerca(ServerLevel level, Entity e, double radio) {
		List<ServerPlayer> out = new ArrayList<>();
		for (ServerPlayer p : level.players()) {
			if (!p.isSpectator() && p.isAlive() && Math.hypot(p.getX() - e.getX(), p.getZ() - e.getZ()) <= radio
					&& Math.abs(p.getY() - e.getY()) <= radio) {
				out.add(p);
			}
		}
		return out;
	}

	private static void avisar(Caravana c, @Nullable Entity m, String clave, ChatFormatting color, Object... args) {
		if (m == null) {
			return;
		}
		for (ServerPlayer p : cerca(c.level, m, RADIO_JUGADORES)) {
			p.sendSystemMessage(Textos.t(Textos.idioma(p.clientInformation().language()), clave, args).withStyle(color));
		}
	}

	// --- el asalto ---

	private static void asalto(Caravana c, @Nullable WanderingTrader m, int jugadores) {
		if (m == null) {
			return;
		}
		int n = Reglas.bandidos(jugadores);
		boolean jefe = Reglas.conJefe(n);
		// delante de la caravana, a los dos lados del camino
		int k = Math.min(c.tramo.vertices() - 1, c.viaje.siguiente());
		double[] nrm = c.tramo.ruta().normal(c.tramo.vertice(k));
		double ax = (m.getX() + c.tramo.x(k) + 0.5) / 2, az = (m.getZ() + c.tramo.z(k) + 0.5) / 2;
		int salieron = 0;
		for (int i = 0; i < n; i++) {
			double lado = i % 2 == 0 ? 1 : -1, off = 7 + 2 * (i / 2);
			BlockPos s = suelo(c.level, (int) Math.floor(ax + nrm[0] * lado * off), (int) Math.floor(az + nrm[1] * lado * off));
			if (s == null) {
				s = suelo(c.level, (int) Math.floor(ax), (int) Math.floor(az));
			}
			if (s == null) {
				continue;
			}
			boolean esJefe = jefe && i == 0;
			Mob b = (esJefe ? EntityTypes.VINDICATOR : EntityTypes.PILLAGER).create(c.level, EntitySpawnReason.EVENT);
			if (b == null) {
				continue;
			}
			b.snapTo(s.getX() + 0.5, s.getY(), s.getZ() + 0.5, c.level.getRandom().nextFloat() * 360f, 0f);
			// las etiquetas antes de añadirlo: la dificultad y el anclaje de Heraldia miran ENTITY_LOAD
			b.addTag(Reglas.TAG);
			b.addTag(Reglas.BANDIDO);
			b.addTag(Dificultad.ANCLADO);
			b.finalizeSpawn(c.level, c.level.getCurrentDifficultyAt(s), EntitySpawnReason.EVENT, null);
			if (b instanceof Raider r) {
				r.setPatrolLeader(false);       // sin estandarte ni mal presagio
				r.setCanJoinRaid(false);
			}
			b.setCustomName(Textos.t(esJefe ? "heraldia.medianas.campamento.vindicador" : "heraldia.medianas.campamento.saqueador"));
			b.setPersistenceRequired();
			b.setTarget(m);
			DE.put(b.getUUID(), c);
			if (c.level.addFreshEntity(b)) {
				c.bandidos.add(b.getUUID());
				salieron++;
			} else {
				DE.remove(b.getUUID());
			}
		}
		c.level.playSound(null, m.getX(), m.getY(), m.getZ(), SoundEvents.RAID_HORN.value(), SoundSource.HOSTILE, 2f, 1.2f);
		avisar(c, m, "heraldia.caravanas.asalto", ChatFormatting.RED, c.destino);
		LOGGER.info("Heraldia: caravanas: asalto a la caravana {}: {} bandidos{} en {} {}", c.id, salieron, jefe ? " con su jefe" : "",
				Math.round(ax), Math.round(az));
	}

	// --- el final ---

	/** Termina la caravana: premia (si llegó), avisa y quita todas sus entidades cargadas. */
	static void acabar(Caravana c) {
		if (!ACTIVAS.containsKey(c.id)) {
			return;
		}
		ACTIVAS.remove(c.id);
		Viaje.Fin fin = c.viaje.fin();
		Entity m = entidad(c, c.mercader);
		if (fin == Viaje.Fin.LLEGADA && m != null) {
			llegadas++;
			premiar(c, m);
		} else if (fin == Viaje.Fin.PERDIDA) {
			perdidas++;
			avisar(c, m, "heraldia.caravanas.perdida", ChatFormatting.RED, c.destino);
		} else if (fin != Viaje.Fin.LIMPIEZA) {
			avisar(c, m, "heraldia.caravanas.despedida", ChatFormatting.GRAY, c.destino);
		}
		int quitadas = 0;
		for (UUID u : c.todas()) {
			DE.remove(u);
			Entity e = entidad(c, u);
			if (e != null && e.isAlive()) {      // el mercader que acaba de morir se queda (es su cadáver)
				if (u.equals(c.mercader)) {
					c.level.sendParticles(ParticleTypes.POOF, e.getX(), e.getY() + 1, e.getZ(), 12, 0.5, 0.5, 0.5, 0.02);
				}
				e.discard();
				quitadas++;
			}
		}
		ultimoFin = c.level.getServer().getTickCount();
		LOGGER.info("Heraldia: caravanas: termina la caravana {}: {} ({} entidades quitadas, {} s en camino)", c.id, fin.id, quitadas,
				c.viaje.ticks() / 20);
	}

	private static void premiar(Caravana c, Entity m) {
		int[] aldea = Reglas.chunk(c.tramo.destino());
		java.util.Random rnd = new java.util.Random(c.semilla ^ 0x5DEECE66DL);
		List<ServerPlayer> jugadores = cerca(c.level, m, RADIO_PREMIO);
		for (ServerPlayer p : jugadores) {
			Reglas.Recompensa r = Reglas.recompensa(c.tramo.vertices(), c.viaje.superada(), rnd.nextDouble());
			Map<String, String> l = Textos.idioma(p.clientInformation().language());
			p.getInventory().placeItemBackInInventory(new ItemStack(Items.EMERALD, r.esmeraldas()), Prediction.SERVER_ONLY);   // al suelo si no cabe
			MutableComponent paga = Textos.t(l, "heraldia.caravanas.paga", r.esmeraldas());
			if (r.conObjeto()) {
				Item item = BuiltInRegistries.ITEM.getValue(Identifier.parse(r.objeto()));
				ItemStack stack = new ItemStack(item, r.cantidad());
				paga = Textos.t(l, "heraldia.caravanas.paga.objeto", r.esmeraldas(), r.cantidad(), stack.getHoverName());
				p.getInventory().placeItemBackInInventory(stack, Prediction.SERVER_ONLY);
			}
			p.sendSystemMessage(Textos.t(l, "heraldia.caravanas.llegada", c.destino, paga).withStyle(ChatFormatting.GREEN));
			int rep = Encargos.sumarReputacion(p, aldea[0], aldea[1], r.reputacion(), c.viaje.superada() ? "defiende la caravana" : "acompaña la caravana");
			if (r.logro()) {
				AdvancementHolder h = c.level.getServer().getAdvancements().get(Heraldia.id(LOGRO));
				if (h != null) {
					p.getAdvancements().award(h, "hecho");
				}
			}
			LOGGER.info("Heraldia: caravanas: {} cobra {} esmeraldas{} y +{} de reputación con {} (ahora {})", p.getGameProfile().name(),
					r.esmeraldas(), r.conObjeto() ? " y " + r.cantidad() + " × " + r.objeto() : "", r.reputacion(), c.destino, rep);
		}
		c.level.playSound(null, m.getX(), m.getY(), m.getZ(), SoundEvents.VILLAGER_CELEBRATE, SoundSource.NEUTRAL, 1f, 1f);
		LOGGER.info("Heraldia: caravanas: la caravana {} llega a {}{} con {} jugadores", c.id, c.destino,
				c.viaje.superada() ? " tras superar el asalto" : "", jugadores.size());
	}

	/** Termina todas (al parar el servidor o con /heraldia caravan clear); devuelve cuántas había. */
	static int limpiar(Viaje.Fin fin) {
		int n = ACTIVAS.size();
		for (Caravana c : new ArrayList<>(ACTIVAS.values())) {
			c.viaje.terminar(fin);
			acabar(c);
		}
		return n;
	}

	// --- comandos: /heraldia caravan [spawn [raid | peaceful] | raid | list | clear] (operadores) ---

	public static LiteralArgumentBuilder<CommandSourceStack> nodo() {
		return Commands.literal("caravan").requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))
				.executes(Caravanas::lista)
				.then(Commands.literal("spawn").executes(ctx -> spawn(ctx, null))
						.then(Commands.literal("raid").executes(ctx -> spawn(ctx, true)))
						.then(Commands.literal("peaceful").executes(ctx -> spawn(ctx, false))))
				.then(Commands.literal("raid").executes(Caravanas::raid))
				.then(Commands.literal("list").executes(Caravanas::lista))
				.then(Commands.literal("clear").executes(Caravanas::clear));
	}

	private static Map<String, String> idioma(CommandSourceStack src) {
		ServerPlayer p = src.getPlayer();
		return Textos.idioma(p == null ? "es_es" : p.clientInformation().language());
	}

	private static int spawn(CommandContext<CommandSourceStack> ctx, @Nullable Boolean asalto) {
		CommandSourceStack src = ctx.getSource();
		Map<String, String> l = idioma(src);
		if (!cfg().getBool(ACTIVADO)) {
			src.sendFailure(Textos.t(l, "heraldia.caravanas.desactivadas"));
			return 0;
		}
		if (src.getLevel().dimension() != Level.OVERWORLD) {
			src.sendFailure(Textos.t(l, "heraldia.caravanas.sin_camino", Tramo.DIST_MAX));
			return 0;
		}
		BlockPos p = BlockPos.containing(src.getPosition());
		src.sendSuccess(() -> Textos.t(l, "heraldia.caravanas.buscando"), false);
		buscar(src.getLevel(), p.getX(), p.getZ(), asalto, c -> src.sendSuccess(() -> c, true));
		return 1;
	}

	private static int raid(CommandContext<CommandSourceStack> ctx) {
		CommandSourceStack src = ctx.getSource();
		Map<String, String> l = idioma(src);
		Caravana mejor = null;
		double mejorD = Double.MAX_VALUE;
		for (Caravana c : ACTIVAS.values()) {
			Entity m = entidad(c, c.mercader);
			if (m != null && c.viaje.fase() == Viaje.Fase.CAMINO && !c.viaje.asaltada()) {
				double d = m.position().distanceToSqr(src.getPosition());
				if (d < mejorD) {
					mejorD = d;
					mejor = c;
				}
			}
		}
		if (mejor == null || !mejor.viaje.forzarAsalto()) {
			src.sendFailure(Textos.t(l, "heraldia.caravanas.asalto.ninguna"));
			return 0;
		}
		WanderingTrader m = (WanderingTrader) entidad(mejor, mejor.mercader);
		asalto(mejor, m, m == null ? 1 : cerca(mejor.level, m, RADIO_JUGADORES).size());
		int id = mejor.id;
		src.sendSuccess(() -> Textos.t(l, "heraldia.caravanas.asalto.forzado", id), true);
		return 1;
	}

	private static int lista(CommandContext<CommandSourceStack> ctx) {
		CommandSourceStack src = ctx.getSource();
		Map<String, String> l = idioma(src);
		src.sendSuccess(() -> Textos.t(l, "heraldia.caravanas.lista.titulo", ACTIVAS.size(), cfg().getInt(MAX_ACTIVAS)).withStyle(ChatFormatting.GOLD), false);
		if (ACTIVAS.isEmpty()) {
			src.sendSuccess(() -> Textos.t(l, "heraldia.caravanas.lista.ninguna").withStyle(ChatFormatting.GRAY), false);
		}
		for (Caravana c : ACTIVAS.values()) {
			Entity m = entidad(c, c.mercader);
			String fase = c.viaje.fase() == Viaje.Fase.ASALTO ? "asalto" : "camino";
			Component linea = Textos.t(l, "heraldia.caravanas.lista.linea", c.id, c.origen, c.destino, Textos.t(l, "heraldia.caravanas.fase." + fase),
					c.viaje.siguiente(), c.viaje.vertices() - 1, m == null ? "?" : m.getBlockX(), m == null ? "?" : m.getBlockY(), m == null ? "?" : m.getBlockZ());
			src.sendSuccess(() -> linea, false);
		}
		return ACTIVAS.size();
	}

	private static int clear(CommandContext<CommandSourceStack> ctx) {
		CommandSourceStack src = ctx.getSource();
		Map<String, String> l = idioma(src);
		int n = limpiar(Viaje.Fin.LIMPIEZA);
		// y las que quedaran sueltas en chunks cargados (no debería haber: se quitan al cargarse)
		int sueltas = 0;
		for (ServerLevel level : src.getServer().getAllLevels()) {
			List<Entity> sobran = new ArrayList<>();
			for (Entity e : level.getAllEntities()) {
				if (e.entityTags().contains(Reglas.TAG)) {
					sobran.add(e);
				}
			}
			for (Entity e : sobran) {
				e.discard();
				sueltas++;
			}
		}
		int s = sueltas;
		src.sendSuccess(() -> Textos.t(l, "heraldia.caravanas.limpiadas", n, s), true);
		return n;
	}

	/** Para /heraldia status. */
	public static List<Component> estado() {
		HeraldiaConfig cfg = cfg();
		if (!cfg.getBool(ACTIVADO)) {
			return List.of(Textos.t("heraldia.estado.caravanas.no"));
		}
		return List.of(Textos.t("heraldia.estado.caravanas", ACTIVAS.size(), cfg.getInt(MAX_ACTIVAS), cfg.getInt(FRECUENCIA),
				cfg.getInt(PROB_ASALTO), llegadas, perdidas));
	}

	/** Caravanas en camino (para los tests y el estado). */
	static int activas() {
		return ACTIVAS.size();
	}
}
