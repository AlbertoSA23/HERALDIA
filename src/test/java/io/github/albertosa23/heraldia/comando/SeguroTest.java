package io.github.albertosa23.heraldia.comando;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import io.github.albertosa23.heraldia.comando.Seguro.Celda;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import org.junit.jupiter.api.Test;

/** Teletransporte seguro (lógica pura): encima del suelo, sin asfixia, nunca en lava, flotando en el agua. */
class SeguroTest {
	/** Mundo de prueba: suelo de piedra hasta y = 63 (lo libre empieza en 64) y lo que se ponga encima. */
	static class Mundo implements Seguro.Mundo {
		final Map<Long, Celda> celdas = new HashMap<>();
		final Map<Long, Integer> alturas = new HashMap<>();
		int suelo = 64;

		static long k(int x, int y, int z) {
			return ((long) x & 0xFFFFF) << 40 | ((long) y & 0xFFF) << 20 | ((long) z & 0xFFFFF);
		}

		static long k(int x, int z) {
			return k(x, 0, z);
		}

		Mundo poner(int x, int y, int z, Celda c) {
			celdas.put(k(x, y, z), c);
			if (c != Celda.LIBRE) {
				alturas.merge(k(x, z), y + 1, Math::max);
			}
			return this;
		}

		@Override
		public Celda en(int x, int y, int z) {
			Celda c = celdas.get(k(x, y, z));
			return c != null ? c : y < suelo ? Celda.SOLIDO : Celda.LIBRE;
		}

		@Override
		public int altura(int x, int z) {
			return alturas.getOrDefault(k(x, z), suelo);
		}

		@Override
		public int minY() {
			return -64;
		}

		@Override
		public int maxY() {
			return 320;
		}
	}

	@Test
	void sueloLlanoEnElCentro() {
		assertEquals(Optional.of(new Seguro.Sitio(10, 64, -5)), Seguro.buscar(new Mundo(), 10, -5, Seguro.RADIO));
	}

	@Test
	void nuncaEnLavaNiFuego() {
		Mundo m = new Mundo().poner(0, 63, 0, Celda.PELIGRO);     // un charco de lava en el centro
		Seguro.Sitio s = Seguro.buscar(m, 0, 0, Seguro.RADIO).orElseThrow();
		assertEquals(64, s.y());
		assertEquals(1, Math.abs(s.x()) + Math.abs(s.z()), "la columna de al lado");
		Mundo fuego = new Mundo().poner(0, 64, 0, Celda.PELIGRO); // fuego encima del suelo
		assertTrue(Math.abs(Seguro.buscar(fuego, 0, 0, Seguro.RADIO).orElseThrow().x())
				+ Math.abs(Seguro.buscar(fuego, 0, 0, Seguro.RADIO).orElseThrow().z()) > 0);
	}

	@Test
	void sinAsfixiaBajoUnSaliente() {
		// la columna tiene un techo bajo: el heightmap da encima del techo, que es un sitio válido (al aire libre)
		Mundo m = new Mundo().poner(0, 65, 0, Celda.SOLIDO);
		assertEquals(Optional.of(new Seguro.Sitio(0, 66, 0)), Seguro.buscar(m, 0, 0, Seguro.RADIO));
		// un bloque que asfixia a la altura de la cabeza (sin heightmap que lo vea: p. ej. hojas) descarta la columna
		Mundo hojas = new Mundo();
		hojas.celdas.put(Mundo.k(0, 65, 0), Celda.SOLIDO);
		Seguro.Sitio s = Seguro.buscar(hojas, 0, 0, Seguro.RADIO).orElseThrow();
		assertTrue(s.x() != 0 || s.z() != 0);
		assertTrue(Seguro.valido(hojas, s.x(), s.y(), s.z()));
	}

	@Test
	void flotaEnElMar() {
		Mundo m = new Mundo();
		m.suelo = 40;
		for (int x = -10; x <= 10; x++) {
			for (int z = -10; z <= 10; z++) {
				for (int y = 40; y < 63; y++) {
					m.poner(x, y, z, Celda.AGUA);
				}
			}
		}
		assertEquals(Optional.of(new Seguro.Sitio(0, 63, 0)), Seguro.buscar(m, 0, 0, Seguro.RADIO), "en la superficie del agua");
	}

	@Test
	void sinSitioSiTodoEsPeligroso() {
		Mundo m = new Mundo();
		for (int x = -3; x <= 3; x++) {
			for (int z = -3; z <= 3; z++) {
				m.poner(x, 63, z, Celda.PELIGRO);
			}
		}
		assertEquals(Optional.empty(), Seguro.buscar(m, 0, 0, 3));
		assertTrue(Seguro.buscar(m, 0, 0, 4).isPresent(), "un poco más lejos ya hay suelo");
	}

	@Test
	void columnasVaciasOHastaElTecho() {
		Mundo vacio = new Mundo() {
			@Override
			public int altura(int x, int z) {
				return minY();
			}
		};
		assertEquals(Optional.empty(), Seguro.buscar(vacio, 0, 0, 2));
		Mundo techo = new Mundo() {
			@Override
			public int altura(int x, int z) {
				return maxY() - 1;
			}
		};
		assertEquals(Optional.empty(), Seguro.buscar(techo, 0, 0, 2));
	}

	@Test
	void espiralDelCentroHaciaFueraYDeterminista() {
		List<int[]> e = Seguro.espiral(2);
		assertArrayEquals(new int[] {0, 0}, e.getFirst());
		for (int i = 1; i < e.size(); i++) {
			int a = e.get(i - 1)[0] * e.get(i - 1)[0] + e.get(i - 1)[1] * e.get(i - 1)[1];
			int b = e.get(i)[0] * e.get(i)[0] + e.get(i)[1] * e.get(i)[1];
			assertTrue(a <= b);
		}
		assertEquals(13, e.size(), "círculo de radio 2");
		assertEquals(e.stream().map(x -> x[0] + "," + x[1]).toList(), Seguro.espiral(2).stream().map(x -> x[0] + "," + x[1]).toList());
	}
}
