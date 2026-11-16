package io.github.albertosa23.heraldia.comun;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

/**
 * Perfil de la generación ({@link Perfil}): sin la propiedad no mide nada (coste cero: ni lee el reloj), activo acumula
 * veces, total y máximo por tramo, y el JSON solo lee (volcarlo dos veces da lo mismo).
 */
class PerfilTest {
	@Test
	void desactivadoPorDefecto() {
		assertFalse(Boolean.getBoolean(Perfil.PROPIEDAD), "las pruebas corren sin -Dheraldia.perfil");
		assertFalse(Perfil.ACTIVO);
		assertEquals(0L, Perfil.inicio(), "sin la propiedad no lee el reloj");
		Perfil.fin(Perfil.Tramo.LADERA, 0L);
		Perfil.contadores().anotar(Perfil.Tramo.CAMINOS, 1_000_000L);
		for (Perfil.Tramo t : Perfil.Tramo.values()) {
			assertEquals(0, Perfil.contadores().veces(t), t.name());
		}
		assertEquals("{}", Perfil.contadores().json());
		Perfil.volcar();      // no hace nada ni falla
	}

	@Test
	void contadoresInactivosNoMiden() {
		Perfil.Contadores c = new Perfil.Contadores(false);
		assertEquals(0L, c.inicio());
		c.fin(Perfil.Tramo.MEDIANAS, 0L);
		c.anotar(Perfil.Tramo.MEDIANAS, 500L);
		assertEquals(0, c.veces(Perfil.Tramo.MEDIANAS));
		assertEquals(0, c.nanos(Perfil.Tramo.MEDIANAS));
		assertEquals("{}", c.json());
	}

	@Test
	void acumulaPorTramo() {
		Perfil.Contadores c = new Perfil.Contadores(true);
		c.anotar(Perfil.Tramo.LADERA, 2_000L);
		c.anotar(Perfil.Tramo.LADERA, 6_000L);
		c.anotar(Perfil.Tramo.ORILLA, 1_500_000L);
		assertEquals(2, c.veces(Perfil.Tramo.LADERA));
		assertEquals(8_000L, c.nanos(Perfil.Tramo.LADERA));
		assertEquals(6_000L, c.maximo(Perfil.Tramo.LADERA));
		assertEquals(0, c.veces(Perfil.Tramo.CAMINOS));
		assertEquals("{\"ladera\":{\"n\":2,\"total_ms\":0.008,\"media_us\":4.0,\"max_us\":6.0},"
				+ "\"orilla\":{\"n\":1,\"total_ms\":1.500,\"media_us\":1500.0,\"max_us\":1500.0}}", c.json());
	}

	@Test
	void jsonIdempotente() {
		Perfil.Contadores c = new Perfil.Contadores(true);
		c.anotar(Perfil.Tramo.REGLAS, 10L);
		String a = c.json();
		assertEquals(a, c.json(), "leer el perfil no lo cambia");
		assertEquals(1, c.veces(Perfil.Tramo.REGLAS));
	}

	@Test
	void midiendoConElReloj() throws InterruptedException {
		Perfil.Contadores c = new Perfil.Contadores(true);
		long t0 = c.inicio();
		assertTrue(t0 != 0L);
		Thread.sleep(2);
		c.fin(Perfil.Tramo.ZONA_AJENAS, t0);
		assertEquals(1, c.veces(Perfil.Tramo.ZONA_AJENAS));
		assertTrue(c.nanos(Perfil.Tramo.ZONA_AJENAS) >= 1_000_000L, "al menos 1 ms medido");
	}

	@Test
	void entreHilos() throws InterruptedException {
		Perfil.Contadores c = new Perfil.Contadores(true);
		Thread[] hilos = new Thread[4];
		for (int h = 0; h < hilos.length; h++) {
			final long d = h + 1;
			hilos[h] = new Thread(() -> {
				for (int i = 0; i < 1000; i++) {
					c.anotar(Perfil.Tramo.MINAS, d);
				}
			});
			hilos[h].start();
		}
		for (Thread t : hilos) {
			t.join();
		}
		assertEquals(4000, c.veces(Perfil.Tramo.MINAS));
		assertEquals(1000L * (1 + 2 + 3 + 4), c.nanos(Perfil.Tramo.MINAS));
		assertEquals(4L, c.maximo(Perfil.Tramo.MINAS));
	}
}
