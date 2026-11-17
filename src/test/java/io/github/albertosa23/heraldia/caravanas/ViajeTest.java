package io.github.albertosa23.heraldia.caravanas;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

/** El viaje de una caravana: avance por los vértices, asalto, llegada, muerte del mercader, alejamiento y atascos. */
class ViajeTest {
	/** Mercader vivo y cargado, en el vértice (distancia 0), con un jugador cerca y sin bandidos. */
	static Viaje.Vista llega() {
		return new Viaje.Vista(true, true, 0, 1, 0, true);
	}

	static Viaje.Vista lejosDelVertice(double d) {
		return new Viaje.Vista(true, true, d, 1, 0, true);
	}

	@Test
	void recorreElTramoYLlega() {
		Viaje v = new Viaje(5, -1);
		assertEquals(1, v.siguiente());
		assertEquals(Viaje.Paso.SIGUE, v.paso(lejosDelVertice(10)));
		for (int k = 1; k < 4; k++) {
			assertEquals(Viaje.Paso.AVANZA, v.paso(llega()));
			assertEquals(k + 1, v.siguiente());
		}
		assertEquals(Viaje.Paso.FIN, v.paso(llega()));
		assertEquals(Viaje.Fin.LLEGADA, v.fin());
		assertFalse(v.asaltada());
		assertFalse(v.superada());
		assertEquals(Viaje.Fase.FIN, v.fase());
		assertEquals(Viaje.Paso.FIN, v.paso(llega()), "terminado se queda terminado");
		assertEquals(5 * Viaje.CADA, v.ticks());
	}

	@Test
	void asaltoAMediaRutaYSuperado() {
		Viaje v = new Viaje(6, 2);
		assertEquals(Viaje.Paso.AVANZA, v.paso(llega()));                 // alcanza el 1
		assertEquals(Viaje.Paso.ASALTO, v.paso(llega()));                 // alcanza el 2: salen los bandidos
		assertTrue(v.asaltada());
		assertEquals(Viaje.Fase.ASALTO, v.fase());
		// mientras queden bandidos no sigue, aunque esté en el vértice
		Viaje.Vista conBandidos = new Viaje.Vista(true, true, 0, 2, 3, true);
		assertEquals(Viaje.Paso.SIGUE, v.paso(conBandidos));
		assertEquals(3, v.siguiente());
		assertEquals(Viaje.Paso.SUPERADO, v.paso(new Viaje.Vista(true, true, 5, 2, 0, true)));
		assertTrue(v.superada());
		assertEquals(Viaje.Fase.CAMINO, v.fase());
		while (v.paso(llega()) != Viaje.Paso.FIN) {
			assertEquals(Viaje.Fase.CAMINO, v.fase(), "no la vuelven a asaltar");
		}
		assertEquals(Viaje.Fin.LLEGADA, v.fin());
		assertTrue(v.superada());
	}

	@Test
	void elMercaderMuereYSePierde() {
		Viaje v = new Viaje(5, 1);
		v.paso(llega());
		assertEquals(Viaje.Fase.ASALTO, v.fase());
		assertEquals(Viaje.Paso.FIN, v.paso(new Viaje.Vista(false, true, 0, 1, 2, true)));
		assertEquals(Viaje.Fin.PERDIDA, v.fin());
		assertFalse(v.fin().despedida());
		assertFalse(v.superada(), "perdida: ni superada ni premio");
		// y terminar otra vez no cambia el motivo
		v.terminar(Viaje.Fin.LIMPIEZA);
		assertEquals(Viaje.Fin.PERDIDA, v.fin());
	}

	@Test
	void sinJugadoresCercaSeDespide() {
		Viaje v = new Viaje(5, -1);
		Viaje.Vista solo = new Viaje.Vista(true, true, 10, 0, 0, true);
		int pasos = 0;
		while (v.paso(solo) != Viaje.Paso.FIN) {
			pasos++;
			if (pasos == 10) {
				assertEquals(Viaje.Paso.SIGUE, v.paso(lejosDelVertice(9)), "un jugador vuelve: la cuenta empieza de nuevo");
			}
		}
		assertEquals(Viaje.Fin.LEJOS, v.fin());
		assertTrue(v.fin().despedida());
		assertTrue(v.ticks() >= Viaje.LEJOS_TICKS);
	}

	@Test
	void chunksDescargadosSeDespide() {
		Viaje v = new Viaje(5, -1);
		assertEquals(Viaje.Paso.FIN, v.paso(new Viaje.Vista(true, false, 0, 0, 0, true)));
		assertEquals(Viaje.Fin.LEJOS, v.fin());
	}

	@Test
	void elCaminoSeAcaba() {
		Viaje v = new Viaje(5, -1);
		v.paso(llega());
		assertEquals(Viaje.Paso.FIN, v.paso(new Viaje.Vista(true, true, 10, 1, 0, false)));
		assertEquals(Viaje.Fin.SIN_CAMINO, v.fin());
	}

	@Test
	void atascadaSaltaVerticesYAcabaDespidiendose() {
		Viaje v = new Viaje(10, -1);
		int avances = 0;
		Viaje.Paso p;
		do {
			p = v.paso(lejosDelVertice(10));       // no se acerca nunca
			avances += p == Viaje.Paso.AVANZA ? 1 : 0;
		} while (p != Viaje.Paso.FIN);
		assertEquals(Viaje.ATASCOS_MAX, avances, "salta un vértice por atasco");
		assertEquals(Viaje.Fin.ATASCADA, v.fin());
	}

	@Test
	void unViajeYUnAsaltoNoDuranParaSiempre() {
		Viaje v = new Viaje(5, -1);
		double d = 1000;
		Viaje.Paso p;
		do {
			d -= 1;                                 // se acerca muy despacio: ni atascada ni llega
			p = v.paso(lejosDelVertice(d));
		} while (p != Viaje.Paso.FIN);
		assertEquals(Viaje.Fin.TIEMPO, v.fin());
		assertEquals(Viaje.MAX_TICKS, v.ticks());
		Viaje a = new Viaje(5, 1);
		a.paso(llega());
		while (a.paso(new Viaje.Vista(true, true, 0, 1, 1, true)) != Viaje.Paso.FIN) {
			assertEquals(Viaje.Fase.ASALTO, a.fase());
		}
		assertEquals(Viaje.Fin.TIEMPO, a.fin());
		assertEquals(Viaje.ASALTO_MAX_TICKS + Viaje.CADA, a.ticks());
	}

	@Test
	void asaltoForzado() {
		Viaje v = new Viaje(5, -1);
		assertTrue(v.forzarAsalto());
		assertEquals(Viaje.Fase.ASALTO, v.fase());
		assertFalse(v.forzarAsalto(), "una vez");
		assertEquals(Viaje.Paso.SUPERADO, v.paso(llega()));
		assertFalse(v.forzarAsalto(), "ya asaltada");
		// el asalto previsto ya no se repite
		Viaje w = new Viaje(5, 2);
		assertTrue(w.forzarAsalto());
		w.paso(llega());
		assertEquals(Viaje.Paso.AVANZA, w.paso(llega()));
		assertEquals(Viaje.Paso.AVANZA, w.paso(llega()));
		Viaje x = new Viaje(5, -1);
		x.terminar(Viaje.Fin.LIMPIEZA);
		assertFalse(x.forzarAsalto(), "terminada no se asalta");
	}

	@Test
	void puntoDeAsaltoHaciaLaMitad() {
		for (int n = 3; n <= 12; n++) {
			for (double a : new double[]{0, 0.5, 0.999}) {
				int k = Viaje.puntoDeAsalto(n, a);
				assertTrue(k >= 1 && k <= n - 2, n + " vértices: " + k);
			}
		}
		assertEquals(4, Viaje.puntoDeAsalto(9, 0.5));
		assertThrows(IllegalArgumentException.class, () -> new Viaje(1, -1));
	}
}
