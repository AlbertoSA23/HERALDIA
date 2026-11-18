package io.github.albertosa23.heraldia.villages;

import java.util.ArrayList;
import java.util.List;
import java.util.function.Function;
import java.util.function.Predicate;
import net.minecraft.core.Direction;

/**
 * Choice of the shore for a coastal village's port (pure logic: the bottom and the obstacles come in as
 * functions, so it is tested with synthetic height maps).
 *
 * <p>The bottom is checked on a grid of {@link #STEP} blocks within a circle of radius {@code reach} around the
 * plaza, inside out. Each low land node (0 to {@link #SHALLOW} blocks above the sea) with a water neighbor gives
 * a candidate shore towards that neighbor, refined between the two with a binary search. So all the shores along
 * the coast come out, not only those of four rays (which followed the avenues and fell next to the plaza or on a street).
 * The village's pieces cost no terrain lookups, so they are checked first: the directions of a node in which the port
 * would collide at any point between the node and its neighbor are discarded without querying the bottom, and in each
 * candidate the obstacles are checked before the water: bottom under the tip, halfway, beyond and to the sides (open sea,
 * not an inlet). The nearest free one wins; if none is free, the nearest one that only displaces houses. The bottom of
 * each column is requested at most once (the cache lives in the function) and only until a free shore is found.
 */
final class Shoreline {
	/** Grid step. */
	static final int STEP = 16;
	/** Maximum height above the sea of the shore's land (a beach; a cliff next to the water does not work). */
	static final int SHALLOW = 4;
	/** Sea beyond the tip and on each side of it (the pier's boats). */
	static final int BEYOND = 6, SIDE = 7;

	private Shoreline() {
	}

	/** Bottom height ({@code OCEAN_FLOOR_WG}) of a column. */
	@FunctionalInterface
	interface Seabed {
		int en(int x, int z);
	}

	/** Candidate shore: last low land point before the water, with the direction to the sea. */
	record Shore(int x, int z, int y, Direction sea) {
	}

	/**
	 * Chosen shore (null if none) with what it displaces, and counts for the log: candidate shores, without bottom,
	 * blocked, node directions discarded by the pieces before looking at the terrain, and bottom queries.
	 */
	record Choice<R>(Shore shore, R gone, int candidates, int noSeabed, int blocked, int discarded, int queries) {
	}

	/** Distances from the node at which the shore is estimated to discard directions using only the pieces. */
	private static final int[] ESTIMATE = {2, 8, 14};
	/** Offsets along the coast of a node's line when the pieces cover it. */
	private static final int[] LATERAL = {0, 8, -8};

	/**
	 * Looks for the shore. {@code obstacle} gives, for a shore, what would have to be removed from the village to put the
	 * port there, or null if it collides with something that is not removed; {@code free} says whether that removes nothing. Before checking the bottom of
	 * a node, each direction is tried with the shore estimated at 2, 8 and 14 blocks (sea level + 1): if it collides in all
	 * three, the parallel line 8 blocks to each side (along the coast) is tried and, if that too, that direction is not
	 * checked (the pieces cost no terrain lookups; the village's center spends no queries). A side line is only queried
	 * where the grid already sees coast (low land node and water neighbor).
	 */
	static <R> Choice<R> choose(Seabed depth, int sea, int cx, int cz, int reach, int length, Function<Shore, R> obstacle,
								  Predicate<R> free) {
		int[] queries = {0};
		Seabed h = (x, z) -> {
			queries[0]++;
			return depth.en(x, z);
		};
		int k = reach / STEP, noSeabed = 0, blocked = 0, candidates = 0, discarded = 0;
		List<Shore> displace = new ArrayList<>();
		List<R> remove = new ArrayList<>();
		int[] off = new int[4];
		for (int[] n : knots(k)) {
			int gx = cx + n[0] * STEP, gz = cz + n[1] * STEP;
			// the node's line towards each direction or, if the pieces cover it, the one beside it (8 blocks along the coast)
			boolean some = false;
			for (Direction d : Direction.Plane.HORIZONTAL) {
				off[d.get2DDataValue()] = line(obstacle, gx, gz, sea, d);
				if (off[d.get2DDataValue()] == NONE) {
					discarded++;
				} else {
					some = true;
				}
			}
			if (!some) {
				continue;
			}
			int fg = h.en(gx, gz);
			if (fg < sea || fg - sea > SHALLOW) {
				continue;
			}
			for (Direction d : Direction.Plane.HORIZONTAL) {
				int o = off[d.get2DDataValue()];
				// the grid must see coast in this direction (low land node, water neighbor) before refining
				if (o == NONE || h.en(gx + d.getStepX() * STEP, gz + d.getStepZ() * STEP) >= sea) {
					continue;
				}
				Direction side = d.getClockWise();
				int x = gx + side.getStepX() * o, z = gz + side.getStepZ() * o, f = o == 0 ? fg : h.en(x, z);
				if (f < sea || f - sea > SHALLOW || (o != 0 && h.en(x + d.getStepX() * STEP, z + d.getStepZ() * STEP) >= sea)) {
					continue;
				}
				Shore s = refine(h, sea, x, z, f, d);
				if (s == null) {
					continue;
				}
				candidates++;
				R gone = obstacle.apply(s);
				if (gone == null) {
					blocked++;
				} else if (!free.test(gone)) {
					displace.add(s);
					remove.add(gone);
				} else if (seaSide(h, sea, s, length)) {
					return new Choice<>(s, gone, candidates, noSeabed, blocked, discarded, queries[0]);
				} else {
					noSeabed++;
				}
			}
		}
		for (int i = 0; i < displace.size(); i++) {
			if (seaSide(h, sea, displace.get(i), length)) {
				return new Choice<>(displace.get(i), remove.get(i), candidates, noSeabed, blocked, discarded, queries[0]);
			}
			noSeabed++;
		}
		return new Choice<>(null, null, candidates, noSeabed, blocked, discarded, queries[0]);
	}

	/** No possible line (in {@link #line}). */
	static final int NONE = Integer.MIN_VALUE;

	/** Lateral offset of the node's first line towards d in which the pieces allow placing the port, or NONE. */
	static <R> int line(Function<Shore, R> obstacle, int x, int z, int sea, Direction d) {
		Direction side = d.getClockWise();
		for (int o : LATERAL) {
			if (possible(obstacle, x + side.getStepX() * o, z + side.getStepZ() * o, sea, d)) {
				return o;
			}
		}
		return NONE;
	}

	/** Does some estimated shore between the node and its neighbor in direction d allow placing the port? (without looking at the terrain) */
	static <R> boolean possible(Function<Shore, R> obstacle, int x, int z, int sea, Direction d) {
		for (int lo : ESTIMATE) {
			if (obstacle.apply(new Shore(x + d.getStepX() * lo, z + d.getStepZ() * lo, sea + 1, d)) != null) {
				return true;
			}
		}
		return false;
	}

	/** Grid nodes (i, j) within the circle of radius k, inside out (always the same order). */
	static List<int[]> knots(int k) {
		List<int[]> out = new ArrayList<>();
		for (int r2 = 0; r2 <= k * k; r2++) {
			for (int i = -k; i <= k; i++) {
				for (int j = -k; j <= k; j++) {
					if (i * i + j * j == r2) {
						out.add(new int[]{i, j});
					}
				}
			}
		}
		return out;
	}

	/**
	 * Between the land node (x, z, with bottom f) and its water neighbor in direction d: the last land point with
	 * step 2 (binary search, 3 columns). Null if that point is no longer low land.
	 */
	static Shore refine(Seabed h, int sea, int x, int z, int f, Direction d) {
		int lo = 0, hi = STEP, flo = f;
		while (hi - lo > 2) {
			int mid = (lo + hi) / 2, fm = h.en(x + d.getStepX() * mid, z + d.getStepZ() * mid);
			if (fm >= sea) {
				lo = mid;
				flo = fm;
			} else {
				hi = mid;
			}
		}
		return flo - sea > SHALLOW ? null : new Shore(x + d.getStepX() * lo, z + d.getStepZ() * lo, flo, d);
	}

	/**
	 * Water for the pier from the shore: bottom of 2 under the tip, water halfway, beyond the tip and to the sides
	 * (open sea, not an inlet that ends in land). From most to least likely, to cut short early.
	 */
	static boolean seaSide(Seabed h, int sea, Shore s, int length) {
		Direction d = s.sea(), side = d.getClockWise();
		int tx = s.x() + d.getStepX() * length, tz = s.z() + d.getStepZ() * length;
		return h.en(tx, tz) <= sea - 2
				&& h.en(s.x() + d.getStepX() * (length / 2), s.z() + d.getStepZ() * (length / 2)) < sea
				&& h.en(tx + d.getStepX() * BEYOND, tz + d.getStepZ() * BEYOND) < sea
				&& h.en(tx + side.getStepX() * SIDE, tz + side.getStepZ() * SIDE) < sea
				&& h.en(tx - side.getStepX() * SIDE, tz - side.getStepZ() * SIDE) < sea;
	}
}
