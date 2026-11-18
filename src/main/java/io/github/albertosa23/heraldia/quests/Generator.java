package io.github.albertosa23.heraldia.quests;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Random;

/**
 * El tablón de cada aldea, lógica pura y determinista (T38): con la semilla, el chunk de la aldea, el periodo de
 * rotación y lo que hay alrededor (los candidatos, que busca {@link Quests} fuera del hilo del servidor), sale siempre
 * el mismo tablón de 2 a 4 encargos. Sin datos guardados: un tablón se rehace igual tras reiniciar el servidor.
 * <p>El primero es siempre de traer objetos; el segundo, vencer a un guardián si hay alguna única cerca (si no,
 * explorar); los demás, al azar entre lo que haya (explorar, viajar a una aldea vecina, la arena, un guardián más lejano
 * u otro de traer).
 */
public final class Generator {
	/** Ticks de un día de juego. */
	public static final long DAY = 24000L;
	public static final int MIN = 2, MAX = 4;
	/** Radio de búsqueda de guardianes y de lugares que explorar, en bloques. */
	public static final int GUARDIAN_RADIUS = 4000, PLACE_RADIUS = 1500;
	/** Oleadas que se pueden pedir en la arena. */
	static final int[] WAVES = {3, 5, 8};

	/** Un objeto que traer: id, cantidad mínima y máxima, y esmeraldas que paga. */
	public record Item(String id, int min, int max, int emeralds) {
	}

	/** Un sitio candidato: id (única, estructura o nombre de la aldea vecina), bloque y distancia a la aldea. */
	public record Objective(String id, int x, int z, int distance) {
	}

	/** Lo que hay alrededor de una aldea, ordenado de más cerca a más lejos. */
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
	/** Menas y lingotes de valor moderado (nada de diamantes, esmeraldas ni netherita). */
	static final List<Item> ORES = List.of(
			new Item("minecraft:coal", 16, 32, 3), new Item("minecraft:raw_iron", 8, 16, 4),
			new Item("minecraft:raw_copper", 16, 32, 3), new Item("minecraft:iron_ingot", 6, 12, 4),
			new Item("minecraft:redstone", 16, 32, 3), new Item("minecraft:lapis_lazuli", 8, 16, 4),
			new Item("minecraft:gold_ingot", 4, 8, 4), new Item("minecraft:amethyst_shard", 8, 16, 3));
	/** Materiales del bioma de cada familia de aldeas (themes.FAMILIES). */
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
	/** Recompensas de cada tipo (además de las esmeraldas de traer, que van por objeto). */
	static final int XP_BRING = 20, XP_PLACE = 40, XP_GUARDIAN = 120, XP_WAVE = 10;
	static final int EM_PLACE = 4, EM_JOURNEY = 4, EM_GUARDIAN = 8, EM_FAR_GUARDIAN = 12, FAR = 2000;

	private Generator() {
	}

	/** Periodo de rotación del tablón: cambia cada {@code days} días de juego (del reloj del mundo, que no se para). */
	public static long period(long gameTime, int days) {
		return Math.floorDiv(gameTime, Math.max(1, days) * DAY);
	}

	/** Tick del mundo en que empieza el periodo. */
	public static long start(long period, int days) {
		return period * Math.max(1, days) * DAY;
	}

	/** Ticks que faltan para el siguiente periodo. */
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

	/** Los objetos que puede pedir una aldea de esa familia (comida, su bioma y menas). */
	public static List<Item> items(String family) {
		List<Item> out = new ArrayList<>(FOOD);
		out.addAll(BIOME.getOrDefault(family, List.of()));
		out.addAll(ORES);
		return out;
	}

	/** El tablón de la aldea con el inicio en el chunk (ax, az) en ese periodo. */
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
		// 40 % comida, 30 % del bioma (si la familia tiene), 30 % menas; sin repetir objeto en el mismo tablón
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

	/** Un guardián: el primero, uno de los dos más cercanos; el segundo («lejano»), el más lejano que quede. */
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
