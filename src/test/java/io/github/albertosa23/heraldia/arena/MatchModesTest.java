package io.github.albertosa23.heraldia.arena;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.Test;

/** Los modos de la partida (T41): pausa de cada modo, fin del contrarreloj, tiempo de partida y lo que puntúa. */
class MatchModesTest {
	private static final UUID A = UUID.randomUUID(), B = UUID.randomUUID();

	/** Ticks hasta que empieza la oleada siguiente. */
	private static int untilWave(Match p) {
		for (int i = 1; i < 10000; i++) {
			if (p.tick() == Match.Step.WAVE_STARTS) {
				return i;
			}
		}
		throw new AssertionError("no empieza la oleada");
	}

	/** Saca y mata a todos los enemigos de la oleada (sin pasar ticks); true si se superó. */
	private static boolean clean(Match p) {
		boolean cleared = false;
		while (p.state() == Match.State.WAVE) {
			p.spawn(20);
			int alive = p.alive();
			for (int i = 0; i < alive; i++) {
				cleared |= p.dies();
			}
		}
		return cleared;
	}

	private static Match started(Mode m, int waves) {
		Match p = new Match(50);
		assertTrue(p.start(m, waves));
		assertTrue(p.participants(List.of(A, B)));
		assertEquals(Match.COUNTDOWN_TICKS, untilWave(p));
		return p;
	}

	@Test
	void coopAsAlways() {
		Match p = new Match(50);
		assertTrue(p.start());
		assertEquals(Mode.COOP, p.mode());
		assertEquals(0, p.target());
		p.participants(List.of(A));
		untilWave(p);
		assertTrue(clean(p));
		assertEquals(Match.State.PAUSE, p.state());
		assertEquals(Match.PAUSE_TICKS / 20, p.seconds());
		assertEquals(Match.PAUSE_TICKS, untilWave(p));
		assertFalse(p.completed(), "el cooperativo no se acaba por oleadas");
	}

	@Test
	void timeTrialEndsAfterTheLast() {
		Match p = started(Mode.TIME_TRIAL, 3);
		assertEquals(3, p.target());
		for (int n = 1; n <= 3; n++) {
			assertEquals(n, p.wave());
			for (int i = 0; i < 40; i++) {
				p.tick();                         // 2 s de lucha por oleada
			}
			assertTrue(clean(p));
			assertEquals(n == 3, p.completed(), "oleada " + n);
			if (n < 3) {
				assertEquals(Mode.TIME_TRIAL.pause(), untilWave(p), "pausa corta");
			}
		}
		assertEquals(3, p.cleared());
		// 3 oleadas de 40 ticks y 2 pausas de 100: lo que puntúa (los ticks al superar la última)
		assertEquals(3 * 40 + 2 * Mode.TIME_TRIAL.pause(), p.clearedTicks());
		p.finish();
		assertEquals(Mode.COOP, p.mode(), "al terminar vuelve al de siempre");
		assertEquals(0, p.ticks());
	}

	@Test
	void timeTrialOfAtLeastOneWave() {
		Match p = new Match(50);
		p.start(Mode.TIME_TRIAL, 0);
		assertEquals(1, p.target());
	}

	@Test
	void survivalWithoutPause() {
		Match p = started(Mode.SURVIVAL, 10);
		assertEquals(0, p.target(), "el número de oleadas solo es del contrarreloj");
		assertTrue(clean(p));
		assertEquals(Match.State.PAUSE, p.state());
		assertEquals(1, untilWave(p), "la siguiente oleada empieza en el tick siguiente");
		assertEquals(2, p.wave());
		assertTrue(clean(p));
		assertEquals(1, untilWave(p));
		assertFalse(p.completed());
		assertEquals(2, p.cleared());
	}

	@Test
	void countdownDoesNotCountTowardsTime() {
		Match p = new Match(50);
		p.start(Mode.TIME_TRIAL, 5);
		p.participants(List.of(A));
		untilWave(p);
		assertEquals(0, p.ticks(), "la cuenta atrás no cuenta");
		for (int i = 0; i < 30; i++) {
			p.tick();
		}
		assertEquals(30, p.ticks());
		assertEquals(0, p.clearedTicks(), "aún no ha superado ninguna");
		clean(p);
		assertEquals(30, p.clearedTicks());
		untilWave(p);
		assertEquals(30 + Mode.TIME_TRIAL.pause(), p.ticks(), "la pausa sí cuenta (va contra el reloj)");
	}

	@Test
	void twoMatchesDoNotMix() {
		Match p = started(Mode.TIME_TRIAL, 2);
		assertFalse(p.start(Mode.SURVIVAL, 0), "con una partida en marcha no empieza otra");
		assertEquals(Mode.TIME_TRIAL, p.mode());
		p.finish();
		assertTrue(p.start(Mode.SURVIVAL, 0));
		assertEquals(Mode.SURVIVAL, p.mode());
		assertEquals(0, p.clearedTicks());
	}
}
