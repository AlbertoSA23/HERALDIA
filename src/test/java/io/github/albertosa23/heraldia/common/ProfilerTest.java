package io.github.albertosa23.heraldia.common;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

/**
 * Perfil de la generación ({@link Profiler}): sin la propiedad no mide nada (coste cero: ni lee el reloj), activo acumula
 * veces, total y máximo por tramo, y el JSON solo lee (volcarlo dos veces da lo mismo).
 */
class ProfilerTest {
	@Test
	void disabledByDefault() {
		assertFalse(Boolean.getBoolean(Profiler.PROPERTY), "las pruebas corren sin -Dheraldia.perfil");
		assertFalse(Profiler.ACTIVE);
		assertEquals(0L, Profiler.start(), "sin la propiedad no lee el reloj");
		Profiler.end(Profiler.Segment.HILLSIDE, 0L);
		Profiler.counters().recordSample(Profiler.Segment.ROADS, 1_000_000L);
		for (Profiler.Segment t : Profiler.Segment.values()) {
			assertEquals(0, Profiler.counters().times(t), t.name());
		}
		assertEquals("{}", Profiler.counters().json());
		Profiler.dump();      // no hace nada ni falla
	}

	@Test
	void inactiveCountersDoNotMeasure() {
		Profiler.Counters c = new Profiler.Counters(false);
		assertEquals(0L, c.start());
		c.end(Profiler.Segment.MEDIUMS, 0L);
		c.recordSample(Profiler.Segment.MEDIUMS, 500L);
		assertEquals(0, c.times(Profiler.Segment.MEDIUMS));
		assertEquals(0, c.nanos(Profiler.Segment.MEDIUMS));
		assertEquals("{}", c.json());
	}

	@Test
	void accumulatesPerSection() {
		Profiler.Counters c = new Profiler.Counters(true);
		c.recordSample(Profiler.Segment.HILLSIDE, 2_000L);
		c.recordSample(Profiler.Segment.HILLSIDE, 6_000L);
		c.recordSample(Profiler.Segment.SHORE, 1_500_000L);
		assertEquals(2, c.times(Profiler.Segment.HILLSIDE));
		assertEquals(8_000L, c.nanos(Profiler.Segment.HILLSIDE));
		assertEquals(6_000L, c.maximum(Profiler.Segment.HILLSIDE));
		assertEquals(0, c.times(Profiler.Segment.ROADS));
		assertEquals("{\"ladera\":{\"n\":2,\"total_ms\":0.008,\"media_us\":4.0,\"max_us\":6.0},"
				+ "\"orilla\":{\"n\":1,\"total_ms\":1.500,\"media_us\":1500.0,\"max_us\":1500.0}}", c.json());
	}

	@Test
	void idempotentJson() {
		Profiler.Counters c = new Profiler.Counters(true);
		c.recordSample(Profiler.Segment.RULES, 10L);
		String a = c.json();
		assertEquals(a, c.json(), "leer el perfil no lo cambia");
		assertEquals(1, c.times(Profiler.Segment.RULES));
	}

	@Test
	void measuringWithTheClock() throws InterruptedException {
		Profiler.Counters c = new Profiler.Counters(true);
		long t0 = c.start();
		assertTrue(t0 != 0L);
		Thread.sleep(2);
		c.end(Profiler.Segment.FOREIGN_ZONE, t0);
		assertEquals(1, c.times(Profiler.Segment.FOREIGN_ZONE));
		assertTrue(c.nanos(Profiler.Segment.FOREIGN_ZONE) >= 1_000_000L, "al menos 1 ms medido");
	}

	@Test
	void acrossThreads() throws InterruptedException {
		Profiler.Counters c = new Profiler.Counters(true);
		Thread[] threads = new Thread[4];
		for (int h = 0; h < threads.length; h++) {
			final long d = h + 1;
			threads[h] = new Thread(() -> {
				for (int i = 0; i < 1000; i++) {
					c.recordSample(Profiler.Segment.MINES, d);
				}
			});
			threads[h].start();
		}
		for (Thread t : threads) {
			t.join();
		}
		assertEquals(4000, c.times(Profiler.Segment.MINES));
		assertEquals(1000L * (1 + 2 + 3 + 4), c.nanos(Profiler.Segment.MINES));
		assertEquals(4L, c.maximum(Profiler.Segment.MINES));
	}
}
