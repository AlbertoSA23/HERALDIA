package io.github.albertosa23.heraldia.caravans;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

/** El viaje de una caravana: avance por los vértices, asalto, llegada, muerte del mercader, alejamiento y atascos. */
class JourneyTest {
	/** Mercader vivo y cargado, en el vértice (distancia 0), con un jugador cerca y sin bandidos. */
	static Journey.View arrives() {
		return new Journey.View(true, true, 0, 1, 0, true);
	}

	static Journey.View farFromVertex(double d) {
		return new Journey.View(true, true, d, 1, 0, true);
	}

	@Test
	void travelsTheSegmentAndArrives() {
		Journey v = new Journey(5, -1);
		assertEquals(1, v.next());
		assertEquals(Journey.Step.CONTINUES, v.step(farFromVertex(10)));
		for (int k = 1; k < 4; k++) {
			assertEquals(Journey.Step.ADVANCES, v.step(arrives()));
			assertEquals(k + 1, v.next());
		}
		assertEquals(Journey.Step.END, v.step(arrives()));
		assertEquals(Journey.End.ARRIVAL, v.end());
		assertFalse(v.ambushed());
		assertFalse(v.cleared());
		assertEquals(Journey.Phase.END, v.phase());
		assertEquals(Journey.Step.END, v.step(arrives()), "terminado se queda terminado");
		assertEquals(5 * Journey.EVERY, v.ticks());
	}

	@Test
	void ambushMidRouteAndCleared() {
		Journey v = new Journey(6, 2);
		assertEquals(Journey.Step.ADVANCES, v.step(arrives()));                 // alcanza el 1
		assertEquals(Journey.Step.AMBUSH, v.step(arrives()));                 // alcanza el 2: salen los bandidos
		assertTrue(v.ambushed());
		assertEquals(Journey.Phase.AMBUSH, v.phase());
		// mientras queden bandidos no sigue, aunque esté en el vértice
		Journey.View withBandits = new Journey.View(true, true, 0, 2, 3, true);
		assertEquals(Journey.Step.CONTINUES, v.step(withBandits));
		assertEquals(3, v.next());
		assertEquals(Journey.Step.CLEARED, v.step(new Journey.View(true, true, 5, 2, 0, true)));
		assertTrue(v.cleared());
		assertEquals(Journey.Phase.ROAD, v.phase());
		while (v.step(arrives()) != Journey.Step.END) {
			assertEquals(Journey.Phase.ROAD, v.phase(), "no la vuelven a asaltar");
		}
		assertEquals(Journey.End.ARRIVAL, v.end());
		assertTrue(v.cleared());
	}

	@Test
	void merchantDiesAndItIsLost() {
		Journey v = new Journey(5, 1);
		v.step(arrives());
		assertEquals(Journey.Phase.AMBUSH, v.phase());
		assertEquals(Journey.Step.END, v.step(new Journey.View(false, true, 0, 1, 2, true)));
		assertEquals(Journey.End.LOST, v.end());
		assertFalse(v.end().farewell());
		assertFalse(v.cleared(), "perdida: ni superada ni premio");
		// y terminar otra vez no cambia el motivo
		v.finish(Journey.End.CLEANUP);
		assertEquals(Journey.End.LOST, v.end());
	}

	@Test
	void noPlayersNearbyDespawns() {
		Journey v = new Journey(5, -1);
		Journey.View alone = new Journey.View(true, true, 10, 0, 0, true);
		int steps = 0;
		while (v.step(alone) != Journey.Step.END) {
			steps++;
			if (steps == 10) {
				assertEquals(Journey.Step.CONTINUES, v.step(farFromVertex(9)), "un jugador vuelve: la cuenta empieza de nuevo");
			}
		}
		assertEquals(Journey.End.FAR, v.end());
		assertTrue(v.end().farewell());
		assertTrue(v.ticks() >= Journey.FAR_TICKS);
	}

	@Test
	void unloadedChunksDespawn() {
		Journey v = new Journey(5, -1);
		assertEquals(Journey.Step.END, v.step(new Journey.View(true, false, 0, 0, 0, true)));
		assertEquals(Journey.End.FAR, v.end());
	}

	@Test
	void roadEnds() {
		Journey v = new Journey(5, -1);
		v.step(arrives());
		assertEquals(Journey.Step.END, v.step(new Journey.View(true, true, 10, 1, 0, false)));
		assertEquals(Journey.End.NO_ROAD, v.end());
	}

	@Test
	void stuckSkipsVerticesAndEventuallyDespawns() {
		Journey v = new Journey(10, -1);
		int advances = 0;
		Journey.Step p;
		do {
			p = v.step(farFromVertex(10));       // no se acerca nunca
			advances += p == Journey.Step.ADVANCES ? 1 : 0;
		} while (p != Journey.Step.END);
		assertEquals(Journey.MAX_STUCK, advances, "salta un vértice por atasco");
		assertEquals(Journey.End.STUCK, v.end());
	}

	@Test
	void journeyAndAmbushDoNotLastForever() {
		Journey v = new Journey(5, -1);
		double d = 1000;
		Journey.Step p;
		do {
			d -= 1;                                 // se acerca muy despacio: ni atascada ni llega
			p = v.step(farFromVertex(d));
		} while (p != Journey.Step.END);
		assertEquals(Journey.End.TIMEOUT, v.end());
		assertEquals(Journey.MAX_TICKS, v.ticks());
		Journey a = new Journey(5, 1);
		a.step(arrives());
		while (a.step(new Journey.View(true, true, 0, 1, 1, true)) != Journey.Step.END) {
			assertEquals(Journey.Phase.AMBUSH, a.phase());
		}
		assertEquals(Journey.End.TIMEOUT, a.end());
		assertEquals(Journey.AMBUSH_MAX_TICKS + Journey.EVERY, a.ticks());
	}

	@Test
	void forcedAmbush() {
		Journey v = new Journey(5, -1);
		assertTrue(v.forceAmbush());
		assertEquals(Journey.Phase.AMBUSH, v.phase());
		assertFalse(v.forceAmbush(), "una vez");
		assertEquals(Journey.Step.CLEARED, v.step(arrives()));
		assertFalse(v.forceAmbush(), "ya asaltada");
		// el asalto previsto ya no se repite
		Journey w = new Journey(5, 2);
		assertTrue(w.forceAmbush());
		w.step(arrives());
		assertEquals(Journey.Step.ADVANCES, w.step(arrives()));
		assertEquals(Journey.Step.ADVANCES, w.step(arrives()));
		Journey x = new Journey(5, -1);
		x.finish(Journey.End.CLEANUP);
		assertFalse(x.forceAmbush(), "terminada no se asalta");
	}

	@Test
	void ambushPointTowardsMiddle() {
		for (int n = 3; n <= 12; n++) {
			for (double a : new double[]{0, 0.5, 0.999}) {
				int k = Journey.ambushPoint(n, a);
				assertTrue(k >= 1 && k <= n - 2, n + " vértices: " + k);
			}
		}
		assertEquals(4, Journey.ambushPoint(9, 0.5));
		assertThrows(IllegalArgumentException.class, () -> new Journey(1, -1));
	}
}
