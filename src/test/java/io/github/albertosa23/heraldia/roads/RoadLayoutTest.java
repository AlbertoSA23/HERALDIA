package io.github.albertosa23.heraldia.roads;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.Test;

/**
 * Trazado de los caminos (lógica pura, sin el juego): determinismo, simetría, distancia máxima, vecindad relativa,
 * fronteras de chunk sin huecos, agua (puente, pasarela, corte), farolas y carteles, puntos de paso y nombres.
 */
class RoadLayoutTest {
	/** Rejilla de las aldeas por defecto: 94 chunks (1.504 bloques), candidata en los primeros 32 chunks de la casilla. */
	static final int CELL = 94 * 16, WINDOW = (94 - 62) * 16;

	/** Aldeas de prueba: una por casilla en la ventana (como random_spread), y casillas vacías al azar. */
	static RoadLayout.Villages villages(long seed, double empties) {
		return (gx, gz) -> {
			if (RoadLayout.rng(seed, RoadLayout.pack(gx, gz), 1) < empties) {
				return RoadLayout.NONE;
			}
			int ox = (int) (RoadLayout.rng(seed, RoadLayout.pack(gx, gz), 2) * WINDOW), oz = (int) (RoadLayout.rng(seed, RoadLayout.pack(gx, gz), 3) * WINDOW);
			return RoadLayout.pack(gx * CELL + ox + 8, gz * CELL + oz + 8);
		};
	}

	static RoadLayout layout(long seed, int maxDist) {
		return new RoadLayout(seed, CELL, maxDist, villages(seed, 0.2), RoadLayout.Milestones.DRY);
	}

	static double dist(long a, long b) {
		return Math.hypot(RoadLayout.px(a) - RoadLayout.px(b), RoadLayout.pz(a) - RoadLayout.pz(b));
	}

	/** Todas las aldeas de las casillas [-n, n]². */
	static List<Long> all(RoadLayout t, int n) {
		List<Long> out = new ArrayList<>();
		for (int gx = -n; gx <= n; gx++) {
			for (int gz = -n; gz <= n; gz++) {
				long a = t.village(gx, gz);
				if (a != RoadLayout.NONE) {
					out.add(a);
				}
			}
		}
		return out;
	}

	static int cell(long a, boolean x) {
		return Math.floorDiv(x ? RoadLayout.px(a) : RoadLayout.pz(a), CELL);
	}

	@Test
	void neighborsSymmetricAndWithinDistance() {
		for (long seed = 1; seed <= 20; seed++) {
			RoadLayout t = layout(seed, 2000);
			int edges = 0;
			for (long a : all(t, 4)) {
				for (long b : t.neighbors(cell(a, true), cell(a, false))) {
					assertTrue(dist(a, b) <= 2000, "a más de la distancia máxima");
					long[] back = t.neighbors(cell(b, true), cell(b, false));
					assertTrue(java.util.Arrays.stream(back).anyMatch(v -> v == a), "A→B sin B→A (semilla " + seed + ")");
					edges++;
				}
			}
			assertTrue(edges > 0, "ningún camino con la rejilla por defecto y 2.000 bloques");
		}
	}

	@Test
	void relativeNeighborhoodWithoutCloserThirds() {
		RoadLayout t = layout(7, 2500);
		List<Long> all = all(t, 6);
		for (long a : all(t, 4)) {
			for (long b : t.neighbors(cell(a, true), cell(a, false))) {
				for (long c : all) {
					if (c != a && c != b) {
						assertFalse(Math.max(dist(a, c), dist(b, c)) < dist(a, b), "hay una tercera más cerca de las dos");
					}
				}
			}
		}
	}

	@Test
	void shortMaxDistance() {
		// con la rejilla mínima de las aldeas (63 chunks, separación 42) dos aldeas nunca están a menos de 672 bloques:
		// a 600 no hay ningún camino
		int cell = 63 * 16, win = (63 - 42) * 16;
		RoadLayout.Villages a = (gx, gz) -> RoadLayout.pack(gx * cell + (int) (RoadLayout.rng(3, RoadLayout.pack(gx, gz), 2) * win),
				gz * cell + (int) (RoadLayout.rng(3, RoadLayout.pack(gx, gz), 3) * win));
		RoadLayout t = new RoadLayout(3, cell, 600, a, RoadLayout.Milestones.DRY);
		for (int gx = -5; gx <= 5; gx++) {
			for (int gz = -5; gz <= 5; gz++) {
				assertEquals(0, t.neighbors(gx, gz).length);
			}
		}
		assertTrue(t.routes(0, 0).isEmpty());
	}

	@Test
	void noVillagesNoRoads() {
		RoadLayout t = new RoadLayout(1, CELL, 2000, (gx, gz) -> RoadLayout.NONE, RoadLayout.Milestones.DRY);
		for (int cx = -50; cx <= 50; cx += 7) {
			assertTrue(t.routes(cx, cx * 3).isEmpty());
		}
	}

	@Test
	void deterministic() {
		RoadLayout a = layout(42, 2000), b = layout(42, 2000), c = layout(43, 2000);
		boolean different = false;
		for (long v : all(a, 3)) {
			for (long w : a.neighbors(cell(v, true), cell(v, false))) {
				RoadLayout.Route r1 = a.route(v, w), r2 = b.route(w, v); // orden contrario y otra instancia: la misma ruta
				assertEquals(r1.vertices(), r2.vertices());
				for (int i = 0; i < r1.vertices(); i++) {
					assertEquals(r1.x(i), r2.x(i));
					assertEquals(r1.z(i), r2.z(i));
				}
				assertEquals(r1.lantern, r2.lantern);
				RoadLayout.Route r3 = new RoadLayout(43, CELL, 2000, villages(42, 0.2), RoadLayout.Milestones.DRY).route(v, w);
				different |= r3.x(r3.vertices() / 2) != r1.x(r1.vertices() / 2);
			}
		}
		assertTrue(different, "la semilla no cambia el serpenteo");
		assertNotEquals(all(a, 3), all(c, 3));
	}

	@Test
	void routeJoinsBothVillagesAndMeandersLittle() {
		RoadLayout t = layout(5, 2000);
		for (long v : all(t, 3)) {
			for (long w : t.neighbors(cell(v, true), cell(v, false))) {
				RoadLayout.Route r = t.route(v, w);
				assertSame(r, t.route(w, v), "A→B y B→A son la misma ruta en memoria");
				long lo = Math.min(v, w), hi = Math.max(v, w);
				assertEquals(RoadLayout.px(lo), r.x(0), 1e-9);
				assertEquals(RoadLayout.pz(lo), r.z(0), 1e-9);
				assertEquals(RoadLayout.px(hi), r.x(r.vertices() - 1), 1e-9);
				assertEquals(RoadLayout.pz(hi), r.z(r.vertices() - 1), 1e-9);
				double straight = dist(v, w);
				assertTrue(r.length() >= straight - 1e-6 && r.length() <= straight * 1.15, "longitud " + r.length() + " para " + straight);
				for (int i = 1; i < r.vertices(); i++) {
					double seg = Math.hypot(r.x(i) - r.x(i - 1), r.z(i) - r.z(i - 1));
					assertTrue(seg <= RoadLayout.STEP * 1.6, "tramo de " + seg + " bloques");
				}
			}
		}
	}

	/** Columnas de camino de una ruta pintando chunk a chunk (instancia nueva por chunk: sin memoria compartida). */
	static Set<Long> byChunks(long seed, int maxDist, RoadLayout.Route r, int width) {
		Set<Long> out = new HashSet<>();
		int cx0 = Math.floorDiv((int) Math.floor(Math.min(r.x(0), r.x(r.vertices() - 1))) - 64, 16);
		int cx1 = Math.floorDiv((int) Math.ceil(Math.max(r.x(0), r.x(r.vertices() - 1))) + 64, 16);
		int cz0 = Math.floorDiv((int) Math.floor(Math.min(r.z(0), r.z(r.vertices() - 1))) - 64, 16);
		int cz1 = Math.floorDiv((int) Math.ceil(Math.max(r.z(0), r.z(r.vertices() - 1))) + 64, 16);
		for (int cx = cx0; cx <= cx1; cx++) {
			for (int cz = cz0; cz <= cz1; cz++) {
				RoadLayout t = layout(seed, maxDist);
				List<RoadLayout.Route> routes = new ArrayList<>();
				for (RoadLayout.Route x : t.routes(cx, cz)) {
					if (x.from == r.from && x.until == r.until) {
						routes.add(x);
					}
				}
				RoadLayout.Cell[] c = t.paint(routes, cx, cz, width);
				for (int i = 0; i < 256; i++) {
					if (c[i] != null) {
						out.add(RoadLayout.pack(cx * 16 + i / 16, cz * 16 + i % 16));
					}
				}
			}
		}
		return out;
	}

	@Test
	void chunkBordersWithoutGaps() {
		long seed = 11;
		RoadLayout t = layout(seed, 2000);
		int tried = 0;
		for (long v : all(t, 1)) {
			for (long w : t.neighbors(cell(v, true), cell(v, false))) {
				if (v > w || tried >= 3) {
					continue;
				}
				tried++;
				RoadLayout.Route r = t.route(v, w);
				for (int width : new int[]{1, 3, 5}) {
					Set<Long> cols = byChunks(seed, 2000, r, width);
					// el eje de la ruta, muestreado cada cuarto de bloque, cae siempre en una columna pintada: sin huecos
					for (int i = 0; i + 1 < r.vertices(); i++) {
						for (double f = 0; f < 1; f += 0.25) {
							double x = r.x(i) + (r.x(i + 1) - r.x(i)) * f, z = r.z(i) + (r.z(i + 1) - r.z(i)) * f;
							assertTrue(cols.contains(RoadLayout.pack((int) Math.floor(x), (int) Math.floor(z))),
									"hueco en " + x + ", " + z + " (ancho " + width + ")");
						}
					}
					// 4-conexo: se puede andar de una aldea a otra sin saltar en diagonal
					assertTrue(connected(cols, r), "camino partido (ancho " + width + ")");
				}
			}
		}
		assertTrue(tried > 0);
	}

	private static boolean connected(Set<Long> cols, RoadLayout.Route r) {
		long start = RoadLayout.pack((int) Math.floor(r.x(0)), (int) Math.floor(r.z(0)));
		long end = RoadLayout.pack((int) Math.floor(r.x(r.vertices() - 1)), (int) Math.floor(r.z(r.vertices() - 1)));
		Set<Long> seen = new HashSet<>();
		List<Long> stack = new ArrayList<>(List.of(start));
		while (!stack.isEmpty()) {
			long p = stack.removeLast();
			if (!cols.contains(p) || !seen.add(p)) {
				continue;
			}
			int x = RoadLayout.px(p), z = RoadLayout.pz(p);
			stack.add(RoadLayout.pack(x + 1, z));
			stack.add(RoadLayout.pack(x - 1, z));
			stack.add(RoadLayout.pack(x, z + 1));
			stack.add(RoadLayout.pack(x, z - 1));
		}
		return seen.contains(end);
	}

	@Test
	void paintingDoesNotDependOnChunkOrOrder() {
		long seed = 21;
		RoadLayout t = layout(seed, 2000);
		// un chunk pintado solo y pintado después de sus vecinos (otra instancia, otro orden) da lo mismo
		for (long v : all(t, 1)) {
			for (long w : t.neighbors(cell(v, true), cell(v, false))) {
				RoadLayout.Route r = t.route(v, w);
				int i = r.vertices() / 3;
				int cx = Math.floorDiv((int) r.x(i), 16), cz = Math.floorDiv((int) r.z(i), 16);
				RoadLayout u = layout(seed, 2000);
				for (int dx = -2; dx <= 2; dx++) {
					for (int dz = -2; dz <= 2; dz++) {
						u.paint(u.routes(cx + dx, cz + dz), cx + dx, cz + dz, 3);
					}
				}
				RoadLayout.Cell[] a = t.paint(t.routes(cx, cz), cx, cz, 3), b = u.paint(u.routes(cx, cz), cx, cz, 3);
				for (int k = 0; k < 256; k++) {
					assertEquals(a[k] == null, b[k] == null);
				}
			}
		}
	}

	@Test
	void roadWidth() {
		long seed = 13;
		RoadLayout t = layout(seed, 2000);
		long v = all(t, 0).getFirst();
		long w = t.neighbors(cell(v, true), cell(v, false))[0];
		RoadLayout.Route r = t.route(v, w);
		int prev = 0;
		for (int width = 1; width <= 5; width++) {
			int n = byChunks(seed, 2000, r, width).size();
			double byBlock = n / r.length();
			// con ancho 1 el núcleo unido por caras pone 1,5 columnas por bloque en las diagonales
			assertTrue(byBlock > width * 0.7 && byBlock < Math.max(width * 1.3, 1.65), "ancho " + width + ": " + byBlock + " columnas por bloque");
			assertTrue(n > prev);
			prev = n;
		}
	}

	// --- agua ---

	/** Ruta recta de prueba de 0,0 a 960,0 (vértices cada 16 bloques) con el fondo dado. */
	static RoadLayout.Route straight() {
		RoadLayout t = new RoadLayout(1, 100_000, 2000, (gx, gz) -> RoadLayout.NONE, RoadLayout.Milestones.DRY);
		RoadLayout.Route r = t.route(RoadLayout.pack(0, 0), RoadLayout.pack(960, 0));
		assertTrue(r.vertices() > 50);
		return r;
	}

	/** Fondo de prueba: por la x del vértice, profundidad bajo el mar 63 (0 = tierra). */
	static RoadLayout.Seabed depth(Map<int[], Integer> segments) {
		return (x, z) -> {
			for (Map.Entry<int[], Integer> e : segments.entrySet()) {
				if (x >= e.getKey()[0] && x < e.getKey()[1]) {
					return 63 - e.getValue();
				}
			}
			return 70;
		};
	}

	@Test
	void waterBridgeWalkwayAndCut() {
		Map<int[], Integer> m = new HashMap<>();
		m.put(new int[]{100, 140}, 6);    // río de 40 bloques y 6 de hondo: puente
		m.put(new int[]{300, 500}, 2);    // marisma de 200 bloques y 2 de hondo: pasarela
		m.put(new int[]{700, 900}, 9);    // lago de 200 bloques y 9 de hondo: se corta
		RoadLayout.Seabed f = depth(m);
		RoadLayout.Route r = straight();
		for (int i = 0; i < r.vertices(); i++) {
			double x = r.x(i);
			RoadLayout.Water a = r.water(i, f, 63);
			RoadLayout.Water expected = x >= 100 && x < 140 ? RoadLayout.Water.BRIDGE : x >= 300 && x < 500 ? RoadLayout.Water.WALKWAY
					: x >= 700 && x < 900 ? RoadLayout.Water.CUT : RoadLayout.Water.LAND;
			assertEquals(expected, a, "vértice en x = " + x);
		}
	}

	@Test
	void neverCrossesLongDeepWater() {
		// un tramo de agua honda más largo que un puente nunca se cruza, empiece donde empiece y mida lo que mida
		for (int start = 50; start < 400; start += 37) {
			for (int len = RoadLayout.MAX_BRIDGE + 2 * RoadLayout.STEP + 1; len < 500; len += 53) {
				Map<int[], Integer> m = new HashMap<>();
				m.put(new int[]{start, start + len}, RoadLayout.WALKWAY_DEPTH + 1 + len % 7);
				RoadLayout.Seabed f = depth(m);
				RoadLayout.Route r = straight();
				for (int i = 0; i < r.vertices(); i++) {
					if (f.en((int) Math.floor(r.x(i)), 0) < 63) {
						assertEquals(RoadLayout.Water.CUT, r.water(i, f, 63), "cruza agua honda de " + len + " bloques en x = " + r.x(i));
					}
				}
			}
		}
	}

	@Test
	void waterSameDecisionWholeSegmentAndFewQueries() {
		Map<int[], Integer> m = new HashMap<>();
		m.put(new int[]{200, 250}, 5);
		AtomicInteger calls = new AtomicInteger();
		RoadLayout.Seabed base = depth(m);
		RoadLayout.Seabed f = (x, z) -> {
			calls.incrementAndGet();
			return base.en(x, z);
		};
		RoadLayout.Route r = straight();
		Set<RoadLayout.Water> seen = new HashSet<>();
		for (int i = 0; i < r.vertices(); i++) {
			if (r.x(i) >= 200 && r.x(i) < 250) {
				seen.add(r.water(i, f, 63));
			}
		}
		assertEquals(Set.of(RoadLayout.Water.BRIDGE), seen);
		int first = calls.get();
		assertTrue(first <= 8, first + " consultas del fondo para un río de 50 bloques");
		for (int i = 0; i < r.vertices(); i++) {
			if (r.x(i) >= 200 && r.x(i) < 250) {
				r.water(i, f, 63);
			}
		}
		assertEquals(first, calls.get(), "en memoria: no se vuelve a preguntar");
	}

	// --- farolas y carteles ---

	@Test
	void lampsAndSignsOnceAndInPlace() {
		long seed = 17;
		RoadLayout t = layout(seed, 2000);
		long v = all(t, 0).getFirst();
		long w = t.neighbors(cell(v, true), cell(v, false))[0];
		RoadLayout.Route r = t.route(v, w);
		List<RoadLayout.Mark> marks = new ArrayList<>();
		Set<Long> road = byChunks(seed, 2000, r, 3);
		for (int cx = -400; cx <= 400; cx++) {
			// solo los chunks cerca de la ruta (la caja), cada uno con su instancia
			int bx = cx * 16;
			if (bx < Math.min(r.x(0), r.x(r.vertices() - 1)) - 80 || bx > Math.max(r.x(0), r.x(r.vertices() - 1)) + 80) {
				continue;
			}
			for (int cz = -400; cz <= 400; cz++) {
				int bz = cz * 16;
				if (bz < Math.min(r.z(0), r.z(r.vertices() - 1)) - 80 || bz > Math.max(r.z(0), r.z(r.vertices() - 1)) + 80) {
					continue;
				}
				RoadLayout u = layout(seed, 2000);
				List<RoadLayout.Route> routes = u.routes(cx, cz).stream().filter(x -> x.from == r.from && x.until == r.until).toList();
				for (RoadLayout.Mark mk : u.marks(routes, cx, cz, 3)) {
					assertTrue(Math.floorDiv(mk.x(), 16) == cx && Math.floorDiv(mk.z(), 16) == cz, "marca fuera de su chunk");
					marks.add(mk);
				}
			}
		}
		List<RoadLayout.Mark> signs = marks.stream().filter(RoadLayout.Mark::signpost).toList();
		assertEquals(2, signs.size(), "un cartel cerca de cada aldea");
		Set<Long> destinations = new HashSet<>();
		for (RoadLayout.Mark c : signs) {
			destinations.add(c.destination());
			long origin = c.destination() == r.until ? r.from : r.until;
			double toOrigin = Math.hypot(c.x() - RoadLayout.px(origin), c.z() - RoadLayout.pz(origin));
			assertTrue(toOrigin > RoadLayout.SIGN_A - 30 && toOrigin < RoadLayout.SIGN_A + 40, "cartel a " + toOrigin + " de su aldea");
			double toDestination = Math.hypot(c.x() - RoadLayout.px(c.destination()), c.z() - RoadLayout.pz(c.destination()));
			assertTrue(Math.abs(c.distance() - toDestination) < toDestination * 0.15 + 20, "distancia " + c.distance() + " frente a " + toDestination);
			assertTrue(c.rotation() >= 0 && c.rotation() < 16);
			// el letrero mira hacia el camino: un paso en la dirección de su cara se acerca al eje
			double ang = Math.toRadians(c.rotation() * 22.5);
			double fx = -Math.sin(ang), fz = Math.cos(ang);
			assertTrue(nearRoad(road, c.x() + fx * 2.5, c.z() + fz * 2.5) || nearRoad(road, c.x() + fx * 3.5, c.z() + fz * 3.5),
					"el cartel no mira al camino");
		}
		assertEquals(Set.of(r.from, r.until), destinations, "cada cartel señala la otra aldea");
		List<RoadLayout.Mark> lamps = marks.stream().filter(x -> !x.signpost()).toList();
		double expected = (r.length() - RoadLayout.SIGN_A) / (RoadLayout.STEP * RoadLayout.LAMP_EVERY);
		assertTrue(lamps.size() >= expected * 0.8 && lamps.size() <= expected * 1.2 + 2, lamps.size() + " farolas, se esperaban " + expected);
		Set<Long> pos = new HashSet<>();
		for (RoadLayout.Mark mk : marks) {
			assertTrue(pos.add(RoadLayout.pack(mk.x(), mk.z())), "dos marcas en la misma columna");
			assertFalse(road.contains(RoadLayout.pack(mk.x(), mk.z())), "marca encima del camino");
		}
	}

	private static boolean nearRoad(Set<Long> road, double x, double z) {
		return road.contains(RoadLayout.pack((int) Math.floor(x), (int) Math.floor(z)));
	}

	@Test
	void signArrow() {
		// ruta de oeste a este por z = 0: el cartel cerca de la aldea del oeste señala la del este
		RoadLayout t = new RoadLayout(1, 100_000, 2000, (gx, gz) -> RoadLayout.NONE, RoadLayout.Milestones.DRY);
		RoadLayout.Route r = t.route(RoadLayout.pack(0, 0), RoadLayout.pack(1200, 0));
		List<RoadLayout.Mark> all = new ArrayList<>();
		for (int cx = -2; cx <= 80; cx++) {
			for (int cz = -6; cz <= 6; cz++) {
				all.addAll(t.marks(List.of(r), cx, cz, 3));
			}
		}
		for (RoadLayout.Mark c : all) {
			if (!c.signpost()) {
				continue;
			}
			double ang = Math.toRadians(c.rotation() * 22.5);
			double fx = -Math.sin(ang), fz = Math.cos(ang); // cara del letrero; el lector mira en -f
			double rightX = fz, rightZ = -fx;              // derecha del lector
			double tx = RoadLayout.px(c.destination()) - c.x(), tz = RoadLayout.pz(c.destination()) - c.z();
			assertEquals(tx * rightX + tz * rightZ > 0, c.right(), "la flecha no señala el destino");
		}
	}

	@Test
	void waypoint() {
		long milestone = RoadLayout.pack(600, 200);
		RoadLayout t = new RoadLayout(1, 100_000, 2000, (gx, gz) -> RoadLayout.NONE, (ax, az, bx, bz) -> milestone);
		RoadLayout.Route r = t.route(RoadLayout.pack(0, 0), RoadLayout.pack(1200, 0));
		boolean passes = false;
		for (int i = 0; i < r.vertices(); i++) {
			passes |= Math.hypot(r.x(i) - 600, r.z(i) - 200) < 1e-6;
		}
		assertTrue(passes, "la ruta no pasa por el punto de paso");
		assertTrue(r.length() > 1200 * 1.05);
	}

	@Test
	void waypointWithCanonicalOrder() {
		List<long[]> questions = new ArrayList<>();
		RoadLayout t = new RoadLayout(1, 100_000, 2000, (gx, gz) -> RoadLayout.NONE, (ax, az, bx, bz) -> {
			questions.add(new long[]{ax, az, bx, bz});
			return RoadLayout.NONE;
		});
		t.route(RoadLayout.pack(900, 50), RoadLayout.pack(0, 0));
		new RoadLayout(1, 100_000, 2000, (gx, gz) -> RoadLayout.NONE, (ax, az, bx, bz) -> {
			questions.add(new long[]{ax, az, bx, bz});
			return RoadLayout.NONE;
		}).route(RoadLayout.pack(0, 0), RoadLayout.pack(900, 50));
		assertArrayEquals(questions.get(0), questions.get(1), "el punto de paso se pregunta igual en los dos sentidos");
	}

	// --- nombres ---

	@Test
	void deterministicNamesThatFit() {
		Set<String> seen = new HashSet<>();
		for (int i = 0; i < 400; i++) {
			String[] a = Names.of(99, i * 1504, i * 777), b = Names.of(99, i * 1504, i * 777);
			assertArrayEquals(a, b);
			assertEquals(2, a.length);
			for (String s : a) {
				assertNotNull(s);
				assertTrue(s.length() <= 13, "no cabe en una línea de cartel: " + s);
			}
			seen.add(a[0] + " " + a[1]);
		}
		assertTrue(seen.size() > 150, "pocos nombres distintos: " + seen.size());
		assertNotEquals(String.join(" ", Names.of(1, 0, 0)) + String.join(" ", Names.of(1, 1504, 0)) + String.join(" ", Names.of(1, 0, 1504)),
				String.join(" ", Names.of(2, 0, 0)) + String.join(" ", Names.of(2, 1504, 0)) + String.join(" ", Names.of(2, 0, 1504)));
	}

	@Test
	void routeOnlyInChunksNearItsAxis() {
		long seed = 31;
		RoadLayout t = layout(seed, 2000);
		long v = all(t, 0).getFirst();
		long w = t.neighbors(cell(v, true), cell(v, false))[0];
		RoadLayout.Route r = t.route(v, w);
		Set<Long> cols = byChunks(seed, 2000, r, 5);
		int far = 0, near = 0;
		for (int cx = Math.floorDiv((int) Math.min(r.x(0), r.x(r.vertices() - 1)) - 200, 16); cx <= Math.floorDiv((int) Math.max(r.x(0), r.x(r.vertices() - 1)) + 200, 16); cx++) {
			for (int cz = Math.floorDiv((int) Math.min(r.z(0), r.z(r.vertices() - 1)) - 200, 16); cz <= Math.floorDiv((int) Math.max(r.z(0), r.z(r.vertices() - 1)) + 200, 16); cz++) {
				final int fx = cx, fz = cz;
				boolean listed = t.routes(cx, cz).stream().anyMatch(x -> x == r);
				boolean painted = cols.stream().anyMatch(p -> Math.floorDiv(RoadLayout.px(p), 16) == fx && Math.floorDiv(RoadLayout.pz(p), 16) == fz);
				if (painted) {
					assertTrue(listed, "chunk con camino sin su ruta");
				}
				if (listed) {
					near++;
				} else {
					far++;
				}
			}
		}
		// la caja de una ruta en diagonal es mucho mayor que la franja de su eje: casi ningún chunk de la caja la recibe
		assertTrue(near < (r.length() / 16 + 2) * 4, near + " chunks reciben la ruta");
		assertTrue(far > near);
	}

	@Test
	void cheapChunkRoutes() {
		// la consulta de un chunk sin camino cerca, con las memorias llenas, es de microsegundos
		RoadLayout t = layout(5, 2000);
		for (int cx = -100; cx <= 100; cx++) {
			t.routes(cx, 7);
		}
		long t0 = System.nanoTime();
		int n = 0;
		for (int k = 0; k < 20; k++) {
			for (int cx = -100; cx <= 100; cx++) {
				n += t.routes(cx, 7).size();
			}
		}
		double us = (System.nanoTime() - t0) / 1000.0 / (20 * 201);
		assertTrue(us < 200, us + " µs por chunk");
		assertTrue(n >= 0);
	}

	@Test
	void nearbySegmentForReview() {
		RoadLayout t = layout(7, 2000);
		long p = t.nearestSegment(0, 0, 4);
		assertTrue(p != RoadLayout.NONE, "con aldeas cada 1.500 bloques hay alguna ruta cerca");
		// es el vértice central de una ruta entre dos aldeas vecinas, y la más cercana de las que se miran
		boolean ofARoute = false;
		double best = Double.MAX_VALUE;
		for (long a : all(t, 5)) {
			int gx = Math.floorDiv(RoadLayout.px(a), CELL), gz = Math.floorDiv(RoadLayout.pz(a), CELL);
			if (Math.abs(gx) > 4 || Math.abs(gz) > 4) {
				continue;
			}
			for (long b : t.neighbors(gx, gz)) {
				RoadLayout.Route r = t.route(a, b);
				int m = r.vertices() / 2;
				long q = RoadLayout.pack((int) Math.round(r.x(m)), (int) Math.round(r.z(m)));
				ofARoute |= q == p;
				best = Math.min(best, Math.hypot(RoadLayout.px(q), RoadLayout.pz(q)));
			}
		}
		assertTrue(ofARoute);
		assertEquals(best, Math.hypot(RoadLayout.px(p), RoadLayout.pz(p)), 1e-9);
		assertEquals(p, layout(7, 2000).nearestSegment(0, 0, 4), "determinista");
		// sin aldeas, nada
		RoadLayout empty = new RoadLayout(7, CELL, 2000, (gx, gz) -> RoadLayout.NONE, RoadLayout.Milestones.DRY);
		assertEquals(RoadLayout.NONE, empty.nearestSegment(0, 0, 4));
	}
}
