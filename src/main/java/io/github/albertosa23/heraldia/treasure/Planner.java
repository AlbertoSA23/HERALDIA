package io.github.albertosa23.heraldia.treasure;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Optional;
import java.util.Random;
import java.util.UUID;

/**
 * Elige la cadena de una pista: lógica pura y determinista (misma semilla, mismo origen y mismas candidatas, misma cadena;
 * PlanificadorTest). Orden de la cadena: una estructura mediana a menos de {@code radius} bloques del origen; desde ella,
 * una entrada a mina (si no hay ninguna, otra mediana); y desde la última, el tesoro, a 48-128 bloques en una dirección al
 * azar. Si no hay mediana, la primera es una mina. Sin ninguna estructura, no hay cadena.
 * <p>Las candidatas las da un {@link Finder} (en el juego, la búsqueda fuera del hilo del servidor de {@link Search},
 * que no carga ni genera chunks). De cada tipo se prefieren las ya generadas; entre las {@value #ELIGIBLE} primeras (las
 * generadas y luego las previstas, por distancia) se sortea una. Ningún destino se repite (ni a menos de
 * {@value #MIN_DISTANCE} bloques de otro).
 */
public final class Planner {
	/** Distancia mínima entre dos marcas seguidas (y entre dos destinos cualesquiera de la cadena). */
	public static final int MIN_DISTANCE = 96;
	public static final int ELIGIBLE = 3;
	public static final int TREASURE_MIN = 48, TREASURE_MAX = 128;

	private Planner() {
	}

	/** Una estructura en la que podría caer una marca. */
	public record Candidate(Destination.Type type, String structure, int x, int z, boolean generated) {
	}

	/** Las candidatas de un tipo a menos de {@code radius} bloques de (x, z), en cualquier orden. */
	@FunctionalInterface
	public interface Finder {
		List<Candidate> search(Destination.Type type, int x, int z, int radius);
	}

	/** El id del bioma en (x, z). */
	@FunctionalInterface
	public interface Biomes {
		String en(int x, int z);
	}

	/** Semilla de la n-ésima pista que descifra un jugador en un mundo: distinta por mundo, jugador y número. */
	public static long seed(long world, UUID player, int n) {
		long h = world * 0x9E3779B97F4A7C15L ^ player.getMostSignificantBits();
		h = merge(h) ^ player.getLeastSignificantBits();
		h = merge(h) + n * 0xBF58476D1CE4E5B9L;
		return merge(h);
	}

	static long merge(long z) {
		z = (z ^ (z >>> 30)) * 0xBF58476D1CE4E5B9L;
		z = (z ^ (z >>> 27)) * 0x94D049BB133111EBL;
		return z ^ (z >>> 31);
	}

	public static Optional<List<Destination>> plan(long seed, int ox, int oz, int radius, Finder finder, Biomes biomes) {
		Random rnd = new Random(seed);
		List<Destination> out = new ArrayList<>();
		Destination first = choose(finder, Destination.Type.MEDIUM, ox, oz, radius, out, rnd, biomes)
				.or(() -> choose(finder, Destination.Type.MINE, ox, oz, radius, out, rnd, biomes)).orElse(null);
		if (first == null) {
			return Optional.empty();
		}
		out.add(first);
		Destination second = choose(finder, Destination.Type.MINE, first.x(), first.z(), radius, out, rnd, biomes)
				.or(() -> choose(finder, Destination.Type.MEDIUM, first.x(), first.z(), radius, out, rnd, biomes)).orElse(null);
		if (second != null) {
			out.add(second);
		}
		Destination latest = out.getLast();
		out.add(treasure(rnd, latest.x(), latest.z(), TREASURE_MIN, TREASURE_MAX, biomes));
		return Optional.of(List.copyOf(out));
	}

	/** El tesoro a [min, max] bloques de (x, z) en una dirección al azar. */
	static Destination treasure(Random rnd, int x, int z, int min, int max, Biomes biomes) {
		double a = rnd.nextDouble() * 2 * Math.PI;
		int d = min + rnd.nextInt(max - min + 1);
		int tx = x + (int) Math.round(Math.cos(a) * d), tz = z + (int) Math.round(Math.sin(a) * d);
		return new Destination(Destination.Type.TREASURE, "", tx, tz, false, biomes.en(tx, tz));
	}

	/** El tesoro movido (su sitio no era seguro): otra vez desde donde estaba, con la semilla y el número de intento. */
	public static Destination moveTreasure(Chain c, Biomes biomes) {
		Random rnd = new Random(c.seed() ^ merge(c.moved() + 1L));
		Destination t = c.destinations().getLast();
		return treasure(rnd, t.x(), t.z(), 32, 64, biomes);
	}

	static Optional<Destination> choose(Finder finder, Destination.Type type, int x, int z, int radius, List<Destination> used, Random rnd,
			Biomes biomes) {
		long min = (long) MIN_DISTANCE * MIN_DISTANCE, max = (long) radius * radius;
		List<Candidate> valid = new ArrayList<>();
		for (Candidate c : finder.search(type, x, z, radius)) {
			long d = dist(c.x() - x, c.z() - z);
			if (c.type() == type && d >= min && d <= max && used.stream().noneMatch(u -> dist(u.x() - c.x(), u.z() - c.z()) < min)) {
				valid.add(c);
			}
		}
		if (valid.isEmpty()) {
			return Optional.empty();
		}
		valid.sort(Comparator.comparing((Candidate c) -> !c.generated()).thenComparingLong(c -> dist(c.x() - x, c.z() - z))
				.thenComparingInt(Candidate::x).thenComparingInt(Candidate::z).thenComparing(Candidate::structure));
		Candidate c = valid.get(rnd.nextInt(Math.min(ELIGIBLE, valid.size())));
		return Optional.of(new Destination(type, c.structure(), c.x(), c.z(), c.generated(), biomes.en(c.x(), c.z())));
	}

	static long dist(long dx, long dz) {
		return dx * dx + dz * dz;
	}
}
