package io.github.albertosa23.heraldia.roads;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Layout of the roads between villages (pure logic, no game classes: the unit tests check it).
 * <p>Everything comes from the seed and the villages' grid, without looking at chunks: each chunk computes on its own which segments
 * cross it and paints them in its 16 x 16 columns, so two neighboring chunks always match at the border, whatever order
 * and whatever thread they are generated in.
 * <ul>
 * <li>Villages: at most one per grid cell ({@link Villages}, in the game with the same rules as
 * generation). Two villages within the maximum distance are joined if no third one is closer to both than they are
 * to each other (relative neighborhood graph): no triangles or crossing roads, and the same answer from both.</li>
 * <li>Route: from the village with the lower key to the one with the higher (so A→B and B→A are the same), optionally through a
 * waypoint next to a structure ({@link Milestones}), with a gentle meander that comes from the seed and fades at the ends.
 * Vertices every {@link #STEP} blocks.</li>
 * <li>Water: each vertex can ask for the bottom height ({@link Seabed}, in the game the terrain noise) to know whether
 * it falls in water; a short water stretch is a bridge, a shallow one a walkway and a long, deep one is cut.
 * It is only asked where the chunk sees real water, and it is memoized in the route.</li>
 * </ul>
 * Memos in {@link ConcurrentHashMap} (the generation threads query at once); the route's arrays are filled
 * with deterministic values, so two threads computing the same slot write the same thing.
 */
public final class RoadLayout {
	public static final long NONE = Long.MIN_VALUE;
	/** Spacing between the vertices of a route, in blocks. */
	public static final int STEP = 16;
	/** Every how many vertices there is a lamp post (about 48 blocks) and how far from each village its sign goes (outside the pieces of a large village, which reach 116 blocks from the plaza). */
	public static final int LAMP_EVERY = 3, SIGN_A = 160;
	/** Water: longest stretch crossed with a bridge and maximum depth of a walkway, in blocks. */
	public static final int MAX_BRIDGE = 64, WALKWAY_DEPTH = 2, MAX_WALKWAY = 320;
	static final int CACHE_MAX = 1 << 13;
	private static final org.slf4j.Logger LOGGER = org.slf4j.LoggerFactory.getLogger("heraldia");
	/** The first routes of each startup go to the log (the server test reads them). */
	private static final int LOG_MAX = 64;
	private static final java.util.concurrent.atomic.AtomicInteger LOGGED = new java.util.concurrent.atomic.AtomicInteger();

	/** Center of the village of cell (gx, gz) in blocks, packed with {@link #pack}, or {@link #NONE}. */
	@FunctionalInterface
	public interface Villages {
		long en(int gx, int gz);
	}

	/** Waypoint between two villages (next to a structure), packed, or {@link #NONE}. It receives the canonical order. */
	@FunctionalInterface
	public interface Milestones {
		long between(int ax, int az, int bx, int bz);

		Milestones NO_MILESTONES = (ax, az, bx, bz) -> NONE;
	}

	/** Bottom height (not counting water) in a column. */
	@FunctionalInterface
	public interface Seabed {
		int en(int x, int z);
	}

	/** What the route does in the water around a vertex. */
	public enum Water { LAND, BRIDGE, WALKWAY, CUT }

	private final long seed;
	private final int cell;          // size of the grid cell, in blocks
	private final int maxDist;
	private final long maxDistSq;
	private final int reach;         // cells around where a neighbor can be
	private final int pad;           // margin of a route's box (meander, width, posts)
	private final Villages villages;
	private final Milestones milestones;
	private final ConcurrentHashMap<Long, Long> villageMemo = new ConcurrentHashMap<>();
	private final ConcurrentHashMap<Long, long[]> neighborMemo = new ConcurrentHashMap<>();
	private final ConcurrentHashMap<Key, Route> routeMemo = new ConcurrentHashMap<>();

	/** cellBlocks: side of the villages' grid cell (blocks); maxDist: maximum distance between villages. */
	public RoadLayout(long seed, int cellBlocks, int maxDist, Villages villages, Milestones milestones) {
		this.seed = seed;
		this.cell = cellBlocks;
		this.maxDist = maxDist;
		this.maxDistSq = (long) maxDist * maxDist;
		this.reach = (maxDist + cellBlocks - 1) / cellBlocks + 1;
		this.pad = MAX_MEANDER + 16;
		this.villages = villages;
		this.milestones = milestones;
	}

	public static long pack(int x, int z) {
		return (long) x << 32 | (z & 0xFFFFFFFFL);
	}

	public static int px(long p) {
		return (int) (p >> 32);
	}

	public static int pz(long p) {
		return (int) p;
	}

	public int maxDist() {
		return maxDist;
	}

	/** Village of the cell, memoized. */
	long village(int gx, int gz) {
		long key = pack(gx, gz);
		Long v = villageMemo.get(key);
		if (v == null) {
			v = villages.en(gx, gz);
			if (villageMemo.size() > CACHE_MAX) {
				villageMemo.clear();
			}
			villageMemo.put(key, v);
		}
		return v;
	}

	private static long distSq(long a, long b) {
		long dx = (long) px(a) - px(b), dz = (long) pz(a) - pz(b);
		return dx * dx + dz * dz;
	}

	/**
	 * Villages joined with the one of cell (gx, gz): within the maximum distance and without a third one closer to both
	 * (relative neighborhood). Any third one that prevents it is within the maximum distance of both, so the
	 * answer is the same computed from either of them. Empty if the cell has no village.
	 */
	public long[] neighbors(int gx, int gz) {
		long key = pack(gx, gz);
		long[] v = neighborMemo.get(key);
		if (v != null) {
			return v;
		}
		long a = village(gx, gz);
		List<Long> near = new ArrayList<>();
		if (a != NONE) {
			for (int x = gx - reach; x <= gx + reach; x++) {
				for (int z = gz - reach; z <= gz + reach; z++) {
					long c = (x == gx && z == gz) ? NONE : village(x, z);
					if (c != NONE && distSq(a, c) <= maxDistSq) {
						near.add(c);
					}
				}
			}
		}
		List<Long> out = new ArrayList<>();
		for (long b : near) {
			long ab = distSq(a, b);
			boolean ok = true;
			for (long c : near) {
				if (c != b && Math.max(distSq(a, c), distSq(b, c)) < ab) {
					ok = false;
					break;
				}
			}
			if (ok) {
				out.add(b);
			}
		}
		v = out.stream().mapToLong(Long::longValue).toArray();
		if (neighborMemo.size() > CACHE_MAX) {
			neighborMemo.clear();
		}
		neighborMemo.put(key, v);
		return v;
	}

	/**
	 * Neighbors (like {@link #neighbors}) of the village with its plaza at (bx, bz) blocks (the center of its start chunk):
	 * it looks for its cell among the surrounding ones. Empty if no grid village spawns there. For the board's journey
	 * quests (T38); memoized, like the rest.
	 */
	public long[] neighborsOf(int bx, int bz) {
		long p = pack(bx, bz);
		int gx = cellOf(bx), gz = cellOf(bz);
		for (int x = gx - 2; x <= gx + 2; x++) {
			for (int z = gz - 2; z <= gz + 2; z++) {
				if (village(x, z) == p) {
					return neighbors(x, z);
				}
			}
		}
		return new long[0];
	}

	private int cellOf(int block) {
		return Math.floorDiv(block, cell);
	}

	/** Routes whose box (with a margin) touches the chunk. Cheap: arithmetic on the nearby cells, all memoized. */
	public List<Route> routes(int chunkX, int chunkZ) {
		int x0 = chunkX * 16, z0 = chunkZ * 16;
		return routesIn(x0, z0, x0 + 15, z0 + 15);
	}

	/**
	 * Routes that pass (with the width margin) through the block box [x0, x1] × [z0, z1]; the same as
	 * {@link #routes(int, int)} with an arbitrary box (the T39 caravans look for the road next to a player this way).
	 */
	public List<Route> routesIn(int x0, int z0, int x1, int z1) {
		int r = maxDist + pad;
		List<Route> out = null;
		// one extra cell on each side: the grid may have a shifted origin (villages do not)
		for (int gx = cellOf(x0 - r) - 1, gxMax = cellOf(x1 + r) + 1; gx <= gxMax; gx++) {
			for (int gz = cellOf(z0 - r) - 1, gzMax = cellOf(z1 + r) + 1; gz <= gzMax; gz++) {
				long a = village(gx, gz);
				if (a == NONE) {
					continue;
				}
				for (long b : neighbors(gx, gz)) {
					if (Long.compare(a, b) >= 0) {
						continue; // each route once: from its village with the lower key
					}
					// box of the straight line with a margin: discards almost everything without building the route
					int minX = Math.min(px(a), px(b)) - pad, maxX = Math.max(px(a), px(b)) + pad;
					int minZ = Math.min(pz(a), pz(b)) - pad, maxZ = Math.max(pz(a), pz(b)) + pad;
					if (maxX < x0 || minX > x1 || maxZ < z0 || minZ > z1) {
						continue;
					}
					Route route = route(a, b);
					if (route.touches(x0, z0, x1, z1)) {
						if (out == null) {
							out = new ArrayList<>(2);
						}
						out.add(route);
					}
				}
			}
		}
		return out == null ? List.of() : out;
	}

	private record Key(long a, long b) {
	}

	/**
	 * Midpoint (the central vertex) of the route nearest to (x, z) among those leaving the villages of the cells within
	 * {@code cells} of its own; {@link #NONE} if there is none. For /heraldia review: it only computes (the
	 * villages and routes, memoized), without touching the world.
	 */
	public long nearestSegment(int x, int z, int cells) {
		long origin = pack(x, z), best = NONE, bestD = Long.MAX_VALUE;
		int gx0 = cellOf(x), gz0 = cellOf(z);
		for (int gx = gx0 - cells; gx <= gx0 + cells; gx++) {
			for (int gz = gz0 - cells; gz <= gz0 + cells; gz++) {
				long a = village(gx, gz);
				if (a == NONE) {
					continue;
				}
				for (long b : neighbors(gx, gz)) {
					Route r = route(a, b);
					int m = r.vertices() / 2;
					long p = pack((int) Math.round(r.x(m)), (int) Math.round(r.z(m)));
					long d = distSq(p, origin);
					if (d < bestD || d == bestD && p < best) {
						best = p;
						bestD = d;
					}
				}
			}
		}
		return best;
	}

	/** Route between two villages (in any order: the same). */
	public Route route(long a, long b) {
		long lo = Math.min(a, b), hi = Math.max(a, b);
		Key k = new Key(lo, hi);
		Route r = routeMemo.get(k);
		if (r == null) {
			r = new Route(lo, hi, milestones.between(px(lo), pz(lo), px(hi), pz(hi)), seed);
			if (routeMemo.size() > CACHE_MAX) {
				routeMemo.clear();
			}
			Route prev = routeMemo.putIfAbsent(k, r);
			if (prev != null) {
				r = prev;
			} else if (LOGGED.getAndIncrement() < LOG_MAX) {
				LOGGER.info("Heraldia: camino entre las aldeas de {} {} y {} {}: {} bloques, {} vértices, {}", px(lo), pz(lo), px(hi), pz(hi),
						Math.round(r.length()), r.vertices(), r.lantern ? "faroles" : "antorchas");
			}
		}
		return r;
	}

	/** Margin around the axis a route can touch: maximum half width, the posts and rounding. */
	static final int MARGIN = 8;

	/** Maximum amplitude of the meander on each side of the straight line, in blocks. */
	static final int MAX_MEANDER = 40;

	static long mix(long z) {
		z = (z ^ (z >>> 30)) * 0xBF58476D1CE4E5B9L;
		z = (z ^ (z >>> 27)) * 0x94D049BB133111EBL;
		return z ^ (z >>> 31);
	}

	/** Number in [0, 1) that only depends on the seed and the arguments. */
	static double rng(long seed, long a, long b) {
		return (mix(seed ^ mix(a * 0x9E3779B97F4A7C15L ^ mix(b + 0x632BE59BD9B4E019L))) >>> 11) * 0x1.0p-53;
	}

	/** Road between two villages: vertices every {@link #STEP} blocks, cumulative length and water memo. */
	public static final class Route {
		public final long from, until;
		final double[] xs, zs, s;
		final int minX, minZ, maxX, maxZ;
		/** Style of this route's lamp posts: lantern on a post or torch. */
		public final boolean lantern;
		private final int[] depth;     // bottom height per vertex (Integer.MIN_VALUE = not computed)
		private final byte[] water;     // Water.ordinal() + 1 per vertex (0 = not computed)

		Route(long from, long until, long milestone, long seed) {
			this(from, until, points(from, until, milestone, mix(seed ^ mix(from) ^ mix(until * 31))),
					(mix(seed ^ mix(from) ^ mix(until * 31)) & 1) == 0);
		}

		private static List<double[]> points(long from, long until, long milestone, long h) {
			List<double[]> pts = new ArrayList<>();
			if (milestone == NONE) {
				segment(pts, px(from), pz(from), px(until), pz(until), h, true);
			} else {
				segment(pts, px(from), pz(from), px(milestone), pz(milestone), h, true);
				segment(pts, px(milestone), pz(milestone), px(until), pz(until), mix(h + 1), false);
			}
			return pts;
		}

		/**
		 * A route through vertices already laid out (the Herald's House roads, {@link SpawnRoadLayout}): the same
		 * painting, water handling and box as a road between villages. {@code from} and {@code until}: its ends, packed.
		 */
		Route(long from, long until, List<double[]> pts, boolean lantern) {
			this.from = from;
			this.until = until;
			this.lantern = lantern;
			int n = pts.size();
			xs = new double[n];
			zs = new double[n];
			s = new double[n];
			double mnx = Double.MAX_VALUE, mnz = Double.MAX_VALUE, mxx = -Double.MAX_VALUE, mxz = -Double.MAX_VALUE;
			for (int i = 0; i < n; i++) {
				xs[i] = pts.get(i)[0];
				zs[i] = pts.get(i)[1];
				if (i > 0) {
					s[i] = s[i - 1] + Math.hypot(xs[i] - xs[i - 1], zs[i] - zs[i - 1]);
				}
				mnx = Math.min(mnx, xs[i]);
				mnz = Math.min(mnz, zs[i]);
				mxx = Math.max(mxx, xs[i]);
				mxz = Math.max(mxz, zs[i]);
			}
			int m = MARGIN;
			minX = (int) Math.floor(mnx) - m;
			minZ = (int) Math.floor(mnz) - m;
			maxX = (int) Math.ceil(mxx) + m;
			maxZ = (int) Math.ceil(mxz) + m;
			depth = new int[n];
			java.util.Arrays.fill(depth, Integer.MIN_VALUE);
			water = new byte[n];
		}

		/** Vertices of a straight segment with meander (two sines of random phase and frequency, zero at the ends). */
		private static void segment(List<double[]> pts, int ax, int az, int bx, int bz, long h, boolean first) {
			segment(pts, ax, az, bx, bz, h, first, Math.min(MAX_MEANDER, Math.hypot(bx - ax, bz - az) * 0.05));
		}

		/** The same with the meander's amplitude given (0: straight). */
		static void segment(List<double[]> pts, double ax, double az, double bx, double bz, long h, boolean first, double amp) {
			double dx = bx - ax, dz = bz - az, len = Math.hypot(dx, dz);
			int n = Math.max(1, (int) Math.round(len / STEP));
			double nx = len == 0 ? 0 : -dz / len, nz = len == 0 ? 0 : dx / len;
			double f1 = 1 + (h >>> 8 & 1), f2 = 3 + (h >>> 9 & 3);
			double p1 = ((h >>> 16) & 0xFFFF) / 65536.0 * 2 * Math.PI, p2 = ((h >>> 32) & 0xFFFF) / 65536.0 * 2 * Math.PI;
			for (int i = first ? 0 : 1; i <= n; i++) {
				double t = (double) i / n;
				double off = amp * Math.sin(Math.PI * t) * (0.7 * Math.sin(2 * Math.PI * f1 * t + p1) + 0.3 * Math.sin(2 * Math.PI * f2 * t + p2));
				pts.add(new double[]{ax + dx * t + nx * off, az + dz * t + nz * off});
			}
		}

		public int vertices() {
			return xs.length;
		}

		public double x(int i) {
			return xs[i];
		}

		public double z(int i) {
			return zs[i];
		}

		/** Cumulative length up to vertex i. */
		public double arc(int i) {
			return s[i];
		}

		public double length() {
			return s[s.length - 1];
		}

		/** Does some segment pass (with the width margin and the posts) through the box: first the whole box, then segment by segment. */
		boolean touches(int x0, int z0, int x1, int z1) {
			if (maxX < x0 || minX > x1 || maxZ < z0 || minZ > z1) {
				return false;
			}
			for (int i = 0; i + 1 < xs.length; i++) {
				if (Math.max(xs[i], xs[i + 1]) + MARGIN >= x0 && Math.min(xs[i], xs[i + 1]) - MARGIN <= x1
						&& Math.max(zs[i], zs[i + 1]) + MARGIN >= z0 && Math.min(zs[i], zs[i + 1]) - MARGIN <= z1) {
					return true;
				}
			}
			return false;
		}

		/** Unit normal (left of the from → until direction) at vertex i. */
		public double[] normal(int i) {
			int a = Math.max(0, i - 1), b = Math.min(xs.length - 1, i + 1);
			double dx = xs[b] - xs[a], dz = zs[b] - zs[a], len = Math.hypot(dx, dz);
			return len == 0 ? new double[]{0, 0} : new double[]{-dz / len, dx / len};
		}

		/** What the route does in the water next to vertex k (memoized). */
		public Water water(int k, Seabed f, int sea) {
			byte v = water[k];
			if (v != 0) {
				return Water.values()[v - 1];
			}
			Water a = classify(k, f, sea);
			water[k] = (byte) (a.ordinal() + 1);
			return a;
		}

		private int depth(int i, Seabed f) {
			int v = depth[i];
			if (v == Integer.MIN_VALUE) {
				v = f.en((int) Math.floor(xs[i]), (int) Math.floor(zs[i]));
				depth[i] = v;
			}
			return v;
		}

		/**
		 * Water at a vertex: bottom below sea level. The route is walked to both sides until land: if the
		 * water stretch is up to {@link #MAX_BRIDGE}, a bridge; if it is longer but never deeper than
		 * {@link #WALKWAY_DEPTH} (marshes, swamps), a walkway up to {@link #MAX_WALKWAY}; otherwise, it is cut.
		 * Only the vertices needed to decide are checked.
		 */
		Water classify(int k, Seabed f, int sea) {
			if (depth(k, f) >= sea) {
				return Water.LAND;
			}
			int lo = k, hi = k, deepest = sea - depth(k, f);
			double limit = MAX_WALKWAY;
			while (lo > 0 && depth(lo - 1, f) < sea && s[k] - s[lo - 1] <= limit) {
				lo--;
				deepest = Math.max(deepest, sea - depth(lo, f));
				if (deepest > WALKWAY_DEPTH) {
					limit = MAX_BRIDGE;
				}
			}
			while (hi < xs.length - 1 && depth(hi + 1, f) < sea && s[hi + 1] - s[k] <= limit) {
				hi++;
				deepest = Math.max(deepest, sea - depth(hi, f));
				if (deepest > WALKWAY_DEPTH) {
					limit = MAX_BRIDGE;
				}
			}
			// length of the water: between the land vertices on both sides (or the end of the route)
			boolean openLo = lo > 0 && depth(lo - 1, f) < sea, openHi = hi < xs.length - 1 && depth(hi + 1, f) < sea;
			double len = s[Math.min(hi + 1, xs.length - 1)] - s[Math.max(lo - 1, 0)];
			if (deepest <= WALKWAY_DEPTH) {
				return !openLo && !openHi && len <= MAX_WALKWAY ? Water.WALKWAY : Water.CUT;
			}
			return !openLo && !openHi && len <= MAX_BRIDGE + STEP ? Water.BRIDGE : Water.CUT;
		}
	}

	// --- painting a chunk ---

	/** Half width that is never jagged: just enough for the road to stay connected through the faces of its columns. */
	static final double CORE = 0.75;

	/** Road column: the nearest route, its nearest vertex, the length traveled and the distance to the axis. */
	public record Cell(Route route, int vertex, double arc, double dist) {
	}

	/**
	 * Columns of the chunk that are road, in order x * 16 + z (null = no). A column is one if its center is within
	 * half the width of the axis; at the edge (the last half block, outside the {@link #CORE}) only sometimes (random per
	 * column), so it does not look straight. It only depends on the column and the routes, not the chunk: neighbors match at the border.
	 */
	public Cell[] paint(List<Route> routes, int chunkX, int chunkZ, int width) {
		Cell[] out = new Cell[256];
		// with a half width of 0.71 or more (square root of 2 over 2) the road's columns stay connected through their faces in
		// any direction: one can walk without passing diagonally between two corners
		double half = Math.max(width / 2.0, CORE);
		int x0 = chunkX * 16, z0 = chunkZ * 16;
		for (Route r : routes) {
			for (int i = 0; i + 1 < r.xs.length; i++) {
				double ax = r.xs[i], az = r.zs[i], bx = r.xs[i + 1], bz = r.zs[i + 1];
				int sx0 = Math.max(x0, (int) Math.floor(Math.min(ax, bx) - half - 1)), sx1 = Math.min(x0 + 15, (int) Math.ceil(Math.max(ax, bx) + half + 1));
				int sz0 = Math.max(z0, (int) Math.floor(Math.min(az, bz) - half - 1)), sz1 = Math.min(z0 + 15, (int) Math.ceil(Math.max(az, bz) + half + 1));
				if (sx0 > sx1 || sz0 > sz1) {
					continue;
				}
				double dx = bx - ax, dz = bz - az, l2 = dx * dx + dz * dz;
				for (int x = sx0; x <= sx1; x++) {
					for (int z = sz0; z <= sz1; z++) {
						double cx = x + 0.5, cz = z + 0.5;
						double t = l2 == 0 ? 0 : Math.clamp(((cx - ax) * dx + (cz - az) * dz) / l2, 0, 1);
						double d = Math.hypot(cx - (ax + dx * t), cz - (az + dz * t));
						if (d > half) {
							continue;
						}
						int idx = (x - x0) * 16 + (z - z0);
						Cell prev = out[idx];
						if (prev == null || d < prev.dist) {
							out[idx] = new Cell(r, t < 0.5 ? i : i + 1, r.s[i] + t * Math.sqrt(l2), d);
						}
					}
				}
			}
		}
		for (int idx = 0; idx < 256; idx++) {
			Cell c = out[idx];
			if (c != null && c.dist > Math.max(half - 0.5, CORE) && rng(seed, pack(x0 + idx / 16, z0 + idx % 16), 7) < 0.35) {
				out[idx] = null; // jagged edge
			}
		}
		return out;
	}

	/** Lamp post or sign by the road. Sign: which village it points to, how far it is and the rotation (0-15) of the sign. */
	public record Mark(boolean signpost, int x, int z, Route route, int vertex, long destination, int distance, int rotation, boolean right) {
	}

	/**
	 * Lamp posts (every {@link #LAMP_EVERY} vertices, alternating sides, away from the villages) and the route's two signs
	 * (at {@link #SIGN_A} blocks from each village, on the side opposite to that vertex's lamp post), of the chunk's
	 * columns. The column comes from the route, not the chunk.
	 */
	public List<Mark> marks(List<Route> routes, int chunkX, int chunkZ, int width) {
		List<Mark> out = new ArrayList<>();
		int x0 = chunkX * 16, z0 = chunkZ * 16;
		double off = width / 2.0 + 1.0;
		for (Route r : routes) {
			int n = r.xs.length;
			int first = -1, last = -1;
			for (int i = 0; i < n; i++) {
				if (first < 0 && r.s[i] >= SIGN_A) {
					first = i;
				}
				if (r.s[i] <= r.length() - SIGN_A) {
					last = i;
				}
			}
			for (int i = 0; i < n; i++) {
				// outside the chunk: just arithmetic
				if (r.xs[i] < x0 - off - 2 || r.xs[i] > x0 + 16 + off + 2 || r.zs[i] < z0 - off - 2 || r.zs[i] > z0 + 16 + off + 2) {
					continue;
				}
				double[] nrm = r.normal(i);
				int side = (i / LAMP_EVERY) % 2 == 0 ? 1 : -1;
				boolean far = r.s[i] >= SIGN_A / 2.0 && r.s[i] <= r.length() - SIGN_A / 2.0;
				if (i % LAMP_EVERY == 0 && far) {
					add(out, false, r, i, nrm, side * off, x0, z0, NONE, 0, 0, false);
				}
				if ((i == first || i == last) && first >= 0 && first < last) {
					boolean towardsUntil = i == first; // the first one (near "from") points to "until"
					long destination = towardsUntil ? r.until : r.from;
					int dist = (int) Math.round(towardsUntil ? r.length() - r.s[i] : r.s[i]);
					double sideOff = -(i % LAMP_EVERY == 0 ? side : 1) * off;
					// the sign faces the road; the arrow says on which hand the destination lies for whoever reads it
					double fx = -Math.signum(sideOff) * nrm[0], fz = -Math.signum(sideOff) * nrm[1];
					int rot = Math.floorMod((int) Math.round(Math.toDegrees(Math.atan2(-fx, fz)) / 22.5), 16);
					double tx = towardsUntil ? r.xs[Math.min(n - 1, i + 1)] - r.xs[i] : r.xs[Math.max(0, i - 1)] - r.xs[i];
					double tz = towardsUntil ? r.zs[Math.min(n - 1, i + 1)] - r.zs[i] : r.zs[Math.max(0, i - 1)] - r.zs[i];
					// reader facing the sign (direction -f): their right is (f.z, -f.x)
					boolean right = tx * fz - tz * fx > 0;
					add(out, true, r, i, nrm, sideOff, x0, z0, destination, dist, rot, right);
				}
			}
		}
		return out;
	}

	private static void add(List<Mark> out, boolean signpost, Route r, int i, double[] nrm, double off, int x0, int z0, long destination,
							int dist, int rot, boolean right) {
		int x = (int) Math.floor(r.xs[i] + nrm[0] * off), z = (int) Math.floor(r.zs[i] + nrm[1] * off);
		if (x >= x0 && x < x0 + 16 && z >= z0 && z < z0 + 16) {
			out.add(new Mark(signpost, x, z, r, i, destination, dist, rot, right));
		}
	}
}
