package io.github.albertosa23.heraldia.quests;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Random;

/**
 * Each village's board, pure and deterministic logic (T38): with the seed, the village's chunk, the rotation
 * period and what is around (the candidates, which {@link Quests} searches for off the server thread), it always gives
 * the same board of 2 to 4 quests. No saved data: a board is rebuilt identically after a server restart.
 * <p>The first is always a bring-items quest; the second, defeating a guardian if there is a unique nearby (otherwise,
 * exploring); the others, at random among what there is (exploring, traveling to a neighboring village, the arena, a
 * farther guardian or another bring quest).
 */
public final class Generator {
	/** Ticks in a game day. */
	public static final long DAY = 24000L;
	public static final int MIN = 2, MAX = 4;
	/** Search radius for guardians and places to explore, in blocks. */
	public static final int GUARDIAN_RADIUS = 4000, PLACE_RADIUS = 1500;
	/** Waves that can be asked for in the arena. */
	static final int[] WAVES = {3, 5, 8};

	/** An item to bring: id, minimum and maximum amount, and emeralds it pays. */
	public record Item(String id, int min, int max, int emeralds) {
	}

	/** A candidate site: id (unique, structure or name of the neighboring village), block and distance to the village. */
	public record Objective(String id, int x, int z, int distance) {
	}

	/** What is around a village, sorted from nearest to farthest. */
	public record Candidates(String family, List<Objective> guardians, List<Objective> places, List<Objective> neighbors, boolean arena) {
		public Candidates {
			guardians = List.copyOf(guardians);
			places = List.copyOf(places);
			neighbors = List.copyOf(neighbors);
		}

		public static Candidates alone(String family) {
			return new Candidates(family, List.of(), List.of(), List.of(), false);
		}
	}

	static final List<Item> FOOD = List.of(
			new Item("minecraft:bread", 12, 24, 3), new Item("minecraft:baked_potato", 16, 32, 3),
			new Item("minecraft:cooked_chicken", 8, 16, 3), new Item("minecraft:cooked_cod", 8, 16, 3),
			new Item("minecraft:pumpkin_pie", 4, 8, 3), new Item("minecraft:cooked_porkchop", 8, 16, 3),
			new Item("minecraft:cookie", 16, 32, 2), new Item("minecraft:apple", 8, 16, 2));
	/** Ores and ingots of moderate value (no diamonds, emeralds or netherite). */
	static final List<Item> ORES = List.of(
			new Item("minecraft:coal", 16, 32, 3), new Item("minecraft:raw_iron", 8, 16, 4),
			new Item("minecraft:raw_copper", 16, 32, 3), new Item("minecraft:iron_ingot", 6, 12, 4),
			new Item("minecraft:redstone", 16, 32, 3), new Item("minecraft:lapis_lazuli", 8, 16, 4),
			new Item("minecraft:gold_ingot", 4, 8, 4), new Item("minecraft:amethyst_shard", 8, 16, 3));
	/** Biome materials of each village family (themes.FAMILIES). */
	static final Map<String, List<Item>> BIOME = Map.ofEntries(
			Map.entry("llanuras", List.of(new Item("minecraft:wheat", 24, 48, 3), new Item("minecraft:hay_block", 4, 8, 3),
					new Item("minecraft:white_wool", 8, 16, 3))),
			Map.entry("bosque", List.of(new Item("minecraft:oak_log", 16, 32, 3), new Item("minecraft:birch_log", 16, 32, 3),
					new Item("minecraft:honeycomb", 3, 6, 4))),
			Map.entry("oscuro", List.of(new Item("minecraft:dark_oak_log", 16, 32, 3),
					new Item("minecraft:brown_mushroom", 8, 16, 2), new Item("minecraft:red_mushroom", 8, 16, 2))),
			Map.entry("taiga", List.of(new Item("minecraft:spruce_log", 16, 32, 3), new Item("minecraft:sweet_berries", 16, 32, 2),
					new Item("minecraft:leather", 6, 12, 3))),
			Map.entry("nieve", List.of(new Item("minecraft:snowball", 16, 32, 2), new Item("minecraft:packed_ice", 8, 16, 3),
					new Item("minecraft:potato", 16, 32, 2))),
			Map.entry("desierto", List.of(new Item("minecraft:sandstone", 16, 32, 2), new Item("minecraft:cactus", 8, 16, 2),
					new Item("minecraft:rabbit_hide", 4, 8, 3))),
			Map.entry("sabana", List.of(new Item("minecraft:acacia_log", 16, 32, 3), new Item("minecraft:white_wool", 8, 16, 3),
					new Item("minecraft:melon_slice", 16, 32, 2))),
			Map.entry("jungla", List.of(new Item("minecraft:bamboo", 24, 48, 2), new Item("minecraft:cocoa_beans", 8, 16, 3),
					new Item("minecraft:jungle_log", 16, 32, 3))),
			Map.entry("pantano", List.of(new Item("minecraft:lily_pad", 4, 8, 3), new Item("minecraft:mangrove_log", 16, 32, 3),
					new Item("minecraft:slime_ball", 4, 8, 4))),
			Map.entry("cerezos", List.of(new Item("minecraft:cherry_log", 16, 32, 3), new Item("minecraft:pink_petals", 8, 16, 2),
					new Item("minecraft:honey_bottle", 2, 4, 3))),
			Map.entry("badlands", List.of(new Item("minecraft:terracotta", 16, 32, 2), new Item("minecraft:red_sand", 16, 32, 2),
					new Item("minecraft:gold_nugget", 16, 32, 3))),
			Map.entry("costa", List.of(new Item("minecraft:kelp", 24, 48, 2), new Item("minecraft:dried_kelp_block", 4, 8, 3),
					new Item("minecraft:ink_sac", 6, 12, 3))));
	/** Rewards of each type (besides the emeralds of bring quests, which go per item). */
	static final int XP_BRING = 20, XP_PLACE = 40, XP_GUARDIAN = 120, XP_WAVE = 10;
	static final int EM_PLACE = 4, EM_JOURNEY = 4, EM_GUARDIAN = 8, EM_FAR_GUARDIAN = 12, FAR = 2000;

	private Generator() {
	}

	/** Board rotation period: it changes every {@code days} game days (by the world clock, which never stops). */
	public static long period(long gameTime, int days) {
		return Math.floorDiv(gameTime, Math.max(1, days) * DAY);
	}

	/** World tick at which the period starts. */
	public static long start(long period, int days) {
		return period * Math.max(1, days) * DAY;
	}

	/** Ticks left until the next period. */
	public static long remaining(long gameTime, int days) {
		long length = Math.max(1, days) * DAY;
		return length - Math.floorMod(gameTime, length);
	}

	static long mix(long z) {
		z = (z ^ (z >>> 33)) * 0xff51afd7ed558ccdL;
		z = (z ^ (z >>> 33)) * 0xc4ceb9fe1a85ec53L;
		return z ^ (z >>> 33);
	}

	static long seed(long seed, int ax, int az, long period) {
		return mix(seed ^ mix(((long) ax << 32) ^ (az & 0xffffffffL)) ^ mix(period * 0x9E3779B97F4A7C15L + 0x7AB1));
	}

	/** The items a village of that family can ask for (food, its biome and ores). */
	public static List<Item> items(String family) {
		List<Item> out = new ArrayList<>(FOOD);
		out.addAll(BIOME.getOrDefault(family, List.of()));
		out.addAll(ORES);
		return out;
	}

	/** The board of the village starting at chunk (ax, az) in that period. */
	public static List<Quest> board(long seed, int ax, int az, long period, Candidates c) {
		Random r = new Random(seed(seed, ax, az, period));
		int n = MIN + r.nextInt(MAX - MIN + 1);
		List<Quest> out = new ArrayList<>();
		List<String> used = new ArrayList<>();
		out.add(bring(r, c.family(), ax, az, period, 0, used));
		if (!c.guardians().isEmpty()) {
			out.add(guardian(r, c, ax, az, period, 1, false, used));
		} else if (!c.places().isEmpty()) {
			out.add(place(r, c, ax, az, period, 1, used));
		} else {
			out.add(bring(r, c.family(), ax, az, period, 1, used));
		}
		List<Type> rest = new ArrayList<>();
		if (!c.places().isEmpty()) {
			rest.add(Type.EXPLORE);
		}
		if (!c.neighbors().isEmpty()) {
			rest.add(Type.JOURNEY);
		}
		if (c.arena()) {
			rest.add(Type.ARENA);
		}
		if (c.guardians().size() > 1) {
			rest.add(Type.GUARDIAN);
		}
		rest.add(Type.BRING);
		java.util.Collections.shuffle(rest, r);
		for (Type t : rest) {
			if (out.size() >= n) {
				break;
			}
			int h = out.size();
			Quest e = switch (t) {
				case BRING -> bring(r, c.family(), ax, az, period, h, used);
				case GUARDIAN -> guardian(r, c, ax, az, period, h, true, used);
				case EXPLORE -> place(r, c, ax, az, period, h, used);
				case JOURNEY -> journey(r, c, ax, az, period, h, used);
				case ARENA -> arena(r, ax, az, period, h);
			};
			if (e != null) {
				out.add(e);
			}
		}
		return List.copyOf(out);
	}

	private static Quest bring(Random r, String family, int ax, int az, long period, int h, List<String> used) {
		// 40 % food, 30 % biome (if the family has any), 30 % ores; no repeated item on the same board
		Item o = null;
		for (int attempt = 0; attempt < 8 && (o == null || used.contains(o.id())); attempt++) {
			int k = r.nextInt(10);
			List<Item> list = k < 4 ? FOOD : k < 7 ? BIOME.getOrDefault(family, FOOD) : ORES;
			o = list.get(r.nextInt(list.size()));
		}
		used.add(o.id());
		int steps = (o.max() - o.min()) / 4;
		int amount = o.min() + 4 * r.nextInt(steps + 1);
		int emeralds = o.emeralds() + (amount > (o.min() + o.max()) / 2 ? 1 : 0);
		return new Quest(ax, az, period, h, Type.BRING, o.id(), Math.min(amount, o.max()), 0, 0, emeralds, XP_BRING);
	}

	/** A guardian: the first, one of the two nearest; the second ("far"), the farthest one left. */
	private static Quest guardian(Random r, Candidates c, int ax, int az, long period, int h, boolean far, List<String> used) {
		List<Objective> free = c.guardians().stream().filter(o -> !used.contains("g:" + o.id() + "@" + o.x() + "," + o.z())).toList();
		if (free.isEmpty()) {
			return null;
		}
		Objective o = far ? free.get(free.size() - 1) : free.get(r.nextInt(Math.min(2, free.size())));
		used.add("g:" + o.id() + "@" + o.x() + "," + o.z());
		int em = o.distance() > FAR ? EM_FAR_GUARDIAN : EM_GUARDIAN;
		return new Quest(ax, az, period, h, Type.GUARDIAN, o.id(), 0, o.x(), o.z(), em, XP_GUARDIAN);
	}

	private static Quest place(Random r, Candidates c, int ax, int az, long period, int h, List<String> used) {
		List<Objective> free = c.places().stream().filter(o -> !used.contains("l:" + o.x() + "," + o.z())).toList();
		if (free.isEmpty()) {
			return null;
		}
		Objective o = free.get(r.nextInt(free.size()));
		used.add("l:" + o.x() + "," + o.z());
		return new Quest(ax, az, period, h, Type.EXPLORE, o.id(), 0, o.x(), o.z(), EM_PLACE + (o.distance() > 1000 ? 1 : 0), XP_PLACE);
	}

	private static Quest journey(Random r, Candidates c, int ax, int az, long period, int h, List<String> used) {
		Objective o = c.neighbors().get(r.nextInt(c.neighbors().size()));
		used.add("v:" + o.x() + "," + o.z());
		return new Quest(ax, az, period, h, Type.JOURNEY, o.id(), 0, o.x(), o.z(), EM_JOURNEY + (o.distance() > 1500 ? 1 : 0), XP_PLACE);
	}

	private static Quest arena(Random r, int ax, int az, long period, int h) {
		int wave = WAVES[r.nextInt(WAVES.length)];
		return new Quest(ax, az, period, h, Type.ARENA, "", wave, 0, 0, 1 + wave, XP_WAVE * wave);
	}
}
