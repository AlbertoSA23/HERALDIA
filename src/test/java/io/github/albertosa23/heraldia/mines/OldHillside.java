package io.github.albertosa23.heraldia.mines;

import io.github.albertosa23.heraldia.mines.Hillside.Shape;
import io.github.albertosa23.heraldia.mines.Hillside.Site;
import io.github.albertosa23.heraldia.mines.Hillside.Terrain;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.block.Rotation;
import org.jspecify.annotations.Nullable;

/**
 * Copia literal de la búsqueda de ladera de la 0.1.0 (antes de T36), para comparar en MinasDeterminismoTest. Busca una ladera para la boca de una mina (lógica pura: el terreno llega por {@link Terrain}, en el juego el mapa de
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
final class OldHillside {
	public static final int RADIUS = 16, DROP = 4, RISE_MIN = 5, HIGH_MIN = 3, RISE_CAP = 16, STEP = 8;
	/** Muestras detrás de la boca (dx, dz en coordenadas de la plantilla, desde la boca). */
	private static final int[][] BEHIND = {{-2, 3}, {0, 3}, {2, 3}, {-2, 6}, {0, 6}, {2, 6}, {-2, 10}, {0, 10}, {2, 10}};
	/** Giros con los que el fondo de la plantilla (+z) mira al sur, al oeste, al norte y al este. */
	private static final Rotation[] ROTATION = {Rotation.NONE, Rotation.CLOCKWISE_90, Rotation.CLOCKWISE_180, Rotation.COUNTERCLOCKWISE_90};
	private static final int[][] DIR = {{0, 1}, {-1, 0}, {0, -1}, {1, 0}};

	private OldHillside() {
	}


	/**
	 * Forma de la plantilla: la boca (el bloque del suelo bajo su centro), la caja del patio y las muestras de techo
	 * (x, z y cuánto por encima o por debajo de los pies de la boca debe quedar el suelo), en coordenadas de la plantilla.
	 */

	/** Sitio elegido: giro, boca (x, z), pies de la boca y nota. */

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

	/** Nota de la boca en (bx, bz) con ese giro, o null si el terreno no sirve (o no puede ganar a `superar`). */
	static @Nullable Site evaluateAt(Terrain t, Shape f, Rotation rotation, int bx, int bz, int minY, double beat) {
		int[] xs = {f.yardX0(), (f.yardX0() + f.yardX1()) / 2, f.yardX1()};
		int[] zs = {f.yardZ0(), (f.yardZ0() + f.yardZ1()) / 2, f.yardZ1()};
		int[] ahead = new int[9];
		int i = 0;
		for (int lx : xs) {
			for (int lz : zs) {
				int[] p = world(f, rotation, bx, bz, lx, lz);
				if (t.water(p[0], p[1])) {
					return null;                        // agua en el patio
				}
				ahead[i++] = t.ground(p[0], p[1]);
			}
		}
		int[] order = ahead.clone();
		java.util.Arrays.sort(order);
		int drop = order[8] - order[0];
		if (drop > DROP) {
			return null;
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
		return new Site(rotation, bx, bz, feet, note);
	}
}
