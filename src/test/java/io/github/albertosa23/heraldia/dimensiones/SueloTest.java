package io.github.albertosa23.heraldia.dimensiones;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import io.github.albertosa23.heraldia.comando.Seguro;
import java.util.function.IntPredicate;
import org.junit.jupiter.api.Test;

/** Dónde se apoyan las estructuras del Nether y el End ({@link Suelo}) y el sitio seguro bajo el techo ({@link Seguro#bajoTecho}). */
class SueloTest {
	/** Columna del Nether de mentira: bedrock arriba (de 123 a 127), aire salvo los tramos macizos [a, b] y lava bajo 32. */
	private record Columna(int[][] macizos) {
		boolean solido(int y) {
			if (y >= 123 || y <= 0) {
				return true;
			}
			for (int[] m : macizos) {
				if (m[0] <= y && y <= m[1]) {
					return true;
				}
			}
			return false;
		}

		boolean lava(int y) {
			return y <= 31 && !solido(y);
		}

		boolean aire(int y) {
			return !solido(y) && !lava(y);
		}

		IntPredicate s() {
			return this::solido;
		}

		IntPredicate a() {
			return this::aire;
		}
	}

	@Test
	void netherBuscaElPrimerSueloConAireEncimaDeArribaAbajo() {
		// suelo a 40 (macizo de 1 a 39) y una repisa a 100 con solo 4 de aire hasta otro macizo a 104
		Columna c = new Columna(new int[][] {{1, 39}, {95, 99}, {104, 122}});
		assertEquals(40, Suelo.nether(c.s(), c.a(), Suelo.NETHER_DESDE, Suelo.NETHER_HASTA, 30), "con 30 de aire, la repisa no cabe");
		assertEquals(100, Suelo.nether(c.s(), c.a(), Suelo.NETHER_DESDE, Suelo.NETHER_HASTA, 4), "la repisa, con 4 de aire");
		assertEquals(40, Suelo.nether(c.s(), c.a(), Suelo.NETHER_DESDE, Suelo.NETHER_HASTA, 5), "con 5 de aire, el suelo de abajo");
		assertEquals(40, Suelo.nether(c.s(), c.a(), Suelo.NETHER_DESDE, Suelo.NETHER_HASTA, 55));
		assertEquals(Suelo.NINGUNO, Suelo.nether(c.s(), c.a(), Suelo.NETHER_DESDE, Suelo.NETHER_HASTA, 56), "no cabe en ningún sitio");
	}

	@Test
	void netherNuncaSobreLaLavaNiBajoElTecho() {
		Columna mar = new Columna(new int[][] {{1, 10}});              // todo lava hasta 31 y aire hasta el techo
		assertEquals(Suelo.NINGUNO, Suelo.nether(mar.s(), mar.a(), Suelo.NETHER_DESDE, Suelo.NETHER_HASTA, 4), "el mar de lava no sostiene");
		Columna alto = new Columna(new int[][] {{1, 118}});             // macizo hasta 118: aire de 119 a 122
		assertEquals(Suelo.NINGUNO, Suelo.nether(alto.s(), alto.a(), Suelo.NETHER_DESDE, Suelo.NETHER_HASTA, 3),
				"un suelo por encima de NETHER_DESDE (pegado al techo) no vale");
		Columna isla = new Columna(new int[][] {{1, 20}, {32, 32}});    // una losa a 32 sobre la lava
		assertEquals(Suelo.NINGUNO, Suelo.nether(isla.s(), isla.a(), Suelo.NETHER_DESDE, Suelo.NETHER_HASTA, 4),
				"por debajo de NETHER_HASTA no se busca");
		for (int libre = 2; libre <= 40; libre++) {
			int y = Suelo.nether(new Columna(new int[][] {{1, 60}}).s(), new Columna(new int[][] {{1, 60}}).a(),
					Suelo.NETHER_DESDE, Suelo.NETHER_HASTA, libre);
			assertEquals(61, y, "libre " + libre);
		}
	}

	@Test
	void netherEsquinasYDesnivel() {
		Columna c = new Columna(new int[][] {{1, 63}});
		assertEquals(64, Suelo.netherCerca(c.s(), c.a(), 60), "a +4 del centro");
		assertEquals(64, Suelo.netherCerca(c.s(), c.a(), 64));
		assertEquals(Suelo.NINGUNO, Suelo.netherCerca(c.s(), c.a(), 50), "a +14: fuera del desnivel");
		assertTrue(Suelo.llano(64, 64, 60, 69, 59));
		assertFalse(Suelo.llano(64, 64, 64, 70, 64), "una esquina a +6");
		assertFalse(Suelo.llano(64, 64, Suelo.NINGUNO, 64, 64), "una esquina sin suelo (barranco)");
	}

	@Test
	void endSoloSobreIslasExterioresYLlanas() {
		int lejos = Suelo.END_RADIO_CENTRAL + 100;
		assertEquals(62, Suelo.end(lejos, 0, 62, 60, 64, 63, 61));
		assertEquals(Suelo.NINGUNO, Suelo.end(lejos, 0, 62, 0, 64, 63, 61), "una esquina sobre el vacío");
		assertEquals(Suelo.NINGUNO, Suelo.end(lejos, 0, 0, 0, 0, 0, 0), "todo vacío");
		assertEquals(Suelo.NINGUNO, Suelo.end(lejos, 0, 62, 62, 62, 62, 70), "desnivel de 8");
		assertEquals(Suelo.NINGUNO, Suelo.end(Suelo.END_RADIO_CENTRAL - 1, 0, 62, 62, 62, 62, 62), "la isla central (y el dragón)");
		assertEquals(Suelo.NINGUNO, Suelo.end(700, 700, 62, 62, 62, 62, 62), "a 990 bloques del centro");
		assertEquals(62, Suelo.end(-800, -800, 62, 62, 62, 62, 62), "a 1.131 bloques");
		assertEquals(Suelo.NINGUNO, Suelo.end(lejos, 0, Suelo.END_MINIMO - 1, 44, 44, 44, 44), "demasiado bajo: un islote suelto");
	}

	/** Un mundo de {@link Seguro} con techo: bedrock a 123-127, macizo hasta {@code suelo} - 1 y lava en y = suelo si se pide. */
	private static Seguro.Mundo mundo(int suelo, boolean lava) {
		return new Seguro.Mundo() {
			@Override
			public Seguro.Celda en(int x, int y, int z) {
				if (y >= 123 || y < suelo) {
					return Seguro.Celda.SOLIDO;
				}
				return lava && y == suelo ? Seguro.Celda.PELIGRO : Seguro.Celda.LIBRE;
			}

			@Override
			public int altura(int x, int z) {
				return 128;
			}

			@Override
			public int minY() {
				return 0;
			}

			@Override
			public int maxY() {
				return 256;
			}
		};
	}

	@Test
	void bajoTechoEncuentraElSueloYNoElTecho() {
		assertEquals(70, Seguro.bajoTecho(mundo(70, false), 0, 0, 120, 32));
		assertEquals(0, Seguro.bajoTecho(mundo(70, true), 0, 0, 120, 32), "sobre lava no: la mínima del mundo");
		assertEquals(0, Seguro.bajoTecho(mundo(20, false), 0, 0, 120, 32), "por debajo de hasta no se busca");
	}
}
