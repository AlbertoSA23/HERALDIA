package io.github.albertosa23.heraldia.arena;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.Test;

/** La partida: cuenta atrás, oleadas por tandas, pausa, mini-jefe, fin y reinicio. */
class MatchTest {
	private static final UUID A = UUID.randomUUID(), B = UUID.randomUUID();

	/** Avanza ticks hasta que empiece la oleada siguiente; devuelve cuántos segundos se anunciaron. */
	private static int untilWave(Match p) {
		int seconds = 0;
		for (int i = 0; i < 10000; i++) {
			Match.Step step = p.tick();
			if (step == Match.Step.WAVE_STARTS) {
				return seconds;
			}
			if (step == Match.Step.SECOND) {
				seconds++;
			}
		}
		throw new AssertionError("no empieza la oleada");
	}

	/** Mata a todos los enemigos de la oleada saliendo en tandas de como mucho `max`; devuelve las tandas. */
	private static int clean(Match p, int max) {
		int batches = 0;
		while (p.state() == Match.State.WAVE) {
			int n = p.spawn(max);
			assertTrue(p.alive() <= max, "más vivos que el límite");
			if (n > 0) {
				batches++;
			}
			int alive = p.alive();
			for (int i = 0; i < alive; i++) {
				p.dies();
			}
		}
		return batches;
	}

	@Test
	void countdownAndFirstWave() {
		Match p = new Match(50);
		assertEquals(Match.State.FREE, p.state());
		assertTrue(p.start());
		assertFalse(p.start(), "dos campanas no empiezan dos partidas");
		assertEquals(Match.State.COUNTDOWN, p.state());
		assertEquals(5, p.seconds());
		assertTrue(p.participants(List.of(A, B)));
		assertEquals(4, untilWave(p));          // 4, 3, 2, 1 y luego empieza
		assertEquals(Match.State.WAVE, p.state());
		assertEquals(1, p.wave());
		assertEquals(4, p.total());
		assertEquals(4, p.remaining());
		assertEquals(0, p.cleared());
	}

	@Test
	void batchesWithTheLimit() {
		Match p = new Match(50);
		p.start();
		p.participants(List.of(A));
		untilWave(p);
		for (int i = 1; i < 10; i++) {          // a la oleada 10: 22 enemigos y el mini-jefe
			clean(p, 100);
			untilWave(p);
		}
		assertEquals(10, p.wave());
		assertEquals(23, p.total());
		assertEquals(5, p.spawn(5));
		assertEquals(0, p.spawn(5), "con 5 vivos y el límite en 5 no sale nadie más");
		p.dies();
		p.dies();
		assertEquals(2, p.spawn(5));
		assertEquals(23 - 7, p.pending());
		assertTrue(clean(p, 5) >= 4, "16 que faltan y 5 vivos a la vez: al menos 4 tandas");
		assertEquals(Match.State.PAUSE, p.state());
	}

	@Test
	void waveClearedAndPause() {
		Match p = new Match(50);
		p.start();
		p.participants(List.of(A));
		untilWave(p);
		assertEquals(4, p.spawn(20));
		assertFalse(p.dies());
		assertFalse(p.dies());
		assertFalse(p.dies());
		assertTrue(p.dies(), "el último enemigo supera la oleada");
		assertEquals(Match.State.PAUSE, p.state());
		assertEquals(1, p.cleared());
		assertFalse(p.dies(), "en la pausa no hay enemigos");
		assertEquals(9, untilWave(p));          // 10 s de pausa: 9 avisos y empieza
		assertEquals(2, p.wave());
		assertEquals(6, p.total());
	}

	@Test
	void miniBossOnce() {
		Match p = new Match(50);
		p.start();
		p.participants(List.of(A));
		for (int n = 1; n <= 5; n++) {
			untilWave(p);
			boolean boss = p.takeBoss();
			assertEquals(n == 5, boss, "oleada " + n);
			assertFalse(p.takeBoss(), "el mini-jefe sale una sola vez");
			if (n < 5) {
				clean(p, 20);
			}
		}
		assertEquals(Waves.mobs(5, 50) + 1, p.total());
	}

	@Test
	void failureAndReinforcements() {
		Match p = new Match(50);
		p.start();
		p.participants(List.of(A));
		untilWave(p);
		p.spawn(20);
		p.fail();
		assertEquals(3, p.alive());
		assertEquals(1, p.pending());
		p.extra();
		assertEquals(5, p.total());
		assertEquals(5, p.remaining());
	}

	@Test
	void endWhenEveryoneLeavesAndCleanReset() {
		Match p = new Match(50);
		p.start();
		p.participants(List.of(A, B));
		untilWave(p);
		p.spawn(20);
		assertFalse(p.outcome(A), "queda B");
		assertTrue(p.participates(B));
		assertFalse(p.participates(A));
		assertTrue(p.outcome(B), "sin participantes la partida acaba");
		p.finish();
		assertEquals(Match.State.FREE, p.state());
		assertEquals(0, p.wave());
		assertEquals(0, p.remaining());
		assertTrue(p.participants().isEmpty());
		// otra partida empieza de cero
		assertTrue(p.start());
		p.participants(List.of(A));
		untilWave(p);
		assertEquals(1, p.wave());
		assertEquals(4, p.total());
	}

	@Test
	void noParticipants() {
		Match p = new Match(50);
		p.start();
		assertFalse(p.participants(List.of()));
		assertFalse(p.outcome(A), "en la cuenta atrás no se acaba por salir");
	}

	@Test
	void freeDoesNothing() {
		Match p = new Match(50);
		assertEquals(Match.Step.NOTHING, p.tick());
		assertEquals(0, p.spawn(20));
		assertFalse(p.dies());
	}
}
