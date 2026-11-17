package io.github.albertosa23.heraldia.caravanas;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import io.github.albertosa23.heraldia.caminos.Trazado;
import java.util.List;
import org.junit.jupiter.api.Test;

/** Elección del tramo y la ruta sobre el camino (lógica pura, con un trazado de prueba de dos aldeas vecinas). */
class TramoTest {
	static final int CELL = 94 * 16;
	/** Dos aldeas a 1.200 bloques en el eje x: la de la casilla (0, 0) en 8, 8 y la de la (1, 0) en 1208, 8. */
	static final long A = Trazado.pack(8, 8), B = Trazado.pack(1208, 8);

	static Trazado trazado() {
		return new Trazado(42, CELL, 2000, (gx, gz) -> gx == 0 && gz == 0 ? A : gx == 1 && gz == 0 ? B : Trazado.NONE,
				Trazado.Hitos.NINGUNO);
	}

	static Trazado.Ruta ruta() {
		return trazado().ruta(A, B);
	}

	/** Un punto a {@code lado} bloques del vértice i de la ruta, por su normal. */
	static int[] junto(Trazado.Ruta r, int i, double lado) {
		double[] n = r.normal(i);
		return new int[]{(int) Math.round(r.x(i) + n[0] * lado), (int) Math.round(r.z(i) + n[1] * lado)};
	}

	@Test
	void laRutaDeUnaCajaEsLaCanonica() {
		Trazado t = trazado();
		Trazado.Ruta r = t.ruta(A, B);
		int m = r.vertices() / 2;
		int x = (int) r.x(m), z = (int) r.z(m);
		List<Trazado.Ruta> rutas = t.rutasEn(x - 80, z - 80, x + 80, z + 80);
		assertEquals(1, rutas.size());
		assertTrue(rutas.get(0) == r, "la misma ruta que la generación (en memoria)");
		assertEquals(List.of(), t.rutasEn(x - 80, z + 500, x + 80, z + 660), "lejos del camino, ninguna");
		// rutas(chunk) es rutasEn con la caja del chunk
		assertEquals(t.rutas(Math.floorDiv(x, 16), Math.floorDiv(z, 16)),
				t.rutasEn(Math.floorDiv(x, 16) * 16, Math.floorDiv(z, 16) * 16, Math.floorDiv(x, 16) * 16 + 15, Math.floorDiv(z, 16) * 16 + 15));
	}

	@Test
	void saleCercaDelJugadorYPasaPorDelante() {
		Trazado.Ruta r = ruta();
		int m = r.vertices() / 2;
		int[] p = junto(r, m, 30);
		Tramo t = Tramo.elegir(List.of(r), p[0], p[1], 0);
		assertNotNull(t);
		double d = Tramo.dist(r, t.inicio(), p[0], p[1]);
		assertTrue(d >= Tramo.DIST_MIN && d <= Tramo.DIST_MAX, "salida a " + d + " bloques del jugador");
		assertEquals(m, t.inicio(), "el vértice válido más cercano");
		assertEquals(Tramo.LARGO + 1, t.vertices());
		assertEquals(Tramo.LARGO, Math.abs(t.fin() - t.inicio()));
		assertTrue(t.longitud() > Tramo.LARGO * Trazado.PASO * 0.9 && t.longitud() < Tramo.LARGO * Trazado.PASO * 1.5, "unos 128 bloques: " + t.longitud());
		// la llegada y la salida, fuera de las aldeas
		for (int i : new int[]{t.inicio(), t.fin()}) {
			assertTrue(i >= Tramo.MARGEN_ALDEA && i <= r.vertices() - 1 - Tramo.MARGEN_ALDEA, "vértice " + i);
		}
		assertEquals(t.paso() > 0 ? B : A, t.destino());
		assertEquals(t.paso() > 0 ? A : B, t.origen());
		assertEquals(t.inicio(), t.vertice(0));
		assertEquals(t.fin(), t.vertice(t.vertices() - 1));
		assertEquals((int) Math.floor(r.x(t.inicio())), t.x(0));
		assertEquals((int) Math.floor(r.z(t.fin())), t.z(t.vertices() - 1));
	}

	@Test
	void vaHaciaElJugador() {
		Trazado.Ruta r = ruta();
		int m = r.vertices() / 2;
		// el jugador junto al camino, 2 vértices más allá de m: la salida queda antes y la caravana va hacia él
		int[] p = junto(r, m + 2, 0);
		Tramo t = Tramo.elegir(List.of(r), p[0], p[1], 0);
		assertNotNull(t);
		int cerca = m + 2;
		assertEquals(Integer.signum(cerca - t.inicio()), t.paso(), "sale a un lado del jugador y va hacia él");
		assertTrue(Math.min(t.inicio(), t.fin()) <= cerca && cerca <= Math.max(t.inicio(), t.fin()), "pasa por delante del jugador");
	}

	@Test
	void deterministaYSinCaminoCercaNinguno() {
		Trazado.Ruta r = ruta();
		int[] p = junto(r, r.vertices() / 3, 40);
		assertEquals(Tramo.elegir(List.of(r), p[0], p[1], 7), Tramo.elegir(List.of(r), p[0], p[1], 7));
		int[] lejos = junto(r, r.vertices() / 3, Tramo.DIST_MAX + 40);
		assertNull(Tramo.elegir(List.of(r), lejos[0], lejos[1], 7), "a más de 80 bloques del camino no sale");
		assertNull(Tramo.elegir(List.of(), p[0], p[1], 7), "sin rutas, ninguna");
	}

	@Test
	void cercaDeUnaAldeaSaleFueraYVaHaciaElOtroLado() {
		Trazado.Ruta r = ruta();
		// el jugador en la plaza de A: la salida no puede estar en la aldea (margen) y cabe hacia B
		Tramo t = Tramo.elegir(List.of(r), Trazado.px(A), Trazado.pz(A), 1);
		assertNotNull(t);
		assertTrue(t.inicio() >= Tramo.MARGEN_ALDEA);
		assertEquals(1, t.paso(), "hacia B: hacia A no cabe");
		assertEquals(B, t.destino());
		// y junto a B, hacia A
		Tramo u = Tramo.elegir(List.of(r), Trazado.px(B), Trazado.pz(B), 0);
		assertNotNull(u);
		assertEquals(-1, u.paso());
		assertEquals(A, u.destino());
		assertTrue(u.fin() >= Tramo.MARGEN_ALDEA, "para antes de la plaza de A");
	}

	@Test
	void rutaCortaSinTramo() {
		long a = Trazado.pack(8, 8), b = Trazado.pack(8 + 16 * (2 * Tramo.MARGEN_ALDEA + Tramo.MINIMO - 1), 8);
		Trazado t = new Trazado(1, CELL, 2000, (gx, gz) -> gx == 0 && gz == 0 ? a : Trazado.NONE, Trazado.Hitos.NINGUNO);
		Trazado.Ruta r = t.ruta(a, b);
		assertNull(Tramo.elegir(List.of(r), Trazado.px(a) + 60, 40, 0), "entre aldeas tan cercanas no cabe un tramo");
	}

	@Test
	void recortarHastaUnVertice() {
		Trazado.Ruta r = ruta();
		int[] p = junto(r, r.vertices() / 2, 30);
		Tramo t = Tramo.elegir(List.of(r), p[0], p[1], 0);
		Tramo c = t.hasta(3);
		assertEquals(4, c.vertices());
		assertEquals(t.inicio(), c.inicio());
		assertEquals(t.vertice(3), c.fin());
		assertEquals(t.destino(), c.destino(), "sigue yendo hacia la misma aldea");
	}
}
