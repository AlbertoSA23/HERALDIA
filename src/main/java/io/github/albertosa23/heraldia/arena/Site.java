package io.github.albertosa23.heraldia.arena;

import java.util.Arrays;
import java.util.Optional;

/**
 * Choice of the arena site, without game classes (the tests check it with made-up terrain): candidates in
 * rings from {@link #RADIUS_MIN} to {@link #RADIUS_MAX} blocks from spawn, every {@link #DEGREE_STEP}°, and in each a
 * {@link #SAMPLES}² grid of heights over the arena's footprint plus a margin. A valid one has no water, the smallest drop
 * (at most {@link #MAX_DROP}) and no already generated structure in its chunks; on a tie, the one closest to
 * {@link #PREFERRED_RADIUS} and then the first in order.
 * Heights come from the world generator ({@code ChunkGenerator.getBaseHeight}: noise only, no chunk loading), so
 * the search can run off the server thread.
 */
public final class Site {
	public static final int RADIUS_MIN = 200, RADIUS_MAX = 300, RADIUS_STEP = 25, PREFERRED_RADIUS = 250, DEGREE_STEP = 15;
	public static final int SAMPLES = 5, MARGIN = 4, MAX_DROP = 12;

	private Site() {
	}

	/** Natural terrain heights in a column. */
	public interface Heights {
		/** First free block above the surface (water included). */
		int surface(int x, int z);

		/** First free or water block above solid ground. */
		int depth(int x, int z);

		/** Is there already a piece of a surface structure (village, mine entrance...) in that chunk? */
		default boolean occupied(int chunkX, int chunkZ) {
			return false;
		}
	}

	/**
	 * A site: center column, and y of the ground block (the median of the heights: what gets levelled), drop and
	 * distance to spawn.
	 */
	public record Choice(int x, int z, int ground, int drop, int distance) {
	}

	/**
	 * The best site for an arena of {@code side} blocks around spawn, or empty if none is flat and dry.
	 * {@code minY} and {@code maxY}: world heights; the arena (from {@code low} blocks below the ground to {@code high}
	 * above) has to fit.
	 */
	public static Optional<Choice> choose(int spawnX, int spawnZ, int side, int low, int high, int minY, int maxY, Heights a) {
		Choice best = null;
		for (int r = RADIUS_MIN; r <= RADIUS_MAX; r += RADIUS_STEP) {
			for (int g = 0; g < 360; g += DEGREE_STEP) {
				double rad = Math.toRadians(g);
				int cx = spawnX + (int) Math.round(r * Math.cos(rad));
				int cz = spawnZ + (int) Math.round(r * Math.sin(rad));
				Choice e = evaluateAt(cx, cz, spawnX, spawnZ, side, a);
				if (e == null || e.ground() - low <= minY || e.ground() + high >= maxY) {
					continue;
				}
				if ((best == null || best(e, best)) && free(e, side, a)) {
					best = e;
				}
			}
		}
		return Optional.ofNullable(best);
	}

	/** The site centered at (cx, cz), or null if there is water or too much drop. */
	static Choice evaluateAt(int cx, int cz, int spawnX, int spawnZ, int side, Heights a) {
		int width = side + 2 * MARGIN;
		int[] heights = new int[SAMPLES * SAMPLES];
		int i = 0;
		for (int u = 0; u < SAMPLES; u++) {
			for (int v = 0; v < SAMPLES; v++) {
				int x = cx - width / 2 + u * (width - 1) / (SAMPLES - 1);
				int z = cz - width / 2 + v * (width - 1) / (SAMPLES - 1);
				int s = a.surface(x, z);
				if (s > a.depth(x, z)) {
					return null;                // water
				}
				heights[i++] = s - 1;
			}
		}
		Arrays.sort(heights);
		int drop = heights[heights.length - 1] - heights[0];
		if (drop > MAX_DROP) {
			return null;
		}
		int dist = (int) Math.round(Math.hypot(cx - spawnX, cz - spawnZ));
		return new Choice(cx, cz, heights[heights.length / 2], drop, dist);
	}

	/** Does no chunk of the footprint and its margin already have a structure? (only checked if the site beats the chosen one) */
	static boolean free(Choice e, int side, Heights a) {
		int m = side / 2 + MARGIN;
		for (int cx = (e.x() - m) >> 4; cx <= (e.x() + m) >> 4; cx++) {
			for (int cz = (e.z() - m) >> 4; cz <= (e.z() + m) >> 4; cz++) {
				if (a.occupied(cx, cz)) {
					return false;
				}
			}
		}
		return true;
	}

	/** Is {@code a} better than {@code b}? Less drop; on a tie, closer to {@link #PREFERRED_RADIUS}. */
	static boolean best(Choice a, Choice b) {
		if (a.drop() != b.drop()) {
			return a.drop() < b.drop();
		}
		return Math.abs(a.distance() - PREFERRED_RADIUS) < Math.abs(b.distance() - PREFERRED_RADIUS);
	}
}
