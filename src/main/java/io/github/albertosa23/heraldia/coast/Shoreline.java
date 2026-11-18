package io.github.albertosa23.heraldia.coast;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import net.minecraft.core.Direction;
import org.jspecify.annotations.Nullable;

/**
 * Shore search for a lighthouse or a shipwreck (pure logic: the terrain comes in as functions, so it is tested with
 * synthetic height maps; in the game, the shared generation height cache).
 *
 * <p>Like the village port ({@code villages/Shoreline}): the bottom on a grid of {@link #STEP} blocks within a
 * circle of {@link #RADIUS} around the candidate's center, inside out; each low land node with a water neighbor
 * gives a candidate shore towards that neighbor, refined with a binary search (the last land block). For
 * each candidate the template's footprint is checked, rotated so its +z faces the sea (x across, z towards the sea,
 * relative to the anchor): the land one behind and the sea one in front, with what each {@link Mode} asks for. The lighthouse
 * also prefers capes: of the first {@link #LIGHTHOUSE_VALID} valid shores, the one with the most water around at
 * {@link #CAPE} blocks. The others, the first valid one (the closest to the center). Each column is requested from the cache
 * at most once; the checks bail out at the first sample that fails.
 */
public final class Shoreline {
	/** Search grid, its reach and the step of the footprint samples (blocks). */
	static final int STEP = 8, RADIUS = 32, SAMPLE = 5;
	/** Valid shores the lighthouse looks at before keeping the most "cape-like", and at what distance it looks at the surrounding water. */
	static final int LIGHTHOUSE_VALID = 4, CAPE = 24, HEADINGS = 16;
	/** Minimum fraction of the sea samples that must pass (shoals with some rock, shore waves). */
	static final double MIN_SEA = 0.8;
	private static final List<int[]> KNOTS = new ArrayList<>();
	private static final int[][] BEARING = new int[HEADINGS][];

	static {
		for (int dx = -RADIUS; dx <= RADIUS; dx += STEP) {
			for (int dz = -RADIUS; dz <= RADIUS; dz += STEP) {
				if (dx * dx + dz * dz <= RADIUS * RADIUS) {
					KNOTS.add(new int[]{dx, dz});
				}
			}
		}
		KNOTS.sort(Comparator.<int[]>comparingInt(c -> c[0] * c[0] + c[1] * c[1]).thenComparingInt(c -> c[0]).thenComparingInt(c -> c[1]));
		for (int i = 0; i < HEADINGS; i++) {
			double a = 2 * Math.PI * i / HEADINGS;
			BEARING[i] = new int[]{(int) Math.round(Math.cos(a) * CAPE), (int) Math.round(Math.sin(a) * CAPE)};
		}
	}

	private Shoreline() {
	}

	/**
	 * What each variant asks for (the ground is the first free height above the bottom, not counting water; sea, sea level):
	 * <ul>
	 * <li>LIGHTHOUSE: dry land, from sea + 1 to sea + 6 and with at most 4 blocks of drop (the platform, at the height
	 * of the highest point, and the rest with foundations); sea with water at least 2 blocks deep under the jetty;</li>
	 * <li>STRANDED: the bow on the shore (ground from sea - 1 to sea + 3) and the stern on a shoal (water, 1 to 6 deep);</li>
	 * <li>SUNKEN: real land next to the shore and the whole hull in waters 3 to 9 deep.</li>
	 * </ul>
	 */
	public enum Mode {
		LIGHTHOUSE("faro"), STRANDED("encallado"), SUNKEN("hundido");

		/** Saved id (files, NBT and translation keys): never renamed. */
		public final String id;

		Mode(String id) {
			this.id = id;
		}
		public static Mode of(String id) {
			for (Mode t : values()) {
				if (t.id.equals(id)) {
					return t;
				}
			}
			throw new IllegalArgumentException("No coast mode " + id);
		}
	}

	/** The terrain: ground (first free height not counting water) and whether there is water in the column. */
	public interface Terrain {
		int ground(int x, int z);

		boolean water(int x, int z);
	}

	/** Land and sea footprints {x0, z0, x1, z1}, relative to the anchor (x across, z towards the sea). */
	public record Shape(Mode mode, int[] land, int[] seaSide) {
	}

	/** Chosen shore: the anchor (x, z), the direction to the sea, the height of row 0 (lighthouse only; otherwise -1) and its score. */
	public record Site(int x, int z, Direction seaSide, int y, int note) {
	}

	/** Looks for the shore around (cx, cz); null if none works. */
	public static @Nullable Site search(Terrain t, int sea, int cx, int cz, Shape f) {
		Site best = null;
		int valid = 0;
		List<Long> seen = new ArrayList<>();
		for (int[] n : KNOTS) {
			int nx = cx + n[0], nz = cz + n[1];
			if (t.water(nx, nz) || t.ground(nx, nz) > sea + 10) {
				continue;                                  // water or high land: not a shore
			}
			for (Direction d : Direction.Plane.HORIZONTAL) {
				if (!t.water(nx + d.getStepX() * STEP, nz + d.getStepZ() * STEP)) {
					continue;
				}
				int lo = 0, hi = STEP;                    // the last land block between the node and its water neighbor
				while (hi - lo > 1) {
					int mid = (lo + hi) >>> 1;
					if (t.water(nx + d.getStepX() * mid, nz + d.getStepZ() * mid)) {
						hi = mid;
					} else {
						lo = mid;
					}
				}
				int px = nx + d.getStepX() * lo, pz = nz + d.getStepZ() * lo;
				long key = ((long) px << 34) ^ ((long) pz << 4) ^ d.ordinal();
				if (seen.contains(key)) {
					continue;
				}
				seen.add(key);
				Site s = evaluateAt(t, sea, px, pz, d, f);
				if (s == null) {
					continue;
				}
				if (f.mode() != Mode.LIGHTHOUSE) {
					return s;
				}
				if (best == null || s.note() > best.note()) {
					best = s;
				}
				if (++valid >= LIGHTHOUSE_VALID) {
					return best;
				}
			}
		}
		return best;
	}

	/** The footprint with the anchor at (px, pz) and the template's +z towards d; null if it does not work. Public for the tests. */
	public static @Nullable Site evaluateAt(Terrain t, int sea, int px, int pz, Direction d, Shape f) {
		Direction e = d.getCounterClockWise();           // the rotated template's +x
		int[] tr = f.land(), mr = f.seaSide();
		int min = Integer.MAX_VALUE, max = Integer.MIN_VALUE;
		for (int s = tr[0]; s <= tr[2]; s = next(s, tr[2])) {
			for (int k = tr[1]; k <= tr[3]; k = next(k, tr[3])) {
				int x = px + d.getStepX() * k + e.getStepX() * s, z = pz + d.getStepZ() * k + e.getStepZ() * s;
				int ground = t.ground(x, z);
				boolean ok = switch (f.mode()) {
					case LIGHTHOUSE -> !t.water(x, z) && ground >= sea + 1 && ground <= sea + 6;
					case STRANDED -> ground >= sea - 1 && ground <= sea + 3;
					case SUNKEN -> !t.water(x, z) && ground <= sea + 10;
				};
				if (!ok) {
					return null;
				}
				min = Math.min(min, ground);
				max = Math.max(max, ground);
			}
		}
		if (f.mode() == Mode.LIGHTHOUSE && max - min > 4) {
			return null;
		}
		int total = 0, good = 0;
		for (int s = mr[0]; s <= mr[2]; s = next(s, mr[2])) {
			for (int k = mr[1]; k <= mr[3]; k = next(k, mr[3])) {
				int x = px + d.getStepX() * k + e.getStepX() * s, z = pz + d.getStepZ() * k + e.getStepZ() * s;
				total++;
				if (t.water(x, z)) {
					int ground = t.ground(x, z);
					boolean ok = switch (f.mode()) {
						case LIGHTHOUSE -> ground <= sea - 2;
						case STRANDED -> ground >= sea - 6 && ground <= sea - 1;
						case SUNKEN -> ground >= sea - 9 && ground <= sea - 3;
					};
					if (ok) {
						good++;
					}
				}
				if (total - good > (1 - MIN_SEA) * howMany(mr)) {
					return null;                          // it can no longer reach the minimum
				}
			}
		}
		if (f.mode() != Mode.LIGHTHOUSE) {
			return new Site(px, pz, d, -1, 0);
		}
		int water = 0;
		for (int[] r : BEARING) {
			if (t.water(px + r[0], pz + r[1])) {
				water++;
			}
		}
		return new Site(px, pz, d, Math.max(max - 1, sea), water);
	}

	/** Step of a footprint's samples: every SAMPLE blocks and always the last one. */
	private static int next(int v, int end) {
		return v == end ? end + 1 : Math.min(v + SAMPLE, end);
	}

	/** Samples of a footprint. */
	static int howMany(int[] r) {
		return steps(r[0], r[2]) * steps(r[1], r[3]);
	}

	private static int steps(int a, int b) {
		int n = 0;
		for (int v = a; v <= b; v = next(v, b)) {
			n++;
		}
		return n;
	}
}
