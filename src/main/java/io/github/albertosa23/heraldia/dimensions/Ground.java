package io.github.albertosa23.heraldia.dimensions;

import java.util.function.IntPredicate;

/**
 * Where a Heraldia structure rests in the Nether or the End (pure logic, no game classes: tested by
 * {@code GroundTest} and used by {@link DimensionStructure}).
 * <ul>
 * <li><b>Nether</b>: there is no useful surface heightmap (WORLD_SURFACE_WG gives the bedrock ceiling). The noise
 * column is walked top down, from {@link #NETHER_FROM} to {@link #NETHER_TO} (above the lava sea,
 * which is at y = 31), and the first y with firm ground below (neither lava nor air) and {@code free} air cells
 * above wins: the structure fits under the ceiling. The footprint's corners must have their ground within ±{@link #DROP} of that
 * height (otherwise it hangs over a ravine or digs into the wall).</li>
 * <li><b>End</b>: the heightmap does work, but the void gives the world's minimum height. The center and the four corners
 * must be over a real island (height &ge; {@link #END_MIN}) and within ±{@link #DROP} of each other, and the site
 * away from the central island ({@link #END_CENTRAL_RADIUS}: neither its island nor the dragon fight).</li>
 * </ul>
 */
public final class Ground {
	/** No valid height. */
	public static final int NONE = Integer.MIN_VALUE;
	/** Nether: from where to where the ground is searched (the bedrock ceiling starts at 123; the lava sea reaches 31). */
	public static final int NETHER_FROM = 112, NETHER_TO = 34;
	/** Maximum drop between the center's ground and that of each footprint corner (blocks). */
	public static final int DROP = 5;
	/** End: minimum surface height of an island (the void gives the world's minimum) and radius of the central island. */
	public static final int END_MIN = 45, END_CENTRAL_RADIUS = 1024;

	private Ground() {
	}

	/**
	 * First y (from {@code from} downwards, to {@code until}) with firm ground at y - 1 and {@code free} air cells
	 * from y to y + free - 1, or {@link #NONE}. {@code solid}: a supporting block (neither air nor liquid); {@code air}:
	 * empty cell (no block or liquid).
	 */
	public static int nether(IntPredicate solid, IntPredicate air, int from, int until, int free) {
		int placeholders = 0; // consecutive air cells above the y being checked
		for (int y = from + free; y >= until; y--) {
			if (y <= from && placeholders >= free && solid.test(y - 1)) {
				return y;
			}
			placeholders = air.test(y - 1) ? placeholders + 1 : 0;
		}
		return NONE;
	}

	/** Ground of a corner near the center's height: the first within ±DROP with air above, or NONE. */
	public static int netherNear(IntPredicate solid, IntPredicate air, int center) {
		return nether(solid, air, center + DROP, center - DROP, 2);
	}

	/** All corners have ground within ±DROP of the center. */
	public static boolean flat(int center, int... corners) {
		for (int e : corners) {
			if (e == NONE || Math.abs(e - center) > DROP) {
				return false;
			}
		}
		return true;
	}

	/**
	 * End: the height (the center's) if the center and the corners are over an island (&ge; END_MIN), flat with each other,
	 * and the site outside the central island; otherwise, NONE. {@code heights}: center first and then the corners (the
	 * first free y of the WORLD_SURFACE_WG heightmap).
	 */
	public static int end(int x, int z, int... heights) {
		if ((long) x * x + (long) z * z < (long) END_CENTRAL_RADIUS * END_CENTRAL_RADIUS) {
			return NONE;
		}
		int center = heights[0];
		for (int h : heights) {
			if (h < END_MIN || Math.abs(h - center) > DROP) {
				return NONE;
			}
		}
		return center;
	}
}
