package io.github.albertosa23.heraldia.mines;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.block.Rotation;
import org.jspecify.annotations.Nullable;

/**
 * Busca una ladera para la boca de una mina (lógica pura: el terreno llega por {@link Terrain}, en el juego el mapa de
 * alturas de generación con caché, {@code common/Heights}). La misma idea que la ciudadela (delante de la puerta llano
 * y seco, detrás el monte), pero barata, porque las minas son frecuentes:
 * <ol>
 * <li>cinco columnas (el centro y cuatro a {@link #RADIUS} bloques) dan la pendiente; si el terreno no sube hacia ningún
 * lado (llanura, meseta), se acaba ahí;</li>
 * <li>la boca mira cuesta abajo (las dos direcciones que más suben, como mucho) y se prueba en tres puntos a lo largo de
 * la pendiente: el patio (nueve muestras de su caja) seco y casi llano ({@link #DROP}), detrás de la boca (nueve
 * muestras a 3-10 bloques) el monte al menos {@link #RISE_MIN} más alto de media y nunca menos de {@link #HIGH_MIN}
 * sobre el patio, y encima de la galería (muestras {@code ceiling} de la plantilla) terreno por encima de su casco;</li>
 * <li>gana la de más subida (hasta {@link #RISE_CAP}) y menos desnivel en el patio.</li>
 * </ol>
 * Con /place (forzada) se coloca siempre: la mejor que haya o, si no, mirando cuesta abajo en el centro.
 */
public final class Hillside {
	public static final int RADIUS = 16, DROP = 4, RISE_MIN = 5, HIGH_MIN = 3, RISE_CAP = 16, STEP = 8;
	/** Muestras detrás de la boca (dx, dz en coordenadas de la plantilla, desde la boca). */
	/** Orden de las nueve muestras del patio (índices en {x0, x1, centro} × {z0, z1, centro}): esquinas, bordes y centro. */
	private static final int[][] YARD = {{0, 0}, {1, 1}, {0, 1}, {1, 0}, {2, 0}, {2, 1}, {0, 2}, {1, 2}, {2, 2}};
	private static final int[][] BEHIND = {{-2, 3}, {0, 3}, {2, 3}, {-2, 6}, {0, 6}, {2, 6}, {-2, 10}, {0, 10}, {2, 10}};
	/** Giros con los que el fondo de la plantilla (+z) mira al sur, al oeste, al norte y al este. */
	private static final Rotation[] ROTATION = {Rotation.NONE, Rotation.CLOCKWISE_90, Rotation.CLOCKWISE_180, Rotation.COUNTERCLOCKWISE_90};
	private static final int[][] DIR = {{0, 1}, {-1, 0}, {0, -1}, {1, 0}};

	private Hillside() {
	}

	/** Terreno de generación: los pies sobre el suelo firme (sin contar el agua) y si hay agua encima. */
	public interface Terrain {
		int ground(int x, int z);

		boolean water(int x, int z);
	}

	/**
	 * Forma de la plantilla: la boca (el bloque del suelo bajo su centro), la caja del patio y las muestras de techo
	 * (x, z y cuánto por encima o por debajo de los pies de la boca debe quedar el suelo), en coordenadas de la plantilla.
	 */
	public record Shape(BlockPos entry, int yardX0, int yardZ0, int yardX1, int yardZ1, List<int[]> ceiling) {
	}

	/** Sitio elegido: giro, boca (x, z), pies de la boca y nota. */
	public record Site(Rotation rotation, int x, int z, int feet, double note) {
	}

	/** Posición del mundo del punto (lx, lz) de la plantilla con la boca en (bx, bz) y ese giro. */
	public static int[] world(Shape f, Rotation rotation, int bx, int bz, int lx, int lz) {
		BlockPos d = new BlockPos(lx - f.entry().getX(), 0, lz - f.entry().getZ()).rotate(rotation);
		return new int[] {bx + d.getX(), bz + d.getZ()};
	}

	/**
	 * La mejor ladera junto a (cx, cz), o null. minY es la altura mínima del mundo: la plantilla no baja de minY + 2.
	 */
	public static @Nullable Site search(Terrain t, int cx, int cz, Shape f, int minY, boolean forced) {
		int h0 = t.ground(cx, cz);
		int[] side = new int[4];
		for (int k = 0; k < 4; k++) {
			side[k] = t.ground(cx + DIR[k][0] * RADIUS, cz + DIR[k][1] * RADIUS);
		}
		List<Integer> dirs = new ArrayList<>(List.of(0, 1, 2, 3));
		dirs.sort(Comparator.comparingInt(k -> -(side[k] - side[(k + 2) % 4])));
		Site best = null;
		for (int n = 0; n < 2; n++) {
			int k = dirs.get(n);
			if (side[k] - side[(k + 2) % 4] < RISE_MIN && !forced) {
				break;                                  // no sube lo bastante hacia ningún otro lado
			}
			for (int o : new int[] {0, -STEP, STEP}) {
				int bx = cx + DIR[k][0] * o, bz = cz + DIR[k][1] * o;
				Site s = evaluateAt(t, f, ROTATION[k], bx, bz, minY, best == null ? Double.NEGATIVE_INFINITY : best.note());
				if (s != null && (best == null || s.note() > best.note())) {
					best = s;
				}
			}
		}
		if (best == null && forced) {
			best = new Site(ROTATION[dirs.get(0)], cx, cz, h0, 0);
		}
		return best;
	}

	/**
	 * Nota de la boca en (bx, bz) con ese giro, o null si el terreno no sirve (o no puede ganar a `superar`). Las
	 * comprobaciones que descartan van de la más barata a la más cara (el agua pide una segunda altura de la columna, la
	 * superficie, y solo hace falta mirarla si todo lo demás vale); como todas dan null, el orden no cambia el resultado.
	 */
	static @Nullable Site evaluateAt(Terrain t, Shape f, Rotation rotation, int bx, int bz, int minY, double beat) {
		if (RISE_CAP <= beat) {
			return null;                                // la nota nunca pasa de SUBIDA_TOPE
		}
		int[] xs = {f.yardX0(), f.yardX1(), (f.yardX0() + f.yardX1()) / 2};
		int[] zs = {f.yardZ0(), f.yardZ1(), (f.yardZ0() + f.yardZ1()) / 2};
		int[] ahead = new int[9];
		int[][] yard = new int[9][];
		int min = Integer.MAX_VALUE, max = Integer.MIN_VALUE;
		for (int i = 0; i < 9; i++) {
			int[] ij = YARD[i];                        // las esquinas primero: lo que más se separa
			int[] p = world(f, rotation, bx, bz, xs[ij[0]], zs[ij[1]]);
			yard[i] = p;
			int h = t.ground(p[0], p[1]);
			ahead[i] = h;
			min = Math.min(min, h);
			max = Math.max(max, h);
			if (max - min > DROP) {
				return null;                            // patio en cuesta (sin mirar el resto de sus columnas)
			}
		}
		int[] order = ahead.clone();
		java.util.Arrays.sort(order);
		int drop = order[8] - order[0];
		if (RISE_CAP - drop <= beat) {
			return null;                                // ni con el monte más alto ganaría a la que ya hay
		}
		int feet = order[4];                            // la mediana: el patio corta lo que sobra y su cimiento rellena
		if (feet - 1 - f.entry().getY() < minY + 2) {
			return null;
		}
		double sum = 0;
		for (int[] d : BEHIND) {
			int[] p = world(f, rotation, bx, bz, f.entry().getX() + d[0], f.entry().getZ() + d[1]);
			int h = t.ground(p[0], p[1]);
			if (h < feet + HIGH_MIN) {
				return null;                            // detrás de la boca no hay monte
			}
			sum += h - feet;
		}
		double rise = sum / BEHIND.length;
		if (rise < RISE_MIN) {
			return null;
		}
		double note = Math.min(rise, RISE_CAP) - drop;
		if (note <= beat) {
			return null;
		}
		for (int[] m : f.ceiling()) {
			int[] p = world(f, rotation, bx, bz, m[0], m[1]);
			if (t.ground(p[0], p[1]) < feet + m[2]) {
				return null;                            // el casco de la galería asomaría
			}
		}
		for (int[] p : yard) {
			if (t.water(p[0], p[1])) {
				return null;                            // agua en el patio
			}
		}
		return new Site(rotation, bx, bz, feet, note);
	}
}
