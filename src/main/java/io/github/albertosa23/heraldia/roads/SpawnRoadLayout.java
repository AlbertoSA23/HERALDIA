package io.github.albertosa23.heraldia.roads;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import org.jspecify.annotations.Nullable;

/**
 * Layout of the roads out of the Herald's House (pure logic, no game classes: the unit tests check it, and
 * tools/gen/spawn_roads.py is the same arithmetic, where its invariants are checked as properties). Everything comes
 * from the seed, the gates and, for the arena road, the arena's box; the vertices then become a {@link RoadLayout.Route},
 * so these roads are painted, paved and bridged exactly like the roads between villages.
 * <ul>
 * <li>A gate's road ({@link #normal}): straight for {@link Params#straight} blocks out of the gate cell (the huts stand
 * along it), then a gentle bend to its end, {@link Params#length} out and up to {@link Params#lateral} to one side.</li>
 * <li>The arena road ({@link #arenaPlan}): from the gate whose road points closest to the arena, that road continued
 * from its end (or from the end of its straight stretch, if its bend comes too close to the arena) to the arena's
 * entrance, on the south side of its box: the shortest of a few detours that keeps out of the arena's box and the
 * town and, if one exists, out of every chunk with a surface structure.</li>
 * <li>Lamp posts ({@link #lamps}) every {@link Params#lampEvery} blocks of road, alternating sides.</li>
 * </ul>
 */
public final class SpawnRoadLayout {
	/** The order the roads are built and the huts filled. */
	public static final List<String> SIDES = List.of("north", "east", "south", "west");

	private SpawnRoadLayout() {
	}

	/** The layout's numbers (heraldia/caminos_casa.json, written by tools/gen/spawn_roads.py). */
	public record Params(int straight, int length, int lateral, int minimum, int width, double meander, double maxMeander,
			int lampEvery, int lampFirst, double lampOffset, double sharp, int approach, int arenaMargin, int townMargin, int maxArena,
			int reach, int[] detours, int corner) {
		public static Params read(JsonObject o) {
			JsonObject l = o.getAsJsonObject("farolas"), a = o.getAsJsonObject("arena");
			JsonArray d = a.getAsJsonArray("desvios");
			int[] detours = new int[d.size()];
			for (int i = 0; i < detours.length; i++) {
				detours[i] = d.get(i).getAsInt();
			}
			return new Params(o.get("recto").getAsInt(), o.get("largo").getAsInt(), o.get("lateral").getAsInt(),
					o.get("minimo").getAsInt(), o.get("ancho").getAsInt(), o.get("meandro").getAsDouble(),
					o.get("meandro_max").getAsDouble(), l.get("cada").getAsInt(), l.get("primera").getAsInt(),
					l.get("separacion").getAsDouble(), l.get("curva").getAsDouble(), a.get("acercamiento").getAsInt(), a.get("margen").getAsInt(),
					a.get("pueblo").getAsInt(), a.get("maximo").getAsInt(), a.get("lados").getAsInt(), detours,
					a.get("esquina").getAsInt());
		}
	}

	/** Is there a surface structure in that chunk? */
	@FunctionalInterface
	public interface Structures {
		boolean at(int chunkX, int chunkZ);

		Structures NONE = (x, z) -> false;
	}

	/** A box of columns, inclusive. */
	public record Box(int x0, int z0, int x1, int z1) {
		public boolean in(int x, int z, int m) {
			return x >= x0 - m && x <= x1 + m && z >= z0 - m && z <= z1 + m;
		}
	}

	public static int[] outward(String side) {
		return switch (side) {
			case "north" -> new int[] {0, -1};
			case "south" -> new int[] {0, 1};
			case "west" -> new int[] {-1, 0};
			case "east" -> new int[] {1, 0};
			default -> throw new IllegalArgumentException(side);
		};
	}

	/** Right of the outward direction. */
	public static int[] right(String side) {
		int[] d = outward(side);
		return new int[] {-d[1], d[0]};
	}

	/** The point u blocks out of the gate cell along its road and v to its right (block centres at .5). */
	public static double[] axis(int[] gate, String side, double u, double v) {
		int[] d = outward(side), r = right(side);
		return new double[] {gate[0] + 0.5 + d[0] * u + r[0] * v, gate[1] + 0.5 + d[1] * u + r[1] * v};
	}

	/** How far to the right (negative: left) a road's end lies. */
	public static int lateral(long seed, int[] gate, Params p) {
		return (int) Math.round((RoadLayout.rng(seed, RoadLayout.pack(gate[0], gate[1]), 41) * 2 - 1) * p.lateral());
	}

	/** Vertices through the knots, each knot-to-knot stretch with its own meander (none on the first or the last if asked). */
	public static List<double[]> route(List<double[]> knots, long seed, boolean straightFirst, boolean straightLast, Params p) {
		List<double[]> pts = new ArrayList<>();
		for (int i = 0; i + 1 < knots.size(); i++) {
			double[] a = knots.get(i), b = knots.get(i + 1);
			long h = RoadLayout.mix(seed ^ RoadLayout.mix(RoadLayout.pack((int) Math.floor(a[0]), (int) Math.floor(a[1])))
					^ RoadLayout.mix(RoadLayout.pack((int) Math.floor(b[0]), (int) Math.floor(b[1])) * 31));
			boolean straight = straightFirst && i == 0 || straightLast && i == knots.size() - 2;
			double amp = straight ? 0 : Math.min(p.maxMeander(), Math.hypot(b[0] - a[0], b[1] - a[1]) * p.meander());
			RoadLayout.Route.segment(pts, a[0], a[1], b[0], b[1], h, i == 0, amp);
		}
		return pts;
	}

	/** A gate's road: straight for {@link Params#straight} blocks, then a bend to its end. */
	public static List<double[]> normal(int[] gate, String side, long seed, Params p) {
		return route(List.of(axis(gate, side, 1, 0), axis(gate, side, p.straight(), 0),
				axis(gate, side, p.length(), lateral(seed, gate, p))), seed, true, false, p);
	}

	/** The vertex before the arena road's first: on the gate's road it continues. */
	public static double[] joined(List<double[]> normal, boolean fromHead, Params p) {
		List<double[]> pts = fromHead ? head(normal, p) : normal;
		return pts.get(pts.size() - 2);
	}

	/** The vertices of a gate's road up to the end of its straight stretch. */
	public static List<double[]> head(List<double[]> normal, Params p) {
		int n = Math.max(1, (int) Math.round((p.straight() - 1) / (double) RoadLayout.STEP));
		return List.copyOf(normal.subList(0, Math.min(normal.size(), n + 1)));
	}

	/** The arena's entrance (just outside the south side of its box, on its centre column) and the approach point out of it. */
	public static double[][] arenaPoints(Box arena, Params p) {
		double cx = Math.floorDiv(arena.x0() + arena.x1(), 2) + 0.5;
		return new double[][] {{cx, arena.z1() + 1.5}, {cx, arena.z1() + 1.5 + p.approach()}};
	}

	/** The knot lists tried for the arena road, in order: straight, side detours at the middle, round the corners. */
	static List<List<double[]>> candidates(double[] start, Box arena, Params p) {
		double[][] ap = arenaPoints(arena, p);
		double[] entrance = ap[0], approach = ap[1];
		double mx = (start[0] + approach[0]) / 2, mz = (start[1] + approach[1]) / 2;
		double ln = Math.hypot(approach[0] - start[0], approach[1] - start[1]);
		if (ln == 0) {
			ln = 1;
		}
		double px = -(approach[1] - start[1]) / ln, pz = (approach[0] - start[0]) / ln;
		int c = p.corner();
		double[] sw = {arena.x0() - c + 0.5, arena.z1() + c + 0.5}, se = {arena.x1() + c + 0.5, arena.z1() + c + 0.5};
		double[] nw = {arena.x0() - c + 0.5, arena.z0() - c + 0.5}, ne = {arena.x1() + c + 0.5, arena.z0() - c + 0.5};
		List<List<double[]>> ways = new ArrayList<>();
		ways.add(List.of());
		for (int k : p.detours()) {
			ways.add(List.of(new double[] {mx + px * k, mz + pz * k}));
		}
		ways.add(List.of(sw));
		ways.add(List.of(se));
		ways.add(List.of(nw, sw));
		ways.add(List.of(ne, se));
		List<List<double[]>> out = new ArrayList<>();
		for (List<double[]> w : ways) {
			List<double[]> k = new ArrayList<>();
			k.add(start);
			k.addAll(w);
			k.add(approach);
			k.add(entrance);
			out.add(k);
		}
		return out;
	}

	public static double length(List<double[]> pts) {
		double s = 0;
		for (int i = 0; i + 1 < pts.size(); i++) {
			s += Math.hypot(pts.get(i + 1)[0] - pts.get(i)[0], pts.get(i + 1)[1] - pts.get(i)[1]);
		}
		return s;
	}

	/** Points every 2 blocks along the polyline: {x, z, normal x, normal z, distance left to its end}. */
	static List<double[]> samples(List<double[]> pts) {
		List<double[]> out = new ArrayList<>();
		double total = length(pts), done = 0, every = 2.0;
		for (int i = 0; i + 1 < pts.size(); i++) {
			double ax = pts.get(i)[0], az = pts.get(i)[1], bx = pts.get(i + 1)[0], bz = pts.get(i + 1)[1];
			double ln = Math.hypot(bx - ax, bz - az);
			if (ln == 0) {
				continue;
			}
			double nx = -(bz - az) / ln, nz = (bx - ax) / ln;
			for (int k = 0; k * every <= ln; k++) {
				double t = k * every / ln;
				out.add(new double[] {ax + (bx - ax) * t, az + (bz - az) * t, nx, nz, total - done - k * every});
			}
			done += ln;
		}
		return out;
	}

	/** {no arena or town in the way, no structure in the way} for a road through these vertices. */
	static boolean[] clear(List<double[]> pts, Box arena, Box town, Structures s, Params p) {
		boolean boxes = true, structures = true;
		double edge = p.width() / 2.0, reach = p.width() / 2.0 + p.reach();
		for (double[] q : samples(pts)) {
			for (double w : new double[] {-edge, 0, edge}) {
				int cx = (int) Math.floor(q[0] + q[2] * w), cz = (int) Math.floor(q[1] + q[3] * w);
				if (q[4] > p.approach() + 1 && arena.in(cx, cz, p.arenaMargin()) || town.in(cx, cz, p.townMargin())) {
					boxes = false;
				}
			}
			if (!boxes) {
				break;
			}
			for (double w : new double[] {-reach, 0, reach}) {
				if (structures && s.at((int) Math.floor(q[0] + q[2] * w) >> 4, (int) Math.floor(q[1] + q[3] * w) >> 4)) {
					structures = false;
				}
			}
		}
		return new boolean[] {boxes, structures};
	}

	/** Does the road through these vertices come close to the arena's box (its margin and 4 more)? */
	public static boolean hitsArena(List<double[]> pts, Box arena, Params p) {
		double r = p.width() / 2.0;
		for (double[] q : samples(pts)) {
			for (double w : new double[] {-r, 0, r}) {
				if (arena.in((int) Math.floor(q[0] + q[2] * w), (int) Math.floor(q[1] + q[3] * w), p.arenaMargin() + 4)) {
					return true;
				}
			}
		}
		return false;
	}

	/** The arena road from {@code start}: its vertices and knots, and whether it keeps out of every structure. */
	public record Result(List<double[]> pts, List<double[]> knots, boolean clear) {
	}

	/** The arena road from {@code start}, or null if the arena is too far or no detour keeps out of its box and the town. */
	public static Result arena(double[] start, Box arena, Box town, long seed, Structures s, Params p) {
		double[] entrance = arenaPoints(arena, p)[0];
		if (Math.hypot(entrance[0] - start[0], entrance[1] - start[1]) > p.maxArena()) {
			return null;
		}
		Result best = null, fallback = null;
		double bestLen = 0, fallbackLen = 0;
		for (List<double[]> knots : candidates(start, arena, p)) {
			List<double[]> pts = route(knots, seed, false, true, p);
			boolean[] c = clear(pts, arena, town, s, p);
			if (!c[0]) {
				continue;
			}
			double ln = length(knots);
			if (c[1] && (best == null || ln < bestLen)) {
				best = new Result(pts, knots, true);
				bestLen = ln;
			}
			if (fallback == null || ln < fallbackLen) {
				fallback = new Result(pts, knots, false);
				fallbackLen = ln;
			}
		}
		return best != null ? best : fallback;
	}

	/** The gate whose road points closest to the arena (largest cosine; ties in {@link #SIDES} order). */
	public static String arenaGate(Map<String, int[]> gates, double[] arenaCenter) {
		String best = null;
		double bestScore = 0;
		for (String side : SIDES) {
			int[] g = gates.get(side), d = outward(side);
			double vx = arenaCenter[0] - g[0], vz = arenaCenter[1] - g[1], ln = Math.hypot(vx, vz);
			double score = (d[0] * vx + d[1] * vz) / (ln == 0 ? 1 : ln);
			if (best == null || score > bestScore) {
				best = side;
				bestScore = score;
			}
		}
		return best;
	}

	/**
	 * The arena road: the gate, that gate's road, where the arena road starts (the end of that road, or of its straight
	 * stretch) and the arena road (null if none).
	 */
	public record Plan(String side, List<double[]> normal, double[] start, boolean fromHead, Result arena) {
	}

	public static Plan arenaPlan(Map<String, int[]> gates, Box arena, long seed, Structures s, Box town, Params p) {
		String side = arenaGate(gates, new double[] {(arena.x0() + arena.x1()) / 2.0, (arena.z0() + arena.z1()) / 2.0});
		List<double[]> nr = normal(gates.get(side), side, seed, p);
		boolean fromHead = hitsArena(nr, arena, p);
		double[] start = fromHead ? axis(gates.get(side), side, p.straight(), 0) : nr.get(nr.size() - 1);
		return new Plan(side, nr, start, fromHead, arena(start, arena, town, seed, s, p));
	}

	/**
	 * Lamp posts along the road: one every {@link Params#lampEvery} blocks, alternating sides, and one more by its end if
	 * the last one is more than half a spacing back: {x, z} columns.
	 */
	public static List<int[]> lamps(List<double[]> pts, Params p) {
		return lamps(pts, null, p);
	}

	/** The same for a road that continues another one: {@code before} is the vertex before its first (its first bend). */
	public static List<int[]> lamps(List<double[]> pts, double @Nullable [] before, Params p) {
		List<int[]> out = new ArrayList<>();
		double arc = 0, target = p.lampFirst();
		int k = 0;
		double[] last = null;
		for (int i = 0; i + 1 < pts.size(); i++) {
			double ax = pts.get(i)[0], az = pts.get(i)[1], bx = pts.get(i + 1)[0], bz = pts.get(i + 1)[1];
			double ln = Math.hypot(bx - ax, bz - az);
			if (ln == 0) {
				continue;
			}
			last = new double[] {ax, az, bx, bz, ln};
			while (target <= arc + ln) {
				out.add(lamp(ax, az, bx, bz, (target - arc) / ln, ln, k, p));
				k++;
				target += p.lampEvery();
			}
			arc += ln;
		}
		if (last != null && arc - (target - p.lampEvery()) > p.lampEvery() / 2.0) {
			out.add(lamp(last[0], last[1], last[2], last[3], Math.max(0.0, (last[4] - 1) / last[4]), last[4], k, p));
		}
		// and one outside each sharp bend (a detour round the arena's corner): its outer edge is the farthest from the others
		List<double[]> full = new ArrayList<>();
		if (before != null) {
			full.add(before);
		}
		full.addAll(pts);
		for (int i = 0; i + 2 < full.size(); i++) {
			double ax = full.get(i)[0], az = full.get(i)[1], bx = full.get(i + 1)[0], bz = full.get(i + 1)[1];
			double cx = full.get(i + 2)[0], cz = full.get(i + 2)[1];
			double l1 = Math.hypot(bx - ax, bz - az), l2 = Math.hypot(cx - bx, cz - bz);
			if (l1 == 0 || l2 == 0) {
				continue;
			}
			double d1x = (bx - ax) / l1, d1z = (bz - az) / l1, d2x = (cx - bx) / l2, d2z = (cz - bz) / l2;
			if (d1x * d2x + d1z * d2z < p.sharp()) {
				double ox = d1x - d2x, oz = d1z - d2z, lo = Math.hypot(ox, oz);
				out.add(new int[] {(int) Math.floor(bx + ox / lo * p.lampOffset()), (int) Math.floor(bz + oz / lo * p.lampOffset())});
			}
		}
		return out;
	}

	private static int[] lamp(double ax, double az, double bx, double bz, double t, double ln, int k, Params p) {
		double nx = -(bz - az) / ln, nz = (bx - ax) / ln;
		int side = k % 2 == 0 ? 1 : -1;
		return new int[] {(int) Math.floor(ax + (bx - ax) * t + nx * p.lampOffset() * side),
				(int) Math.floor(az + (bz - az) * t + nz * p.lampOffset() * side)};
	}

	/** The share of the road's segments along which the distance to (cx, cz) grows. */
	public static double awayShare(List<double[]> pts, double cx, double cz) {
		int up = 0, n = 0;
		for (int i = 0; i + 1 < pts.size(); i++) {
			n++;
			if (Math.hypot(pts.get(i + 1)[0] - cx, pts.get(i + 1)[1] - cz) > Math.hypot(pts.get(i)[0] - cx, pts.get(i)[1] - cz)) {
				up++;
			}
		}
		return n == 0 ? 0 : (double) up / n;
	}

	/** The vertices as a {@link RoadLayout.Route}: painted, paved and bridged like a road between villages. */
	public static RoadLayout.Route toRoute(List<double[]> pts) {
		double[] a = pts.get(0), b = pts.get(pts.size() - 1);
		return new RoadLayout.Route(RoadLayout.pack((int) Math.floor(a[0]), (int) Math.floor(a[1])),
				RoadLayout.pack((int) Math.floor(b[0]), (int) Math.floor(b[1])), pts, true);
	}

	// --- the huts ---

	/**
	 * Where a hut stands: {rotation (0 none, 1 clockwise 90, 2 180, 3 counterclockwise 90), x, z of its local origin}.
	 * The local x runs along the road (outwards on the right side, towards the town on the left) and the local z away from
	 * it; the template's first row (its porch) is {@code edge} blocks off the axis.
	 */
	public static int[] hutFrame(int[] gate, String side, int slotSide, int along, int sizeX, int edge) {
		int[] o = hutCell(gate, side, slotSide, along, sizeX, edge, 0, 0), a = hutCell(gate, side, slotSide, along, sizeX, edge, 1, 0);
		int dx = a[0] - o[0], dz = a[1] - o[1];
		int rot = dx == 1 ? 0 : dz == 1 ? 1 : dx == -1 ? 2 : 3;
		return new int[] {rot, o[0], o[1]};
	}

	/** The world column of the hut's local (x, z). */
	public static int[] hutCell(int[] gate, String side, int slotSide, int along, int sizeX, int edge, int lx, int lz) {
		int[] d = outward(side), r = right(side);
		int u = slotSide > 0 ? along + lx : along + sizeX - 1 - lx;
		int v = slotSide * (edge + lz);
		return new int[] {gate[0] + d[0] * u + r[0] * v, gate[1] + d[1] * u + r[1] * v};
	}
}
