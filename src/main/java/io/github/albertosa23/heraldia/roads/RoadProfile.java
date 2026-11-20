package io.github.albertosa23.heraldia.roads;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.jspecify.annotations.Nullable;

/**
 * The height and the kind of ground a BUILT road keeps along its length (herald/SpawnRoads through {@link BuiltRoads}),
 * so that it reads as one work instead of following every bump of the terrain:
 * <ul>
 * <li>The natural ground (under any tree, plant or snow) is sampled on the axis, one sample per block of length.</li>
 * <li>The road's height at a block of length is the mean of the samples {@link #LEVEL} blocks before and after it (the
 * highest and the lowest left out), and never more than one block from the height next to it (the heights are worked
 * out as one unbroken stretch): the whole width at that length sits at that one height, and a slope climbs in regular
 * one-block steps.</li>
 * <li>Its kind of ground (and so its paving) is the one most samples {@link #KIND} blocks around it have (the nearest
 * weigh more): a road changes from dirt to sand at one line across it, not in loose patches.</li>
 * </ul>
 * Every sample and every height is kept once computed, so the chunks the road crosses (built one by one, in any order)
 * agree at their borders and never break the one-block rule. A sample whose chunk is not loaded yet is not kept (it is asked for again later) and does not
 * count. No game classes: the tests check it.
 * <p>
 * Built roads work out the whole road at once first ({@link #prepare}), once every chunk under its axis and its two edges
 * is loaded: the heights are then the mean above, made one-block-per-block (the mean of its two closest such envelopes)
 * and kept within what the paving's caps allow at every block of length (the ground under the axis and both edges cut
 * at most {@code cut} and filled at most {@code fill}), with those bounds' own one-block closures: a climb starts early
 * enough to top a rise the caps could not cut alone, so no column needs more than the caps and the road never steps.
 * Where even that cannot be done (a cliff higher than both caps and the road's run together), the caps are widened a
 * block at a time (up to {@link #MAX_CAP}) only as far as needed; {@link #cut()} and {@link #fill()} say how far, for the
 * columns' own clamp. Computed lazily block by block (as above) only if {@link #prepare} never ran.
 */
public final class RoadProfile {
	/** Samples on each side that make a height (the mean of 2 * LEVEL + 1, the highest and the lowest left out). */
	public static final int LEVEL = 5;
	/** Samples on each side that choose the kind of ground. */
	public static final int KIND = 8;
	/** No height: no land sample near (water, a structure, chunks not loaded). */
	public static final int MISSING = Integer.MIN_VALUE;
	/** The most a prepared road may cut or fill where its normal caps cannot keep it walkable. */
	public static final int MAX_CAP = 24;

	/** The kinds of natural ground, each with its own paving ({@link BuiltRoads#deck}). */
	public enum Ground { MUD, DIRT, RED, SAND, STONE }

	/** The natural ground at a column: its kind (null: no land, i.e. water, a structure or a player's block) and height. */
	public record Sample(@Nullable Ground ground, int y) {
	}

	/** The ground at a column, or null if its chunk is not loaded (it will be asked for again). */
	public interface Sampler {
		@Nullable Sample at(int x, int z);
	}

	private final RoadLayout.Route route;
	private final Map<Integer, Sample> samples = new HashMap<>();
	private final Map<Integer, Integer> heights = new HashMap<>();
	private final Map<Integer, Ground> grounds = new HashMap<>();

	/** The caps the prepared heights need (the normal ones unless a cliff asked for more); 0 until prepared. */
	private int cut, fill;

	public RoadProfile(RoadLayout.Route route) {
		this.route = route;
	}

	public int cut() {
		return cut;
	}

	public int fill() {
		return fill;
	}

	public boolean prepared() {
		return cut > 0;
	}

	/** The columns {@link #prepare} reads (x, z): the axis and both edges at every block of length. */
	public List<int[]> columns(double halfWidth) {
		List<int[]> out = new ArrayList<>();
		for (int i = 0; i <= last(); i++) {
			for (double[] q : across(i, halfWidth)) {
				out.add(new int[] {(int) Math.floor(q[0]), (int) Math.floor(q[1])});
			}
		}
		return out;
	}

	/** The axis point at block i of length and the two points {@code halfWidth} to either side of it. */
	private double[][] across(int i, double halfWidth) {
		double[] p = point(i), a = point(Math.max(0, i - 1)), b = point(Math.min(last(), i + 1));
		double dx = b[0] - a[0], dz = b[1] - a[1], len = Math.hypot(dx, dz);
		if (len < 1e-9) {
			return new double[][] {p};
		}
		double nx = -dz / len * halfWidth, nz = dx / len * halfWidth;
		return new double[][] {p, {p[0] + nx, p[1] + nz}, {p[0] - nx, p[1] - nz}};
	}

	/**
	 * The whole road's heights at once (see the class comment), within caps of {@code cut} and {@code fill} (widened only
	 * where needed). False, and nothing kept, if a column it reads is not loaded yet.
	 */
	public boolean prepare(Sampler f, double halfWidth, int cut, int fill) {
		int m = last() + 1;
		int[] lo = new int[m], up = new int[m];
		double[] raw = new double[m];
		boolean any = false;
		for (int i = 0; i < m; i++) {
			int min = Integer.MAX_VALUE, max = Integer.MIN_VALUE;
			for (double[] q : across(i, halfWidth)) {
				Sample s = f.at((int) Math.floor(q[0]), (int) Math.floor(q[1]));
				if (s == null) {
					return false;
				}
				if (s.ground() != null) {
					min = Math.min(min, s.y());
					max = Math.max(max, s.y());
				}
			}
			lo[i] = max == Integer.MIN_VALUE ? MISSING : max;   // the highest ground across (it is cut down to the road)
			up[i] = min == Integer.MAX_VALUE ? MISSING : min;   // and the lowest (filled up to it)
			int r = raw(i, f);
			raw[i] = r == MISSING ? Double.NaN : r;
			any |= r != MISSING;
		}
		if (!any) {
			return false;
		}
		double carry = Double.NaN;                         // a stretch with no land (water) carries the height it reached
		for (int i = 0; i < m; i++) {
			carry = Double.isNaN(raw[i]) ? carry : raw[i];
			raw[i] = carry;
		}
		for (int i = m - 1; i >= 0; i--) {
			carry = Double.isNaN(raw[i]) ? carry : raw[i];
			raw[i] = Double.isNaN(raw[i]) ? carry : raw[i];
		}
		double[] below = raw.clone(), above = raw.clone();
		for (int i = 1; i < m; i++) {
			below[i] = Math.min(below[i], below[i - 1] + 1);
			above[i] = Math.max(above[i], above[i - 1] - 1);
		}
		for (int i = m - 2; i >= 0; i--) {
			below[i] = Math.min(below[i], below[i + 1] + 1);
			above[i] = Math.max(above[i], above[i + 1] - 1);
		}
		for (int c = 0; ; c++) {
			int cu = cut + c, fi = fill + c;
			int[] a = new int[m], b = new int[m];
			for (int i = 0; i < m; i++) {
				a[i] = lo[i] == MISSING ? Integer.MIN_VALUE / 2 : lo[i] - cu;
				b[i] = up[i] == MISSING ? Integer.MAX_VALUE / 2 : up[i] + fi;
			}
			for (int i = 1; i < m; i++) {
				a[i] = Math.max(a[i], a[i - 1] - 1);
				b[i] = Math.min(b[i], b[i - 1] + 1);
			}
			boolean ok = true;
			for (int i = m - 2; i >= 0; i--) {
				a[i] = Math.max(a[i], a[i + 1] - 1);
				b[i] = Math.min(b[i], b[i + 1] + 1);
			}
			for (int i = 0; i < m; i++) {
				ok &= a[i] <= b[i];
			}
			if (!ok && cut + c < MAX_CAP && fill + c < MAX_CAP) {
				continue;
			}
			heights.clear();
			for (int i = 0; i < m; i++) {
				int h = (int) Math.floor((below[i] + above[i]) / 2 + 0.5);
				heights.put(i, a[i] <= b[i] ? Math.clamp(h, a[i], b[i]) : Math.clamp(h, b[i], a[i]));
			}
			this.lo = 0;
			this.hi = m - 1;
			this.cut = cu;
			this.fill = fi;
			return true;
		}
	}

	/** The last block of length. */
	int last() {
		return (int) Math.floor(route.s[route.s.length - 1]);
	}

	private int index(double arc) {
		return Math.clamp(Math.round(arc), 0, last());
	}

	/** The point of the axis {@code arc} blocks along it. */
	double[] point(double arc) {
		double[] s = route.s;
		int lo = 0, hi = s.length - 1;
		while (hi - lo > 1) {
			int mid = (lo + hi) >>> 1;
			if (s[mid] <= arc) {
				lo = mid;
			} else {
				hi = mid;
			}
		}
		double len = s[hi] - s[lo], t = len <= 0 ? 0 : Math.clamp((arc - s[lo]) / len, 0, 1);
		return new double[] {route.xs[lo] + (route.xs[hi] - route.xs[lo]) * t, route.zs[lo] + (route.zs[hi] - route.zs[lo]) * t};
	}

	private @Nullable Sample sample(int i, Sampler f) {
		Sample s = samples.get(i);
		if (s == null) {
			double[] p = point(i);
			s = f.at((int) Math.floor(p[0]), (int) Math.floor(p[1]));
			if (s != null) {
				samples.put(i, s);
			}
		}
		return s;
	}

	/**
	 * The road's height at {@code arc} blocks along it (the y of its paving), or {@link #MISSING}. The heights known are
	 * always one unbroken stretch of the road: a height outside it extends it block by block from its nearer end, each
	 * within one of the one before, so no two neighbouring heights are ever more than one apart, whatever order the
	 * chunks ask in. A stretch with no land sample (water) carries the height it reached.
	 */
	public int height(double arc, Sampler f) {
		int i = index(arc);
		Integer known = heights.get(i);
		if (known != null) {
			return known;
		}
		if (heights.isEmpty()) {
			int h = raw(i, f);
			if (h == MISSING) {
				return MISSING;
			}
			heights.put(i, h);
			lo = hi = i;
			return h;
		}
		while (hi < i) {
			int before = heights.get(hi), h = raw(hi + 1, f);
			heights.put(++hi, h == MISSING ? before : Math.clamp(h, before - 1, before + 1));
		}
		while (lo > i) {
			int after = heights.get(lo), h = raw(lo - 1, f);
			heights.put(--lo, h == MISSING ? after : Math.clamp(h, after - 1, after + 1));
		}
		return heights.get(i);
	}

	/** The first and last block of length whose height is known (with {@link #heights} not empty). */
	private int lo, hi;

	/** The mean of the land samples LEVEL blocks around i (the highest and the lowest left out), or MISSING. */
	private int raw(int i, Sampler f) {
		int n = 0, min = Integer.MAX_VALUE, max = Integer.MIN_VALUE;
		long sum = 0;
		for (int j = Math.max(0, i - LEVEL); j <= Math.min(last(), i + LEVEL); j++) {
			Sample s = sample(j, f);
			if (s != null && s.ground() != null) {
				n++;
				sum += s.y();
				min = Math.min(min, s.y());
				max = Math.max(max, s.y());
			}
		}
		if (n == 0) {
			return MISSING;
		}
		if (n >= 5) {
			sum -= min + max;
			n -= 2;
		}
		return (int) Math.round((double) sum / n);
	}

	/** The road's kind of ground at {@code arc} blocks along it, or null with no land sample near. */
	public @Nullable Ground ground(double arc, Sampler f) {
		int i = index(arc);
		Ground known = grounds.get(i);
		if (known != null) {
			return known;
		}
		int[] weight = new int[Ground.values().length];
		boolean any = false;
		for (int j = Math.max(0, i - KIND); j <= Math.min(last(), i + KIND); j++) {
			Sample s = sample(j, f);
			if (s != null && s.ground() != null) {
				weight[s.ground().ordinal()] += KIND + 1 - Math.abs(j - i);
				any = true;
			}
		}
		if (!any) {
			return null;
		}
		int best = 0;
		for (int k = 1; k < weight.length; k++) {
			if (weight[k] > weight[best]) {
				best = k;
			}
		}
		Ground g = Ground.values()[best];
		grounds.put(i, g);
		return g;
	}
}
