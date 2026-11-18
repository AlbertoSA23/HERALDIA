package io.github.albertosa23.heraldia.huts;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.HashSet;
import java.util.Set;
import org.junit.jupiter.api.Test;

/** La decisión de cada choza: determinista, con la proporción configurada y que no se rehace una vez guardada. */
class DecisionTest {
	private static final long[] SEEDS = {0L, 1L, -4242L, 20261117L, Long.MIN_VALUE, Long.MAX_VALUE};

	/** Cuenta cuántas chozas de una malla de chunks son malvadas (o llevan premio) con una probabilidad. */
	private static double ratio(int prob, boolean premium) {
		int yes = 0, n = 0;
		for (long s : SEEDS) {
			for (int x = -60; x < 60; x += 3) {
				for (int z = -60; z < 60; z += 3) {
					boolean r = premium ? Decision.premium(s, x * 37, z * 41, prob) : Decision.evil(s, x * 37, z * 41, prob);
					yes += r ? 1 : 0;
					n++;
				}
			}
		}
		return (double) yes / n;
	}

	@Test
	void evilOneInFiveByDefault() {
		double p = ratio(20, false);
		assertTrue(p > 0.18 && p < 0.22, "20 %: " + p);
		double q = ratio(50, false);
		assertTrue(q > 0.47 && q < 0.53, "50 %: " + q);
	}

	@Test
	void premiumThreeInTen() {
		double p = ratio(30, true);
		assertTrue(p > 0.27 && p < 0.33, "30 %: " + p);
	}

	@Test
	void zeroAndHundred() {
		assertEquals(0.0, ratio(0, false));
		assertEquals(1.0, ratio(100, false));
		assertEquals(0.0, ratio(0, true));
		assertEquals(1.0, ratio(100, true));
		// fuera de rango se recorta (la configuración ya lo valida, pero por si acaso)
		assertEquals(0.0, ratio(-5, false));
		assertEquals(1.0, ratio(250, true));
	}

	@Test
	void deterministicPerHutAndSeed() {
		for (long s : SEEDS) {
			for (int x = -20; x < 20; x++) {
				assertEquals(Decision.evil(s, x, 7, 20), Decision.evil(s, x, 7, 20));
				assertArrayEquals(Decision.name(s, x, 7, 16, 8), Decision.name(s, x, 7, 16, 8));
			}
		}
		// la decisión depende de la semilla y de la choza: no es la misma para todas
		Set<Boolean> seen = new HashSet<>();
		for (int x = 0; x < 40; x++) {
			seen.add(Decision.evil(1L, x, 0, 20));
		}
		assertEquals(Set.of(true, false), seen);
	}

	@Test
	void monotonicInProbability() {
		// subir la probabilidad solo añade malvados: una choza malvada con 20 lo sigue siendo con 40
		for (int x = -30; x < 30; x++) {
			for (int z = -30; z < 30; z++) {
				if (Decision.evil(99L, x, z, 20)) {
					assertTrue(Decision.evil(99L, x, z, 40));
				}
			}
		}
	}

	@Test
	void prizeIndependentOfEvil() {
		int both = 0, evil = 0;
		for (int x = -100; x < 100; x++) {
			for (int z = -50; z < 50; z++) {
				if (Decision.evil(7L, x, z, 50)) {
					evil++;
					both += Decision.premium(7L, x, z, 50) ? 1 : 0;
				}
			}
		}
		double r = (double) both / evil;
		assertTrue(r > 0.45 && r < 0.55, "premio entre los malvados: " + r);
	}

	@Test
	void namesInRangeAndVaried() {
		Set<Integer> names = new HashSet<>(), nicknames = new HashSet<>();
		for (int x = 0; x < 200; x++) {
			int[] n = Decision.name(5L, x, -x, 16, 8);
			assertTrue(n[0] >= 0 && n[0] < 16 && n[1] >= 0 && n[1] < 8);
			names.add(n[0]);
			nicknames.add(n[1]);
		}
		assertEquals(16, names.size());
		assertEquals(8, nicknames.size());
		assertArrayEquals(new int[] {0, 0}, Decision.name(5L, 3, 3, 0, 0), "sin lista no falla");
	}

	@Test
	void statesAndRevealOnlyOnce() {
		assertFalse(Decision.isWizard(Set.of()));
		assertFalse(Decision.isWizard(Set.of("heraldia_mediana")));
		assertTrue(Decision.isWizard(Set.of(Decision.TAG, "heraldia_mediana")));
		assertEquals(Decision.State.UNDECIDED, Decision.state(Set.of(Decision.TAG)));
		assertEquals(Decision.State.BENIGN, Decision.state(Set.of(Decision.TAG, Decision.BENIGN)));
		assertEquals(Decision.State.EVIL, Decision.state(Set.of(Decision.TAG, Decision.EVIL_UNREVEALED)));
		// revelado manda sobre todo: un mago ya revelado no vuelve a revelarse
		assertEquals(Decision.State.REVEALED, Decision.state(Set.of(Decision.TAG, Decision.EVIL_UNREVEALED, Decision.REVEALED)));
		// las etiquetas del generador son las mismas que mira el Java
		assertEquals("heraldia_mago", Decision.TAG);
		assertEquals("heraldia_mago_malvado", Decision.EVIL);
	}
}
