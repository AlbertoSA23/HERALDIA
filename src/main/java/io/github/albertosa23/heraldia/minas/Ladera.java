package io.github.albertosa23.heraldia.minas;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.block.Rotation;
import org.jspecify.annotations.Nullable;

/**
 * Busca una ladera para la boca de una mina (lógica pura: el terreno llega por {@link Terreno}, en el juego el mapa de
 * alturas de generación con caché, {@code comun/Alturas}). La misma idea que la ciudadela (delante de la puerta llano
 * y seco, detrás el monte), pero barata, porque las minas son frecuentes:
 * <ol>
 * <li>cinco columnas (el centro y cuatro a {@link #RADIO} bloques) dan la pendiente; si el terreno no sube hacia ningún
 * lado (llanura, meseta), se acaba ahí;</li>
 * <li>la boca mira cuesta abajo (las dos direcciones que más suben, como mucho) y se prueba en tres puntos a lo largo de
 * la pendiente: el patio (nueve muestras de su caja) seco y casi llano ({@link #DESNIVEL}), detrás de la boca (nueve
 * muestras a 3-10 bloques) el monte al menos {@link #SUBIDA_MIN} más alto de media y nunca menos de {@link #ALTO_MIN}
 * sobre el patio, y encima de la galería (muestras {@code techo} de la plantilla) terreno por encima de su casco;</li>
 * <li>gana la de más subida (hasta {@link #SUBIDA_TOPE}) y menos desnivel en el patio.</li>
 * </ol>
 * Con /place (forzada) se coloca siempre: la mejor que haya o, si no, mirando cuesta abajo en el centro.
 */
public final class Ladera {
	public static final int RADIO = 16, DESNIVEL = 4, SUBIDA_MIN = 5, ALTO_MIN = 3, SUBIDA_TOPE = 16, PASO = 8;
	/** Muestras detrás de la boca (dx, dz en coordenadas de la plantilla, desde la boca). */
	/** Orden de las nueve muestras del patio (índices en {x0, x1, centro} × {z0, z1, centro}): esquinas, bordes y centro. */
	private static final int[][] PATIO = {{0, 0}, {1, 1}, {0, 1}, {1, 0}, {2, 0}, {2, 1}, {0, 2}, {1, 2}, {2, 2}};
	private static final int[][] DETRAS = {{-2, 3}, {0, 3}, {2, 3}, {-2, 6}, {0, 6}, {2, 6}, {-2, 10}, {0, 10}, {2, 10}};
	/** Giros con los que el fondo de la plantilla (+z) mira al sur, al oeste, al norte y al este. */
	private static final Rotation[] GIRO = {Rotation.NONE, Rotation.CLOCKWISE_90, Rotation.CLOCKWISE_180, Rotation.COUNTERCLOCKWISE_90};
	private static final int[][] DIR = {{0, 1}, {-1, 0}, {0, -1}, {1, 0}};

	private Ladera() {
	}

	/** Terreno de generación: los pies sobre el suelo firme (sin contar el agua) y si hay agua encima. */
	public interface Terreno {
		int suelo(int x, int z);

		boolean agua(int x, int z);
	}

	/**
	 * Forma de la plantilla: la boca (el bloque del suelo bajo su centro), la caja del patio y las muestras de techo
	 * (x, z y cuánto por encima o por debajo de los pies de la boca debe quedar el suelo), en coordenadas de la plantilla.
	 */
	public record Forma(BlockPos entrada, int patioX0, int patioZ0, int patioX1, int patioZ1, List<int[]> techo) {
	}

	/** Sitio elegido: giro, boca (x, z), pies de la boca y nota. */
	public record Sitio(Rotation giro, int x, int z, int pies, double nota) {
	}

	/** Posición del mundo del punto (lx, lz) de la plantilla con la boca en (bx, bz) y ese giro. */
	public static int[] mundo(Forma f, Rotation giro, int bx, int bz, int lx, int lz) {
		BlockPos d = new BlockPos(lx - f.entrada().getX(), 0, lz - f.entrada().getZ()).rotate(giro);
		return new int[] {bx + d.getX(), bz + d.getZ()};
	}

	/**
	 * La mejor ladera junto a (cx, cz), o null. minY es la altura mínima del mundo: la plantilla no baja de minY + 2.
	 */
	public static @Nullable Sitio buscar(Terreno t, int cx, int cz, Forma f, int minY, boolean forzada) {
		int h0 = t.suelo(cx, cz);
		int[] lado = new int[4];
		for (int k = 0; k < 4; k++) {
			lado[k] = t.suelo(cx + DIR[k][0] * RADIO, cz + DIR[k][1] * RADIO);
		}
		List<Integer> dirs = new ArrayList<>(List.of(0, 1, 2, 3));
		dirs.sort(Comparator.comparingInt(k -> -(lado[k] - lado[(k + 2) % 4])));
		Sitio mejor = null;
		for (int n = 0; n < 2; n++) {
			int k = dirs.get(n);
			if (lado[k] - lado[(k + 2) % 4] < SUBIDA_MIN && !forzada) {
				break;                                  // no sube lo bastante hacia ningún otro lado
			}
			for (int o : new int[] {0, -PASO, PASO}) {
				int bx = cx + DIR[k][0] * o, bz = cz + DIR[k][1] * o;
				Sitio s = evaluar(t, f, GIRO[k], bx, bz, minY, mejor == null ? Double.NEGATIVE_INFINITY : mejor.nota());
				if (s != null && (mejor == null || s.nota() > mejor.nota())) {
					mejor = s;
				}
			}
		}
		if (mejor == null && forzada) {
			mejor = new Sitio(GIRO[dirs.get(0)], cx, cz, h0, 0);
		}
		return mejor;
	}

	/**
	 * Nota de la boca en (bx, bz) con ese giro, o null si el terreno no sirve (o no puede ganar a `superar`). Las
	 * comprobaciones que descartan van de la más barata a la más cara (el agua pide una segunda altura de la columna, la
	 * superficie, y solo hace falta mirarla si todo lo demás vale); como todas dan null, el orden no cambia el resultado.
	 */
	static @Nullable Sitio evaluar(Terreno t, Forma f, Rotation giro, int bx, int bz, int minY, double superar) {
		if (SUBIDA_TOPE <= superar) {
			return null;                                // la nota nunca pasa de SUBIDA_TOPE
		}
		int[] xs = {f.patioX0(), f.patioX1(), (f.patioX0() + f.patioX1()) / 2};
		int[] zs = {f.patioZ0(), f.patioZ1(), (f.patioZ0() + f.patioZ1()) / 2};
		int[] delante = new int[9];
		int[][] patio = new int[9][];
		int min = Integer.MAX_VALUE, max = Integer.MIN_VALUE;
		for (int i = 0; i < 9; i++) {
			int[] ij = PATIO[i];                        // las esquinas primero: lo que más se separa
			int[] p = mundo(f, giro, bx, bz, xs[ij[0]], zs[ij[1]]);
			patio[i] = p;
			int h = t.suelo(p[0], p[1]);
			delante[i] = h;
			min = Math.min(min, h);
			max = Math.max(max, h);
			if (max - min > DESNIVEL) {
				return null;                            // patio en cuesta (sin mirar el resto de sus columnas)
			}
		}
		int[] orden = delante.clone();
		java.util.Arrays.sort(orden);
		int desnivel = orden[8] - orden[0];
		if (SUBIDA_TOPE - desnivel <= superar) {
			return null;                                // ni con el monte más alto ganaría a la que ya hay
		}
		int pies = orden[4];                            // la mediana: el patio corta lo que sobra y su cimiento rellena
		if (pies - 1 - f.entrada().getY() < minY + 2) {
			return null;
		}
		double suma = 0;
		for (int[] d : DETRAS) {
			int[] p = mundo(f, giro, bx, bz, f.entrada().getX() + d[0], f.entrada().getZ() + d[1]);
			int h = t.suelo(p[0], p[1]);
			if (h < pies + ALTO_MIN) {
				return null;                            // detrás de la boca no hay monte
			}
			suma += h - pies;
		}
		double subida = suma / DETRAS.length;
		if (subida < SUBIDA_MIN) {
			return null;
		}
		double nota = Math.min(subida, SUBIDA_TOPE) - desnivel;
		if (nota <= superar) {
			return null;
		}
		for (int[] m : f.techo()) {
			int[] p = mundo(f, giro, bx, bz, m[0], m[1]);
			if (t.suelo(p[0], p[1]) < pies + m[2]) {
				return null;                            // el casco de la galería asomaría
			}
		}
		for (int[] p : patio) {
			if (t.agua(p[0], p[1])) {
				return null;                            // agua en el patio
			}
		}
		return new Sitio(giro, bx, bz, pies, nota);
	}
}
