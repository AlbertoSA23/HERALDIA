package io.github.albertosa23.heraldia.herald;

import java.util.ArrayList;
import java.util.List;

/**
 * The plan of the Herald's House grounds (herald/Outskirts builds it): the height every column of the protected ring
 * will have, the houses that fit and the cherry trees, from what the survey read of the ground. No game classes (the
 * tests check it with made-up terrain).
 * <ul>
 * <li>The grid is the protected area ({@link Grounds#inArea}), {@code n} x {@code n} columns from (x0, z0). Each column
 * is the town's ({@link #TOWN}: at the town's ground height), natural ground ({@link #LAND}: the only kind it changes),
 * water ({@link #WATER}: left as it is) or kept ({@link #KEPT}: whatever must not move: a road that was built, a hut, a
 * structure, a player's block; its height is a fixed point).</li>
 * <li>The shape it aims at: the ground's mean over a (2 {@code smooth} + 1)^2 window, then the mean of its two closest
 * 1-Lipschitz envelopes (Manhattan: no two side by side columns more than one block apart) and rounded: gentle, with
 * no step, cutting as much as it fills.</li>
 * <li>What it must keep: the town's ground at the footprint, the kept columns, the outer {@code edge} rows as they are
 * (the natural ground the rest blends into), the shore at least as high as the water beside it, and at each column at
 * most {@code cut} blocks cut away or {@code fill} filled in. Each of those is a bound, and so is everything it implies
 * one block per column away from it (the bounds' own 1-Lipschitz closures, two sweeps each). Where the bounds leave
 * room the column takes the shape clamped between them: a 1-Lipschitz height, so no step. Where they do not (a cliff
 * no 10-block cut or fill can soften) it does what the caps allow and the column is counted as {@link #steep}: it may
 * keep a step, and the log says how many.</li>
 * <li>Houses: each slot in order (at most one per group: the others are its second places), while the count asked
 * for is not reached, whose plot (and a block around it) is all
 * natural ground off the {@code avoid} columns, within the caps and whose planned ground varies by at most
 * {@code flat}: its pad is the mean height and the plan is worked out again with the pads as fixed points.</li>
 * <li>Cherry trees: each site in order, up to {@code cherries}, on natural ground with the 3 x 3 around its trunk within
 * a block of it, no water within 3 and no avoided column within 5.</li>
 * </ul>
 */
public final class OutskirtsPlan {
	public static final byte TOWN = 0, LAND = 1, WATER = 2, KEPT = 3;
	private static final int FAR = 1 << 20;

	/** The plan's numbers (heraldia/alrededores_casa.json). */
	public record Params(int cut, int fill, int smooth, int edge, int flat) {
	}

	/** A house slot in world columns: its plot (inclusive), its index in the blueprint and its group (one house each). */
	public record Slot(int index, int x0, int z0, int x1, int z1, int group) {
		public Slot(int index, int x0, int z0, int x1, int z1) {
			this(index, x0, z0, x1, z1, index);
		}
	}

	/** A house that fits: its slot and the pad's height (the y of its ground layer). */
	public record House(Slot slot, int y) {
	}

	/** The result: the planned heights (LAND columns; the rest as surveyed), the houses, the trees and the counts. */
	public record Result(int[] target, List<House> houses, List<int[]> cherries, int changed, int maxCut, int maxFill, int steep,
			int steps, int before, int lids) {
	}

	/** The window (a square of 2 NARROW + 1) a pit or a spike must fit in to be taken as one, not as a valley or a hill. */
	public static final int NARROW = 3;

	private final int x0, z0, n, groundY;
	private final byte[] kind;
	private final int[] h;
	private final Params p;
	/** The height each column's caps count from: its own, but that of the ground round a narrow pit or spike. */
	private final int[] ref;

	/**
	 * @param kind    {@link #TOWN}, {@link #LAND}, {@link #WATER} or {@link #KEPT} per column, index (x - x0) * n + (z - z0)
	 * @param h       the ground's top block y (the water's top for WATER; anything for TOWN)
	 * @param groundY the town's ground height (its footprint's top layer)
	 */
	public OutskirtsPlan(int x0, int z0, int n, byte[] kind, int[] h, int groundY, Params p) {
		this.x0 = x0;
		this.z0 = z0;
		this.n = n;
		this.kind = kind;
		this.h = h;
		this.groundY = groundY;
		this.p = p;
		this.ref = reference();
	}

	/**
	 * The caps' reference heights. A narrow pit (a ravine, a cave's mouth, a sinkhole: deeper than {@code fill} under the
	 * natural ground's morphological closing over a (2 NARROW + 1)^2 window) counts from the ground round it, so it is
	 * covered (with a lid, {@link #lid}) instead of a crater being dug round it. Anything wider (a valley, a hill) keeps
	 * its own height: the caps hold there, and a spike, which no window tells from the rim of a pit beside it, too.
	 */
	private int[] reference() {
		int[] low = new int[n * n];                       // natural ground only: water, kept columns and the town are
		for (int i = 0; i < n * n; i++) {                 // neutral (a flooded ravine beside raises nothing)
			low[i] = kind[i] == LAND ? h[i] : Integer.MIN_VALUE / 2;
		}
		int[] closing = window(window(low, true), false);
		int[] out = h.clone();
		for (int i = 0; i < n * n; i++) {
			if (kind[i] == LAND && closing[i] - h[i] > p.fill()) {
				out[i] = closing[i];
			}
		}
		return out;
	}

	/** The max ({@code max}) or min over the (2 NARROW + 1)^2 window round each column (two separable passes). */
	private int[] window(int[] a, boolean max) {
		int[] row = new int[n * n], out = new int[n * n];
		for (int u = 0; u < n; u++) {
			for (int v = 0; v < n; v++) {
				int best = a[u * n + v];
				for (int k = Math.max(0, v - NARROW); k <= Math.min(n - 1, v + NARROW); k++) {
					best = max ? Math.max(best, a[u * n + k]) : Math.min(best, a[u * n + k]);
				}
				row[u * n + v] = best;
			}
		}
		for (int u = 0; u < n; u++) {
			for (int v = 0; v < n; v++) {
				int best = row[u * n + v];
				for (int k = Math.max(0, u - NARROW); k <= Math.min(n - 1, u + NARROW); k++) {
					best = max ? Math.max(best, row[k * n + v]) : Math.min(best, row[k * n + v]);
				}
				out[u * n + v] = best;
			}
		}
		return out;
	}

	/** Is the column a narrow pit the plan covers with a lid (filled more than {@code fill} over its floor)? */
	public boolean lid(int i, int target) {
		return kind[i] == LAND && target - h[i] > p.fill();
	}

	public int index(int x, int z) {
		return (x - x0) * n + (z - z0);
	}

	public boolean contains(int x, int z) {
		return x >= x0 && z >= z0 && x < x0 + n && z < z0 + n;
	}

	private boolean edge(int i) {
		int u = i / n, v = i % n;
		return u < p.edge() || v < p.edge() || u >= n - p.edge() || v >= n - p.edge();
	}

	/** The value the shape is made from: the ground, the water's surface, the town's ground. */
	private int value(int i) {
		return kind[i] == TOWN ? groundY : h[i];
	}

	/** The whole plan: heights, then the houses (and the heights again with their pads), then the trees. */
	public Result plan(List<Slot> slots, int houses, List<int[]> sites, int cherries, boolean[] avoid) {
		double[] shape = shape();
		int[] fixed = new int[n * n];
		java.util.Arrays.fill(fixed, Integer.MIN_VALUE);
		int[] steep = new int[1];
		int[] t = solve(shape, fixed, steep);
		List<House> chosen = new ArrayList<>();
		java.util.Set<Integer> groups = new java.util.HashSet<>();
		for (Slot s : slots) {
			if (chosen.size() >= houses) {
				break;
			}
			if (groups.contains(s.group())) {
				continue;                              // its group has its house (an alternative is only a second place)
			}
			Integer y = pad(s, t, avoid);
			if (y != null) {
				groups.add(s.group());
				chosen.add(new House(s, y));
				for (int x = s.x0() - 1; x <= s.x1() + 1; x++) {
					for (int z = s.z0() - 1; z <= s.z1() + 1; z++) {
						fixed[index(x, z)] = y;
					}
				}
			}
		}
		if (!chosen.isEmpty()) {
			steep[0] = 0;
			t = solve(shape, fixed, steep);
		}
		List<int[]> trees = new ArrayList<>();
		for (int[] c : sites) {
			if (trees.size() >= cherries) {
				break;
			}
			if (tree(c[0], c[1], t, avoid, chosen)) {
				trees.add(c);
			}
		}
		int changed = 0, maxCut = 0, maxFill = 0, lids = 0;
		for (int i = 0; i < n * n; i++) {
			if (kind[i] == LAND && t[i] != h[i]) {
				changed++;
				lids += lid(i, t[i]) ? 1 : 0;
				maxCut = Math.max(maxCut, ref[i] - t[i]);        // the earthwork: a pit's lid and a spike's cut are not
				maxFill = Math.max(maxFill, t[i] - ref[i]);
			}
		}
		return new Result(t, List.copyOf(chosen), List.copyOf(trees), changed, maxCut, maxFill, steep[0], steps(t), steps(h), lids);
	}

	/** The shape: the window's mean, then the mean of its two 1-Lipschitz envelopes. */
	double[] shape() {
		long[] sum = new long[(n + 1) * (n + 1)];          // a summed-area table
		for (int u = 0; u < n; u++) {
			long row = 0;
			for (int v = 0; v < n; v++) {
				row += value(u * n + v);
				sum[(u + 1) * (n + 1) + v + 1] = sum[u * (n + 1) + v + 1] + row;
			}
		}
		int r = p.smooth();
		double[] mean = new double[n * n];
		for (int u = 0; u < n; u++) {
			int a = Math.max(0, u - r), b = Math.min(n - 1, u + r);
			for (int v = 0; v < n; v++) {
				int c = Math.max(0, v - r), d = Math.min(n - 1, v + r);
				long s = sum[(b + 1) * (n + 1) + d + 1] - sum[a * (n + 1) + d + 1] - sum[(b + 1) * (n + 1) + c] + sum[a * (n + 1) + c];
				mean[u * n + v] = (double) s / ((b - a + 1) * (d - c + 1));
			}
		}
		double[] lo = mean.clone(), hi = mean.clone();
		sweep(lo, true);
		sweep(hi, false);
		for (int i = 0; i < n * n; i++) {
			lo[i] = (lo[i] + hi[i]) / 2;
		}
		return lo;
	}

	/**
	 * In place, the closest 1-Lipschitz (Manhattan) function on one side of {@code a}: {@code below} the largest one under
	 * it (each value at most its neighbour's + 1), else the smallest one over it. Two sweeps are exact for this metric.
	 */
	void sweep(double[] a, boolean below) {
		for (int pass = 0; pass < 2; pass++) {
			for (int k = 0; k < n * n; k++) {
				int i = pass == 0 ? k : n * n - 1 - k, u = i / n, v = i % n, d = pass == 0 ? -1 : 1;
				int pu = u + d, pv = v + d;
				if (pu >= 0 && pu < n) {
					a[i] = below ? Math.min(a[i], a[pu * n + v] + 1) : Math.max(a[i], a[pu * n + v] - 1);
				}
				if (pv >= 0 && pv < n) {
					a[i] = below ? Math.min(a[i], a[u * n + pv] + 1) : Math.max(a[i], a[u * n + pv] - 1);
				}
			}
		}
	}

	private void sweep(int[] a, boolean below) {
		for (int pass = 0; pass < 2; pass++) {
			for (int k = 0; k < n * n; k++) {
				int i = pass == 0 ? k : n * n - 1 - k, u = i / n, v = i % n, d = pass == 0 ? -1 : 1;
				int pu = u + d, pv = v + d;
				if (pu >= 0 && pu < n) {
					a[i] = below ? Math.min(a[i], a[pu * n + v] + 1) : Math.max(a[i], a[pu * n + v] - 1);
				}
				if (pv >= 0 && pv < n) {
					a[i] = below ? Math.min(a[i], a[u * n + pv] + 1) : Math.max(a[i], a[u * n + pv] - 1);
				}
			}
		}
	}

	/** The heights: the shape clamped between the bounds (fixed: extra fixed points, MIN_VALUE where none). */
	int[] solve(double[] shape, int[] fixed, int[] steep) {
		int[] lo = new int[n * n], up = new int[n * n];
		for (int i = 0; i < n * n; i++) {
			if (fixed[i] != Integer.MIN_VALUE) {
				lo[i] = up[i] = fixed[i];
			} else if (kind[i] == TOWN) {
				lo[i] = up[i] = groundY;
			} else if (kind[i] == KEPT) {
				lo[i] = up[i] = h[i];
			} else if (kind[i] == LAND && edge(i)) {
				lo[i] = up[i] = ref[i];                  // the natural ground, but a pit's lid where it meets one
			} else if (kind[i] == WATER) {
				lo[i] = -FAR;
				up[i] = FAR;
			} else {
				lo[i] = ref[i] - p.cut();
				up[i] = ref[i] + p.fill();
				int u = i / n, v = i % n;            // the shore: never under the water beside it
				int[][] nb = {{u + 1, v}, {u - 1, v}, {u, v + 1}, {u, v - 1}};
				for (int[] q : nb) {
					if (q[0] >= 0 && q[1] >= 0 && q[0] < n && q[1] < n && kind[q[0] * n + q[1]] == WATER) {
						lo[i] = Math.max(lo[i], Math.min(h[q[0] * n + q[1]], up[i]));
					}
				}
			}
		}
		sweep(lo, false);                              // what each bound implies one block per column away
		sweep(up, true);
		int[] t = new int[n * n];
		boolean[] free = new boolean[n * n];
		for (int i = 0; i < n * n; i++) {
			if (kind[i] != LAND) {
				t[i] = h[i];
				continue;
			}
			if (fixed[i] != Integer.MIN_VALUE) {
				t[i] = fixed[i];
				continue;
			}
			if (edge(i)) {
				t[i] = ref[i];
				continue;
			}
			int s = (int) Math.floor(shape[i] + 0.5);
			if (lo[i] <= up[i]) {
				t[i] = Math.clamp(s, lo[i], up[i]);
			} else {
				steep[0]++;
				free[i] = true;
				t[i] = Math.clamp(s, up[i], lo[i]);
			}
			t[i] = Math.clamp(t[i], ref[i] - p.cut(), ref[i] + p.fill());
		}
		relax(t, free);
		return t;
	}

	/**
	 * Where the bounds left no room ({@code free}: the columns counted as too steep): a few passes that move each of them
	 * to the height that leaves the fewest steps with its neighbours, within the caps; a column the bounds did leave room
	 * for is never moved (it is already within a block of all of its own), so the harm cannot spread.
	 */
	private void relax(int[] t, boolean[] free) {
		for (int pass = 0; pass < 8; pass++) {
			boolean moved = false;
			for (int i = 0; i < n * n; i++) {
				if (!free[i]) {
					continue;
				}
				int u = i / n, v = i % n, best = t[i], worst = Integer.MAX_VALUE;
				for (int y = ref[i] - p.cut(); y <= ref[i] + p.fill(); y++) {
					int bad = 0;
					int[][] nb = {{u + 1, v}, {u - 1, v}, {u, v + 1}, {u, v - 1}};
					for (int[] q : nb) {
						if (q[0] >= 0 && q[1] >= 0 && q[0] < n && q[1] < n && kind[q[0] * n + q[1]] != WATER) {
							bad += Math.max(0, Math.abs(t[q[0] * n + q[1]] - y) - 1);
						}
					}
					if (bad < worst || bad == worst && Math.abs(y - t[i]) < Math.abs(best - t[i])) {
						worst = bad;
						best = y;
					}
				}
				if (best != t[i]) {
					t[i] = best;
					moved = true;
				}
			}
			if (!moved) {
				return;
			}
		}
	}

	/**
	 * Pairs of side by side columns more than a block apart (in {@code t}): neither water nor the town's, and one of them
	 * at least natural ground the plan may move (two kept columns, or two of the edge's, are the world's own).
	 */
	int steps(int[] t) {
		int out = 0;
		for (int u = 0; u < n; u++) {
			for (int v = 0; v < n; v++) {
				int i = u * n + v;
				if (u + 1 < n && pair(i, i + n) && Math.abs(t[i + n] - t[i]) > 1) {
					out++;
				}
				if (v + 1 < n && pair(i, i + 1) && Math.abs(t[i + 1] - t[i]) > 1) {
					out++;
				}
			}
		}
		return out;
	}

	private boolean pair(int a, int b) {
		if (kind[a] == WATER || kind[a] == TOWN || kind[b] == WATER || kind[b] == TOWN) {
			return false;
		}
		return kind[a] == LAND && !edge(a) || kind[b] == LAND && !edge(b);
	}

	/** A house's pad height, or null if its plot (and a block around it) does not fit. */
	private Integer pad(Slot s, int[] t, boolean[] avoid) {
		if (!contains(s.x0() - 1, s.z0() - 1) || !contains(s.x1() + 1, s.z1() + 1)) {
			return null;
		}
		long sum = 0;
		int cells = 0, min = Integer.MAX_VALUE, max = Integer.MIN_VALUE;
		for (int x = s.x0() - 1; x <= s.x1() + 1; x++) {
			for (int z = s.z0() - 1; z <= s.z1() + 1; z++) {
				int i = index(x, z);
				if (kind[i] != LAND || edge(i) || avoid[i]) {
					return null;
				}
				sum += t[i];
				cells++;
				min = Math.min(min, t[i]);
				max = Math.max(max, t[i]);
			}
		}
		if (max - min > p.flat()) {
			return null;
		}
		int y = (int) Math.round((double) sum / cells);
		for (int x = s.x0() - 1; x <= s.x1() + 1; x++) {
			for (int z = s.z0() - 1; z <= s.z1() + 1; z++) {
				int i = index(x, z);
				if (y < ref[i] - p.cut() || y > ref[i] + p.fill()) {
					return null;
				}
			}
		}
		return y;
	}

	private boolean tree(int x, int z, int[] t, boolean[] avoid, List<House> houses) {
		if (!contains(x - 5, z - 5) || !contains(x + 5, z + 5)) {
			return false;
		}
		int c = t[index(x, z)];
		for (int dx = -5; dx <= 5; dx++) {
			for (int dz = -5; dz <= 5; dz++) {
				int i = index(x + dx, z + dz);
				if (avoid[i] || Math.abs(dx) <= 3 && Math.abs(dz) <= 3 && (kind[i] == WATER || kind[i] == TOWN || kind[i] == KEPT)
						|| Math.abs(dx) <= 1 && Math.abs(dz) <= 1 && (kind[i] != LAND || Math.abs(t[i] - c) > 1)) {
					return false;
				}
			}
		}
		for (House hs : houses) {
			Slot s = hs.slot();
			if (x >= s.x0() - 6 && x <= s.x1() + 6 && z >= s.z0() - 6 && z <= s.z1() + 6) {
				return false;
			}
		}
		return true;
	}
}
