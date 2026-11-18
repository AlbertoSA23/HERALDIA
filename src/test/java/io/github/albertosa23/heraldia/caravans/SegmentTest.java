package io.github.albertosa23.heraldia.caravans;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import io.github.albertosa23.heraldia.roads.RoadLayout;
import java.util.List;
import org.junit.jupiter.api.Test;

/** Elección del tramo y la ruta sobre el camino (lógica pura, con un trazado de prueba de dos aldeas vecinas). */
class SegmentTest {
	static final int CELL = 94 * 16;
	/** Dos aldeas a 1.200 bloques en el eje x: la de la casilla (0, 0) en 8, 8 y la de la (1, 0) en 1208, 8. */
	static final long A = RoadLayout.pack(8, 8), B = RoadLayout.pack(1208, 8);

	static RoadLayout layout() {
		return new RoadLayout(42, CELL, 2000, (gx, gz) -> gx == 0 && gz == 0 ? A : gx == 1 && gz == 0 ? B : RoadLayout.NONE,
				RoadLayout.Milestones.NO_MILESTONES);
	}

	static RoadLayout.Route route() {
		return layout().route(A, B);
	}

	/** Un punto a {@code side} bloques del vértice i de la ruta, por su normal. */
	static int[] beside(RoadLayout.Route r, int i, double side) {
		double[] n = r.normal(i);
		return new int[]{(int) Math.round(r.x(i) + n[0] * side), (int) Math.round(r.z(i) + n[1] * side)};
	}

	@Test
	void routeOfABoxIsCanonical() {
		RoadLayout t = layout();
		RoadLayout.Route r = t.route(A, B);
		int m = r.vertices() / 2;
		int x = (int) r.x(m), z = (int) r.z(m);
		List<RoadLayout.Route> routes = t.routesIn(x - 80, z - 80, x + 80, z + 80);
		assertEquals(1, routes.size());
		assertTrue(routes.get(0) == r, "la misma ruta que la generación (en memoria)");
		assertEquals(List.of(), t.routesIn(x - 80, z + 500, x + 80, z + 660), "lejos del camino, ninguna");
		// rutas(chunk) es rutasEn con la caja del chunk
		assertEquals(t.routes(Math.floorDiv(x, 16), Math.floorDiv(z, 16)),
				t.routesIn(Math.floorDiv(x, 16) * 16, Math.floorDiv(z, 16) * 16, Math.floorDiv(x, 16) * 16 + 15, Math.floorDiv(z, 16) * 16 + 15));
	}

	@Test
	void spawnsNearPlayerAndPassesInFront() {
		RoadLayout.Route r = route();
		int m = r.vertices() / 2;
		int[] p = beside(r, m, 30);
		Segment t = Segment.choose(List.of(r), p[0], p[1], 0);
		assertNotNull(t);
		double d = Segment.dist(r, t.start(), p[0], p[1]);
		assertTrue(d >= Segment.DIST_MIN && d <= Segment.DIST_MAX, "salida a " + d + " bloques del jugador");
		assertEquals(m, t.start(), "el vértice válido más cercano");
		assertEquals(Segment.LENGTH + 1, t.vertices());
		assertEquals(Segment.LENGTH, Math.abs(t.end() - t.start()));
		assertTrue(t.length() > Segment.LENGTH * RoadLayout.STEP * 0.9 && t.length() < Segment.LENGTH * RoadLayout.STEP * 1.5, "unos 128 bloques: " + t.length());
		// la llegada y la salida, fuera de las aldeas
		for (int i : new int[]{t.start(), t.end()}) {
			assertTrue(i >= Segment.VILLAGE_MARGIN && i <= r.vertices() - 1 - Segment.VILLAGE_MARGIN, "vértice " + i);
		}
		assertEquals(t.step() > 0 ? B : A, t.destination());
		assertEquals(t.step() > 0 ? A : B, t.origin());
		assertEquals(t.start(), t.vertex(0));
		assertEquals(t.end(), t.vertex(t.vertices() - 1));
		assertEquals((int) Math.floor(r.x(t.start())), t.x(0));
		assertEquals((int) Math.floor(r.z(t.end())), t.z(t.vertices() - 1));
	}

	@Test
	void headsTowardsPlayer() {
		RoadLayout.Route r = route();
		int m = r.vertices() / 2;
		// el jugador junto al camino, 2 vértices más allá de m: la salida queda antes y la caravana va hacia él
		int[] p = beside(r, m + 2, 0);
		Segment t = Segment.choose(List.of(r), p[0], p[1], 0);
		assertNotNull(t);
		int near = m + 2;
		assertEquals(Integer.signum(near - t.start()), t.step(), "sale a un lado del jugador y va hacia él");
		assertTrue(Math.min(t.start(), t.end()) <= near && near <= Math.max(t.start(), t.end()), "pasa por delante del jugador");
	}

	@Test
	void deterministicAndNoneWithoutNearbyRoad() {
		RoadLayout.Route r = route();
		int[] p = beside(r, r.vertices() / 3, 40);
		assertEquals(Segment.choose(List.of(r), p[0], p[1], 7), Segment.choose(List.of(r), p[0], p[1], 7));
		int[] far = beside(r, r.vertices() / 3, Segment.DIST_MAX + 40);
		assertNull(Segment.choose(List.of(r), far[0], far[1], 7), "a más de 80 bloques del camino no sale");
		assertNull(Segment.choose(List.of(), p[0], p[1], 7), "sin rutas, ninguna");
	}

	@Test
	void nearAVillageSpawnsOutsideAndHeadsToOtherSide() {
		RoadLayout.Route r = route();
		// el jugador en la plaza de A: la salida no puede estar en la aldea (margen) y cabe hacia B
		Segment t = Segment.choose(List.of(r), RoadLayout.px(A), RoadLayout.pz(A), 1);
		assertNotNull(t);
		assertTrue(t.start() >= Segment.VILLAGE_MARGIN);
		assertEquals(1, t.step(), "hacia B: hacia A no cabe");
		assertEquals(B, t.destination());
		// y junto a B, hacia A
		Segment u = Segment.choose(List.of(r), RoadLayout.px(B), RoadLayout.pz(B), 0);
		assertNotNull(u);
		assertEquals(-1, u.step());
		assertEquals(A, u.destination());
		assertTrue(u.end() >= Segment.VILLAGE_MARGIN, "para antes de la plaza de A");
	}

	@Test
	void shortRouteNoSegment() {
		long a = RoadLayout.pack(8, 8), b = RoadLayout.pack(8 + 16 * (2 * Segment.VILLAGE_MARGIN + Segment.MIN - 1), 8);
		RoadLayout t = new RoadLayout(1, CELL, 2000, (gx, gz) -> gx == 0 && gz == 0 ? a : RoadLayout.NONE, RoadLayout.Milestones.NO_MILESTONES);
		RoadLayout.Route r = t.route(a, b);
		assertNull(Segment.choose(List.of(r), RoadLayout.px(a) + 60, 40, 0), "entre aldeas tan cercanas no cabe un tramo");
	}

	@Test
	void trimToAVertex() {
		RoadLayout.Route r = route();
		int[] p = beside(r, r.vertices() / 2, 30);
		Segment t = Segment.choose(List.of(r), p[0], p[1], 0);
		Segment c = t.until(3);
		assertEquals(4, c.vertices());
		assertEquals(t.start(), c.start());
		assertEquals(t.vertex(3), c.end());
		assertEquals(t.destination(), c.destination(), "sigue yendo hacia la misma aldea");
	}
}
