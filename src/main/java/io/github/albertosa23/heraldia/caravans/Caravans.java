package io.github.albertosa23.heraldia.caravans;

import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;
import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.roads.Roads;
import io.github.albertosa23.heraldia.roads.Names;
import io.github.albertosa23.heraldia.roads.RoadLayout;
import io.github.albertosa23.heraldia.command.Texts;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.difficulty.ModDifficulty;
import io.github.albertosa23.heraldia.quests.Quests;
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
 * Caravanas por los caminos entre aldeas (T39): lo que toca el juego. La lógica pura está en {@link Segment} (qué tramo de
 * la ruta canónica recorre), {@link Journey} (sus fases), {@link Rules} (cuándo sale, cómo es, qué paga) y {@link Ground}
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
 * reputación con la aldea de destino ({@link Quests#addReputation}); defenderla da el logro. Si el mercader muere,
 * la caravana se pierde y sus entidades no sueltan nada.</li>
 * <li>Sin trabajo por tick salvo la caravana activa (un paso por segundo). Si los jugadores se alejan, el camino se acaba o
 * pasa el tiempo, se despide y se quitan todas sus entidades. Nada se guarda: al parar el servidor se quitan las cargadas
 * y, al arrancar, cualquier entidad de caravana que se cargue se quita ({@code ENTITY_LOAD}): sin huérfanas ni duplicadas.</li>
 * </ul>
 * Las opciones caravanas.* se leen en cada uso: se recargan con /heraldia reload.
 */
public final class Caravans {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	public static final String ENABLED = "caravanas.activado", FREQUENCY = "caravanas.frecuencia", AMBUSH_PROB = "caravanas.prob_asalto",
			MAX_ACTIVE = "caravanas.max_activas";
	/** Jugadores que cuentan como cerca del mercader (los que la acompañan), y los que cobran al llegar. */
	public static final double PLAYER_RADIUS = 64, REWARD_RADIUS = 48;
	/** Logro (tools/gen/caravanas.py): heraldia:caravanas/defensa, criterio «hecho». */
	static final String ADVANCEMENT = "caravanas/defensa";
	private static final Map<Integer, Caravan> ACTIVE = new LinkedHashMap<>();
	/** Entidad → su caravana: las que no están aquí y llevan la etiqueta sobran. */
	private static final Map<UUID, Caravan> DE = new HashMap<>();
	private static int counter, searching, arrivals, losses;
	private static long lastEnd = -Rules.WAIT_TICKS;

	private Caravans() {
	}

	/** Una caravana en camino (solo en el hilo del servidor). */
	static final class Caravan {
		final int id;
		final ServerLevel level;
		final Segment segment;
		final Journey journey;
		final UUID merchant;
		final List<UUID> escort = new ArrayList<>();      // llamas y guardia, en orden de marcha
		final List<UUID> bandits = new ArrayList<>();
		final String origin, destination;
		final long seed;
		/** Vértice del tramo cuyo camino ya se comprobó (para no mirarlo cada segundo). */
		int checked = 0;

		Caravan(int id, ServerLevel level, Segment segment, Journey journey, UUID merchant, long seed) {
			this.id = id;
			this.level = level;
			this.segment = segment;
			this.journey = journey;
			this.merchant = merchant;
			this.seed = seed;
			this.origin = name(level, segment.origin());
			this.destination = name(level, segment.destination());
		}

		List<UUID> all() {
			List<UUID> out = new ArrayList<>(escort);
			out.addAll(bandits);
			out.add(merchant);
			return out;
		}
	}

	/** Una línea en Heraldia.onInitialize. */
	public static void register() {
		ServerEntityEvents.ENTITY_LOAD.register(Caravans::onLoad);
		ServerLivingEntityEvents.AFTER_DEATH.register((entity, source) -> onDeath(entity));
		LootTableEvents.MODIFY_DROPS.register((table, context, drops) -> {
			Entity e = context.getOptional(LootContextParams.THIS_ENTITY);
			if (e != null && noLoot(e.entityTags())) {
				drops.clear();
			}
		});
		ServerTickEvents.END_SERVER_TICK.register(Caravans::tick);
		ServerLifecycleEvents.SERVER_STOPPING.register(server -> clean(Journey.End.CLEANUP));
		ServerLifecycleEvents.SERVER_STOPPED.register(server -> {
			ACTIVE.clear();
			DE.clear();
			counter = searching = arrivals = losses = 0;
			lastEnd = -Rules.WAIT_TICKS;
		});
	}

	/** El mercader, las llamas y el guardia no sueltan nada (los bandidos, lo suyo). */
	static boolean noLoot(Set<String> tags) {
		return !tags.isEmpty() && tags.contains(Rules.TAG) && !tags.contains(Rules.BANDIT);
	}

	static HeraldiaConfig cfg() {
		return HeraldiaConfig.get();
	}

	static String name(ServerLevel level, long village) {
		String[] n = Names.of(level.getSeed(), RoadLayout.px(village), RoadLayout.pz(village));
		return n[0] + " " + n[1];
	}

	// --- entidades sobrantes ---

	private static void onLoad(Entity e, ServerLevel level) {
		if (Rules.orphan(e.entityTags(), e.getUUID(), DE.keySet())) {
			LOGGER.info("Heraldia: caravanas: quitada una entidad de una caravana que ya no está en camino ({} en {} {} {})",
					BuiltInRegistries.ENTITY_TYPE.getKey(e.getType()).getPath(), e.getBlockX(), e.getBlockY(), e.getBlockZ());
			e.discard();
		}
	}

	private static void onDeath(LivingEntity e) {
		Set<String> tags = e.entityTags();
		if (tags.isEmpty() || !tags.contains(Rules.MERCHANT)) {
			return;
		}
		Caravan c = DE.get(e.getUUID());
		if (c != null) {
			c.journey.finish(Journey.End.LOST);
			finish(c);       // ya, en el mismo tick: las llamas no llegan a soltar nada
		}
	}

	// --- cada tick: solo la caravana activa y el sorteo de cada minuto ---

	private static void tick(MinecraftServer server) {
		int t = server.getTickCount();
		if (!ACTIVE.isEmpty() && t % Journey.EVERY == 0 && !cfg().getBool(ENABLED)) {
			clean(Journey.End.CLEANUP);      // desactivadas con /heraldia reload: se van las que había
		}
		if (!ACTIVE.isEmpty() && t % Journey.EVERY == 0) {
			for (Caravan c : new ArrayList<>(ACTIVE.values())) {
				update(c);
			}
		}
		if (t % Rules.DRAW_TICKS == 0) {
			draw(server, t);
		}
	}

	private static void draw(MinecraftServer server, long t) {
		HeraldiaConfig cfg = cfg();
		ServerLevel level = server.overworld();
		if (!Rules.outcome(cfg.getBool(ENABLED), ACTIVE.size() + searching, cfg.getInt(MAX_ACTIVE), t, lastEnd, cfg.getInt(FREQUENCY),
				level.getRandom().nextDouble())) {
			return;
		}
		List<ServerPlayer> candidates = new ArrayList<>();
		for (ServerPlayer p : level.players()) {
			if (!p.isSpectator() && p.isAlive()) {
				candidates.add(p);
			}
		}
		if (candidates.isEmpty()) {
			return;
		}
		ServerPlayer p = candidates.get(level.getRandom().nextInt(candidates.size()));
		search(level, p.getBlockX(), p.getBlockZ(), null, msg -> LOGGER.debug("Heraldia: caravanas: sorteo junto a {}: {}",
				p.getGameProfile().name(), msg.getString()));
	}

	/**
	 * Busca el tramo junto a (x, z) fuera del hilo del servidor y, de vuelta en él, crea la caravana.
	 *
	 * @param asalto true/false para fijar si la asaltan (el comando); null, con caravanas.prob_asalto
	 * @param aviso  lo que se dice si no sale (o cuando sale)
	 */
	static void search(ServerLevel level, int x, int z, @Nullable Boolean ambush, Consumer<Component> notice) {
		MinecraftServer server = level.getServer();
		long seed = level.getRandom().nextLong();
		searching++;
		CompletableFuture.supplyAsync(() -> {
					RoadLayout t = Roads.layout(level);
					if (t == null) {
						return null;
					}
					int r = Segment.DIST_MAX;
					return Segment.choose(t.routesIn(x - r, z - r, x + r, z + r), x, z, seed);
				}, Util.backgroundExecutor())
				.whenCompleteAsync((segment, e) -> {
					searching--;
					if (e != null) {
						LOGGER.error("Heraldia: caravanas: no se pudo buscar el camino junto a {} {}", x, z, e);
						return;
					}
					create(level, segment, ambush, seed, notice);
				}, server);
	}

	// --- crear ---

	/** La altura del suelo en (x, z) si su chunk está cargado con entidades; si no, null (no carga nada). */
	static @Nullable BlockPos ground(ServerLevel level, int x, int z) {
		BlockPos p = new BlockPos(x, level.getMinY(), z);
		if (!level.isPositionEntityTicking(p)) {
			return null;
		}
		return new BlockPos(x, level.getHeight(Heightmap.Types.MOTION_BLOCKING_NO_LEAVES, x, z), z);
	}

	/** ¿Hay camino de verdad en (x, z)? Solo con su 3 × 3 cargado; null si no se puede saber sin cargar chunks. */
	static @Nullable Boolean hasRoad(ServerLevel level, int x, int z) {
		int n = 0;
		for (int dx = -1; dx <= 1; dx++) {
			for (int dz = -1; dz <= 1; dz++) {
				BlockPos s = ground(level, x + dx, z + dz);
				if (s == null) {
					return null;
				}
				n += Ground.ofRoad(level.getBlockState(s.below())) ? 1 : 0;
			}
		}
		return Ground.hasRoad(n);
	}

	private static void create(ServerLevel level, @Nullable Segment segment, @Nullable Boolean ambush, long seed, Consumer<Component> notice) {
		HeraldiaConfig cfg = cfg();
		if (!cfg.getBool(ENABLED)) {
			notice.accept(Texts.t("heraldia.caravanas.desactivadas"));
			return;
		}
		if (ACTIVE.size() >= cfg.getInt(MAX_ACTIVE)) {
			notice.accept(Texts.t("heraldia.caravanas.limite", ACTIVE.size(), cfg.getInt(MAX_ACTIVE)));
			return;
		}
		if (segment == null) {
			notice.accept(Texts.t("heraldia.caravanas.sin_camino", Segment.DIST_MAX));
			return;
		}
		// la salida: cargada y con camino de verdad
		BlockPos departure = ground(level, segment.x(0), segment.z(0));
		if (departure == null || !Boolean.TRUE.equals(hasRoad(level, segment.x(0), segment.z(0)))) {
			notice.accept(Texts.t("heraldia.caravanas.sin_camino", Segment.DIST_MAX));
			LOGGER.info("Heraldia: caravanas: sin camino en la salida {} {} ({})", segment.x(0), segment.z(0), departure == null ? "sin cargar" : "no hay camino");
			return;
		}
		// en un mundo existente el camino puede acabar antes: el tramo llega hasta el último vértice cargado con camino
		int until = segment.vertices() - 1;
		for (int k = 1; k < segment.vertices(); k++) {
			Boolean there = hasRoad(level, segment.x(k), segment.z(k));
			if (there == null) {
				break;              // aún sin cargar: se mira al llegar
			}
			if (!there) {
				until = k - 1;
				break;
			}
		}
		if (until < 2) {
			notice.accept(Texts.t("heraldia.caravanas.sin_camino", Segment.DIST_MAX));
			LOGGER.info("Heraldia: caravanas: el camino de {} {} se acaba enseguida", segment.x(0), segment.z(0));
			return;
		}
		Segment t = until < segment.vertices() - 1 ? segment.until(until) : segment;
		java.util.Random rnd = new java.util.Random(seed);
		boolean ambushed = ambush != null ? ambush : Rules.ambush(cfg.getInt(AMBUSH_PROB), rnd.nextDouble());
		int ambushAt = ambushed ? Journey.ambushPoint(t.vertices(), rnd.nextDouble()) : -1;
		int llamas = Rules.llamas(rnd.nextDouble());
		boolean guard = Rules.guard(rnd.nextDouble());
		int id = ++counter;
		// rumbo: del vértice de salida al siguiente
		double dx = t.x(1) - t.x(0), dz = t.z(1) - t.z(0), len = Math.max(1e-6, Math.hypot(dx, dz));
		dx /= len;
		dz /= len;
		float yaw = (float) Math.toDegrees(Math.atan2(-dx, dz));
		WanderingTrader m = EntityTypes.WANDERING_TRADER.create(level, EntitySpawnReason.EVENT);
		if (m == null) {
			return;
		}
		m.snapTo(departure.getX() + 0.5, departure.getY(), departure.getZ() + 0.5, yaw, 0f);
		m.addTag(Rules.TAG);
		m.addTag(Rules.MERCHANT);
		m.setCustomName(Texts.t("heraldia.caravanas.mercader").withStyle(ChatFormatting.GOLD));
		m.setCustomNameVisible(true);
		m.setPersistenceRequired();
		m.setDespawnDelay(Journey.MAX_TICKS + 2 * Rules.DRAW_TICKS);   // lo quita la caravana, no el reloj del vendedor
		var health = m.getAttribute(Attributes.MAX_HEALTH);
		if (health != null) {
			health.setBaseValue(MERCHANT_HEALTH);   // aguanta un asalto el tiempo de llegar a defenderlo
			m.setHealth((float) MERCHANT_HEALTH);
		}
		Journey journey = new Journey(t.vertices(), ambushAt);
		Caravan c = new Caravan(id, level, t, journey, m.getUUID(), seed);
		DE.put(m.getUUID(), c);
		if (!level.addFreshEntity(m)) {
			DE.remove(m.getUUID());
			return;
		}
		ACTIVE.put(id, c);
		// las llamas detrás, en fila; el guardia a un lado
		for (int i = 1; i <= llamas; i++) {
			TraderLlama l = EntityTypes.TRADER_LLAMA.create(level, EntitySpawnReason.EVENT);
			if (l != null) {
				l.setDespawnDelay(Journey.MAX_TICKS + 2 * Rules.DRAW_TICKS);
				add(c, l, Rules.LLAMA, departure, -dx * 2.5 * i, -dz * 2.5 * i, yaw);
			}
		}
		if (guard) {
			IronGolem g = EntityTypes.IRON_GOLEM.create(level, EntitySpawnReason.EVENT);
			if (g != null) {
				g.setPlayerCreated(true);       // no se vuelve contra los jugadores sin motivo
				add(c, g, Rules.GUARD, departure, -dz * 3, dx * 3, yaw);
			}
		}
		goTo(c, m);
		LOGGER.info("Heraldia: caravanas: sale la caravana {} de {} hacia {}: {} vértices ({} bloques) desde {} {} {} hasta {} {}, asalto {}, "
						+ "{} llamas, {}", id, c.origin, c.destination, t.vertices(), Math.round(t.length()), departure.getX(), departure.getY(), departure.getZ(),
				t.x(t.vertices() - 1), t.z(t.vertices() - 1), ambushAt < 0 ? "no" : "en el vértice " + ambushAt, llamas, guard ? "con guardia" : "sin guardia");
		StringBuilder vertices = new StringBuilder();
		for (int k = 0; k < t.vertices(); k++) {
			vertices.append(k == 0 ? "" : "; ").append(t.x(k)).append(' ').append(t.z(k));
		}
		LOGGER.info("Heraldia: caravanas: vértices de la caravana {}: {}", id, vertices);   // los sigue la prueba de servidor
		notice.accept(Texts.t("heraldia.caravanas.creada", id, c.origin, c.destination, Math.round(t.length())));
		warn(c, m, "heraldia.caravanas.sale", ChatFormatting.YELLOW, c.origin, c.destination);
	}

	static final double MERCHANT_HEALTH = 40;

	private static void add(Caravan c, Mob mob, String paper, BlockPos departure, double ox, double oz, float yaw) {
		BlockPos s = ground(c.level, (int) Math.floor(departure.getX() + 0.5 + ox), (int) Math.floor(departure.getZ() + 0.5 + oz));
		if (s == null) {
			s = departure;
		}
		mob.snapTo(s.getX() + 0.5, s.getY(), s.getZ() + 0.5, yaw, 0f);
		mob.addTag(Rules.TAG);
		mob.addTag(paper);
		mob.setPersistenceRequired();
		DE.put(mob.getUUID(), c);
		if (c.level.addFreshEntity(mob)) {
			c.escort.add(mob.getUUID());
		} else {
			DE.remove(mob.getUUID());
		}
	}

	// --- cada segundo, la caravana activa ---

	private static @Nullable Entity entity(Caravan c, UUID u) {
		Entity e = c.level.getEntity(u);
		return e == null || e.isRemoved() ? null : e;
	}

	private static void update(Caravan c) {
		Entity e = entity(c, c.merchant);
		WanderingTrader m = e instanceof WanderingTrader w ? w : null;
		int k = c.journey.next();
		int tx = c.segment.x(k), tz = c.segment.z(k);
		boolean loaded = m != null && c.level.isPositionEntityTicking(m.blockPosition())
				&& c.level.isPositionEntityTicking(new BlockPos(tx, m.getBlockY(), tz));
		double dist = m == null ? Double.MAX_VALUE : Math.hypot(m.getX() - (tx + 0.5), m.getZ() - (tz + 0.5));
		int players = m == null ? 0 : near(c.level, m, PLAYER_RADIUS).size();
		int bandits = 0;
		for (UUID u : c.bandits) {
			bandits += entity(c, u) instanceof LivingEntity l && l.isAlive() ? 1 : 0;
		}
		boolean road = true;
		if (loaded && c.checked < k) {
			Boolean there = hasRoad(c.level, tx, tz);
			road = !Boolean.FALSE.equals(there);
			if (there != null) {
				c.checked = k;
			}
		}
		Journey.Step step = c.journey.step(new Journey.View(m == null || m.isAlive(), loaded, dist, players, bandits, road));
		switch (step) {
			case END -> finish(c);
			case AMBUSH -> ambush(c, m, players);
			case CLEARED -> {
				warn(c, m, "heraldia.caravanas.superado", ChatFormatting.GREEN);
				LOGGER.info("Heraldia: caravanas: la caravana {} supera el asalto", c.id);
				goTo(c, m);
			}
			default -> goTo(c, m);
		}
	}

	/** El mercader hacia el vértice siguiente (con el objetivo de IA del vendedor) y su séquito detrás. */
	private static void goTo(Caravan c, @Nullable WanderingTrader m) {
		if (m == null || c.journey.phase() == Journey.Phase.END) {
			return;
		}
		if (c.journey.phase() == Journey.Phase.ROAD) {
			int k = c.journey.next();
			BlockPos s = ground(c.level, c.segment.x(k), c.segment.z(k));
			if (s != null) {
				m.setWanderTarget(s);
			}
		}
		Entity ahead = m;
		for (UUID u : c.escort) {
			if (entity(c, u) instanceof Mob mob) {
				boolean guard = mob.entityTags().contains(Rules.GUARD);
				Entity continues = guard ? m : ahead;
				if (mob.getTarget() == null && mob.distanceToSqr(continues) > (guard ? 36 : 16)) {
					mob.getNavigation().moveTo(continues, guard ? 0.8 : 1.2);
				}
				if (!guard) {
					ahead = mob;
				}
			}
		}
	}

	static List<ServerPlayer> near(ServerLevel level, Entity e, double radius) {
		List<ServerPlayer> out = new ArrayList<>();
		for (ServerPlayer p : level.players()) {
			if (!p.isSpectator() && p.isAlive() && Math.hypot(p.getX() - e.getX(), p.getZ() - e.getZ()) <= radius
					&& Math.abs(p.getY() - e.getY()) <= radius) {
				out.add(p);
			}
		}
		return out;
	}

	private static void warn(Caravan c, @Nullable Entity m, String key, ChatFormatting color, Object... args) {
		if (m == null) {
			return;
		}
		for (ServerPlayer p : near(c.level, m, PLAYER_RADIUS)) {
			p.sendSystemMessage(Texts.t(Texts.language(p), key, args).withStyle(color));
		}
	}

	// --- el asalto ---

	private static void ambush(Caravan c, @Nullable WanderingTrader m, int players) {
		if (m == null) {
			return;
		}
		int n = Rules.bandits(players);
		boolean boss = Rules.withBoss(n);
		// delante de la caravana, a los dos lados del camino
		int k = Math.min(c.segment.vertices() - 1, c.journey.next());
		double[] nrm = c.segment.route().normal(c.segment.vertex(k));
		double ax = (m.getX() + c.segment.x(k) + 0.5) / 2, az = (m.getZ() + c.segment.z(k) + 0.5) / 2;
		int departed = 0;
		for (int i = 0; i < n; i++) {
			double side = i % 2 == 0 ? 1 : -1, off = 7 + 2 * (i / 2);
			BlockPos s = ground(c.level, (int) Math.floor(ax + nrm[0] * side * off), (int) Math.floor(az + nrm[1] * side * off));
			if (s == null) {
				s = ground(c.level, (int) Math.floor(ax), (int) Math.floor(az));
			}
			if (s == null) {
				continue;
			}
			boolean isBoss = boss && i == 0;
			Mob b = (isBoss ? EntityTypes.VINDICATOR : EntityTypes.PILLAGER).create(c.level, EntitySpawnReason.EVENT);
			if (b == null) {
				continue;
			}
			b.snapTo(s.getX() + 0.5, s.getY(), s.getZ() + 0.5, c.level.getRandom().nextFloat() * 360f, 0f);
			// las etiquetas antes de añadirlo: la dificultad y el anclaje de Heraldia miran ENTITY_LOAD
			b.addTag(Rules.TAG);
			b.addTag(Rules.BANDIT);
			b.addTag(ModDifficulty.ANCHORED);
			b.finalizeSpawn(c.level, c.level.getCurrentDifficultyAt(s), EntitySpawnReason.EVENT, null);
			if (b instanceof Raider r) {
				r.setPatrolLeader(false);       // sin estandarte ni mal presagio
				r.setCanJoinRaid(false);
			}
			b.setCustomName(Texts.t(isBoss ? "heraldia.medianas.campamento.vindicador" : "heraldia.medianas.campamento.saqueador"));
			b.setPersistenceRequired();
			b.setTarget(m);
			DE.put(b.getUUID(), c);
			if (c.level.addFreshEntity(b)) {
				c.bandits.add(b.getUUID());
				departed++;
			} else {
				DE.remove(b.getUUID());
			}
		}
		c.level.playSound(null, m.getX(), m.getY(), m.getZ(), SoundEvents.RAID_HORN.value(), SoundSource.HOSTILE, 2f, 1.2f);
		warn(c, m, "heraldia.caravanas.asalto", ChatFormatting.RED, c.destination);
		LOGGER.info("Heraldia: caravanas: asalto a la caravana {}: {} bandidos{} en {} {}", c.id, departed, boss ? " con su jefe" : "",
				Math.round(ax), Math.round(az));
	}

	// --- el final ---

	/** Termina la caravana: premia (si llegó), avisa y quita todas sus entidades cargadas. */
	static void finish(Caravan c) {
		if (!ACTIVE.containsKey(c.id)) {
			return;
		}
		ACTIVE.remove(c.id);
		Journey.End end = c.journey.end();
		Entity m = entity(c, c.merchant);
		if (end == Journey.End.ARRIVAL && m != null) {
			arrivals++;
			reward(c, m);
		} else if (end == Journey.End.LOST) {
			losses++;
			warn(c, m, "heraldia.caravanas.perdida", ChatFormatting.RED, c.destination);
		} else if (end != Journey.End.CLEANUP) {
			warn(c, m, "heraldia.caravanas.despedida", ChatFormatting.GRAY, c.destination);
		}
		int removed = 0;
		for (UUID u : c.all()) {
			DE.remove(u);
			Entity e = entity(c, u);
			if (e != null && e.isAlive()) {      // el mercader que acaba de morir se queda (es su cadáver)
				if (u.equals(c.merchant)) {
					c.level.sendParticles(ParticleTypes.POOF, e.getX(), e.getY() + 1, e.getZ(), 12, 0.5, 0.5, 0.5, 0.02);
				}
				e.discard();
				removed++;
			}
		}
		lastEnd = c.level.getServer().getTickCount();
		LOGGER.info("Heraldia: caravanas: termina la caravana {}: {} ({} entidades quitadas, {} s en camino)", c.id, end.id, removed,
				c.journey.ticks() / 20);
	}

	private static void reward(Caravan c, Entity m) {
		int[] village = Rules.chunk(c.segment.destination());
		java.util.Random rnd = new java.util.Random(c.seed ^ 0x5DEECE66DL);
		List<ServerPlayer> players = near(c.level, m, REWARD_RADIUS);
		for (ServerPlayer p : players) {
			Rules.Reward r = Rules.reward(c.segment.vertices(), c.journey.cleared(), rnd.nextDouble());
			Map<String, String> l = Texts.language(p);
			p.getInventory().placeItemBackInInventory(new ItemStack(Items.EMERALD, r.emeralds()), Prediction.SERVER_ONLY);   // al suelo si no cabe
			MutableComponent pays = Texts.t(l, "heraldia.caravanas.paga", r.emeralds());
			if (r.withItem()) {
				Item item = BuiltInRegistries.ITEM.getValue(Identifier.parse(r.item()));
				ItemStack stack = new ItemStack(item, r.amount());
				pays = Texts.t(l, "heraldia.caravanas.paga.objeto", r.emeralds(), r.amount(), stack.getHoverName());
				p.getInventory().placeItemBackInInventory(stack, Prediction.SERVER_ONLY);
			}
			p.sendSystemMessage(Texts.t(l, "heraldia.caravanas.llegada", c.destination, pays).withStyle(ChatFormatting.GREEN));
			int rep = Quests.addReputation(p, village[0], village[1], r.reputation(), c.journey.cleared() ? "defiende la caravana" : "acompaña la caravana");
			if (r.advancement()) {
				AdvancementHolder h = c.level.getServer().getAdvancements().get(Heraldia.id(ADVANCEMENT));
				if (h != null) {
					p.getAdvancements().award(h, "hecho");
				}
			}
			LOGGER.info("Heraldia: caravanas: {} cobra {} esmeraldas{} y +{} de reputación con {} (ahora {})", p.getGameProfile().name(),
					r.emeralds(), r.withItem() ? " y " + r.amount() + " × " + r.item() : "", r.reputation(), c.destination, rep);
		}
		c.level.playSound(null, m.getX(), m.getY(), m.getZ(), SoundEvents.VILLAGER_CELEBRATE, SoundSource.NEUTRAL, 1f, 1f);
		LOGGER.info("Heraldia: caravanas: la caravana {} llega a {}{} con {} jugadores", c.id, c.destination,
				c.journey.cleared() ? " tras superar el asalto" : "", players.size());
	}

	/** Termina todas (al parar el servidor o con /heraldia caravan clear); devuelve cuántas había. */
	static int clean(Journey.End end) {
		int n = ACTIVE.size();
		for (Caravan c : new ArrayList<>(ACTIVE.values())) {
			c.journey.finish(end);
			finish(c);
		}
		return n;
	}

	// --- comandos: /heraldia caravan [spawn [raid | peaceful] | raid | list | clear] (operadores) ---

	public static LiteralArgumentBuilder<CommandSourceStack> node() {
		return Commands.literal("caravan").requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))
				.executes(Caravans::list)
				.then(Commands.literal("spawn").executes(ctx -> spawn(ctx, null))
						.then(Commands.literal("raid").executes(ctx -> spawn(ctx, true)))
						.then(Commands.literal("peaceful").executes(ctx -> spawn(ctx, false))))
				.then(Commands.literal("raid").executes(Caravans::raid))
				.then(Commands.literal("list").executes(Caravans::list))
				.then(Commands.literal("clear").executes(Caravans::clear));
	}

	private static Map<String, String> language(CommandSourceStack src) {
		ServerPlayer p = src.getPlayer();
		return p == null ? Texts.language("es_es") : Texts.language(p);
	}

	private static int spawn(CommandContext<CommandSourceStack> ctx, @Nullable Boolean ambush) {
		CommandSourceStack src = ctx.getSource();
		Map<String, String> l = language(src);
		if (!cfg().getBool(ENABLED)) {
			src.sendFailure(Texts.t(l, "heraldia.caravanas.desactivadas"));
			return 0;
		}
		if (src.getLevel().dimension() != Level.OVERWORLD) {
			src.sendFailure(Texts.t(l, "heraldia.caravanas.sin_camino", Segment.DIST_MAX));
			return 0;
		}
		BlockPos p = BlockPos.containing(src.getPosition());
		src.sendSuccess(() -> Texts.t(l, "heraldia.caravanas.buscando"), false);
		search(src.getLevel(), p.getX(), p.getZ(), ambush, c -> src.sendSuccess(() -> c, true));
		return 1;
	}

	private static int raid(CommandContext<CommandSourceStack> ctx) {
		CommandSourceStack src = ctx.getSource();
		Map<String, String> l = language(src);
		Caravan best = null;
		double bestD = Double.MAX_VALUE;
		for (Caravan c : ACTIVE.values()) {
			Entity m = entity(c, c.merchant);
			if (m != null && c.journey.phase() == Journey.Phase.ROAD && !c.journey.ambushed()) {
				double d = m.position().distanceToSqr(src.getPosition());
				if (d < bestD) {
					bestD = d;
					best = c;
				}
			}
		}
		if (best == null || !best.journey.forceAmbush()) {
			src.sendFailure(Texts.t(l, "heraldia.caravanas.asalto.ninguna"));
			return 0;
		}
		WanderingTrader m = (WanderingTrader) entity(best, best.merchant);
		ambush(best, m, m == null ? 1 : near(best.level, m, PLAYER_RADIUS).size());
		int id = best.id;
		src.sendSuccess(() -> Texts.t(l, "heraldia.caravanas.asalto.forzado", id), true);
		return 1;
	}

	private static int list(CommandContext<CommandSourceStack> ctx) {
		CommandSourceStack src = ctx.getSource();
		Map<String, String> l = language(src);
		src.sendSuccess(() -> Texts.t(l, "heraldia.caravanas.lista.titulo", ACTIVE.size(), cfg().getInt(MAX_ACTIVE)).withStyle(ChatFormatting.GOLD), false);
		if (ACTIVE.isEmpty()) {
			src.sendSuccess(() -> Texts.t(l, "heraldia.caravanas.lista.ninguna").withStyle(ChatFormatting.GRAY), false);
		}
		for (Caravan c : ACTIVE.values()) {
			Entity m = entity(c, c.merchant);
			String phase = c.journey.phase() == Journey.Phase.AMBUSH ? "asalto" : "camino";
			Component line = Texts.t(l, "heraldia.caravanas.lista.linea", c.id, c.origin, c.destination, Texts.t(l, "heraldia.caravanas.fase." + phase),
					c.journey.next(), c.journey.vertices() - 1, m == null ? "?" : m.getBlockX(), m == null ? "?" : m.getBlockY(), m == null ? "?" : m.getBlockZ());
			src.sendSuccess(() -> line, false);
		}
		return ACTIVE.size();
	}

	private static int clear(CommandContext<CommandSourceStack> ctx) {
		CommandSourceStack src = ctx.getSource();
		Map<String, String> l = language(src);
		int n = clean(Journey.End.CLEANUP);
		// y las que quedaran sueltas en chunks cargados (no debería haber: se quitan al cargarse)
		int loose = 0;
		for (ServerLevel level : src.getServer().getAllLevels()) {
			List<Entity> extra = new ArrayList<>();
			for (Entity e : level.getAllEntities()) {
				if (e.entityTags().contains(Rules.TAG)) {
					extra.add(e);
				}
			}
			for (Entity e : extra) {
				e.discard();
				loose++;
			}
		}
		int s = loose;
		src.sendSuccess(() -> Texts.t(l, "heraldia.caravanas.limpiadas", n, s), true);
		return n;
	}

	/** Para /heraldia status. */
	public static List<Component> state() {
		HeraldiaConfig cfg = cfg();
		if (!cfg.getBool(ENABLED)) {
			return List.of(Texts.t("heraldia.estado.caravanas.no"));
		}
		return List.of(Texts.t("heraldia.estado.caravanas", ACTIVE.size(), cfg.getInt(MAX_ACTIVE), cfg.getInt(FREQUENCY),
				cfg.getInt(AMBUSH_PROB), arrivals, losses));
	}

	/** Caravanas en camino (para los tests y el estado). */
	static int active() {
		return ACTIVE.size();
	}
}
