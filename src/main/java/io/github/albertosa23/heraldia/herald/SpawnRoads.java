package io.github.albertosa23.heraldia.herald;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.serialization.Codec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.arena.Arena;
import io.github.albertosa23.heraldia.choice.Choice;
import io.github.albertosa23.heraldia.choice.Choices;
import io.github.albertosa23.heraldia.command.Texts;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.roads.BuiltRoads;
import io.github.albertosa23.heraldia.roads.RoadLayout;
import io.github.albertosa23.heraldia.roads.SpawnRoadLayout;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.concurrent.CompletableFuture;
import net.fabricmc.fabric.api.attachment.v1.AttachmentRegistry;
import net.fabricmc.fabric.api.attachment.v1.AttachmentType;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.fabricmc.fabric.api.event.player.UseEntityCallback;
import net.minecraft.ChatFormatting;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.Identifier;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.tags.BlockTags;
import net.minecraft.util.Util;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.EntityTypes;
import net.minecraft.world.entity.npc.villager.Villager;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.SpawnEggItem;
import net.minecraft.world.level.LightLayer;
import net.minecraft.world.level.block.BedBlock;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.Rotation;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.chunk.LevelChunk;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.level.levelgen.RandomState;
import net.minecraft.world.level.levelgen.structure.templatesystem.StructurePlaceSettings;
import net.minecraft.world.level.levelgen.structure.templatesystem.StructureTemplate;
import net.minecraft.world.phys.AABB;
import org.jspecify.annotations.Nullable;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * The roads out of the Herald's House (casa_heraldo.caminos.*; the layout in roads/SpawnRoadLayout and
 * tools/gen/spawn_roads.py): BUILT, not generated, in chunks that already exist, spread over ticks as the town is.
 * <ul>
 * <li>When: right after a town is placed (Building, through {@link HeraldHouse#placed}); in a world whose town came
 * before this feature, only with /heraldia herald roads (an operator): a town already standing is never touched on its
 * own. The arena road is built with the rest if the arena already stands, and otherwise when the arena is placed, if
 * this world has these roads. What was built is saved ({@link Saved}, a new attachment): nothing is ever built twice,
 * and the command builds only what is missing.</li>
 * <li>Steps (one per tick, the next ones wait {@link #REST} ticks after a slow one): the chunks of each road (loaded
 * or generated, then paved: {@link BuiltRoads#pave}), its lamp posts and signs, the huts (each one whole, then its beds
 * set again), and, {@link #LIGHT_WAIT} ticks later, a check that every road column outside the protected ring has
 * light (logged).</li>
 * <li>The huts: at most casa_heraldo.caminos.aldeanos villagers in all (the owner's cap: {@link #MAX}), one per hut,
 * the guide's included; with no guide yet one place is kept for it. A site that is under water, too steep or on a
 * structure is skipped.</li>
 * <li>The guide: a click (not sneaking) opens its conversation in the choice window (choice/: the mod's screen or the
 * container menu, never the chat), whatever dialogos.en_pantalla says; [Show me your wares] opens its vanilla trades.
 * Sneak + click trades at once.</li>
 * </ul>
 * No per-tick work when nothing is being built (one field check, from {@link HeraldHouse}'s tick).
 */
public final class SpawnRoads {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	public static final String ENABLED = "casa_heraldo.caminos.activado", VILLAGERS = "casa_heraldo.caminos.aldeanos";
	static final String K = HeraldHouse.K + "caminos.";
	static final String HUT_TAG = "heraldia_choza", GUIDE_TAG = "heraldia_guia";
	static final int REST = 2, SLOW_MS = 50, LIGHT_WAIT = 60, FOUNDATION = 10, CLEAR = 12, STEEP = 4;
	/** The guide's conversation only answers this close. */
	static final double RANGE = 8;

	private static @Nullable Blueprint blueprint;
	private static @Nullable Work work;

	private SpawnRoads() {
	}

	// --- what the generator wrote (heraldia/caminos_casa.json) ---

	/** A hut slot beside a road: its name, side (+1 right of the way out), where along the road it starts. */
	record Slot(String name, int side, int along) {
	}

	record Blueprint(SpawnRoadLayout.Params params, int[] size, int edge, int[] door, int[][] bed, int[] bell, Slot guide,
			String guideTemplate, List<Slot> slots, List<String[]> professions, int max) {
		static Blueprint read(JsonObject o) {
			JsonObject h = o.getAsJsonObject("chozas"), g = h.getAsJsonObject("guia");
			List<Slot> slots = new ArrayList<>();
			for (JsonElement e : h.getAsJsonArray("huecos")) {
				JsonObject s = e.getAsJsonObject();
				slots.add(new Slot(s.get("hueco").getAsString(), s.get("lado").getAsInt(), s.get("desde").getAsInt()));
			}
			List<String[]> prof = new ArrayList<>();
			for (JsonElement e : h.getAsJsonArray("oficios")) {
				JsonObject s = e.getAsJsonObject();
				prof.add(new String[] {s.get("oficio").getAsString(), s.get("plantilla").getAsString()});
			}
			JsonArray bed = h.getAsJsonArray("cama");
			return new Blueprint(SpawnRoadLayout.Params.read(o), ints(h.getAsJsonArray("tamano")), h.get("borde").getAsInt(),
					ints(h.getAsJsonArray("puerta")), new int[][] {ints(bed.get(0).getAsJsonArray()), ints(bed.get(1).getAsJsonArray())},
					ints(h.getAsJsonArray("campana")), new Slot(g.get("hueco").getAsString(), g.get("lado").getAsInt(),
					g.get("desde").getAsInt()), g.get("plantilla").getAsString(), List.copyOf(slots), List.copyOf(prof),
					h.get("maximo").getAsInt());
		}

		private static int[] ints(JsonArray a) {
			int[] out = new int[a.size()];
			for (int i = 0; i < out.length; i++) {
				out[i] = a.get(i).getAsInt();
			}
			return out;
		}

		static Blueprint fromJar() {
			String path = "/heraldia/caminos_casa.json";
			try (InputStream in = SpawnRoads.class.getResourceAsStream(path)) {
				if (in == null) {
					throw new IllegalStateException("Missing " + path + " in the Heraldia .jar");
				}
				return read(JsonParser.parseReader(new InputStreamReader(in, StandardCharsets.UTF_8)).getAsJsonObject());
			} catch (IOException e) {
				throw new IllegalStateException("Could not read " + path, e);
			}
		}
	}

	static Blueprint blueprint() {
		Blueprint b = blueprint;
		if (b == null) {
			b = blueprint = Blueprint.fromJar();
		}
		return b;
	}

	// --- what is saved (a new attachment, heraldia:casa_heraldo_caminos) ---

	/**
	 * What this world's roads have: whether the gates' roads were built, the huts built (by "side:slot"), the arena
	 * the arena road joins (its box's minimum corner) and the guide.
	 */
	public record Saved(boolean built, List<String> huts, Optional<BlockPos> arena) {
		public static final Codec<Saved> CODEC = RecordCodecBuilder.create(i -> i.group(
				Codec.BOOL.optionalFieldOf("construidos", false).forGetter(Saved::built),
				Codec.STRING.listOf().optionalFieldOf("chozas", List.of()).forGetter(Saved::huts),
				BlockPos.CODEC.optionalFieldOf("arena").forGetter(Saved::arena)).apply(i, Saved::new));
		public static final Saved EMPTY = new Saved(false, List.of(), Optional.empty());

		Saved withBuilt() {
			return new Saved(true, huts, arena);
		}

		Saved withHut(String key) {
			List<String> l = new ArrayList<>(huts);
			if (!l.contains(key)) {
				l.add(key);
			}
			return new Saved(built, List.copyOf(l), arena);
		}

		Saved withArena(BlockPos a) {
			return new Saved(built, huts, Optional.of(a));
		}

		boolean guide() {
			return huts.stream().anyMatch(h -> h.endsWith(":guia"));
		}
	}

	static final class Type {
		static final AttachmentType<Saved> ROADS = AttachmentRegistry.create(Heraldia.id("casa_heraldo_caminos"), b -> b.persistent(Saved.CODEC));

		private Type() {
		}
	}

	static Saved saved(ServerLevel level) {
		return Optional.ofNullable(level.getAttached(Type.ROADS)).orElse(Saved.EMPTY);
	}

	private static void save(ServerLevel level, Saved s) {
		level.setAttached(Type.ROADS, s);
	}

	// --- registration and triggers ---

	/** From HeraldHouse.register. */
	static void register() {
		Type.ROADS.identifier();
		ServerLifecycleEvents.SERVER_STOPPING.register(server -> work = null);
		UseEntityCallback.EVENT.register((player, level, hand, entity, hit) -> {
			if (player instanceof ServerPlayer p && entity instanceof Villager v && entity.getType() == EntityTypes.VILLAGER
					&& !v.entityTags().isEmpty() && v.entityTags().contains(GUIDE_TAG) && hand == InteractionHand.MAIN_HAND
					&& !p.isShiftKeyDown() && !p.isSpectator() && !v.isBaby() && !v.isSleeping() && !v.isTrading()
					&& !withUse(p) && talk(p, v)) {
				return InteractionResult.SUCCESS;
			}
			return InteractionResult.PASS;
		});
	}

	static boolean enabled() {
		return HeraldiaConfig.get().getBool(ENABLED);
	}

	static boolean busy() {
		return work != null;
	}

	/** The town was just placed (Building finished): its roads, if the feature is on. */
	static void townPlaced(ServerLevel level, Grounds g, @Nullable ServerPlayer who) {
		if (!enabled()) {
			LOGGER.info("Heraldia: herald's house roads: disabled ({} = false)", ENABLED);
			return;
		}
		start(level, g, who);
	}

	/** The arena was just placed: its road, if this world has the town's roads and that road is still missing. */
	public static void arenaPlaced(ServerLevel level) {
		Grounds g = HeraldHouse.grounds();
		Saved s = saved(level);
		if (g == null || level != HeraldHouse.level() || !enabled() || !s.built() || s.arena().isPresent()) {
			return;
		}
		if (work != null || Building.busy()) {
			if (work != null) {
				work.again = true;                  // once the work in course ends
			}
			return;
		}
		LOGGER.info("Heraldia: herald's house roads: the arena was placed: building its road");
		start(level, g, null);
	}

	// --- the work ---

	enum Kind { PAVE, LAMPS, SIGN, HUT, BUILT, ARENA_DONE, WAIT, LIGHT, FINISH }

	record Step(Kind kind, int cx, int cz, @Nullable String key, int[] extra) {
		Step(Kind kind, int cx, int cz) {
			this(kind, cx, cz, null, new int[0]);
		}
	}

	static final class Work {
		final ServerLevel level;
		final Grounds g;
		final @Nullable ServerPlayer who;
		final List<Step> steps = new ArrayList<>();
		final List<RoadLayout.Route> routes = new ArrayList<>();
		final List<int[]> lamps = new ArrayList<>();      // {x, z, edge x, edge z}
		final List<String> huts = new ArrayList<>();      // keys still to try, in order
		final List<long[]> paved = new ArrayList<>();     // {x, y, z} of the paved columns (the light check)
		final RoadLayout layout;
		final RoadLayout.Seabed seabed;
		SpawnRoadLayout.@Nullable Result arenaRoad;
		@Nullable BlockPos arenaOrigin;
		@Nullable String arenaSide;
		int index, rest, ticks, allowed, newHuts, newVillagers, roads, lampsPlaced, signs, pavedN, bridged, left;
		long nanos, worst;
		boolean waiting, again;

		Work(ServerLevel level, Grounds g, @Nullable ServerPlayer who) {
			this.level = level;
			this.g = g;
			this.who = who;
			this.layout = new RoadLayout(level.getSeed(), 16, 0, (x, z) -> RoadLayout.NONE, RoadLayout.Milestones.NO_MILESTONES);
			var gen = level.getChunkSource().getGenerator();
			RandomState rs = level.getChunkSource().randomState();
			this.seabed = (x, z) -> gen.getBaseHeight(x, z, Heightmap.Types.OCEAN_FLOOR_WG, level, rs);
		}
	}

	static Map<String, int[]> gates(Grounds g) {
		Map<String, int[]> out = new LinkedHashMap<>();
		for (String side : SpawnRoadLayout.SIDES) {
			int[] rel = g.plan().gates().get(side);
			if (rel != null) {
				out.put(side, new int[] {g.ox() + rel[0], g.oz() + rel[1]});
			}
		}
		return out;
	}

	static SpawnRoadLayout.Box town(Grounds g) {
		return new SpawnRoadLayout.Box(g.ox(), g.oz(), g.maxX(), g.maxZ());
	}

	/** The arena's box in columns, or null with no arena (or the arena off). */
	static SpawnRoadLayout.@Nullable Box arenaBox() {
		int[] b = Arena.box();
		return b == null ? null : new SpawnRoadLayout.Box(b[0], b[1], b[2], b[3]);
	}

	/** Starts building whatever this world's roads are missing. False if there is nothing to build. */
	static boolean start(ServerLevel level, Grounds g, @Nullable ServerPlayer who) {
		if (work != null) {
			return false;
		}
		Blueprint bp = blueprint();
		SpawnRoadLayout.Params p = bp.params();
		Saved s = saved(level);
		long seed = level.getSeed();
		Map<String, int[]> gates = gates(g);
		SpawnRoadLayout.Box arena = arenaBox();
		boolean arenaMissing = arena != null && s.arena().isEmpty();
		Work w = new Work(level, g, who);
		int cap = Math.min(bp.max(), Math.max(0, HeraldiaConfig.get().getInt(VILLAGERS)));
		long normals = s.huts().stream().filter(h -> !h.endsWith(":guia")).count();
		w.allowed = (int) Math.max(0, cap - 1 - normals);
		String arenaSide = arena == null ? null : SpawnRoadLayout.arenaGate(gates,
				new double[] {(arena.x0() + arena.x1()) / 2.0, (arena.z0() + arena.z1()) / 2.0});
		if (!s.built()) {
			for (Map.Entry<String, int[]> e : gates.entrySet()) {
				List<double[]> nr = SpawnRoadLayout.normal(e.getValue(), e.getKey(), seed, p);
				if (e.getKey().equals(arenaSide) && arenaMissing && SpawnRoadLayout.hitsArena(nr, arena, p)) {
					nr = SpawnRoadLayout.head(nr, p);           // the arena comes too close to the bend: the arena road takes over
				}
				addRoad(w, nr, null, p);
			}
			w.steps.add(new Step(Kind.BUILT, 0, 0));
		}
		for (Slot slot : bp.slots()) {
			for (String side : gates.keySet()) {
				String key = side + ":" + slot.name();
				if (!s.huts().contains(key)) {
					w.huts.add(key);
				}
			}
		}
		if (!w.huts.isEmpty() && w.allowed > 0) {
			w.steps.add(new Step(Kind.HUT, 0, 0));
		}
		boolean guide = arenaMissing && cap >= 1 && !s.guide();
		if (w.steps.isEmpty() && !arenaMissing) {
			return false;
		}
		work = w;
		if (arenaMissing) {
			w.waiting = true;
			planArena(w, gates, arena, seed, p, guide, arenaSide, s.built());
		} else {
			finishSteps(w);
		}
		LOGGER.info("Heraldia: herald's house roads: building ({} roads, up to {} new huts{})", w.routes.size(), w.allowed,
				arenaMissing ? ", the arena road" : "");
		if (who != null) {
			who.sendSystemMessage(Texts.t(K + "construyendo").withStyle(ChatFormatting.GOLD));
		}
		return true;
	}

	private static void addRoad(Work w, List<double[]> pts, double @Nullable [] before, SpawnRoadLayout.Params p) {
		RoadLayout.Route r = SpawnRoadLayout.toRoute(pts);
		w.routes.add(r);
		w.roads++;
		Set<Long> chunks = new LinkedHashSet<>();
		for (int i = 0; i + 1 < pts.size(); i++) {      // the chunks along each segment (with the road's half width and a margin)
			double ax = pts.get(i)[0], az = pts.get(i)[1], bx = pts.get(i + 1)[0], bz = pts.get(i + 1)[1];
			double len = Math.hypot(bx - ax, bz - az);
			for (double t = 0; t <= len; t += 4) {
				double x = ax + (bx - ax) * t / Math.max(len, 1e-9), z = az + (bz - az) * t / Math.max(len, 1e-9);
				for (int dx = -1; dx <= 1; dx++) {
					for (int dz = -1; dz <= 1; dz++) {
						chunks.add(RoadLayout.pack(((int) Math.floor(x + dx * 4)) >> 4, ((int) Math.floor(z + dz * 4)) >> 4));
					}
				}
			}
		}
		for (long c : chunks) {
			w.steps.add(new Step(Kind.PAVE, RoadLayout.px(c), RoadLayout.pz(c)));
		}
		List<int[]> lamps = SpawnRoadLayout.lamps(pts, before, p);
		for (int[] l : lamps) {
			// the bridge's edge, in case the lamp's column is water: one block nearer the axis
			double[] q = nearest(pts, l[0] + 0.5, l[1] + 0.5);
			double dx = l[0] + 0.5 - q[0], dz = l[1] + 0.5 - q[1], d = Math.hypot(dx, dz);
			int ex = d == 0 ? l[0] : (int) Math.floor(q[0] + dx / d * (p.width() / 2.0 - 0.5));
			int ez = d == 0 ? l[1] : (int) Math.floor(q[1] + dz / d * (p.width() / 2.0 - 0.5));
			w.lamps.add(new int[] {l[0], l[1], ex, ez});
		}
		w.steps.add(new Step(Kind.LAMPS, w.lamps.size() - lamps.size(), w.lamps.size()));
	}

	/** The nearest point of the polyline to (x, z). */
	static double[] nearest(List<double[]> pts, double x, double z) {
		double[] best = pts.get(0);
		double bd = Double.MAX_VALUE;
		for (int i = 0; i + 1 < pts.size(); i++) {
			double ax = pts.get(i)[0], az = pts.get(i)[1], dx = pts.get(i + 1)[0] - ax, dz = pts.get(i + 1)[1] - az;
			double l2 = dx * dx + dz * dz, t = l2 == 0 ? 0 : Math.clamp(((x - ax) * dx + (z - az) * dz) / l2, 0, 1);
			double px = ax + dx * t, pz = az + dz * t, d = Math.hypot(x - px, z - pz);
			if (d < bd) {
				bd = d;
				best = new double[] {px, pz};
			}
		}
		return best;
	}

	/** The arena road's plan, off the server thread (it reads which chunks hold structures from disk). */
	private static void planArena(Work w, Map<String, int[]> gates, SpawnRoadLayout.Box arena, long seed, SpawnRoadLayout.Params p,
			boolean guide, String side, boolean built) {
		ServerLevel level = w.level;
		Map<Long, Boolean> memo = new HashMap<>();
		SpawnRoadLayout.Structures structures = (cx, cz) -> memo.computeIfAbsent(RoadLayout.pack(cx, cz),
				k -> Arena.structureAt(level, cx, cz));
		long t0 = System.nanoTime();
		CompletableFuture.supplyAsync(() -> SpawnRoadLayout.arenaPlan(gates, arena, seed, structures, town(w.g), p), Util.backgroundExecutor())
				.whenCompleteAsync((plan, err) -> {
					if (work != w) {
						return;
					}
					w.waiting = false;
					long ms = (System.nanoTime() - t0) / 1_000_000;
					if (err != null || plan == null || plan.arena() == null) {
						LOGGER.info("Heraldia: herald's house roads: no arena road ({}; {} ms)", err != null ? err.toString()
								: "the arena is too far from the town or every way crosses it", ms);
					} else {
						w.arenaRoad = plan.arena();
						w.arenaSide = plan.side();
						w.arenaOrigin = new BlockPos(arena.x0(), 0, arena.z0());
						List<double[]> pts = plan.arena().pts();
						LOGGER.info("Heraldia: herald's house roads: arena road from the {} gate, {} blocks{} ({} ms)", plan.side(),
								Math.round(SpawnRoadLayout.length(pts)), plan.arena().clear() ? "" : ", across a structure's chunks (its "
										+ "columns are left as they are)", ms);
						addRoad(w, pts, SpawnRoadLayout.joined(plan.normal(), plan.fromHead(), p), p);
						signs(w, plan, pts, p);
						if (guide) {
							w.steps.add(new Step(Kind.HUT, 0, 0, plan.side() + ":guia", new int[0]));
						}
						w.steps.add(new Step(Kind.ARENA_DONE, 0, 0));
					}
					finishSteps(w);
				}, level.getServer());
	}

	/** The two signs of the arena road: at its start (towards the arena) and by the arena's entrance (towards the town). */
	private static void signs(Work w, SpawnRoadLayout.Plan plan, List<double[]> pts, SpawnRoadLayout.Params p) {
		int[] gate = gates(w.g).get(plan.side());
		int total = (int) Math.round(SpawnRoadLayout.length(pts) + (plan.fromHead() ? p.straight() : p.length()));
		// by the gate, on the left of the way out (the guide's hut is on the right)
		double[] a = SpawnRoadLayout.axis(gate, plan.side(), 4, -(p.width() / 2.0 + 1));
		int[] r = SpawnRoadLayout.right(plan.side());
		w.steps.add(new Step(Kind.SIGN, (int) Math.floor(a[0]), (int) Math.floor(a[1]), K + "arena",
				new int[] {BuiltRoads.rotation(r[0], r[1]), total}));
		double[] e = pts.get(pts.size() - 1);
		w.steps.add(new Step(Kind.SIGN, (int) Math.floor(e[0] + p.width() / 2.0 + 1), (int) Math.floor(e[1] + 3), HeraldHouse.K + "camino.cartel",
				new int[] {BuiltRoads.rotation(-1, 0), total}));
	}

	private static void finishSteps(Work w) {
		w.steps.add(new Step(Kind.WAIT, 0, 0));
		w.steps.add(new Step(Kind.LIGHT, 0, 0));
		w.steps.add(new Step(Kind.FINISH, 0, 0));
	}

	/** One step per tick (from HeraldHouse's tick); none when nothing is being built. */
	static void tick(MinecraftServer server) {
		Work w = work;
		if (w == null) {
			return;
		}
		w.ticks++;
		if (w.rest > 0) {
			w.rest--;
			return;
		}
		if (w.index >= w.steps.size()) {
			return;                                // the arena plan is still on its way
		}
		Step st = w.steps.get(w.index);
		if (st.kind() == Kind.FINISH && w.waiting) {
			return;
		}
		long t0 = System.nanoTime();
		w.index++;
		try {
			step(w, st);
		} catch (RuntimeException e) {
			LOGGER.error("Heraldia: herald's house roads: step {} failed", st, e);
		}
		long ns = System.nanoTime() - t0;
		w.nanos += ns;
		w.worst = Math.max(w.worst, ns);
		if (ns > SLOW_MS * 1_000_000L) {
			w.rest = REST;                         // a slow step (a chunk generated): let the server breathe
		}
	}

	private static void step(Work w, Step st) {
		ServerLevel level = w.level;
		switch (st.kind()) {
			case PAVE -> {
				LevelChunk chunk = level.getChunk(st.cx(), st.cz());
				RoadLayout.Cell[] cells = new RoadLayout.Cell[256];
				BuiltRoads.Painted pr = BuiltRoads.pave(level, chunk, w.layout, w.routes, blueprint().params().width(), w.seabed,
						(x, z) -> skip(w, x, z), cells);
				w.pavedN += pr.paved();
				w.bridged += pr.bridged();
				w.left += pr.left();
				for (int i = 0; i < 256; i++) {
					if (cells[i] != null) {
						int x = chunk.getPos().getMinBlockX() + i / 16, z = chunk.getPos().getMinBlockZ() + i % 16;
						w.paved.add(new long[] {x, chunk.getHeight(Heightmap.Types.MOTION_BLOCKING_NO_LEAVES, x & 15, z & 15) + 1, z});
					}
				}
			}
			case LAMPS -> {
				for (int i = st.cx(); i < st.cz(); i++) {
					int[] l = w.lamps.get(i);
					if (BuiltRoads.lamp(level, l[0], l[1], l[2], l[3], (x, z) -> skip(w, x, z) || onHutSlot(w, x, z))) {
						w.lampsPlaced++;
					}
				}
			}
			case SIGN -> {
				Map<String, String> es = Texts.texts("es_es");
				Component first = Texts.t(es, st.key()), second = Texts.t(es, HeraldHouse.K + "camino.cartel2", st.extra()[1]);
				if (BuiltRoads.sign(level, st.cx(), st.cz(), st.extra()[0], first, second, (x, z) -> skip(w, x, z) || onHutSlot(w, x, z))) {
					w.signs++;
				}
			}
			case HUT -> {
				if (st.key() != null) {
					hut(w, st.key());                  // the guide's
				} else if (!w.huts.isEmpty() && w.allowed > 0) {
					hut(w, w.huts.remove(0));
					if (!w.huts.isEmpty() && w.allowed > 0) {
						w.steps.add(w.index, new Step(Kind.HUT, 0, 0));   // the next one, next tick
					}
				}
			}
			case BUILT -> save(level, saved(level).withBuilt());
			case ARENA_DONE -> {
				if (w.arenaOrigin != null) {
					save(level, saved(level).withArena(w.arenaOrigin));
				}
			}
			case WAIT -> w.rest = LIGHT_WAIT;
			case LIGHT -> light(w);
			case FINISH -> finish(w);
		}
	}

	/** Columns the roads never touch: the town's footprint and the arena's box. */
	private static boolean skip(Work w, int x, int z) {
		if (w.g.inColumns(x, z)) {
			return true;
		}
		SpawnRoadLayout.Box a = arenaBox();
		return a != null && a.in(x, z, 0);
	}

	/** Is (x, z) on one of the huts' places (built or not: the guide's hut may come later)? */
	private static boolean onHutSlot(Work w, int x, int z) {
		Blueprint bp = blueprint();
		for (Map.Entry<String, int[]> e : gates(w.g).entrySet()) {
			List<Slot> all = new ArrayList<>(bp.slots());
			all.add(bp.guide());
			for (Slot s : all) {
				int[] a = SpawnRoadLayout.hutCell(e.getValue(), e.getKey(), s.side(), s.along(), bp.size()[0], bp.edge(), 0, 0);
				int[] b = SpawnRoadLayout.hutCell(e.getValue(), e.getKey(), s.side(), s.along(), bp.size()[0], bp.edge(),
						bp.size()[0] - 1, bp.size()[2] - 1);
				if (x >= Math.min(a[0], b[0]) && x <= Math.max(a[0], b[0]) && z >= Math.min(a[1], b[1]) && z <= Math.max(a[1], b[1])) {
					return true;
				}
			}
		}
		return false;
	}

	// --- the huts ---

	/** The hut "side:slot": its site checked, the ground prepared, the template placed and its beds set again. */
	private static void hut(Work w, String key) {
		Blueprint bp = blueprint();
		String side = key.substring(0, key.indexOf(':')), name = key.substring(key.indexOf(':') + 1);
		boolean guide = name.equals(bp.guide().name());
		Slot slot = guide ? bp.guide() : bp.slots().stream().filter(s -> s.name().equals(name)).findFirst().orElse(null);
		int[] gate = gates(w.g).get(side);
		if (slot == null || gate == null || saved(w.level).huts().contains(key)) {
			return;
		}
		String template;
		if (guide) {
			template = bp.guideTemplate();
		} else {
			int order = bp.slots().indexOf(slot) * SpawnRoadLayout.SIDES.size() + SpawnRoadLayout.SIDES.indexOf(side);
			template = bp.professions().get(order % bp.professions().size())[1];
		}
		ServerLevel level = w.level;
		Optional<StructureTemplate> t = level.getStructureTemplateManager().get(Identifier.parse(template));
		if (t.isEmpty()) {
			LOGGER.error("Heraldia: herald's house roads: missing template {}", template);
			return;
		}
		int sx = bp.size()[0], sz = bp.size()[2];
		int[] frame = SpawnRoadLayout.hutFrame(gate, side, slot.side(), slot.along(), sx, bp.edge());
		// the ground: the road's surface in front of the door
		int[] front = SpawnRoadLayout.hutCell(gate, side, slot.side(), slot.along(), sx, bp.edge(), bp.door()[0], -1);
		int y0 = ground(level, front[0], front[1]);
		String why = null;
		SpawnRoadLayout.Box arena = arenaBox();
		BlockPos.MutableBlockPos pos = new BlockPos.MutableBlockPos();
		for (int lx = 0; lx < sx && why == null; lx++) {
			for (int lz = 0; lz < sz && why == null; lz++) {
				int[] c = SpawnRoadLayout.hutCell(gate, side, slot.side(), slot.along(), sx, bp.edge(), lx, lz);
				LevelChunk chunk = level.getChunk(c[0] >> 4, c[1] >> 4);
				int y = ground(level, c[0], c[1]);
				if (!level.getBlockState(pos.set(c[0], y, c[1])).getFluidState().isEmpty()) {
					why = "water";
				} else if (Math.abs(y - y0) > STEEP) {
					why = "too steep";
				} else if (w.g.inColumns(c[0], c[1]) || arena != null && arena.in(c[0], c[1], 2)) {
					why = "the town or the arena";
				} else if (!BuiltRoads.boxes(level, chunk).stream().allMatch(b -> !b.isInside(c[0], y + 1, c[1]))) {
					why = "a structure";
				}
			}
		}
		if (why != null) {
			LOGGER.info("Heraldia: herald's house roads: no hut {} ({} at its site)", key, why);
			return;
		}
		// foundation down to the ground and room above (trees, a hillside)
		for (int lx = 0; lx < sx; lx++) {
			for (int lz = 0; lz < sz; lz++) {
				int[] c = SpawnRoadLayout.hutCell(gate, side, slot.side(), slot.along(), sx, bp.edge(), lx, lz);
				for (int y = y0 - 1; y > y0 - FOUNDATION; y--) {
					BlockState s = level.getBlockState(pos.set(c[0], y, c[1]));
					if (!s.isAir() && s.getFluidState().isEmpty() && !s.canBeReplaced()) {
						break;
					}
					level.setBlock(pos, Blocks.COBBLESTONE.defaultBlockState(), BuiltRoads.FLAGS);
				}
				for (int y = y0 + bp.size()[1]; y <= y0 + CLEAR; y++) {
					if (!level.getBlockState(pos.set(c[0], y, c[1])).isAir()) {
						level.setBlock(pos, Blocks.AIR.defaultBlockState(), BuiltRoads.FLAGS);
					}
				}
			}
		}
		Rotation rot = switch (frame[0]) {
			case 1 -> Rotation.CLOCKWISE_90;
			case 2 -> Rotation.CLOCKWISE_180;
			case 3 -> Rotation.COUNTERCLOCKWISE_90;
			default -> Rotation.NONE;
		};
		BlockPos origin = new BlockPos(frame[1], y0, frame[2]);
		StructurePlaceSettings settings = new StructurePlaceSettings().setRotation(rot).setIgnoreEntities(false).setFinalizeEntities(false);
		t.get().placeInWorld(level, origin, origin, settings, level.getRandom(), BuiltRoads.FLAGS);
		int beds = 0;          // a bed's two halves, set again (as the town's: a half may have been dropped)
		for (Block b : BuiltInRegistries.BLOCK) {
			if (b instanceof BedBlock) {
				for (StructureTemplate.StructureBlockInfo info : t.get().filterBlocks(origin, settings, b)) {
					if (!level.getBlockState(info.pos()).equals(info.state())) {
						level.setBlock(info.pos(), info.state(), BuiltRoads.FLAGS);
						beds++;
					}
				}
			}
		}
		AABB box = new AABB(frame[1] - 8, y0 - 2, frame[2] - 8, frame[1] + 9, y0 + 8, frame[2] + 9);
		int villagers = 0;
		for (Villager v : level.getEntitiesOfClass(Villager.class, box, v -> v.entityTags().contains(HUT_TAG))) {
			villagers++;
			if (guide && v.entityTags().contains(GUIDE_TAG)) {
				v.setCustomName(Texts.t(K + "guia.nombre"));
				v.setCustomNameVisible(true);
			}
		}
		save(level, saved(level).withHut(key));
		w.newHuts++;
		w.newVillagers++;
		if (!guide) {
			w.allowed--;
		}
		LOGGER.info("Heraldia: herald's house roads: hut {} ({}) at {} {} {}{}", key, template, origin.getX(), y0, origin.getZ(),
				beds > 0 ? ", " + beds + " bed halves set again" : "");
		if (villagers == 0) {
			LOGGER.warn("Heraldia: herald's house roads: the hut {} has no villager", key);
		}
	}

	/** The ground block's y at a column (under any tree trunk or leaves). */
	static int ground(ServerLevel level, int x, int z) {
		LevelChunk chunk = level.getChunk(x >> 4, z >> 4);
		int y = chunk.getHeight(Heightmap.Types.MOTION_BLOCKING_NO_LEAVES, x & 15, z & 15);
		BlockPos.MutableBlockPos pos = new BlockPos.MutableBlockPos(x, y, z);
		while (y > level.getMinY() && (level.getBlockState(pos.set(x, y, z)).is(BlockTags.LOGS)
				|| level.getBlockState(pos).is(BlockTags.LEAVES) || level.getBlockState(pos).canBeReplaced()
				&& level.getBlockState(pos).getFluidState().isEmpty())) {
			y--;
		}
		return y;
	}

	// --- the end ---

	/** How many road columns outside the protected ring have no block light (logged; a monster could spawn there). */
	private static void light(Work w) {
		int dark = 0, checked = 0;
		BlockPos.MutableBlockPos pos = new BlockPos.MutableBlockPos();
		for (long[] c : w.paved) {
			int x = (int) c[0], z = (int) c[2];
			if (w.g.inArea(x, z) || w.level.getChunkSource().getChunkNow(x >> 4, z >> 4) == null) {
				continue;
			}
			checked++;
			if (w.level.getBrightness(LightLayer.BLOCK, pos.set(x, (int) c[1], z)) == 0) {
				dark++;
			}
		}
		LOGGER.info("Heraldia: herald's house roads: light: {} of {} road columns outside the protected ring are dark", dark, checked);
	}

	private static void finish(Work w) {
		work = null;
		Saved s = saved(w.level);
		LOGGER.info("Heraldia: herald's house roads: built in {} ticks ({} ms on the server thread, the slowest step {} ms): {} roads, "
						+ "{} columns paved, {} on bridges, {} left, {} lamp posts, {} signs, {} new huts, {} new villagers ({} huts in all)",
				w.ticks, w.nanos / 1_000_000, w.worst / 1_000_000, w.roads, w.pavedN, w.bridged, w.left, w.lampsPlaced, w.signs, w.newHuts,
				w.newVillagers, s.huts().size());
		if (w.who != null && !w.who.hasDisconnected()) {
			w.who.sendSystemMessage(Texts.t(K + "hechos", w.roads, w.newHuts, w.newVillagers).withStyle(ChatFormatting.GOLD));
		}
		if (w.again) {
			arenaPlaced(w.level);
		}
	}

	// --- /heraldia herald roads ---

	static int command(CommandContext<CommandSourceStack> ctx) {
		CommandSourceStack src = ctx.getSource();
		if (!enabled()) {
			src.sendFailure(Texts.t(K + "desactivados"));
			return 0;
		}
		Grounds g = HeraldHouse.grounds();
		ServerLevel level = HeraldHouse.level();
		if (g == null || level == null) {
			src.sendFailure(Texts.t(HeraldHouse.K + "no_existe"));
			return 0;
		}
		if (work != null || Building.busy()) {
			src.sendFailure(Texts.t(K + "ocupado"));
			return 0;
		}
		if (!start(level, g, src.getPlayer())) {
			src.sendSuccess(() -> Texts.t(K + "nada"), false);
			return 0;
		}
		src.sendSuccess(() -> Texts.t(K + "construyendo"), true);
		return 1;
	}

	// --- the guide ---

	private static boolean withUse(ServerPlayer p) {
		var s = p.getMainHandItem();
		return s.is(Items.NAME_TAG) || s.is(Items.LEAD) || s.getItem() instanceof SpawnEggItem;
	}

	private static boolean near(ServerPlayer p, Villager v) {
		return v.isAlive() && v.level() == p.level() && v.distanceTo(p) <= RANGE;
	}

	/** Is this villager the road guide? */
	public static boolean isGuide(Villager v) {
		return !v.entityTags().isEmpty() && v.entityTags().contains(GUIDE_TAG);
	}

	/**
	 * The guide's first page; false if no window can open (then the click trades, as with any villager). Also from
	 * /heraldia talk with (operators and the server tests: a simulated player's click does not reach the callback).
	 */
	public static boolean talk(ServerPlayer p, Villager v) {
		v.getLookControl().setLookAt(p);
		v.playAmbientSound();
		Map<String, String> l = Texts.language(p);
		BlockPos arena = Arena.center();
		List<Choice.Line> lines = new ArrayList<>();
		lines.add(line(l, "guia.saludo"));
		if (arena != null && v.level() == HeraldHouse.level()) {
			int blocks = (int) (Math.round(Math.hypot(arena.getX() - v.getX(), arena.getZ() - v.getZ()) / 10.0) * 10);
			lines.add(line(l, "guia.linea1"));
			lines.add(new Choice.Line(Choices.text(Texts.t(l, K + "guia.linea2", blocks), l), Choice.WHITE, false));
		} else {
			lines.add(line(l, "guia.sin_arena"));
		}
		LOGGER.info("Heraldia: herald's house roads: {} talks with the guide", p.getGameProfile().name());
		return page(p, v, lines, List.of(option(l, "more", "mas", Choice.AQUA), option(l, "trade", "tratar", Choice.GREEN),
				option(l, "bye", "adios", Choice.GRAY)));
	}

	private static Choice.Line line(Map<String, String> l, String key) {
		return new Choice.Line(Choices.text(Texts.t(l, K + key), l), Choice.WHITE, false);
	}

	private static Choice.Option option(Map<String, String> l, String id, String key, int color) {
		return new Choice.Option(id, Choices.text(Texts.t(l, K + "guia.boton." + key), l), color, "");
	}

	private static boolean page(ServerPlayer p, Villager v, List<Choice.Line> lines, List<Choice.Option> options) {
		Choice.Prompt prompt = new Choice.Prompt(v.getDisplayName(), lines, options);
		return Choices.show(p, "guide", prompt, pl -> near(pl, v), (pl, id) -> picked(pl, v, id), true);
	}

	private static boolean picked(ServerPlayer p, Villager v, String id) {
		Map<String, String> l = Texts.language(p);
		switch (id) {
			case "more" -> page(p, v, List.of(line(l, "guia.mas1"), line(l, "guia.mas2"), line(l, "guia.mas3")),
					List.of(option(l, "trade", "tratar", Choice.GREEN), option(l, "bye", "adios", Choice.GRAY)));
			case "trade" -> v.mobInteract(p, InteractionHand.MAIN_HAND);   // as the villagers' conversations do (dialogue/)
			case "bye" -> page(p, v, List.of(line(l, "guia.adios")), List.of(option(l, "close", "cerrar", Choice.GRAY)));
			default -> {
			}
		}
		return false;
	}
}
