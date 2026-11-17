package io.github.albertosa23.heraldia.costa;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import net.minecraft.core.Direction;
import org.jspecify.annotations.Nullable;

/**
 * Búsqueda de la orilla de un faro o un naufragio (lógica pura: el terreno llega como funciones, así que se prueba con
 * mapas de alturas sintéticos; en el juego, la caché compartida de alturas de generación).
 *
 * <p>Como el puerto de las aldeas ({@code aldeas/Orilla}): el fondo en una malla de {@link #PASO} bloques dentro de un
 * círculo de {@link #RADIO} alrededor del centro de la candidata, de dentro afuera; cada nudo de tierra baja con un vecino
 * de agua da una orilla candidata hacia ese vecino, afinada con una búsqueda binaria (el último bloque de tierra). En
 * cada candidata se mira la huella de la plantilla girada para que su +z mire al mar (x a lo ancho, z hacia el mar,
 * relativas al ancla): la de tierra detrás y la de mar delante, con lo que pide cada {@link Modo}. El faro, además,
 * prefiere los cabos: de las {@link #VALIDAS_FARO} primeras orillas válidas, la que tiene más agua alrededor a
 * {@link #CABO} bloques. Los demás, la primera válida (la más cercana al centro). Cada columna se pide una vez como
 * mucho a la caché; las comprobaciones salen a la primera muestra que falla.
 */
public final class Orilla {
	/** Malla de la búsqueda, su alcance y el paso de las muestras de la huella (bloques). */
	static final int PASO = 8, RADIO = 32, MUESTRA = 5;
	/** Orillas válidas que mira el faro antes de quedarse con la más «cabo», y a qué distancia mira el agua de alrededor. */
	static final int VALIDAS_FARO = 4, CABO = 24, RUMBOS = 16;
	/** Fracción mínima de las muestras de mar que deben cumplir (bajíos con alguna roca, olas de la orilla). */
	static final double MAR_MINIMO = 0.8;
	private static final List<int[]> NUDOS = new ArrayList<>();
	private static final int[][] RUMBO = new int[RUMBOS][];

	static {
		for (int dx = -RADIO; dx <= RADIO; dx += PASO) {
			for (int dz = -RADIO; dz <= RADIO; dz += PASO) {
				if (dx * dx + dz * dz <= RADIO * RADIO) {
					NUDOS.add(new int[]{dx, dz});
				}
			}
		}
		NUDOS.sort(Comparator.<int[]>comparingInt(c -> c[0] * c[0] + c[1] * c[1]).thenComparingInt(c -> c[0]).thenComparingInt(c -> c[1]));
		for (int i = 0; i < RUMBOS; i++) {
			double a = 2 * Math.PI * i / RUMBOS;
			RUMBO[i] = new int[]{(int) Math.round(Math.cos(a) * CABO), (int) Math.round(Math.sin(a) * CABO)};
		}
	}

	private Orilla() {
	}

	/**
	 * Qué pide cada variante (el suelo es la primera altura libre sobre el fondo, sin contar el agua; sea, el nivel del mar):
	 * <ul>
	 * <li>FARO: tierra seca, de sea + 1 a sea + 6 y con 4 bloques de desnivel como mucho (la plataforma, a la altura
	 * de lo más alto, y lo demás con cimientos); mar con agua de 2 bloques de hondo al menos bajo el embarcadero;</li>
	 * <li>ENCALLADO: la proa en la orilla (suelo de sea - 1 a sea + 3) y la popa en un bajío (agua, de 1 a 6 de hondo);</li>
	 * <li>HUNDIDO: tierra de verdad junto a la orilla y el casco entero en aguas de 3 a 9 de hondo.</li>
	 * </ul>
	 */
	public enum Modo {
		FARO, ENCALLADO, HUNDIDO;

		public static Modo de(String s) {
			return valueOf(s.toUpperCase(Locale.ROOT));
		}
	}

	/** El terreno: suelo (primera altura libre sin contar el agua) y si hay agua en la columna. */
	public interface Terreno {
		int suelo(int x, int z);

		boolean agua(int x, int z);
	}

	/** Huellas de tierra y de mar {x0, z0, x1, z1}, relativas al ancla (x a lo ancho, z hacia el mar). */
	public record Forma(Modo modo, int[] tierra, int[] mar) {
	}

	/** Orilla elegida: el ancla (x, z), la dirección al mar, la altura de la fila 0 (solo el faro; si no, -1) y su nota. */
	public record Sitio(int x, int z, Direction mar, int y, int nota) {
	}

	/** Busca la orilla alrededor de (cx, cz); null si no hay ninguna que sirva. */
	public static @Nullable Sitio buscar(Terreno t, int sea, int cx, int cz, Forma f) {
		Sitio mejor = null;
		int validas = 0;
		List<Long> vistas = new ArrayList<>();
		for (int[] n : NUDOS) {
			int nx = cx + n[0], nz = cz + n[1];
			if (t.agua(nx, nz) || t.suelo(nx, nz) > sea + 10) {
				continue;                                  // agua o tierra alta: no es una orilla
			}
			for (Direction d : Direction.Plane.HORIZONTAL) {
				if (!t.agua(nx + d.getStepX() * PASO, nz + d.getStepZ() * PASO)) {
					continue;
				}
				int lo = 0, hi = PASO;                    // el último bloque de tierra entre el nudo y su vecino de agua
				while (hi - lo > 1) {
					int mid = (lo + hi) >>> 1;
					if (t.agua(nx + d.getStepX() * mid, nz + d.getStepZ() * mid)) {
						hi = mid;
					} else {
						lo = mid;
					}
				}
				int px = nx + d.getStepX() * lo, pz = nz + d.getStepZ() * lo;
				long clave = ((long) px << 34) ^ ((long) pz << 4) ^ d.ordinal();
				if (vistas.contains(clave)) {
					continue;
				}
				vistas.add(clave);
				Sitio s = evaluar(t, sea, px, pz, d, f);
				if (s == null) {
					continue;
				}
				if (f.modo() != Modo.FARO) {
					return s;
				}
				if (mejor == null || s.nota() > mejor.nota()) {
					mejor = s;
				}
				if (++validas >= VALIDAS_FARO) {
					return mejor;
				}
			}
		}
		return mejor;
	}

	/** La huella con el ancla en (px, pz) y el +z de la plantilla hacia d; null si no sirve. Pública para las pruebas. */
	public static @Nullable Sitio evaluar(Terreno t, int sea, int px, int pz, Direction d, Forma f) {
		Direction e = d.getCounterClockWise();           // el +x de la plantilla girada
		int[] tr = f.tierra(), mr = f.mar();
		int min = Integer.MAX_VALUE, max = Integer.MIN_VALUE;
		for (int s = tr[0]; s <= tr[2]; s = siguiente(s, tr[2])) {
			for (int k = tr[1]; k <= tr[3]; k = siguiente(k, tr[3])) {
				int x = px + d.getStepX() * k + e.getStepX() * s, z = pz + d.getStepZ() * k + e.getStepZ() * s;
				int suelo = t.suelo(x, z);
				boolean ok = switch (f.modo()) {
					case FARO -> !t.agua(x, z) && suelo >= sea + 1 && suelo <= sea + 6;
					case ENCALLADO -> suelo >= sea - 1 && suelo <= sea + 3;
					case HUNDIDO -> !t.agua(x, z) && suelo <= sea + 10;
				};
				if (!ok) {
					return null;
				}
				min = Math.min(min, suelo);
				max = Math.max(max, suelo);
			}
		}
		if (f.modo() == Modo.FARO && max - min > 4) {
			return null;
		}
		int total = 0, bien = 0;
		for (int s = mr[0]; s <= mr[2]; s = siguiente(s, mr[2])) {
			for (int k = mr[1]; k <= mr[3]; k = siguiente(k, mr[3])) {
				int x = px + d.getStepX() * k + e.getStepX() * s, z = pz + d.getStepZ() * k + e.getStepZ() * s;
				total++;
				if (t.agua(x, z)) {
					int suelo = t.suelo(x, z);
					boolean ok = switch (f.modo()) {
						case FARO -> suelo <= sea - 2;
						case ENCALLADO -> suelo >= sea - 6 && suelo <= sea - 1;
						case HUNDIDO -> suelo >= sea - 9 && suelo <= sea - 3;
					};
					if (ok) {
						bien++;
					}
				}
				if (total - bien > (1 - MAR_MINIMO) * cuantas(mr)) {
					return null;                          // ya no llega al mínimo
				}
			}
		}
		if (f.modo() != Modo.FARO) {
			return new Sitio(px, pz, d, -1, 0);
		}
		int agua = 0;
		for (int[] r : RUMBO) {
			if (t.agua(px + r[0], pz + r[1])) {
				agua++;
			}
		}
		return new Sitio(px, pz, d, Math.max(max - 1, sea), agua);
	}

	/** Paso de las muestras de una huella: cada MUESTRA bloques y siempre el último. */
	private static int siguiente(int v, int fin) {
		return v == fin ? fin + 1 : Math.min(v + MUESTRA, fin);
	}

	/** Muestras de una huella. */
	static int cuantas(int[] r) {
		return pasos(r[0], r[2]) * pasos(r[1], r[3]);
	}

	private static int pasos(int a, int b) {
		int n = 0;
		for (int v = a; v <= b; v = siguiente(v, b)) {
			n++;
		}
		return n;
	}
}
