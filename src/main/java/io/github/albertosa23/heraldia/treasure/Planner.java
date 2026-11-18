package io.github.albertosa23.heraldia.treasure;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Optional;
import java.util.Random;
import java.util.UUID;

/**
 * Chooses a clue's chain: pure and deterministic logic (same seed, same origin and same candidates, same chain;
 * PlannerTest). Order of the chain: a medium structure within {@code radius} blocks of the origin; from it,
 * a mine entrance (if there is none, another medium); and from the last one, the treasure, 48-128 blocks away in a random
 * direction. If there is no medium, the first is a mine. Without any structure, there is no chain.
 * <p>The candidates come from a {@link Finder} (in the game, {@link Search}'s search off the server thread,
 * which neither loads nor generates chunks). Of each type the already generated ones are preferred; among the first {@value #ELIGIBLE} (the
 * generated ones and then the expected ones, by distance) one is drawn. No destination repeats (nor within
 * {@value #MIN_DISTANCE} blocks of another).
 */
public final class Planner {
	/** Minimum distance between two consecutive marks (and between any two destinations of the chain). */
	public static final int MIN_DISTANCE = 96;
	public static final int ELIGIBLE = 3;
	public static final int TREASURE_MIN = 48, TREASURE_MAX = 128;

	private Planner() {
	}

	/** A structure a mark could fall on. */
	public record Candidate(Destination.Type type, String structure, int x, int z, boolean generated) {
	}

	/** The candidates of a type within {@code radius} blocks of (x, z), in any order. */
	@FunctionalInterface
	public interface Finder {
		List<Candidate> search(Destination.Type type, int x, int z, int radius);
	}

	/** The biome id at (x, z). */
	@FunctionalInterface
	public interface Biomes {
		String en(int x, int z);
	}

	/** Seed of the n-th clue a player deciphers in a world: different per world, player and number. */
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

	/** The treasure [min, max] blocks from (x, z) in a random direction. */
	static Destination treasure(Random rnd, int x, int z, int min, int max, Biomes biomes) {
		double a = rnd.nextDouble() * 2 * Math.PI;
		int d = min + rnd.nextInt(max - min + 1);
		int tx = x + (int) Math.round(Math.cos(a) * d), tz = z + (int) Math.round(Math.sin(a) * d);
		return new Destination(Destination.Type.TREASURE, "", tx, tz, false, biomes.en(tx, tz));
	}

	/** The treasure moved (its spot was not safe): again from where it was, with the seed and the attempt number. */
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
