package io.github.albertosa23.heraldia.command;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Optional;

/**
 * Safe teleport (pure logic, no game classes): searches, from a column and in a spiral, for a spot where one can
 * stand on the ground without suffocating. A spot is valid if the feet and the head are in free cells and below
 * there is firm ground or water (floating on water is safe: Atlantis and the island are in the sea). Never on or in
 * lava, fire, magma, cactus or powder snow.
 */
public final class SafeSpot {
	/** Default search radius around the requested column, in blocks. */
	public static final int RADIUS = 8;

	private SafeSpot() {
	}

	/** What a cell holds, as far as standing in it goes. */
	public enum Cell {
		/** No collision or damage (air, grass, flowers, thin snow...). */
		FREE,
		/** Block that supports and suffocates if one is inside. */
		SOLID,
		/** Water: one can float on top; it does not suffocate instantly, but one does not appear inside. */
		WATER,
		/** Hurts or traps: lava, fire, magma, cactus, powder snow, berries... */
		DANGER
	}

	/** What is needed from the world. Only already loaded columns are asked about. */
	public interface World {
		Cell en(int x, int y, int z);

		/** First free y above the highest block that blocks movement in the column (the heightmap). */
		int height(int x, int z);

		int minY();

		/** First y outside the world (above). */
		int maxY();
	}

	/** (x, y, z) of the feet. */
	public record Site(int x, int y, int z) {
	}

	/** Spiral offsets up to {@code radius}, from the center out (fixed order: distance, x, z). */
	static List<int[]> spiral(int radius) {
		List<int[]> out = new ArrayList<>();
		for (int dx = -radius; dx <= radius; dx++) {
			for (int dz = -radius; dz <= radius; dz++) {
				if (dx * dx + dz * dz <= radius * radius) {
					out.add(new int[] {dx, dz});
				}
			}
		}
		out.sort(Comparator.<int[]>comparingInt(o -> o[0] * o[0] + o[1] * o[1]).thenComparingInt(o -> o[0]).thenComparingInt(o -> o[1]));
		return out;
	}

	/** The safe spot nearest to column (x, z), or empty if there is none within {@code radius} blocks. */
	public static Optional<Site> search(World m, int x, int z, int radius) {
		for (int[] d : spiral(radius)) {
			int cx = x + d[0], cz = z + d[1];
			Optional<Site> s = column(m, cx, cz);
			if (s.isPresent()) {
				return s;
			}
		}
		return Optional.empty();
	}

	/**
	 * Safe spot of a column: on top of the highest point (the heightmap) and, if that does not work (under an overhang, among
	 * leaves), nothing else; caves are not searched (one always appears in the open air).
	 */
	static Optional<Site> column(World m, int x, int z) {
		int y = m.height(x, z);
		if (y <= m.minY() || y + 1 >= m.maxY()) {
			return Optional.empty();       // empty column (void) or up to the world ceiling
		}
		return valid(m, x, y, z) ? Optional.of(new Site(x, y, z)) : Optional.empty();
	}

	/**
	 * Worlds with a ceiling (the Nether): the heightmap gives the bedrock ceiling, so the "height" of a column is the first
	 * y, from {@code from} down to {@code until}, with the feet and head free and firm ground below; if there is
	 * none, the world's minimum (the column is not valid). /heraldia review uses it for the Nether stops.
	 */
	public static int underCeiling(World m, int x, int z, int from, int until) {
		for (int y = from; y > until; y--) {
			if (m.en(x, y, z) == Cell.FREE && m.en(x, y + 1, z) == Cell.FREE && m.en(x, y - 1, z) == Cell.SOLID) {
				return y;
			}
		}
		return m.minY();
	}

	/** Can one stand with the feet at y? Feet and head free; below, firm ground or water. */
	static boolean valid(World m, int x, int y, int z) {
		Cell below = m.en(x, y - 1, z);
		return m.en(x, y, z) == Cell.FREE && m.en(x, y + 1, z) == Cell.FREE
				&& (below == Cell.SOLID || below == Cell.WATER);
	}
}
