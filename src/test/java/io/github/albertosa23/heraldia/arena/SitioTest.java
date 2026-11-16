package io.github.albertosa23.heraldia.arena;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.Optional;
import org.junit.jupiter.api.Test;

/** Elección del sitio: a 200-300 bloques del spawn, en llano y sin agua. */
class SitioTest {
	private static final int LADO = 57, BAJO = 7, ALTO = 7, MIN_Y = -64, MAX_Y = 320;

	/** Terreno inventado: llano a 70, con lo que diga `alto` (altura) y `agua` (columnas con agua). */
	private record Terreno(java.util.function.IntBinaryOperator alto, java.util.function.BiPredicate<Integer, Integer> agua)
			implements Sitio.Alturas {
		@Override
		public int superficie(int x, int z) {
			return alto.applyAsInt(x, z) + 1 + (agua.test(x, z) ? 3 : 0);
		}

		@Override
		public int fondo(int x, int z) {
			return alto.applyAsInt(x, z) + 1;
		}
	}

	private static Optional<Sitio.Eleccion> elegir(int sx, int sz, Sitio.Alturas a) {
		return Sitio.elegir(sx, sz, LADO, BAJO, ALTO, MIN_Y, MAX_Y, a);
	}

	@Test
	void llanoEntreDoscientosYTrescientos() {
		Sitio.Eleccion e = elegir(40, -30, new Terreno((x, z) -> 70, (x, z) -> false)).orElseThrow();
		double d = Math.hypot(e.x() - 40, e.z() + 30);
		assertTrue(d >= 199.5 && d <= 300.5, "distancia " + d);
		assertEquals(Sitio.RADIO_PREFERIDO, e.distancia(), 1, "en llano, a la distancia preferida");
		assertEquals(70, e.suelo());
		assertEquals(0, e.desnivel());
	}

	@Test
	void evitaLasPendientesYElAgua() {
		// al este (x > 0) una ladera fuerte; al norte (z < 0), un lago; el llano, al oeste y al sur
		Terreno t = new Terreno((x, z) -> x > 0 ? 70 + x / 3 : 70, (x, z) -> z < -100);
		Sitio.Eleccion e = elegir(0, 0, t).orElseThrow();
		assertTrue(e.x() + LADO / 2 + Sitio.MARGEN <= 0 || e.desnivel() <= 2, "no en la ladera: " + e);
		assertTrue(e.z() - LADO / 2 - Sitio.MARGEN >= -100, "no en el lago: " + e);
		assertTrue(e.desnivel() <= Sitio.DESNIVEL_MAX);
	}

	@Test
	void prefiereElMenorDesnivel() {
		// ondulado con amplitud que crece hacia el sur: el mejor sitio, al norte
		Terreno t = new Terreno((x, z) -> 70 + (int) (Math.sin(x / 9.0) * Math.max(0, z + 320) / 60.0), (x, z) -> false);
		Sitio.Eleccion e = elegir(0, 0, t).orElseThrow();
		assertTrue(e.z() < -150, "debería quedar al norte: " + e);
	}

	@Test
	void sinSitioSiTodoEsAguaOMontana() {
		assertTrue(elegir(0, 0, new Terreno((x, z) -> 70, (x, z) -> true)).isEmpty(), "todo agua");
		assertTrue(elegir(0, 0, new Terreno((x, z) -> 70 + Math.abs(x + z), (x, z) -> false)).isEmpty(), "todo ladera");
	}

	@Test
	void caberEnLaAlturaDelMundo() {
		assertTrue(elegir(0, 0, new Terreno((x, z) -> MAX_Y - 3, (x, z) -> false)).isEmpty(), "pegada al techo del mundo");
		assertTrue(elegir(0, 0, new Terreno((x, z) -> MIN_Y + 2, (x, z) -> false)).isEmpty(), "pegada al fondo del mundo");
	}

	@Test
	void medianaComoSuelo() {
		Sitio.Eleccion e = Sitio.evaluar(250, 0, 0, 0, LADO, new Terreno((x, z) -> x > 250 ? 74 : 70, (x, z) -> false));
		assertEquals(4, e.desnivel());
		assertTrue(e.suelo() == 70 || e.suelo() == 74);
		assertEquals(250, e.distancia());
	}
}
