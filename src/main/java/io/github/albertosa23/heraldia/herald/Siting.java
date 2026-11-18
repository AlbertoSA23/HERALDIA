package io.github.albertosa23.heraldia.herald;

import io.github.albertosa23.heraldia.arena.Site;
import java.util.Arrays;
import java.util.Optional;

/**
 * Choice of the Herald's House site around spawn, without game classes (the tests check it with made-up terrain):
 * candidates every {@link #STEP} blocks up to {@link #RADIUS} from spawn (spawn itself first) and in each a
 * {@link #SAMPLES}² grid of heights over the footprint plus {@link #MARGIN}. The best one has the fewest water samples,
 * then the smallest drop, then is the closest; a site whose protected area touches a forbidden rectangle (the arena) or
 * whose chunks hold another surface structure is not a candidate. Unlike the arena, water and slopes are allowed: the
 * house brings a foundation that goes down to the ground and the margin is blended into the terrain. Heights come from
 * the world generator (noise only), so the search runs off the server thread. Same height interface as the arena
 * ({@link Site.Heights}).
 */
public final class Siting {
	/** At most this far from spawn: the protected area (side / 2 + RING) never reaches the arena's ring (200-300 blocks). */
	public static final int RADIUS = 48, STEP = 16, SAMPLES = 5, MARGIN = 8;

	private Siting() {
	}

	/** A rectangle the protected area must not touch. */
	public interface Forbidden {
		boolean touches(int minX, int minZ, int maxX, int maxZ);
	}

	/** A site: center column, the median ground height, the drop, how many samples are water and the distance. */
	public record Choice(int x, int z, int ground, int drop, int water, int distance) {
	}

	public static Optional<Choice> choose(int spawnX, int spawnZ, int side, int low, int high, int minY, int maxY,
			Site.Heights h, Forbidden forbidden) {
		Choice best = null;
		for (int r = 0; r <= RADIUS; r += STEP) {
			for (int dx = -r; dx <= r; dx += STEP) {
				for (int dz = -r; dz <= r; dz += STEP) {
					if (Math.max(Math.abs(dx), Math.abs(dz)) != r) {
						continue;                       // only the ring at r (spawn first, then outwards)
					}
					Choice c = evaluate(spawnX + dx, spawnZ + dz, spawnX, spawnZ, side, h);
					if (c.ground() - low <= minY || c.ground() + high >= maxY) {
						continue;
					}
					if ((best == null || better(c, best)) && free(c, side, h, forbidden)) {
						best = c;
					}
				}
			}
		}
		return Optional.ofNullable(best);
	}

	/** The site centered at (cx, cz): its median height, drop and water samples. */
	static Choice evaluate(int cx, int cz, int spawnX, int spawnZ, int side, Site.Heights h) {
		int width = side + 2 * MARGIN;
		int[] heights = new int[SAMPLES * SAMPLES];
		int water = 0, i = 0;
		for (int u = 0; u < SAMPLES; u++) {
			for (int v = 0; v < SAMPLES; v++) {
				int x = cx - width / 2 + u * (width - 1) / (SAMPLES - 1);
				int z = cz - width / 2 + v * (width - 1) / (SAMPLES - 1);
				int s = h.surface(x, z), d = h.depth(x, z);
				if (s > d) {
					water++;
				}
				heights[i++] = s - 1;                 // over water, the water's surface
			}
		}
		Arrays.sort(heights);
		int dist = (int) Math.round(Math.hypot(cx - spawnX, cz - spawnZ));
		return new Choice(cx, cz, heights[heights.length / 2], heights[heights.length - 1] - heights[0], water, dist);
	}

	static boolean free(Choice c, int side, Site.Heights h, Forbidden forbidden) {
		int half = side / 2;
		int m = half + Grounds.RING;
		if (forbidden.touches(c.x() - m, c.z() - m, c.x() + m, c.z() + m)) {
			return false;
		}
		for (int cx = (c.x() - half) >> 4; cx <= (c.x() + half) >> 4; cx++) {
			for (int cz = (c.z() - half) >> 4; cz <= (c.z() + half) >> 4; cz++) {
				if (h.occupied(cx, cz)) {
					return false;
				}
			}
		}
		return true;
	}

	/** Fewer water samples; then less drop; then closer to spawn. */
	static boolean better(Choice a, Choice b) {
		if (a.water() != b.water()) {
			return a.water() < b.water();
		}
		if (a.drop() != b.drop()) {
			return a.drop() < b.drop();
		}
		return a.distance() < b.distance();
	}
}
