package io.github.albertosa23.heraldia.encargos;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Random;

/**
 * El tablón de cada aldea, lógica pura y determinista (T38): con la semilla, el chunk de la aldea, el periodo de
 * rotación y lo que hay alrededor (los candidatos, que busca {@link Encargos} fuera del hilo del servidor), sale siempre
 * el mismo tablón de 2 a 4 encargos. Sin datos guardados: un tablón se rehace igual tras reiniciar el servidor.
 * <p>El primero es siempre de traer objetos; el segundo, vencer a un guardián si hay alguna única cerca (si no,
 * explorar); los demás, al azar entre lo que haya (explorar, viajar a una aldea vecina, la arena, un guardián más lejano
 * u otro de traer).
 */
public final class Generador {
	/** Ticks de un día de juego. */
	public static final long DIA = 24000L;
	public static final int MIN = 2, MAX = 4;
	/** Radio de búsqueda de guardianes y de lugares que explorar, en bloques. */
	public static final int RADIO_GUARDIAN = 4000, RADIO_LUGAR = 1500;
	/** Oleadas que se pueden pedir en la arena. */
	static final int[] OLEADAS = {3, 5, 8};

	/** Un objeto que traer: id, cantidad mínima y máxima, y esmeraldas que paga. */
	public record Objeto(String id, int min, int max, int esmeraldas) {
	}

	/** Un sitio candidato: id (única, estructura o nombre de la aldea vecina), bloque y distancia a la aldea. */
	public record Objetivo(String id, int x, int z, int distancia) {
	}

	/** Lo que hay alrededor de una aldea, ordenado de más cerca a más lejos. */
	public record Candidatos(String familia, List<Objetivo> guardianes, List<Objetivo> lugares, List<Objetivo> vecinas, boolean arena) {
		public Candidatos {
			guardianes = List.copyOf(guardianes);
			lugares = List.copyOf(lugares);
			vecinas = List.copyOf(vecinas);
		}

		public static Candidatos solo(String familia) {
			return new Candidatos(familia, List.of(), List.of(), List.of(), false);
		}
	}

	static final List<Objeto> COMIDA = List.of(
			new Objeto("minecraft:bread", 12, 24, 3), new Objeto("minecraft:baked_potato", 16, 32, 3),
			new Objeto("minecraft:cooked_chicken", 8, 16, 3), new Objeto("minecraft:cooked_cod", 8, 16, 3),
			new Objeto("minecraft:pumpkin_pie", 4, 8, 3), new Objeto("minecraft:cooked_porkchop", 8, 16, 3),
			new Objeto("minecraft:cookie", 16, 32, 2), new Objeto("minecraft:apple", 8, 16, 2));
	/** Menas y lingotes de valor moderado (nada de diamantes, esmeraldas ni netherita). */
	static final List<Objeto> MENAS = List.of(
			new Objeto("minecraft:coal", 16, 32, 3), new Objeto("minecraft:raw_iron", 8, 16, 4),
			new Objeto("minecraft:raw_copper", 16, 32, 3), new Objeto("minecraft:iron_ingot", 6, 12, 4),
			new Objeto("minecraft:redstone", 16, 32, 3), new Objeto("minecraft:lapis_lazuli", 8, 16, 4),
			new Objeto("minecraft:gold_ingot", 4, 8, 4), new Objeto("minecraft:amethyst_shard", 8, 16, 3));
	/** Materiales del bioma de cada familia de aldeas (themes.FAMILIES). */
	static final Map<String, List<Objeto>> BIOMA = Map.ofEntries(
			Map.entry("llanuras", List.of(new Objeto("minecraft:wheat", 24, 48, 3), new Objeto("minecraft:hay_block", 4, 8, 3),
					new Objeto("minecraft:white_wool", 8, 16, 3))),
			Map.entry("bosque", List.of(new Objeto("minecraft:oak_log", 16, 32, 3), new Objeto("minecraft:birch_log", 16, 32, 3),
					new Objeto("minecraft:honeycomb", 3, 6, 4))),
			Map.entry("oscuro", List.of(new Objeto("minecraft:dark_oak_log", 16, 32, 3),
					new Objeto("minecraft:brown_mushroom", 8, 16, 2), new Objeto("minecraft:red_mushroom", 8, 16, 2))),
			Map.entry("taiga", List.of(new Objeto("minecraft:spruce_log", 16, 32, 3), new Objeto("minecraft:sweet_berries", 16, 32, 2),
					new Objeto("minecraft:leather", 6, 12, 3))),
			Map.entry("nieve", List.of(new Objeto("minecraft:snowball", 16, 32, 2), new Objeto("minecraft:packed_ice", 8, 16, 3),
					new Objeto("minecraft:potato", 16, 32, 2))),
			Map.entry("desierto", List.of(new Objeto("minecraft:sandstone", 16, 32, 2), new Objeto("minecraft:cactus", 8, 16, 2),
					new Objeto("minecraft:rabbit_hide", 4, 8, 3))),
			Map.entry("sabana", List.of(new Objeto("minecraft:acacia_log", 16, 32, 3), new Objeto("minecraft:white_wool", 8, 16, 3),
					new Objeto("minecraft:melon_slice", 16, 32, 2))),
			Map.entry("jungla", List.of(new Objeto("minecraft:bamboo", 24, 48, 2), new Objeto("minecraft:cocoa_beans", 8, 16, 3),
					new Objeto("minecraft:jungle_log", 16, 32, 3))),
			Map.entry("pantano", List.of(new Objeto("minecraft:lily_pad", 4, 8, 3), new Objeto("minecraft:mangrove_log", 16, 32, 3),
					new Objeto("minecraft:slime_ball", 4, 8, 4))),
			Map.entry("cerezos", List.of(new Objeto("minecraft:cherry_log", 16, 32, 3), new Objeto("minecraft:pink_petals", 8, 16, 2),
					new Objeto("minecraft:honey_bottle", 2, 4, 3))),
			Map.entry("badlands", List.of(new Objeto("minecraft:terracotta", 16, 32, 2), new Objeto("minecraft:red_sand", 16, 32, 2),
					new Objeto("minecraft:gold_nugget", 16, 32, 3))),
			Map.entry("costa", List.of(new Objeto("minecraft:kelp", 24, 48, 2), new Objeto("minecraft:dried_kelp_block", 4, 8, 3),
					new Objeto("minecraft:ink_sac", 6, 12, 3))));
	/** Recompensas de cada tipo (además de las esmeraldas de traer, que van por objeto). */
	static final int XP_TRAER = 20, XP_LUGAR = 40, XP_GUARDIAN = 120, XP_OLEADA = 10;
	static final int EM_LUGAR = 4, EM_VIAJE = 4, EM_GUARDIAN = 8, EM_GUARDIAN_LEJOS = 12, LEJOS = 2000;

	private Generador() {
	}

	/** Periodo de rotación del tablón: cambia cada {@code dias} días de juego (del reloj del mundo, que no se para). */
	public static long periodo(long gameTime, int dias) {
		return Math.floorDiv(gameTime, Math.max(1, dias) * DIA);
	}

	/** Tick del mundo en que empieza el periodo. */
	public static long inicio(long periodo, int dias) {
		return periodo * Math.max(1, dias) * DIA;
	}

	/** Ticks que faltan para el siguiente periodo. */
	public static long restante(long gameTime, int dias) {
		long largo = Math.max(1, dias) * DIA;
		return largo - Math.floorMod(gameTime, largo);
	}

	static long mix(long z) {
		z = (z ^ (z >>> 33)) * 0xff51afd7ed558ccdL;
		z = (z ^ (z >>> 33)) * 0xc4ceb9fe1a85ec53L;
		return z ^ (z >>> 33);
	}

	static long semilla(long seed, int ax, int az, long periodo) {
		return mix(seed ^ mix(((long) ax << 32) ^ (az & 0xffffffffL)) ^ mix(periodo * 0x9E3779B97F4A7C15L + 0x7AB1));
	}

	/** Los objetos que puede pedir una aldea de esa familia (comida, su bioma y menas). */
	public static List<Objeto> objetos(String familia) {
		List<Objeto> out = new ArrayList<>(COMIDA);
		out.addAll(BIOMA.getOrDefault(familia, List.of()));
		out.addAll(MENAS);
		return out;
	}

	/** El tablón de la aldea con el inicio en el chunk (ax, az) en ese periodo. */
	public static List<Encargo> tablon(long seed, int ax, int az, long periodo, Candidatos c) {
		Random r = new Random(semilla(seed, ax, az, periodo));
		int n = MIN + r.nextInt(MAX - MIN + 1);
		List<Encargo> out = new ArrayList<>();
		List<String> usados = new ArrayList<>();
		out.add(traer(r, c.familia(), ax, az, periodo, 0, usados));
		if (!c.guardianes().isEmpty()) {
			out.add(guardian(r, c, ax, az, periodo, 1, false, usados));
		} else if (!c.lugares().isEmpty()) {
			out.add(lugar(r, c, ax, az, periodo, 1, usados));
		} else {
			out.add(traer(r, c.familia(), ax, az, periodo, 1, usados));
		}
		List<Tipo> resto = new ArrayList<>();
		if (!c.lugares().isEmpty()) {
			resto.add(Tipo.EXPLORAR);
		}
		if (!c.vecinas().isEmpty()) {
			resto.add(Tipo.VIAJE);
		}
		if (c.arena()) {
			resto.add(Tipo.ARENA);
		}
		if (c.guardianes().size() > 1) {
			resto.add(Tipo.GUARDIAN);
		}
		resto.add(Tipo.TRAER);
		java.util.Collections.shuffle(resto, r);
		for (Tipo t : resto) {
			if (out.size() >= n) {
				break;
			}
			int h = out.size();
			Encargo e = switch (t) {
				case TRAER -> traer(r, c.familia(), ax, az, periodo, h, usados);
				case GUARDIAN -> guardian(r, c, ax, az, periodo, h, true, usados);
				case EXPLORAR -> lugar(r, c, ax, az, periodo, h, usados);
				case VIAJE -> viaje(r, c, ax, az, periodo, h, usados);
				case ARENA -> arena(r, ax, az, periodo, h);
			};
			if (e != null) {
				out.add(e);
			}
		}
		return List.copyOf(out);
	}

	private static Encargo traer(Random r, String familia, int ax, int az, long periodo, int h, List<String> usados) {
		// 40 % comida, 30 % del bioma (si la familia tiene), 30 % menas; sin repetir objeto en el mismo tablón
		Objeto o = null;
		for (int intento = 0; intento < 8 && (o == null || usados.contains(o.id())); intento++) {
			int k = r.nextInt(10);
			List<Objeto> lista = k < 4 ? COMIDA : k < 7 ? BIOMA.getOrDefault(familia, COMIDA) : MENAS;
			o = lista.get(r.nextInt(lista.size()));
		}
		usados.add(o.id());
		int pasos = (o.max() - o.min()) / 4;
		int cantidad = o.min() + 4 * r.nextInt(pasos + 1);
		int esmeraldas = o.esmeraldas() + (cantidad > (o.min() + o.max()) / 2 ? 1 : 0);
		return new Encargo(ax, az, periodo, h, Tipo.TRAER, o.id(), Math.min(cantidad, o.max()), 0, 0, esmeraldas, XP_TRAER);
	}

	/** Un guardián: el primero, uno de los dos más cercanos; el segundo («lejano»), el más lejano que quede. */
	private static Encargo guardian(Random r, Candidatos c, int ax, int az, long periodo, int h, boolean lejano, List<String> usados) {
		List<Objetivo> libres = c.guardianes().stream().filter(o -> !usados.contains("g:" + o.id() + "@" + o.x() + "," + o.z())).toList();
		if (libres.isEmpty()) {
			return null;
		}
		Objetivo o = lejano ? libres.get(libres.size() - 1) : libres.get(r.nextInt(Math.min(2, libres.size())));
		usados.add("g:" + o.id() + "@" + o.x() + "," + o.z());
		int em = o.distancia() > LEJOS ? EM_GUARDIAN_LEJOS : EM_GUARDIAN;
		return new Encargo(ax, az, periodo, h, Tipo.GUARDIAN, o.id(), 0, o.x(), o.z(), em, XP_GUARDIAN);
	}

	private static Encargo lugar(Random r, Candidatos c, int ax, int az, long periodo, int h, List<String> usados) {
		List<Objetivo> libres = c.lugares().stream().filter(o -> !usados.contains("l:" + o.x() + "," + o.z())).toList();
		if (libres.isEmpty()) {
			return null;
		}
		Objetivo o = libres.get(r.nextInt(libres.size()));
		usados.add("l:" + o.x() + "," + o.z());
		return new Encargo(ax, az, periodo, h, Tipo.EXPLORAR, o.id(), 0, o.x(), o.z(), EM_LUGAR + (o.distancia() > 1000 ? 1 : 0), XP_LUGAR);
	}

	private static Encargo viaje(Random r, Candidatos c, int ax, int az, long periodo, int h, List<String> usados) {
		Objetivo o = c.vecinas().get(r.nextInt(c.vecinas().size()));
		usados.add("v:" + o.x() + "," + o.z());
		return new Encargo(ax, az, periodo, h, Tipo.VIAJE, o.id(), 0, o.x(), o.z(), EM_VIAJE + (o.distancia() > 1500 ? 1 : 0), XP_LUGAR);
	}

	private static Encargo arena(Random r, int ax, int az, long periodo, int h) {
		int oleada = OLEADAS[r.nextInt(OLEADAS.length)];
		return new Encargo(ax, az, periodo, h, Tipo.ARENA, "", oleada, 0, 0, 1 + oleada, XP_OLEADA * oleada);
	}
}
