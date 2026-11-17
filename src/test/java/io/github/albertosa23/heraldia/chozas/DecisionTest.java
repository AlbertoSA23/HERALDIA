package io.github.albertosa23.heraldia.chozas;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.HashSet;
import java.util.Set;
import org.junit.jupiter.api.Test;

/** La decisión de cada choza: determinista, con la proporción configurada y que no se rehace una vez guardada. */
class DecisionTest {
	private static final long[] SEMILLAS = {0L, 1L, -4242L, 20261117L, Long.MIN_VALUE, Long.MAX_VALUE};

	/** Cuenta cuántas chozas de una malla de chunks son malvadas (o llevan premio) con una probabilidad. */
	private static double proporcion(int prob, boolean premium) {
		int si = 0, n = 0;
		for (long s : SEMILLAS) {
			for (int x = -60; x < 60; x += 3) {
				for (int z = -60; z < 60; z += 3) {
					boolean r = premium ? Decision.premium(s, x * 37, z * 41, prob) : Decision.malvado(s, x * 37, z * 41, prob);
					si += r ? 1 : 0;
					n++;
				}
			}
		}
		return (double) si / n;
	}

	@Test
	void malvadoUnaDeCadaCincoPorDefecto() {
		double p = proporcion(20, false);
		assertTrue(p > 0.18 && p < 0.22, "20 %: " + p);
		double q = proporcion(50, false);
		assertTrue(q > 0.47 && q < 0.53, "50 %: " + q);
	}

	@Test
	void premiumTresDeCadaDiez() {
		double p = proporcion(30, true);
		assertTrue(p > 0.27 && p < 0.33, "30 %: " + p);
	}

	@Test
	void ceroYCien() {
		assertEquals(0.0, proporcion(0, false));
		assertEquals(1.0, proporcion(100, false));
		assertEquals(0.0, proporcion(0, true));
		assertEquals(1.0, proporcion(100, true));
		// fuera de rango se recorta (la configuración ya lo valida, pero por si acaso)
		assertEquals(0.0, proporcion(-5, false));
		assertEquals(1.0, proporcion(250, true));
	}

	@Test
	void deterministaPorChozaYSemilla() {
		for (long s : SEMILLAS) {
			for (int x = -20; x < 20; x++) {
				assertEquals(Decision.malvado(s, x, 7, 20), Decision.malvado(s, x, 7, 20));
				assertArrayEquals(Decision.nombre(s, x, 7, 16, 8), Decision.nombre(s, x, 7, 16, 8));
			}
		}
		// la decisión depende de la semilla y de la choza: no es la misma para todas
		Set<Boolean> vistas = new HashSet<>();
		for (int x = 0; x < 40; x++) {
			vistas.add(Decision.malvado(1L, x, 0, 20));
		}
		assertEquals(Set.of(true, false), vistas);
	}

	@Test
	void monotonaEnLaProbabilidad() {
		// subir la probabilidad solo añade malvados: una choza malvada con 20 lo sigue siendo con 40
		for (int x = -30; x < 30; x++) {
			for (int z = -30; z < 30; z++) {
				if (Decision.malvado(99L, x, z, 20)) {
					assertTrue(Decision.malvado(99L, x, z, 40));
				}
			}
		}
	}

	@Test
	void premioIndependienteDelMalvado() {
		int ambos = 0, malos = 0;
		for (int x = -100; x < 100; x++) {
			for (int z = -50; z < 50; z++) {
				if (Decision.malvado(7L, x, z, 50)) {
					malos++;
					ambos += Decision.premium(7L, x, z, 50) ? 1 : 0;
				}
			}
		}
		double r = (double) ambos / malos;
		assertTrue(r > 0.45 && r < 0.55, "premio entre los malvados: " + r);
	}

	@Test
	void nombresEnRangoYVariados() {
		Set<Integer> nombres = new HashSet<>(), apodos = new HashSet<>();
		for (int x = 0; x < 200; x++) {
			int[] n = Decision.nombre(5L, x, -x, 16, 8);
			assertTrue(n[0] >= 0 && n[0] < 16 && n[1] >= 0 && n[1] < 8);
			nombres.add(n[0]);
			apodos.add(n[1]);
		}
		assertEquals(16, nombres.size());
		assertEquals(8, apodos.size());
		assertArrayEquals(new int[] {0, 0}, Decision.nombre(5L, 3, 3, 0, 0), "sin lista no falla");
	}

	@Test
	void estadosYRevelacionUnaSolaVez() {
		assertFalse(Decision.esMago(Set.of()));
		assertFalse(Decision.esMago(Set.of("heraldia_mediana")));
		assertTrue(Decision.esMago(Set.of(Decision.TAG, "heraldia_mediana")));
		assertEquals(Decision.Estado.SIN_DECIDIR, Decision.estado(Set.of(Decision.TAG)));
		assertEquals(Decision.Estado.BENIGNO, Decision.estado(Set.of(Decision.TAG, Decision.BENIGNO)));
		assertEquals(Decision.Estado.MALVADO, Decision.estado(Set.of(Decision.TAG, Decision.MALVADO_SIN_REVELAR)));
		// revelado manda sobre todo: un mago ya revelado no vuelve a revelarse
		assertEquals(Decision.Estado.REVELADO, Decision.estado(Set.of(Decision.TAG, Decision.MALVADO_SIN_REVELAR, Decision.REVELADO)));
		// las etiquetas del generador son las mismas que mira el Java
		assertEquals("heraldia_mago", Decision.TAG);
		assertEquals("heraldia_mago_malvado", Decision.MALVADO);
	}
}
