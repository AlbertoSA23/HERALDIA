package io.github.albertosa23.heraldia.caminos;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.Test;

/**
 * Trazado de los caminos (lógica pura, sin el juego): determinismo, simetría, distancia máxima, vecindad relativa,
 * fronteras de chunk sin huecos, agua (puente, pasarela, corte), farolas y carteles, puntos de paso y nombres.
 */
class TrazadoTest {
	/** Rejilla de las aldeas por defecto: 94 chunks (1.504 bloques), candidata en los primeros 32 chunks de la casilla. */
	static final int CELL = 94 * 16, WINDOW = (94 - 62) * 16;

	/** Aldeas de prueba: una por casilla en la ventana (como random_spread), y casillas vacías al azar. */
	static Trazado.Aldeas aldeas(long seed, double vacias) {
		return (gx, gz) -> {
			if (Trazado.azar(seed, Trazado.pack(gx, gz), 1) < vacias) {
				return Trazado.NONE;
			}
			int ox = (int) (Trazado.azar(seed, Trazado.pack(gx, gz), 2) * WINDOW), oz = (int) (Trazado.azar(seed, Trazado.pack(gx, gz), 3) * WINDOW);
			return Trazado.pack(gx * CELL + ox + 8, gz * CELL + oz + 8);
		};
	}

	static Trazado trazado(long seed, int maxDist) {
		return new Trazado(seed, CELL, maxDist, aldeas(seed, 0.2), Trazado.Hitos.NINGUNO);
	}

	static double dist(long a, long b) {
		return Math.hypot(Trazado.px(a) - Trazado.px(b), Trazado.pz(a) - Trazado.pz(b));
	}

	/** Todas las aldeas de las casillas [-n, n]². */
	static List<Long> todas(Trazado t, int n) {
		List<Long> out = new ArrayList<>();
		for (int gx = -n; gx <= n; gx++) {
			for (int gz = -n; gz <= n; gz++) {
				long a = t.aldea(gx, gz);
				if (a != Trazado.NONE) {
					out.add(a);
				}
			}
		}
		return out;
	}

	static int cell(long a, boolean x) {
		return Math.floorDiv(x ? Trazado.px(a) : Trazado.pz(a), CELL);
	}

	@Test
	void vecinasSimetricasYDentroDeLaDistancia() {
		for (long seed = 1; seed <= 20; seed++) {
			Trazado t = trazado(seed, 2000);
			int edges = 0;
			for (long a : todas(t, 4)) {
				for (long b : t.vecinas(cell(a, true), cell(a, false))) {
					assertTrue(dist(a, b) <= 2000, "a más de la distancia máxima");
					long[] back = t.vecinas(cell(b, true), cell(b, false));
					assertTrue(java.util.Arrays.stream(back).anyMatch(v -> v == a), "A→B sin B→A (semilla " + seed + ")");
					edges++;
				}
			}
			assertTrue(edges > 0, "ningún camino con la rejilla por defecto y 2.000 bloques");
		}
	}

	@Test
	void vecindadRelativaSinTercerasMasCerca() {
		Trazado t = trazado(7, 2500);
		List<Long> all = todas(t, 6);
		for (long a : todas(t, 4)) {
			for (long b : t.vecinas(cell(a, true), cell(a, false))) {
				for (long c : all) {
					if (c != a && c != b) {
						assertFalse(Math.max(dist(a, c), dist(b, c)) < dist(a, b), "hay una tercera más cerca de las dos");
					}
				}
			}
		}
	}

	@Test
	void distanciaMaximaCorta() {
		// con la rejilla mínima de las aldeas (63 chunks, separación 42) dos aldeas nunca están a menos de 672 bloques:
		// a 600 no hay ningún camino
		int cell = 63 * 16, win = (63 - 42) * 16;
		Trazado.Aldeas a = (gx, gz) -> Trazado.pack(gx * cell + (int) (Trazado.azar(3, Trazado.pack(gx, gz), 2) * win),
				gz * cell + (int) (Trazado.azar(3, Trazado.pack(gx, gz), 3) * win));
		Trazado t = new Trazado(3, cell, 600, a, Trazado.Hitos.NINGUNO);
		for (int gx = -5; gx <= 5; gx++) {
			for (int gz = -5; gz <= 5; gz++) {
				assertEquals(0, t.vecinas(gx, gz).length);
			}
		}
		assertTrue(t.rutas(0, 0).isEmpty());
	}

	@Test
	void sinAldeasNoHayCaminos() {
		Trazado t = new Trazado(1, CELL, 2000, (gx, gz) -> Trazado.NONE, Trazado.Hitos.NINGUNO);
		for (int cx = -50; cx <= 50; cx += 7) {
			assertTrue(t.rutas(cx, cx * 3).isEmpty());
		}
	}

	@Test
	void determinista() {
		Trazado a = trazado(42, 2000), b = trazado(42, 2000), c = trazado(43, 2000);
		boolean distinta = false;
		for (long v : todas(a, 3)) {
			for (long w : a.vecinas(cell(v, true), cell(v, false))) {
				Trazado.Ruta r1 = a.ruta(v, w), r2 = b.ruta(w, v); // orden contrario y otra instancia: la misma ruta
				assertEquals(r1.vertices(), r2.vertices());
				for (int i = 0; i < r1.vertices(); i++) {
					assertEquals(r1.x(i), r2.x(i));
					assertEquals(r1.z(i), r2.z(i));
				}
				assertEquals(r1.farol, r2.farol);
				Trazado.Ruta r3 = new Trazado(43, CELL, 2000, aldeas(42, 0.2), Trazado.Hitos.NINGUNO).ruta(v, w);
				distinta |= r3.x(r3.vertices() / 2) != r1.x(r1.vertices() / 2);
			}
		}
		assertTrue(distinta, "la semilla no cambia el serpenteo");
		assertNotEquals(todas(a, 3), todas(c, 3));
	}

	@Test
	void rutaUneLasDosAldeasYSerpenteaPoco() {
		Trazado t = trazado(5, 2000);
		for (long v : todas(t, 3)) {
			for (long w : t.vecinas(cell(v, true), cell(v, false))) {
				Trazado.Ruta r = t.ruta(v, w);
				assertSame(r, t.ruta(w, v), "A→B y B→A son la misma ruta en memoria");
				long lo = Math.min(v, w), hi = Math.max(v, w);
				assertEquals(Trazado.px(lo), r.x(0), 1e-9);
				assertEquals(Trazado.pz(lo), r.z(0), 1e-9);
				assertEquals(Trazado.px(hi), r.x(r.vertices() - 1), 1e-9);
				assertEquals(Trazado.pz(hi), r.z(r.vertices() - 1), 1e-9);
				double recta = dist(v, w);
				assertTrue(r.longitud() >= recta - 1e-6 && r.longitud() <= recta * 1.15, "longitud " + r.longitud() + " para " + recta);
				for (int i = 1; i < r.vertices(); i++) {
					double seg = Math.hypot(r.x(i) - r.x(i - 1), r.z(i) - r.z(i - 1));
					assertTrue(seg <= Trazado.PASO * 1.6, "tramo de " + seg + " bloques");
				}
			}
		}
	}

	/** Columnas de camino de una ruta pintando chunk a chunk (instancia nueva por chunk: sin memoria compartida). */
	static Set<Long> porChunks(long seed, int maxDist, Trazado.Ruta r, int ancho) {
		Set<Long> out = new HashSet<>();
		int cx0 = Math.floorDiv((int) Math.floor(Math.min(r.x(0), r.x(r.vertices() - 1))) - 64, 16);
		int cx1 = Math.floorDiv((int) Math.ceil(Math.max(r.x(0), r.x(r.vertices() - 1))) + 64, 16);
		int cz0 = Math.floorDiv((int) Math.floor(Math.min(r.z(0), r.z(r.vertices() - 1))) - 64, 16);
		int cz1 = Math.floorDiv((int) Math.ceil(Math.max(r.z(0), r.z(r.vertices() - 1))) + 64, 16);
		for (int cx = cx0; cx <= cx1; cx++) {
			for (int cz = cz0; cz <= cz1; cz++) {
				Trazado t = trazado(seed, maxDist);
				List<Trazado.Ruta> rutas = new ArrayList<>();
				for (Trazado.Ruta x : t.rutas(cx, cz)) {
					if (x.desde == r.desde && x.hasta == r.hasta) {
						rutas.add(x);
					}
				}
				Trazado.Celda[] c = t.pintar(rutas, cx, cz, ancho);
				for (int i = 0; i < 256; i++) {
					if (c[i] != null) {
						out.add(Trazado.pack(cx * 16 + i / 16, cz * 16 + i % 16));
					}
				}
			}
		}
		return out;
	}

	@Test
	void fronterasDeChunkSinHuecos() {
		long seed = 11;
		Trazado t = trazado(seed, 2000);
		int probadas = 0;
		for (long v : todas(t, 1)) {
			for (long w : t.vecinas(cell(v, true), cell(v, false))) {
				if (v > w || probadas >= 3) {
					continue;
				}
				probadas++;
				Trazado.Ruta r = t.ruta(v, w);
				for (int ancho : new int[]{1, 3, 5}) {
					Set<Long> cols = porChunks(seed, 2000, r, ancho);
					// el eje de la ruta, muestreado cada cuarto de bloque, cae siempre en una columna pintada: sin huecos
					for (int i = 0; i + 1 < r.vertices(); i++) {
						for (double f = 0; f < 1; f += 0.25) {
							double x = r.x(i) + (r.x(i + 1) - r.x(i)) * f, z = r.z(i) + (r.z(i + 1) - r.z(i)) * f;
							assertTrue(cols.contains(Trazado.pack((int) Math.floor(x), (int) Math.floor(z))),
									"hueco en " + x + ", " + z + " (ancho " + ancho + ")");
						}
					}
					// 4-conexo: se puede andar de una aldea a otra sin saltar en diagonal
					assertTrue(conexo(cols, r), "camino partido (ancho " + ancho + ")");
				}
			}
		}
		assertTrue(probadas > 0);
	}

	private static boolean conexo(Set<Long> cols, Trazado.Ruta r) {
		long start = Trazado.pack((int) Math.floor(r.x(0)), (int) Math.floor(r.z(0)));
		long end = Trazado.pack((int) Math.floor(r.x(r.vertices() - 1)), (int) Math.floor(r.z(r.vertices() - 1)));
		Set<Long> seen = new HashSet<>();
		List<Long> stack = new ArrayList<>(List.of(start));
		while (!stack.isEmpty()) {
			long p = stack.removeLast();
			if (!cols.contains(p) || !seen.add(p)) {
				continue;
			}
			int x = Trazado.px(p), z = Trazado.pz(p);
			stack.add(Trazado.pack(x + 1, z));
			stack.add(Trazado.pack(x - 1, z));
			stack.add(Trazado.pack(x, z + 1));
			stack.add(Trazado.pack(x, z - 1));
		}
		return seen.contains(end);
	}

	@Test
	void pintarNoDependeDelChunkNiDelOrden() {
		long seed = 21;
		Trazado t = trazado(seed, 2000);
		// un chunk pintado solo y pintado después de sus vecinos (otra instancia, otro orden) da lo mismo
		for (long v : todas(t, 1)) {
			for (long w : t.vecinas(cell(v, true), cell(v, false))) {
				Trazado.Ruta r = t.ruta(v, w);
				int i = r.vertices() / 3;
				int cx = Math.floorDiv((int) r.x(i), 16), cz = Math.floorDiv((int) r.z(i), 16);
				Trazado u = trazado(seed, 2000);
				for (int dx = -2; dx <= 2; dx++) {
					for (int dz = -2; dz <= 2; dz++) {
						u.pintar(u.rutas(cx + dx, cz + dz), cx + dx, cz + dz, 3);
					}
				}
				Trazado.Celda[] a = t.pintar(t.rutas(cx, cz), cx, cz, 3), b = u.pintar(u.rutas(cx, cz), cx, cz, 3);
				for (int k = 0; k < 256; k++) {
					assertEquals(a[k] == null, b[k] == null);
				}
			}
		}
	}

	@Test
	void anchoDelCamino() {
		long seed = 13;
		Trazado t = trazado(seed, 2000);
		long v = todas(t, 0).getFirst();
		long w = t.vecinas(cell(v, true), cell(v, false))[0];
		Trazado.Ruta r = t.ruta(v, w);
		int prev = 0;
		for (int ancho = 1; ancho <= 5; ancho++) {
			int n = porChunks(seed, 2000, r, ancho).size();
			double porBloque = n / r.longitud();
			// con ancho 1 el núcleo unido por caras pone 1,5 columnas por bloque en las diagonales
			assertTrue(porBloque > ancho * 0.7 && porBloque < Math.max(ancho * 1.3, 1.65), "ancho " + ancho + ": " + porBloque + " columnas por bloque");
			assertTrue(n > prev);
			prev = n;
		}
	}

	// --- agua ---

	/** Ruta recta de prueba de 0,0 a 960,0 (vértices cada 16 bloques) con el fondo dado. */
	static Trazado.Ruta recta() {
		Trazado t = new Trazado(1, 100_000, 2000, (gx, gz) -> Trazado.NONE, Trazado.Hitos.NINGUNO);
		Trazado.Ruta r = t.ruta(Trazado.pack(0, 0), Trazado.pack(960, 0));
		assertTrue(r.vertices() > 50);
		return r;
	}

	/** Fondo de prueba: por la x del vértice, profundidad bajo el mar 63 (0 = tierra). */
	static Trazado.Fondo fondo(Map<int[], Integer> tramos) {
		return (x, z) -> {
			for (Map.Entry<int[], Integer> e : tramos.entrySet()) {
				if (x >= e.getKey()[0] && x < e.getKey()[1]) {
					return 63 - e.getValue();
				}
			}
			return 70;
		};
	}

	@Test
	void aguaPuentePasarelaYCorte() {
		Map<int[], Integer> m = new HashMap<>();
		m.put(new int[]{100, 140}, 6);    // río de 40 bloques y 6 de hondo: puente
		m.put(new int[]{300, 500}, 2);    // marisma de 200 bloques y 2 de hondo: pasarela
		m.put(new int[]{700, 900}, 9);    // lago de 200 bloques y 9 de hondo: se corta
		Trazado.Fondo f = fondo(m);
		Trazado.Ruta r = recta();
		for (int i = 0; i < r.vertices(); i++) {
			double x = r.x(i);
			Trazado.Agua a = r.agua(i, f, 63);
			Trazado.Agua esperado = x >= 100 && x < 140 ? Trazado.Agua.PUENTE : x >= 300 && x < 500 ? Trazado.Agua.PASARELA
					: x >= 700 && x < 900 ? Trazado.Agua.CORTE : Trazado.Agua.TIERRA;
			assertEquals(esperado, a, "vértice en x = " + x);
		}
	}

	@Test
	void nuncaCruzaAguaProfundaLarga() {
		// un tramo de agua honda más largo que un puente nunca se cruza, empiece donde empiece y mida lo que mida
		for (int start = 50; start < 400; start += 37) {
			for (int len = Trazado.PUENTE_MAX + 2 * Trazado.PASO + 1; len < 500; len += 53) {
				Map<int[], Integer> m = new HashMap<>();
				m.put(new int[]{start, start + len}, Trazado.PASARELA_PROFUNDIDAD + 1 + len % 7);
				Trazado.Fondo f = fondo(m);
				Trazado.Ruta r = recta();
				for (int i = 0; i < r.vertices(); i++) {
					if (f.en((int) Math.floor(r.x(i)), 0) < 63) {
						assertEquals(Trazado.Agua.CORTE, r.agua(i, f, 63), "cruza agua honda de " + len + " bloques en x = " + r.x(i));
					}
				}
			}
		}
	}

	@Test
	void aguaMismaDecisionEnTodoElTramoYPocasConsultas() {
		Map<int[], Integer> m = new HashMap<>();
		m.put(new int[]{200, 250}, 5);
		AtomicInteger calls = new AtomicInteger();
		Trazado.Fondo base = fondo(m);
		Trazado.Fondo f = (x, z) -> {
			calls.incrementAndGet();
			return base.en(x, z);
		};
		Trazado.Ruta r = recta();
		Set<Trazado.Agua> vistas = new HashSet<>();
		for (int i = 0; i < r.vertices(); i++) {
			if (r.x(i) >= 200 && r.x(i) < 250) {
				vistas.add(r.agua(i, f, 63));
			}
		}
		assertEquals(Set.of(Trazado.Agua.PUENTE), vistas);
		int first = calls.get();
		assertTrue(first <= 8, first + " consultas del fondo para un río de 50 bloques");
		for (int i = 0; i < r.vertices(); i++) {
			if (r.x(i) >= 200 && r.x(i) < 250) {
				r.agua(i, f, 63);
			}
		}
		assertEquals(first, calls.get(), "en memoria: no se vuelve a preguntar");
	}

	// --- farolas y carteles ---

	@Test
	void farolasYCartelesUnaVezYEnSuSitio() {
		long seed = 17;
		Trazado t = trazado(seed, 2000);
		long v = todas(t, 0).getFirst();
		long w = t.vecinas(cell(v, true), cell(v, false))[0];
		Trazado.Ruta r = t.ruta(v, w);
		List<Trazado.Marca> marcas = new ArrayList<>();
		Set<Long> camino = porChunks(seed, 2000, r, 3);
		for (int cx = -400; cx <= 400; cx++) {
			// solo los chunks cerca de la ruta (la caja), cada uno con su instancia
			int bx = cx * 16;
			if (bx < Math.min(r.x(0), r.x(r.vertices() - 1)) - 80 || bx > Math.max(r.x(0), r.x(r.vertices() - 1)) + 80) {
				continue;
			}
			for (int cz = -400; cz <= 400; cz++) {
				int bz = cz * 16;
				if (bz < Math.min(r.z(0), r.z(r.vertices() - 1)) - 80 || bz > Math.max(r.z(0), r.z(r.vertices() - 1)) + 80) {
					continue;
				}
				Trazado u = trazado(seed, 2000);
				List<Trazado.Ruta> rutas = u.rutas(cx, cz).stream().filter(x -> x.desde == r.desde && x.hasta == r.hasta).toList();
				for (Trazado.Marca mk : u.marcas(rutas, cx, cz, 3)) {
					assertTrue(Math.floorDiv(mk.x(), 16) == cx && Math.floorDiv(mk.z(), 16) == cz, "marca fuera de su chunk");
					marcas.add(mk);
				}
			}
		}
		List<Trazado.Marca> carteles = marcas.stream().filter(Trazado.Marca::cartel).toList();
		assertEquals(2, carteles.size(), "un cartel cerca de cada aldea");
		Set<Long> destinos = new HashSet<>();
		for (Trazado.Marca c : carteles) {
			destinos.add(c.destino());
			long origen = c.destino() == r.hasta ? r.desde : r.hasta;
			double aOrigen = Math.hypot(c.x() - Trazado.px(origen), c.z() - Trazado.pz(origen));
			assertTrue(aOrigen > Trazado.CARTEL_A - 30 && aOrigen < Trazado.CARTEL_A + 40, "cartel a " + aOrigen + " de su aldea");
			double aDestino = Math.hypot(c.x() - Trazado.px(c.destino()), c.z() - Trazado.pz(c.destino()));
			assertTrue(Math.abs(c.distancia() - aDestino) < aDestino * 0.15 + 20, "distancia " + c.distancia() + " frente a " + aDestino);
			assertTrue(c.rotacion() >= 0 && c.rotacion() < 16);
			// el letrero mira hacia el camino: un paso en la dirección de su cara se acerca al eje
			double ang = Math.toRadians(c.rotacion() * 22.5);
			double fx = -Math.sin(ang), fz = Math.cos(ang);
			assertTrue(cercaDeCamino(camino, c.x() + fx * 2.5, c.z() + fz * 2.5) || cercaDeCamino(camino, c.x() + fx * 3.5, c.z() + fz * 3.5),
					"el cartel no mira al camino");
		}
		assertEquals(Set.of(r.desde, r.hasta), destinos, "cada cartel señala la otra aldea");
		List<Trazado.Marca> farolas = marcas.stream().filter(x -> !x.cartel()).toList();
		double esperadas = (r.longitud() - Trazado.CARTEL_A) / (Trazado.PASO * Trazado.FAROLA_CADA);
		assertTrue(farolas.size() >= esperadas * 0.8 && farolas.size() <= esperadas * 1.2 + 2, farolas.size() + " farolas, se esperaban " + esperadas);
		Set<Long> pos = new HashSet<>();
		for (Trazado.Marca mk : marcas) {
			assertTrue(pos.add(Trazado.pack(mk.x(), mk.z())), "dos marcas en la misma columna");
			assertFalse(camino.contains(Trazado.pack(mk.x(), mk.z())), "marca encima del camino");
		}
	}

	private static boolean cercaDeCamino(Set<Long> camino, double x, double z) {
		return camino.contains(Trazado.pack((int) Math.floor(x), (int) Math.floor(z)));
	}

	@Test
	void flechaDelCartel() {
		// ruta de oeste a este por z = 0: el cartel cerca de la aldea del oeste señala la del este
		Trazado t = new Trazado(1, 100_000, 2000, (gx, gz) -> Trazado.NONE, Trazado.Hitos.NINGUNO);
		Trazado.Ruta r = t.ruta(Trazado.pack(0, 0), Trazado.pack(1200, 0));
		List<Trazado.Marca> all = new ArrayList<>();
		for (int cx = -2; cx <= 80; cx++) {
			for (int cz = -6; cz <= 6; cz++) {
				all.addAll(t.marcas(List.of(r), cx, cz, 3));
			}
		}
		for (Trazado.Marca c : all) {
			if (!c.cartel()) {
				continue;
			}
			double ang = Math.toRadians(c.rotacion() * 22.5);
			double fx = -Math.sin(ang), fz = Math.cos(ang); // cara del letrero; el lector mira en -f
			double rightX = fz, rightZ = -fx;              // derecha del lector
			double tx = Trazado.px(c.destino()) - c.x(), tz = Trazado.pz(c.destino()) - c.z();
			assertEquals(tx * rightX + tz * rightZ > 0, c.derecha(), "la flecha no señala el destino");
		}
	}

	@Test
	void puntoDePaso() {
		long hito = Trazado.pack(600, 200);
		Trazado t = new Trazado(1, 100_000, 2000, (gx, gz) -> Trazado.NONE, (ax, az, bx, bz) -> hito);
		Trazado.Ruta r = t.ruta(Trazado.pack(0, 0), Trazado.pack(1200, 0));
		boolean pasa = false;
		for (int i = 0; i < r.vertices(); i++) {
			pasa |= Math.hypot(r.x(i) - 600, r.z(i) - 200) < 1e-6;
		}
		assertTrue(pasa, "la ruta no pasa por el punto de paso");
		assertTrue(r.longitud() > 1200 * 1.05);
	}

	@Test
	void puntoDePasoConOrdenCanonico() {
		List<long[]> preguntas = new ArrayList<>();
		Trazado t = new Trazado(1, 100_000, 2000, (gx, gz) -> Trazado.NONE, (ax, az, bx, bz) -> {
			preguntas.add(new long[]{ax, az, bx, bz});
			return Trazado.NONE;
		});
		t.ruta(Trazado.pack(900, 50), Trazado.pack(0, 0));
		new Trazado(1, 100_000, 2000, (gx, gz) -> Trazado.NONE, (ax, az, bx, bz) -> {
			preguntas.add(new long[]{ax, az, bx, bz});
			return Trazado.NONE;
		}).ruta(Trazado.pack(0, 0), Trazado.pack(900, 50));
		assertArrayEquals(preguntas.get(0), preguntas.get(1), "el punto de paso se pregunta igual en los dos sentidos");
	}

	// --- nombres ---

	@Test
	void nombresDeterministasYQueCaben() {
		Set<String> vistos = new HashSet<>();
		for (int i = 0; i < 400; i++) {
			String[] a = Nombres.de(99, i * 1504, i * 777), b = Nombres.de(99, i * 1504, i * 777);
			assertArrayEquals(a, b);
			assertEquals(2, a.length);
			for (String s : a) {
				assertNotNull(s);
				assertTrue(s.length() <= 13, "no cabe en una línea de cartel: " + s);
			}
			vistos.add(a[0] + " " + a[1]);
		}
		assertTrue(vistos.size() > 150, "pocos nombres distintos: " + vistos.size());
		assertNotEquals(String.join(" ", Nombres.de(1, 0, 0)) + String.join(" ", Nombres.de(1, 1504, 0)) + String.join(" ", Nombres.de(1, 0, 1504)),
				String.join(" ", Nombres.de(2, 0, 0)) + String.join(" ", Nombres.de(2, 1504, 0)) + String.join(" ", Nombres.de(2, 0, 1504)));
	}

	@Test
	void unaRutaSoloEnLosChunksCercaDeSuEje() {
		long seed = 31;
		Trazado t = trazado(seed, 2000);
		long v = todas(t, 0).getFirst();
		long w = t.vecinas(cell(v, true), cell(v, false))[0];
		Trazado.Ruta r = t.ruta(v, w);
		Set<Long> cols = porChunks(seed, 2000, r, 5);
		int lejos = 0, cerca = 0;
		for (int cx = Math.floorDiv((int) Math.min(r.x(0), r.x(r.vertices() - 1)) - 200, 16); cx <= Math.floorDiv((int) Math.max(r.x(0), r.x(r.vertices() - 1)) + 200, 16); cx++) {
			for (int cz = Math.floorDiv((int) Math.min(r.z(0), r.z(r.vertices() - 1)) - 200, 16); cz <= Math.floorDiv((int) Math.max(r.z(0), r.z(r.vertices() - 1)) + 200, 16); cz++) {
				final int fx = cx, fz = cz;
				boolean listed = t.rutas(cx, cz).stream().anyMatch(x -> x == r);
				boolean painted = cols.stream().anyMatch(p -> Math.floorDiv(Trazado.px(p), 16) == fx && Math.floorDiv(Trazado.pz(p), 16) == fz);
				if (painted) {
					assertTrue(listed, "chunk con camino sin su ruta");
				}
				if (listed) {
					cerca++;
				} else {
					lejos++;
				}
			}
		}
		// la caja de una ruta en diagonal es mucho mayor que la franja de su eje: casi ningún chunk de la caja la recibe
		assertTrue(cerca < (r.longitud() / 16 + 2) * 4, cerca + " chunks reciben la ruta");
		assertTrue(lejos > cerca);
	}

	@Test
	void rutasDeUnChunkBaratas() {
		// la consulta de un chunk sin camino cerca, con las memorias llenas, es de microsegundos
		Trazado t = trazado(5, 2000);
		for (int cx = -100; cx <= 100; cx++) {
			t.rutas(cx, 7);
		}
		long t0 = System.nanoTime();
		int n = 0;
		for (int k = 0; k < 20; k++) {
			for (int cx = -100; cx <= 100; cx++) {
				n += t.rutas(cx, 7).size();
			}
		}
		double us = (System.nanoTime() - t0) / 1000.0 / (20 * 201);
		assertTrue(us < 200, us + " µs por chunk");
		assertTrue(n >= 0);
	}

	@Test
	void tramoCercanoParaLaRevision() {
		Trazado t = trazado(7, 2000);
		long p = t.tramoCercano(0, 0, 4);
		assertTrue(p != Trazado.NONE, "con aldeas cada 1.500 bloques hay alguna ruta cerca");
		// es el vértice central de una ruta entre dos aldeas vecinas, y la más cercana de las que se miran
		boolean deUnaRuta = false;
		double mejor = Double.MAX_VALUE;
		for (long a : todas(t, 5)) {
			int gx = Math.floorDiv(Trazado.px(a), CELL), gz = Math.floorDiv(Trazado.pz(a), CELL);
			if (Math.abs(gx) > 4 || Math.abs(gz) > 4) {
				continue;
			}
			for (long b : t.vecinas(gx, gz)) {
				Trazado.Ruta r = t.ruta(a, b);
				int m = r.vertices() / 2;
				long q = Trazado.pack((int) Math.round(r.x(m)), (int) Math.round(r.z(m)));
				deUnaRuta |= q == p;
				mejor = Math.min(mejor, Math.hypot(Trazado.px(q), Trazado.pz(q)));
			}
		}
		assertTrue(deUnaRuta);
		assertEquals(mejor, Math.hypot(Trazado.px(p), Trazado.pz(p)), 1e-9);
		assertEquals(p, trazado(7, 2000).tramoCercano(0, 0, 4), "determinista");
		// sin aldeas, nada
		Trazado vacio = new Trazado(7, CELL, 2000, (gx, gz) -> Trazado.NONE, Trazado.Hitos.NINGUNO);
		assertEquals(Trazado.NONE, vacio.tramoCercano(0, 0, 4));
	}
}
