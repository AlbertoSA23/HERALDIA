package io.github.albertosa23.heraldia.caravanas;

import io.github.albertosa23.heraldia.caminos.Trazado;
import java.util.List;
import org.jspecify.annotations.Nullable;

/**
 * Tramo de camino que recorre una caravana (lógica pura): de un vértice de la ruta canónica entre dos aldeas vecinas
 * ({@link Trazado.Ruta}) a otro, en un sentido. La caravana sale de un vértice a entre {@link #DIST_MIN} y
 * {@link #DIST_MAX} bloques del jugador (nunca encima de él ni dentro de una aldea) y va hacia el punto de la ruta más
 * cercano al jugador, de modo que pasa por delante de él; recorre como mucho {@link #LARGO} vértices y para antes de la
 * plaza de la aldea de destino.
 *
 * @param inicio índice del vértice de salida en la ruta
 * @param fin    índice del vértice de llegada
 * @param paso   +1 (de {@code ruta.desde} a {@code ruta.hasta}) o -1
 */
public record Tramo(Trazado.Ruta ruta, int inicio, int fin, int paso) {
	/** Vértices que recorre como mucho (16 bloques cada uno: unos 128 bloques) y como poco. */
	public static final int LARGO = 8, MINIMO = 4;
	/** Vértices que deja libres en cada punta de la ruta: la salida no está en una aldea y la llegada no es la plaza. */
	public static final int MARGEN_ALDEA = 3;
	/** Distancia en bloques (en el plano) del jugador al vértice de salida. */
	public static final int DIST_MIN = 24, DIST_MAX = 80;

	/** Aldea a la que va (su plaza, empaquetada con {@link Trazado#pack}). */
	public long destino() {
		return paso > 0 ? ruta.hasta : ruta.desde;
	}

	/** Aldea de la que viene. */
	public long origen() {
		return paso > 0 ? ruta.desde : ruta.hasta;
	}

	/** Vértices del tramo, contando la salida y la llegada. */
	public int vertices() {
		return Math.abs(fin - inicio) + 1;
	}

	/** Índice en la ruta del k-ésimo vértice del tramo (0 = salida). */
	public int vertice(int k) {
		return inicio + k * paso;
	}

	public int x(int k) {
		return (int) Math.floor(ruta.x(vertice(k)));
	}

	public int z(int k) {
		return (int) Math.floor(ruta.z(vertice(k)));
	}

	/** Longitud del tramo en bloques (a lo largo del camino). */
	public double longitud() {
		return Math.abs(ruta.arco(fin) - ruta.arco(inicio));
	}

	/**
	 * El tramo para una caravana junto al jugador en (x, z), o null si no pasa ninguna ruta lo bastante cerca. De las
	 * rutas dadas se toma el vértice de salida válido más cercano al jugador (a igual distancia, el de la ruta anterior
	 * en la lista y el índice menor: determinista); el sentido, hacia el vértice de esa ruta más cercano al jugador (si es
	 * el mismo, el que dice {@code semilla}), y si en ese sentido no caben {@link #MINIMO} vértices, el otro.
	 */
	public static @Nullable Tramo elegir(List<Trazado.Ruta> rutas, int x, int z, long semilla) {
		Tramo mejor = null;
		double mejorD = Double.MAX_VALUE;
		for (Trazado.Ruta r : rutas) {
			int n = r.vertices();
			int lo = MARGEN_ALDEA, hi = n - 1 - MARGEN_ALDEA;
			if (hi - lo < MINIMO) {
				continue;           // ruta demasiado corta para un tramo fuera de las aldeas
			}
			int cerca = 0;
			double cercaD = Double.MAX_VALUE;
			for (int i = 0; i < n; i++) {
				double d = dist(r, i, x, z);
				if (d < cercaD) {
					cercaD = d;
					cerca = i;
				}
			}
			for (int i = lo; i <= hi; i++) {
				double d = dist(r, i, x, z);
				if (d < DIST_MIN || d > DIST_MAX || d >= mejorD) {
					continue;
				}
				int paso = cerca > i ? 1 : cerca < i ? -1 : ((semilla & 1) == 0 ? 1 : -1);
				int cabe = paso > 0 ? hi - i : i - lo;
				if (cabe < MINIMO) {
					paso = -paso;
					cabe = paso > 0 ? hi - i : i - lo;
				}
				if (cabe < MINIMO) {
					continue;
				}
				mejorD = d;
				mejor = new Tramo(r, i, i + paso * Math.min(LARGO, cabe), paso);
			}
		}
		return mejor;
	}

	static double dist(Trazado.Ruta r, int i, int x, int z) {
		return Math.hypot(r.x(i) - x, r.z(i) - z);
	}

	/** Recorta el tramo para que acabe en su k-ésimo vértice (el camino no sigue más allá en un mundo existente). */
	public Tramo hasta(int k) {
		return new Tramo(ruta, inicio, vertice(k), paso);
	}
}
