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
import java.util.EnumSet;
import java.util.HashMap;
import java.util.HashSet;
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
import net.minecraft.world.entity.animal.wolf.Wolf;
import net.minecraft.world.entity.npc.wanderingtrader.WanderingTrader;
import net.minecraft.world.entity.raid.Raider;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.level.storage.loot.parameters.LootContextParams;
import net.minecraft.core.registries.Registries;
import net.minecraft.tags.TagKey;
import org.jspecify.annotations.Nullable;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Caravans along the roads between villages (T39): the part that touches the game. The pure logic is in {@link Segment} (which
 * stretch of the canonical route it travels), {@link Journey} (its phases), {@link Rules} (when it spawns, what it is like,
 * what it pays) and {@link Ground} (whether the road really exists in the world).
 * <ul>
 * <li>Every minute, with players in the overworld, a caravan is rolled (caravanas.frecuencia %) next to one of
 * them: the nearest route within 80 blocks is searched off the server thread (the layout is in memory; it neither
 * loads nor generates chunks) and the caravan only spawns if its starting vertex is in a chunk loaded with entities and
 * the road really is there (in an existing world, not in the chunks from before the roads).</li>
 * <li>A Heraldia merchant (wandering trader) with 1-3 pack llamas and sometimes a guard golem travels about
 * 128 blocks towards the destination village: the trader's own AI goal ({@code setWanderTarget}) takes it from
 * vertex to vertex; the llamas and the guard follow it. With caravanas.prob_asalto %, halfway along 2 to 4
 * bandits spawn (those of the bandit camp: pillagers and a vindicator leader, anchored and with Heraldia's difficulty).</li>
 * <li>On arrival, each player escorting it earns emeralds (plus an item if they defended it from an ambush) and gains
 * reputation with the destination village ({@link Quests#addReputation}); defending it grants the advancement. If the
 * merchant dies, the caravan is lost and its entities drop nothing.</li>
 * <li>No per-tick work except the active caravan (one step per second). If the players move away, the road ends or
 * time runs out, it says goodbye and all its entities are removed. Nothing is saved: when the server stops the loaded ones
 * are removed and, at startup, any caravan entity that loads is removed ({@code ENTITY_LOAD}): no orphans or duplicates.</li>
 * </ul>
 * The caravanas.* options are read on each use: they reload with /heraldia reload.
 * <p>
 * The same engine moves the wayfarers ({@link Wayfarers}, the viajeros.* options): a pilgrim, a shepherd with its flock, a
 * messenger, a pair of guards or a hunter with its dog that pass along the road near a player. Their own roll (every minute,
 * half a minute after the caravans'), their own limit and rest; the same search for a stretch, the same {@link Journey}
 * (without ambush), goodbye and cleanup. No reward: they are life on the road; the shepherd and the hunter trade, and
 * attacking them costs reputation with their village of origin.
 */
public final class Caravans {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	public static final String ENABLED = "caravanas.activado", FREQUENCY = "caravanas.frecuencia", AMBUSH_PROB = "caravanas.prob_asalto",
			MAX_ACTIVE = "caravanas.max_activas";
	/** Players who count as near the merchant (those escorting it), and those who get paid on arrival. */
	public static final double PLAYER_RADIUS = 64, REWARD_RADIUS = 48;
	/** Advancement (tools/gen/caravans.py): heraldia:caravanas/defensa, criterion "hecho". */
	static final String ADVANCEMENT = "caravanas/defensa";
	private static final Map<Integer, Caravan> ACTIVE = new LinkedHashMap<>();
	/** Entity → its caravan: tagged entities missing from here are leftovers. */
	private static final Map<UUID, Caravan> BY_ENTITY = new HashMap<>();
	private static int counter, searching, arrivals, losses, searchingWayfarers, passed;
	private static long lastEnd = -Rules.WAIT_TICKS, lastWayfarerEnd = -Rules.WAIT_TICKS;

	private Caravans() {
	}

	/** A caravan on its way (server thread only). */
	static final class Caravan {
		final int id;
		final ServerLevel level;
		final Segment segment;
		final Journey journey;
		final UUID merchant;
		final List<UUID> escort = new ArrayList<>();      // llamas and guard, in marching order
		final List<UUID> bandits = new ArrayList<>();
		final String origin, destination;
		final long seed;
		/** Vertex of the segment whose road has already been checked (so it is not checked every second). */
		int checked = 0;
		/** Null: a caravan; otherwise, the wayfarer (its leader is {@link #merchant}). */
		final Wayfarers.@Nullable Kind kind;
		/** Where the pilgrim is going (the name of its shrine), or null. */
		@Nullable Component goal;
		/** Players who have already paid for hurting it (a hit counts once per encounter). */
		final Set<UUID> attackers = new HashSet<>();
		/** Ticks walking on after the end with a player in sight (wayfarers), or -1. */
		int linger = -1;

		Caravan(int id, ServerLevel level, Segment segment, Journey journey, UUID merchant, long seed) {
			this(id, level, segment, journey, merchant, seed, null);
		}

		Caravan(int id, ServerLevel level, Segment segment, Journey journey, UUID merchant, long seed, Wayfarers.@Nullable Kind kind) {
			this.kind = kind;
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

	/** One line in Heraldia.onInitialize. */
	public static void register() {
		ServerEntityEvents.ENTITY_LOAD.register(Caravans::onLoad);
		ServerLivingEntityEvents.AFTER_DEATH.register((entity, source) -> {
			hurt(entity, source, true);
			onDeath(entity);
		});
		ServerLivingEntityEvents.AFTER_DAMAGE.register((entity, source, base, taken, blocked) -> {
			if (taken > 0 && !entity.isDeadOrDying()) {
				hurt(entity, source, false);
			}
		});
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
			BY_ENTITY.clear();
			counter = searching = arrivals = losses = searchingWayfarers = passed = 0;
			lastEnd = lastWayfarerEnd = -Rules.WAIT_TICKS;
			Shrines.clear();
		});
	}

	/** The merchant, the llamas and the guard drop nothing (the bandits, their own). */
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

	// --- leftover entities ---

	private static void onLoad(Entity e, ServerLevel level) {
		if (Rules.orphan(e.entityTags(), e.getUUID(), BY_ENTITY.keySet())) {
			LOGGER.info("Heraldia: caravanas: quitada una entidad de una caravana que ya no está en camino ({} en {} {} {})",
					BuiltInRegistries.ENTITY_TYPE.getKey(e.getType()).getPath(), e.getBlockX(), e.getBlockY(), e.getBlockZ());
			e.discard();
		}
	}

	private static void onDeath(LivingEntity e) {
		Set<String> tags = e.entityTags();
		if (tags.isEmpty() || !(tags.contains(Rules.MERCHANT) || tags.contains(Wayfarers.LEADER))) {
			return;
		}
		Caravan c = BY_ENTITY.get(e.getUUID());
		if (c != null) {
			c.journey.finish(Journey.End.LOST);
			finish(c);       // now, in the same tick: the llamas never get to drop anything
		}
	}

	// --- every tick: only the active caravan and the per-minute roll ---

	private static void tick(MinecraftServer server) {
		int t = server.getTickCount();
		if (!ACTIVE.isEmpty() && t % Journey.EVERY == 0) {
			cleanDisabled();      // disabled with /heraldia reload: the existing ones leave
		}
		if (!ACTIVE.isEmpty() && t % Journey.EVERY == 0) {
			for (Caravan c : new ArrayList<>(ACTIVE.values())) {
				update(c);
			}
		}
		if (t % Rules.DRAW_TICKS == 0) {
			draw(server, t);
		}
		if (t % Rules.DRAW_TICKS == Rules.DRAW_TICKS / 2) {
			drawWayfarer(server, t);
		}
	}

	/** Caravans on the road (not counting the wayfarers). */
	static int caravans() {
		int n = 0;
		for (Caravan c : ACTIVE.values()) {
			n += c.kind == null ? 1 : 0;
		}
		return n;
	}

	static int wayfarers() {
		return ACTIVE.size() - caravans();
	}

	/** Ends the caravans if they have been disabled, and the wayfarers if they (or their kind) have. */
	private static void cleanDisabled() {
		HeraldiaConfig cfg = cfg();
		for (Caravan c : new ArrayList<>(ACTIVE.values())) {
			boolean on = c.kind == null ? cfg.getBool(ENABLED) : cfg.getBool(Wayfarers.ENABLED) && cfg.getBool(c.kind.option());
			if (!on) {
				c.journey.finish(Journey.End.CLEANUP);
				finish(c);
			}
		}
	}

	private static void draw(MinecraftServer server, long t) {
		HeraldiaConfig cfg = cfg();
		ServerLevel level = server.overworld();
		if (!Rules.outcome(cfg.getBool(ENABLED), caravans() + searching, cfg.getInt(MAX_ACTIVE), t, lastEnd, cfg.getInt(FREQUENCY),
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
	 * Searches for the segment near (x, z) off the server thread and, back on it, creates the caravan.
	 *
	 * @param ambush true/false to force whether it is ambushed (the command); null, with caravanas.prob_asalto
	 * @param notice what is said if it does not spawn (or when it does)
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

	// --- create ---

	/** Ground height at (x, z) if its chunk is loaded with entities; otherwise null (loads nothing). */
	static @Nullable BlockPos ground(ServerLevel level, int x, int z) {
		BlockPos p = new BlockPos(x, level.getMinY(), z);
		if (!level.isPositionEntityTicking(p)) {
			return null;
		}
		return new BlockPos(x, level.getHeight(Heightmap.Types.MOTION_BLOCKING_NO_LEAVES, x, z), z);
	}

	/** Is there really a road at (x, z)? Only with its 3 × 3 loaded; null if it cannot be known without loading chunks. */
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
		if (caravans() >= cfg.getInt(MAX_ACTIVE)) {
			notice.accept(Texts.t("heraldia.caravanas.limite", caravans(), cfg.getInt(MAX_ACTIVE)));
			return;
		}
		Segment t = ready(level, segment, notice);
		if (t == null) {
			return;
		}
		BlockPos departure = ground(level, t.x(0), t.z(0));
		java.util.Random rnd = new java.util.Random(seed);
		boolean ambushed = ambush != null ? ambush : Rules.ambush(cfg.getInt(AMBUSH_PROB), rnd.nextDouble());
		int ambushAt = ambushed ? Journey.ambushPoint(t.vertices(), rnd.nextDouble()) : -1;
		int llamas = Rules.llamas(rnd.nextDouble());
		boolean guard = Rules.guard(rnd.nextDouble());
		int id = ++counter;
		// heading: from the starting vertex to the next
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
		m.setDespawnDelay(Journey.MAX_TICKS + 2 * Rules.DRAW_TICKS);   // the caravan removes it, not the trader's clock
		var health = m.getAttribute(Attributes.MAX_HEALTH);
		if (health != null) {
			health.setBaseValue(MERCHANT_HEALTH);   // it withstands an ambush long enough for someone to come defend it
			m.setHealth((float) MERCHANT_HEALTH);
		}
		Journey journey = new Journey(t.vertices(), ambushAt);
		Caravan c = new Caravan(id, level, t, journey, m.getUUID(), seed);
		BY_ENTITY.put(m.getUUID(), c);
		if (!level.addFreshEntity(m)) {
			BY_ENTITY.remove(m.getUUID());
			return;
		}
		ACTIVE.put(id, c);
		// llamas behind, in a line; the guard to one side
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
				g.setPlayerCreated(true);       // it does not turn on the players for no reason
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
		LOGGER.info("Heraldia: caravanas: vértices de la caravana {}: {}", id, vertices);   // the server test follows them
		notice.accept(Texts.t("heraldia.caravanas.creada", id, c.origin, c.destination, Math.round(t.length())));
		warn(c, m, "heraldia.caravanas.sale", ChatFormatting.YELLOW, c.origin, c.destination);
	}

	static final double MERCHANT_HEALTH = 40;

	/**
	 * The segment as it really is in the world, or null (and it says why): its start loaded and with a real road and, in an
	 * existing world where the road may end earlier, up to the last loaded vertex with a road (at least 2 vertices).
	 */
	static @Nullable Segment ready(ServerLevel level, @Nullable Segment segment, Consumer<Component> notice) {
		if (segment == null) {
			notice.accept(Texts.t("heraldia.caravanas.sin_camino", Segment.DIST_MAX));
			return null;
		}
		// the start: loaded and with a real road
		BlockPos departure = ground(level, segment.x(0), segment.z(0));
		if (departure == null || !Boolean.TRUE.equals(hasRoad(level, segment.x(0), segment.z(0)))) {
			notice.accept(Texts.t("heraldia.caravanas.sin_camino", Segment.DIST_MAX));
			LOGGER.info("Heraldia: caravanas: sin camino en la salida {} {} ({})", segment.x(0), segment.z(0), departure == null ? "sin cargar" : "no hay camino");
			return null;
		}
		// in an existing world the road may end earlier: the segment goes up to the last loaded vertex with a road
		int until = segment.vertices() - 1;
		for (int k = 1; k < segment.vertices(); k++) {
			Boolean there = hasRoad(level, segment.x(k), segment.z(k));
			if (there == null) {
				break;              // not loaded yet: checked on arrival
			}
			if (!there) {
				until = k - 1;
				break;
			}
		}
		if (until < 2) {
			notice.accept(Texts.t("heraldia.caravanas.sin_camino", Segment.DIST_MAX));
			LOGGER.info("Heraldia: caravanas: el camino de {} {} se acaba enseguida", segment.x(0), segment.z(0));
			return null;
		}
		return until < segment.vertices() - 1 ? segment.until(until) : segment;
	}

	static void add(Caravan c, Mob mob, String paper, BlockPos departure, double ox, double oz, float yaw) {
		BlockPos s = ground(c.level, (int) Math.floor(departure.getX() + 0.5 + ox), (int) Math.floor(departure.getZ() + 0.5 + oz));
		if (s == null) {
			s = departure;
		}
		mob.snapTo(s.getX() + 0.5, s.getY(), s.getZ() + 0.5, yaw, 0f);
		mob.addTag(Rules.TAG);
		mob.addTag(paper);
		mob.setPersistenceRequired();
		BY_ENTITY.put(mob.getUUID(), c);
		if (c.level.addFreshEntity(mob)) {
			c.escort.add(mob.getUUID());
		} else {
			BY_ENTITY.remove(mob.getUUID());
		}
	}

	// --- every second, the active caravan ---

	static @Nullable Entity entity(Caravan c, UUID u) {
		Entity e = c.level.getEntity(u);
		return e == null || e.isRemoved() ? null : e;
	}

	private static void update(Caravan c) {
		Entity e = entity(c, c.merchant);
		Mob m = e instanceof Mob w ? w : null;
		if (c.linger >= 0) {
			linger(c, m);
			return;
		}
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
			case END -> {
				if (!startLinger(c, m)) {
					finish(c);
				}
			}
			case AMBUSH -> ambush(c, m, players);
			case CLEARED -> {
				warn(c, m, "heraldia.caravanas.superado", ChatFormatting.GREEN);
				LOGGER.info("Heraldia: caravanas: la caravana {} supera el asalto", c.id);
				goTo(c, m);
			}
			default -> goTo(c, m);
		}
	}

	/**
	 * The merchant (or the wayfarer's leader) towards the next vertex (a trader with its own AI goal; a golem with its
	 * navigation, when it is not fighting) and its escort behind.
	 */
	private static void goTo(Caravan c, @Nullable Mob m) {
		if (m == null || c.journey.phase() == Journey.Phase.END) {
			return;
		}
		if (c.journey.phase() == Journey.Phase.ROAD) {
			int k = c.journey.next();
			BlockPos s = ground(c.level, c.segment.x(k), c.segment.z(k));
			if (s != null) {
				head(m, s);
			}
		}
		if (c.kind != null) {
			follow(c, m);
			return;
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

	// --- the ambush ---

	private static void ambush(Caravan c, @Nullable Mob m, int players) {
		if (m == null) {
			return;
		}
		int n = Rules.bandits(players);
		boolean boss = Rules.withBoss(n);
		// ahead of the caravan, on both sides of the road
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
			// tags before adding it: Heraldia's difficulty and anchoring look at ENTITY_LOAD
			b.addTag(Rules.TAG);
			b.addTag(Rules.BANDIT);
			b.addTag(ModDifficulty.ANCHORED);
			b.finalizeSpawn(c.level, c.level.getCurrentDifficultyAt(s), EntitySpawnReason.EVENT, null);
			if (b instanceof Raider r) {
				r.setPatrolLeader(false);       // no banner and no bad omen
				r.setCanJoinRaid(false);
			}
			b.setCustomName(Texts.t(isBoss ? "heraldia.medianas.campamento.vindicador" : "heraldia.medianas.campamento.saqueador"));
			b.setPersistenceRequired();
			b.setTarget(m);
			BY_ENTITY.put(b.getUUID(), c);
			if (c.level.addFreshEntity(b)) {
				c.bandits.add(b.getUUID());
				departed++;
			} else {
				BY_ENTITY.remove(b.getUUID());
			}
		}
		c.level.playSound(null, m.getX(), m.getY(), m.getZ(), SoundEvents.RAID_HORN.value(), SoundSource.HOSTILE, 2f, 1.2f);
		warn(c, m, "heraldia.caravanas.asalto", ChatFormatting.RED, c.destination);
		LOGGER.info("Heraldia: caravanas: asalto a la caravana {}: {} bandidos{} en {} {}", c.id, departed, boss ? " con su jefe" : "",
				Math.round(ax), Math.round(az));
	}

	// --- the end ---

	/** Ends the caravan: rewards (if it arrived), notifies and removes all its loaded entities. */
	static void finish(Caravan c) {
		if (!ACTIVE.containsKey(c.id)) {
			return;
		}
		ACTIVE.remove(c.id);
		Journey.End end = c.journey.end();
		Entity m = entity(c, c.merchant);
		if (c.kind != null) {
			finishWayfarer(c, end);
			return;
		}
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
			BY_ENTITY.remove(u);
			Entity e = entity(c, u);
			if (e != null && e.isAlive()) {      // the merchant who just died stays (it is its corpse)
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
			p.getInventory().placeItemBackInInventory(new ItemStack(Items.EMERALD, r.emeralds()), Prediction.SERVER_ONLY);   // on the ground if it does not fit
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

	/** Ends them all (when the server stops or with /heraldia caravan clear); returns how many there were. */
	static int clean(Journey.End end) {
		int n = ACTIVE.size();
		for (Caravan c : new ArrayList<>(ACTIVE.values())) {
			c.journey.finish(end);
			finish(c);
		}
		return n;
	}

	// --- the wayfarers: the same engine, their own roll, limit and rest ---

	private static void drawWayfarer(MinecraftServer server, long t) {
		HeraldiaConfig cfg = cfg();
		ServerLevel level = server.overworld();
		if (!Wayfarers.outcome(cfg.getBool(Wayfarers.ENABLED), wayfarers() + searchingWayfarers, cfg.getInt(Wayfarers.MAX_ACTIVE), t,
				lastWayfarerEnd, cfg.getInt(Wayfarers.FREQUENCY), level.getRandom().nextDouble())) {
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
		searchWayfarer(level, p.getBlockX(), p.getBlockZ(), null, msg -> LOGGER.debug("Heraldia: viajeros: sorteo junto a {}: {}",
				p.getGameProfile().name(), msg.getString()));
	}

	/** What the search off the server thread finds: the stretch near the player and, for a pilgrim, its shrine. */
	record Plan(@Nullable Segment segment, Shrines.@Nullable Shrine shrine) {
	}

	/**
	 * Searches for the segment near (x, z) (and, if a pilgrim may set off, the nearest shrine) off the server thread and,
	 * back on it, creates the wayfarer.
	 *
	 * @param forced the kind (the command, which ignores the zone and the hour); null: the draw chooses
	 */
	static void searchWayfarer(ServerLevel level, int x, int z, Wayfarers.@Nullable Kind forced, Consumer<Component> notice) {
		MinecraftServer server = level.getServer();
		long seed = level.getRandom().nextLong();
		boolean pilgrim = (forced == null || forced == Wayfarers.Kind.PILGRIM) && cfg().getBool(Wayfarers.Kind.PILGRIM.option());
		searchingWayfarers++;
		CompletableFuture.supplyAsync(() -> {
					RoadLayout t = Roads.layout(level);
					if (t == null) {
						return new Plan(null, null);
					}
					int r = Segment.DIST_MAX;
					Segment s = Segment.choose(t.routesIn(x - r, z - r, x + r, z + r), x, z, seed);
					return new Plan(s, s != null && pilgrim ? Shrines.nearest(level, x, z) : null);
				}, Util.backgroundExecutor())
				.whenCompleteAsync((plan, e) -> {
					searchingWayfarers--;
					if (e != null) {
						LOGGER.error("Heraldia: viajeros: no se pudo buscar el camino junto a {} {}", x, z, e);
						return;
					}
					createWayfarer(level, plan, forced, x, z, seed, notice);
				}, server);
	}

	/** Village family of the biome at {@code pos} (the tags heraldia:<family>), or null outside all of them. */
	static @Nullable String zone(ServerLevel level, BlockPos pos) {
		var biome = level.getBiome(pos);
		for (String f : Wayfarers.FAMILIES) {
			if (biome.is(TagKey.create(Registries.BIOME, Heraldia.id(f)))) {
				return f;
			}
		}
		return null;
	}

	/** Is another caravan or wayfarer on the road near there? (So that two never crowd the same stretch.) */
	private static boolean crowded(ServerLevel level, BlockPos p) {
		for (Caravan c : ACTIVE.values()) {
			Entity m = entity(c, c.merchant);
			if (c.level == level && m != null && Math.hypot(m.getX() - p.getX(), m.getZ() - p.getZ()) < Wayfarers.SPACING) {
				return true;
			}
		}
		return false;
	}

	private static void createWayfarer(ServerLevel level, Plan plan, Wayfarers.@Nullable Kind forced, int px, int pz, long seed,
									   Consumer<Component> notice) {
		HeraldiaConfig cfg = cfg();
		if (!cfg.getBool(Wayfarers.ENABLED)) {
			notice.accept(Texts.t("heraldia.viajeros.desactivados"));
			return;
		}
		if (forced != null && !cfg.getBool(forced.option())) {
			notice.accept(Texts.t("heraldia.viajeros.tipo_desactivado", Texts.t("heraldia.viajeros." + forced.id)));
			return;
		}
		if (wayfarers() >= cfg.getInt(Wayfarers.MAX_ACTIVE)) {
			notice.accept(Texts.t("heraldia.viajeros.limite", wayfarers(), cfg.getInt(Wayfarers.MAX_ACTIVE)));
			return;
		}
		Segment t = ready(level, plan.segment(), notice);
		if (t == null) {
			return;
		}
		BlockPos departure = ground(level, t.x(0), t.z(0));
		if (forced == null && crowded(level, departure)) {
			LOGGER.debug("Heraldia: viajeros: ya hay alguien en camino cerca de {} {}", departure.getX(), departure.getZ());
			return;
		}
		java.util.Random rnd = new java.util.Random(seed);
		String zone = zone(level, departure);
		// the pilgrim, towards its shrine: the stretch as it is or the other way round (it still passes in front of the player)
		Segment toShrine = null;
		Shrines.Shrine shrine = plan.shrine();
		if (shrine != null) {
			Segment r = t.reversed();
			if (Wayfarers.towards(t, shrine.x(), shrine.z())) {
				toShrine = t;
			} else if (Boolean.TRUE.equals(hasRoad(level, r.x(0), r.z(0))) && Math.hypot(r.x(0) - px, r.z(0) - pz) >= Segment.DIST_MIN) {
				toShrine = r;
			}
		}
		Wayfarers.Kind kind = forced;
		if (kind == null) {
			Set<Wayfarers.Kind> enabled = EnumSet.noneOf(Wayfarers.Kind.class);
			for (Wayfarers.Kind k : Wayfarers.Kind.values()) {
				if (cfg.getBool(k.option())) {
					enabled.add(k);
				}
			}
			kind = Wayfarers.choose(enabled, zone, level.isBrightOutside(), toShrine != null, rnd.nextDouble());
		}
		if (kind == null) {
			notice.accept(Texts.t("heraldia.viajeros.ninguno"));
			return;
		}
		if (kind == Wayfarers.Kind.PILGRIM) {
			if (toShrine == null) {
				notice.accept(Texts.t("heraldia.viajeros.sin_santuario", Wayfarers.SHRINE_RANGE));
				return;
			}
			t = toShrine;
			departure = ground(level, t.x(0), t.z(0));
			if (departure == null) {
				return;
			}
		}
		double dx = t.x(1) - t.x(0), dz = t.z(1) - t.z(0), len = Math.max(1e-6, Math.hypot(dx, dz));
		dx /= len;
		dz /= len;
		float yaw = (float) Math.toDegrees(Math.atan2(-dx, dz));
		int id = ++counter;
		List<String> colors = new ArrayList<>();
		if (kind == Wayfarers.Kind.SHEPHERD) {
			for (int i = Wayfarers.flock(rnd.nextDouble()); i > 0; i--) {
				colors.add(Wayfarers.woolColor(zone, rnd.nextDouble()));
			}
		}
		String origin = name(level, t.origin());
		Mob m = Wayfaring.leader(level, kind, zone, origin, colors);
		if (m == null) {
			return;
		}
		m.snapTo(departure.getX() + 0.5, departure.getY(), departure.getZ() + 0.5, yaw, 0f);
		m.addTag(Rules.TAG);
		m.addTag(Wayfarers.LEADER);
		m.addTag(kind.tag());
		m.setPersistenceRequired();
		Journey journey = new Journey(t.vertices(), -1);
		Caravan c = new Caravan(id, level, t, journey, m.getUUID(), seed, kind);
		if (shrine != null && kind == Wayfarers.Kind.PILGRIM) {
			c.goal = Texts.t("heraldia.unicas." + shrine.id().getPath().substring("unicas/".length()) + ".nombre");
		}
		BY_ENTITY.put(m.getUUID(), c);
		if (!level.addFreshEntity(m)) {
			BY_ENTITY.remove(m.getUUID());
			return;
		}
		ACTIVE.put(id, c);
		Wayfaring.companions(c, m, departure, dx, dz, yaw, colors);
		goTo(c, m);
		LOGGER.info("Heraldia: viajeros: sale {} {} de {} hacia {}: {} vértices ({} bloques) desde {} {} {} hasta {} {}, zona {}, {} entidades{}",
				kind.id, id, c.origin, c.destination, t.vertices(), Math.round(t.length()), departure.getX(), departure.getY(), departure.getZ(),
				t.x(t.vertices() - 1), t.z(t.vertices() - 1), zone == null ? "ninguna" : zone, 1 + c.escort.size(),
				shrine != null && kind == Wayfarers.Kind.PILGRIM ? ", camino de " + shrine.id() + " en " + shrine.x() + " " + shrine.z() : "");
		StringBuilder vertices = new StringBuilder();
		for (int k = 0; k < t.vertices(); k++) {
			vertices.append(k == 0 ? "" : "; ").append(t.x(k)).append(' ').append(t.z(k));
		}
		LOGGER.info("Heraldia: viajeros: vértices de {}: {}", id, vertices);   // the server test follows them
		Component where = c.goal != null ? c.goal : Component.literal(c.destination);
		notice.accept(Texts.t("heraldia.viajeros.creado", id, Texts.t("heraldia.viajeros." + kind.id), c.origin, where, Math.round(t.length())));
		for (ServerPlayer p : near(level, m, PLAYER_RADIUS)) {
			Map<String, String> l = Texts.language(p);
			p.sendOverlayMessage(Texts.t(l, "heraldia.viajeros." + kind.id + ".pasa", c.goal != null ? c.goal : c.destination)
					.withStyle(ChatFormatting.GRAY));
		}
	}

	/** The leader towards {@code s}: a trader with its own goal (it keeps it), a golem with its navigation when not fighting. */
	static void head(Mob m, BlockPos s) {
		if (m instanceof WanderingTrader w) {
			w.setWanderTarget(s);
		} else if (m.getTarget() == null) {
			m.getNavigation().moveTo(s.getX() + 0.5, s.getY(), s.getZ() + 0.5, 1.0);
		}
	}

	/** The wayfarer's companions behind it: the flock around the shepherd, the second guard beside the first; the dog follows its owner. */
	private static void follow(Caravan c, Mob m) {
		for (UUID u : c.escort) {
			if (entity(c, u) instanceof Mob mob && mob.getTarget() == null && !(mob instanceof Wolf w && w.isTame())) {
				boolean partner = mob.entityTags().contains(Wayfarers.PARTNER);
				if (mob.distanceToSqr(m) > (partner ? 9 : 20)) {
					mob.getNavigation().moveTo(m, partner ? 1.0 : 1.15);
				}
			}
		}
	}

	/**
	 * At the end of its stretch, with a player in sight, the wayfarer does not vanish: it walks on towards its village (at
	 * most to its plaza) and is removed when nobody is within {@link Wayfarers#LINGER_RADIUS} blocks, or after
	 * {@link Wayfarers#LINGER_TICKS}. Not if it died, the players left or it is a cleanup.
	 */
	private static boolean startLinger(Caravan c, @Nullable Mob m) {
		Journey.End end = c.journey.end();
		if (c.kind == null || m == null || !m.isAlive() || end == Journey.End.LOST || end == Journey.End.FAR || end == Journey.End.CLEANUP
				|| near(c.level, m, Wayfarers.LINGER_RADIUS).isEmpty()) {
			return false;
		}
		c.linger = 0;
		Segment s = c.segment;
		int beyond = Math.max(0, Math.min(s.route().vertices() - 1, s.vertex(s.vertices() - 1) + s.step() * Segment.VILLAGE_MARGIN));
		BlockPos p = ground(c.level, (int) Math.floor(s.route().x(beyond)), (int) Math.floor(s.route().z(beyond)));
		if (p != null) {
			head(m, p);
		}
		return true;
	}

	private static void linger(Caravan c, @Nullable Mob m) {
		c.linger += Journey.EVERY;
		if (m == null || !m.isAlive() || c.linger >= Wayfarers.LINGER_TICKS || !c.level.isPositionEntityTicking(m.blockPosition())
				|| near(c.level, m, Wayfarers.LINGER_RADIUS).isEmpty()) {
			finish(c);
		} else {
			follow(c, m);
		}
	}

	/** Removes a wayfarer's loaded entities (no reward: they are life on the road). */
	private static void finishWayfarer(Caravan c, Journey.End end) {
		passed++;
		int removed = 0;
		for (UUID u : c.all()) {
			BY_ENTITY.remove(u);
			Entity e = entity(c, u);
			if (e != null && e.isAlive()) {
				if (u.equals(c.merchant)) {
					c.level.sendParticles(ParticleTypes.POOF, e.getX(), e.getY() + 1, e.getZ(), 12, 0.5, 0.5, 0.5, 0.02);
				}
				e.discard();
				removed++;
			}
		}
		lastWayfarerEnd = c.level.getServer().getTickCount();
		LOGGER.info("Heraldia: viajeros: termina {} {}: {} ({} entidades quitadas, {} s en camino{})", c.kind.id, c.id, end.id, removed,
				c.journey.ticks() / 20, c.linger >= 0 ? ", " + c.linger / 20 + " s más a la vista" : "");
	}

	/**
	 * A player hurts (or kills) one of a wayfarer's entities: reputation with its village of origin drops (a hit once per
	 * player and encounter, every death), as with a village's villagers and golems; the guards defend each other. A golem
	 * inside a village is already counted by the quests (Quests.attack).
	 */
	private static void hurt(LivingEntity e, DamageSource source, boolean death) {
		Set<String> tags = e.entityTags();
		if (tags.isEmpty() || !tags.contains(Rules.TAG) || !(source.getEntity() instanceof ServerPlayer p)) {
			return;
		}
		Caravan c = BY_ENTITY.get(e.getUUID());
		if (c == null || c.kind == null) {
			return;
		}
		boolean golem = e instanceof IronGolem;
		if (golem && Quests.village(c.level, e.blockPosition()) != null) {
			return;
		}
		if (!death && !c.attackers.add(p.getUUID())) {
			return;
		}
		if (c.kind == Wayfarers.Kind.PATROL && !death) {
			for (UUID u : c.all()) {
				if (entity(c, u) instanceof IronGolem g && g.getTarget() == null) {
					g.setTarget(p);
				}
			}
		}
		if (!cfg().getBool(Quests.REPUTATION)) {
			return;
		}
		int[] village = Rules.chunk(c.segment.origin());
		Quests.addReputation(p, village[0], village[1], Wayfarers.penalty(Wayfarers.role(tags, golem), death),
				(death ? "mata" : "golpea") + " a un viajero (" + c.kind.id + ")");
		if (!death) {
			p.sendSystemMessage(Texts.t(Texts.language(p), "heraldia.viajeros.atacado", c.origin).withStyle(ChatFormatting.RED));
		}
	}

	private static void listWayfarers(CommandSourceStack src, Map<String, String> l) {
		int n = wayfarers();
		src.sendSuccess(() -> Texts.t(l, "heraldia.viajeros.lista.titulo", n, cfg().getInt(Wayfarers.MAX_ACTIVE)).withStyle(ChatFormatting.GOLD), false);
		for (Caravan c : ACTIVE.values()) {
			if (c.kind == null) {
				continue;
			}
			Entity m = entity(c, c.merchant);
			Component line = Texts.t(l, "heraldia.viajeros.lista.linea", c.id, Texts.t(l, "heraldia.viajeros." + c.kind.id), c.origin,
					c.goal != null ? c.goal : c.destination, c.journey.next(), c.journey.vertices() - 1,
					m == null ? "?" : m.getBlockX(), m == null ? "?" : m.getBlockY(), m == null ? "?" : m.getBlockZ());
			src.sendSuccess(() -> line, false);
		}
	}

	/** /heraldia caravan wayfarer [pilgrim | shepherd | messenger | patrol | hunter] (operators). */
	private static LiteralArgumentBuilder<CommandSourceStack> wayfarerNode() {
		LiteralArgumentBuilder<CommandSourceStack> n = Commands.literal("wayfarer").executes(ctx -> wayfarer(ctx, null));
		for (Wayfarers.Kind k : Wayfarers.Kind.values()) {
			n.then(Commands.literal(k.command).executes(ctx -> wayfarer(ctx, k)));
		}
		return n;
	}

	private static int wayfarer(CommandContext<CommandSourceStack> ctx, Wayfarers.@Nullable Kind kind) {
		CommandSourceStack src = ctx.getSource();
		Map<String, String> l = language(src);
		if (!cfg().getBool(Wayfarers.ENABLED)) {
			src.sendFailure(Texts.t(l, "heraldia.viajeros.desactivados"));
			return 0;
		}
		if (src.getLevel().dimension() != Level.OVERWORLD) {
			src.sendFailure(Texts.t(l, "heraldia.caravanas.sin_camino", Segment.DIST_MAX));
			return 0;
		}
		BlockPos p = BlockPos.containing(src.getPosition());
		src.sendSuccess(() -> Texts.t(l, "heraldia.caravanas.buscando"), false);
		searchWayfarer(src.getLevel(), p.getX(), p.getZ(), kind, c -> src.sendSuccess(() -> c, true));
		return 1;
	}

	// --- commands: /heraldia caravan [spawn [raid | peaceful] | raid | list | clear | wayfarer [<kind>]] (operators) ---

	public static LiteralArgumentBuilder<CommandSourceStack> node() {
		return Commands.literal("caravan").requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))
				.executes(Caravans::list)
				.then(Commands.literal("spawn").executes(ctx -> spawn(ctx, null))
						.then(Commands.literal("raid").executes(ctx -> spawn(ctx, true)))
						.then(Commands.literal("peaceful").executes(ctx -> spawn(ctx, false))))
				.then(Commands.literal("raid").executes(Caravans::raid))
				.then(Commands.literal("list").executes(Caravans::list))
				.then(Commands.literal("clear").executes(Caravans::clear))
				.then(wayfarerNode());
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
			if (m != null && c.kind == null && c.journey.phase() == Journey.Phase.ROAD && !c.journey.ambushed()) {
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
		Mob m = entity(best, best.merchant) instanceof Mob mob ? mob : null;
		ambush(best, m, m == null ? 1 : near(best.level, m, PLAYER_RADIUS).size());
		int id = best.id;
		src.sendSuccess(() -> Texts.t(l, "heraldia.caravanas.asalto.forzado", id), true);
		return 1;
	}

	private static int list(CommandContext<CommandSourceStack> ctx) {
		CommandSourceStack src = ctx.getSource();
		Map<String, String> l = language(src);
		int caravans = caravans();
		src.sendSuccess(() -> Texts.t(l, "heraldia.caravanas.lista.titulo", caravans, cfg().getInt(MAX_ACTIVE)).withStyle(ChatFormatting.GOLD), false);
		if (caravans == 0) {
			src.sendSuccess(() -> Texts.t(l, "heraldia.caravanas.lista.ninguna").withStyle(ChatFormatting.GRAY), false);
		}
		for (Caravan c : ACTIVE.values()) {
			Entity m = entity(c, c.merchant);
			if (c.kind != null) {
				continue;
			}
			String phase = c.journey.phase() == Journey.Phase.AMBUSH ? "asalto" : "camino";
			Component line = Texts.t(l, "heraldia.caravanas.lista.linea", c.id, c.origin, c.destination, Texts.t(l, "heraldia.caravanas.fase." + phase),
					c.journey.next(), c.journey.vertices() - 1, m == null ? "?" : m.getBlockX(), m == null ? "?" : m.getBlockY(), m == null ? "?" : m.getBlockZ());
			src.sendSuccess(() -> line, false);
		}
		listWayfarers(src, l);
		return ACTIVE.size();
	}

	private static int clear(CommandContext<CommandSourceStack> ctx) {
		CommandSourceStack src = ctx.getSource();
		Map<String, String> l = language(src);
		int n = clean(Journey.End.CLEANUP);
		// and any left loose in loaded chunks (there should be none: they are removed when they load)
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

	/** For /heraldia status. */
	public static List<Component> state() {
		HeraldiaConfig cfg = cfg();
		List<Component> out = new ArrayList<>();
		out.add(!cfg.getBool(ENABLED) ? Texts.t("heraldia.estado.caravanas.no")
				: Texts.t("heraldia.estado.caravanas", caravans(), cfg.getInt(MAX_ACTIVE), cfg.getInt(FREQUENCY), cfg.getInt(AMBUSH_PROB), arrivals, losses));
		out.add(!cfg.getBool(Wayfarers.ENABLED) ? Texts.t("heraldia.estado.viajeros.no")
				: Texts.t("heraldia.estado.viajeros", wayfarers(), cfg.getInt(Wayfarers.MAX_ACTIVE), cfg.getInt(Wayfarers.FREQUENCY), passed));
		return out;
	}

	/** Caravans on their way (for the tests and the status). */
	static int active() {
		return ACTIVE.size();
	}
}
