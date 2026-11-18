package io.github.albertosa23.heraldia.coast;

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
 * <p>Como el puerto de las aldeas ({@code villages/Shoreline}): el fondo en una malla de {@link #STEP} bloques dentro de un
 * círculo de {@link #RADIUS} alrededor del centro de la candidata, de dentro afuera; cada nudo de tierra baja con un vecino
 * de agua da una orilla candidata hacia ese vecino, afinada con una búsqueda binaria (el último bloque de tierra). En
 * cada candidata se mira la huella de la plantilla girada para que su +z mire al mar (x a lo ancho, z hacia el mar,
 * relativas al ancla): la de tierra detrás y la de mar delante, con lo que pide cada {@link Mode}. El faro, además,
 * prefiere los cabos: de las {@link #LIGHTHOUSE_VALID} primeras orillas válidas, la que tiene más agua alrededor a
 * {@link #CAPE} bloques. Los demás, la primera válida (la más cercana al centro). Cada columna se pide una vez como
 * mucho a la caché; las comprobaciones salen a la primera muestra que falla.
 */
public final class Shoreline {
	/** Malla de la búsqueda, su alcance y el paso de las muestras de la huella (bloques). */
	static final int STEP = 8, RADIUS = 32, SAMPLE = 5;
	/** Orillas válidas que mira el faro antes de quedarse con la más «cabo», y a qué distancia mira el agua de alrededor. */
	static final int LIGHTHOUSE_VALID = 4, CAPE = 24, HEADINGS = 16;
	/** Fracción mínima de las muestras de mar que deben cumplir (bajíos con alguna roca, olas de la orilla). */
	static final double MIN_SEA = 0.8;
	private static final List<int[]> KNOTS = new ArrayList<>();
	private static final int[][] BEARING = new int[HEADINGS][];

	static {
		for (int dx = -RADIUS; dx <= RADIUS; dx += STEP) {
			for (int dz = -RADIUS; dz <= RADIUS; dz += STEP) {
				if (dx * dx + dz * dz <= RADIUS * RADIUS) {
					KNOTS.add(new int[]{dx, dz});
				}
			}
		}
		KNOTS.sort(Comparator.<int[]>comparingInt(c -> c[0] * c[0] + c[1] * c[1]).thenComparingInt(c -> c[0]).thenComparingInt(c -> c[1]));
		for (int i = 0; i < HEADINGS; i++) {
			double a = 2 * Math.PI * i / HEADINGS;
			BEARING[i] = new int[]{(int) Math.round(Math.cos(a) * CAPE), (int) Math.round(Math.sin(a) * CAPE)};
		}
	}

	private Shoreline() {
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
	public enum Mode {
		LIGHTHOUSE("faro"), STRANDED("encallado"), SUNKEN("hundido");

		/** Saved id (files, NBT and translation keys): never renamed. */
		public final String id;

		Mode(String id) {
			this.id = id;
		}
		public static Mode of(String id) {
			for (Mode t : values()) {
				if (t.id.equals(id)) {
					return t;
				}
			}
			throw new IllegalArgumentException("No coast mode " + id);
		}
	}

	/** El terreno: suelo (primera altura libre sin contar el agua) y si hay agua en la columna. */
	public interface Terrain {
		int ground(int x, int z);

		boolean water(int x, int z);
	}

	/** Huellas de tierra y de mar {x0, z0, x1, z1}, relativas al ancla (x a lo ancho, z hacia el mar). */
	public record Shape(Mode mode, int[] land, int[] seaSide) {
	}

	/** Orilla elegida: el ancla (x, z), la dirección al mar, la altura de la fila 0 (solo el faro; si no, -1) y su nota. */
	public record Site(int x, int z, Direction seaSide, int y, int note) {
	}

	/** Busca la orilla alrededor de (cx, cz); null si no hay ninguna que sirva. */
	public static @Nullable Site search(Terrain t, int sea, int cx, int cz, Shape f) {
		Site best = null;
		int valid = 0;
		List<Long> seen = new ArrayList<>();
		for (int[] n : KNOTS) {
			int nx = cx + n[0], nz = cz + n[1];
			if (t.water(nx, nz) || t.ground(nx, nz) > sea + 10) {
				continue;                                  // agua o tierra alta: no es una orilla
			}
			for (Direction d : Direction.Plane.HORIZONTAL) {
				if (!t.water(nx + d.getStepX() * STEP, nz + d.getStepZ() * STEP)) {
					continue;
				}
				int lo = 0, hi = STEP;                    // el último bloque de tierra entre el nudo y su vecino de agua
				while (hi - lo > 1) {
					int mid = (lo + hi) >>> 1;
					if (t.water(nx + d.getStepX() * mid, nz + d.getStepZ() * mid)) {
						hi = mid;
					} else {
						lo = mid;
					}
				}
				int px = nx + d.getStepX() * lo, pz = nz + d.getStepZ() * lo;
				long key = ((long) px << 34) ^ ((long) pz << 4) ^ d.ordinal();
				if (seen.contains(key)) {
					continue;
				}
				seen.add(key);
				Site s = evaluateAt(t, sea, px, pz, d, f);
				if (s == null) {
					continue;
				}
				if (f.mode() != Mode.LIGHTHOUSE) {
					return s;
				}
				if (best == null || s.note() > best.note()) {
					best = s;
				}
				if (++valid >= LIGHTHOUSE_VALID) {
					return best;
				}
			}
		}
		return best;
	}

	/** La huella con el ancla en (px, pz) y el +z de la plantilla hacia d; null si no sirve. Pública para las pruebas. */
	public static @Nullable Site evaluateAt(Terrain t, int sea, int px, int pz, Direction d, Shape f) {
		Direction e = d.getCounterClockWise();           // el +x de la plantilla girada
		int[] tr = f.land(), mr = f.seaSide();
		int min = Integer.MAX_VALUE, max = Integer.MIN_VALUE;
		for (int s = tr[0]; s <= tr[2]; s = next(s, tr[2])) {
			for (int k = tr[1]; k <= tr[3]; k = next(k, tr[3])) {
				int x = px + d.getStepX() * k + e.getStepX() * s, z = pz + d.getStepZ() * k + e.getStepZ() * s;
				int ground = t.ground(x, z);
				boolean ok = switch (f.mode()) {
					case LIGHTHOUSE -> !t.water(x, z) && ground >= sea + 1 && ground <= sea + 6;
					case STRANDED -> ground >= sea - 1 && ground <= sea + 3;
					case SUNKEN -> !t.water(x, z) && ground <= sea + 10;
				};
				if (!ok) {
					return null;
				}
				min = Math.min(min, ground);
				max = Math.max(max, ground);
			}
		}
		if (f.mode() == Mode.LIGHTHOUSE && max - min > 4) {
			return null;
		}
		int total = 0, good = 0;
		for (int s = mr[0]; s <= mr[2]; s = next(s, mr[2])) {
			for (int k = mr[1]; k <= mr[3]; k = next(k, mr[3])) {
				int x = px + d.getStepX() * k + e.getStepX() * s, z = pz + d.getStepZ() * k + e.getStepZ() * s;
				total++;
				if (t.water(x, z)) {
					int ground = t.ground(x, z);
					boolean ok = switch (f.mode()) {
						case LIGHTHOUSE -> ground <= sea - 2;
						case STRANDED -> ground >= sea - 6 && ground <= sea - 1;
						case SUNKEN -> ground >= sea - 9 && ground <= sea - 3;
					};
					if (ok) {
						good++;
					}
				}
				if (total - good > (1 - MIN_SEA) * howMany(mr)) {
					return null;                          // ya no llega al mínimo
				}
			}
		}
		if (f.mode() != Mode.LIGHTHOUSE) {
			return new Site(px, pz, d, -1, 0);
		}
		int water = 0;
		for (int[] r : BEARING) {
			if (t.water(px + r[0], pz + r[1])) {
				water++;
			}
		}
		return new Site(px, pz, d, Math.max(max - 1, sea), water);
	}

	/** Paso de las muestras de una huella: cada MUESTRA bloques y siempre el último. */
	private static int next(int v, int end) {
		return v == end ? end + 1 : Math.min(v + SAMPLE, end);
	}

	/** Muestras de una huella. */
	static int howMany(int[] r) {
		return steps(r[0], r[2]) * steps(r[1], r[3]);
	}

	private static int steps(int a, int b) {
		int n = 0;
		for (int v = a; v <= b; v = next(v, b)) {
			n++;
		}
		return n;
	}
}
