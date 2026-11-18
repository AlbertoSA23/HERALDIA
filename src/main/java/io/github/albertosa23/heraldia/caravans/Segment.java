package io.github.albertosa23.heraldia.caravans;

import io.github.albertosa23.heraldia.roads.RoadLayout;
import java.util.List;
import org.jspecify.annotations.Nullable;

/**
 * Tramo de camino que recorre una caravana (lógica pura): de un vértice de la ruta canónica entre dos aldeas vecinas
 * ({@link RoadLayout.Route}) a otro, en un sentido. La caravana sale de un vértice a entre {@link #DIST_MIN} y
 * {@link #DIST_MAX} bloques del jugador (nunca encima de él ni dentro de una aldea) y va hacia el punto de la ruta más
 * cercano al jugador, de modo que pasa por delante de él; recorre como mucho {@link #LENGTH} vértices y para antes de la
 * plaza de la aldea de destino.
 *
 * @param inicio índice del vértice de salida en la ruta
 * @param fin    índice del vértice de llegada
 * @param paso   +1 (de {@code route.from} a {@code route.until}) o -1
 */
public record Segment(RoadLayout.Route route, int start, int end, int step) {
	/** Vértices que recorre como mucho (16 bloques cada uno: unos 128 bloques) y como poco. */
	public static final int LENGTH = 8, MIN = 4;
	/** Vértices que deja libres en cada punta de la ruta: la salida no está en una aldea y la llegada no es la plaza. */
	public static final int VILLAGE_MARGIN = 3;
	/** Distancia en bloques (en el plano) del jugador al vértice de salida. */
	public static final int DIST_MIN = 24, DIST_MAX = 80;

	/** Aldea a la que va (su plaza, empaquetada con {@link RoadLayout#pack}). */
	public long destination() {
		return step > 0 ? route.until : route.from;
	}

	/** Aldea de la que viene. */
	public long origin() {
		return step > 0 ? route.from : route.until;
	}

	/** Vértices del tramo, contando la salida y la llegada. */
	public int vertices() {
		return Math.abs(end - start) + 1;
	}

	/** Índice en la ruta del k-ésimo vértice del tramo (0 = salida). */
	public int vertex(int k) {
		return start + k * step;
	}

	public int x(int k) {
		return (int) Math.floor(route.x(vertex(k)));
	}

	public int z(int k) {
		return (int) Math.floor(route.z(vertex(k)));
	}

	/** Longitud del tramo en bloques (a lo largo del camino). */
	public double length() {
		return Math.abs(route.arc(end) - route.arc(start));
	}

	/**
	 * El tramo para una caravana junto al jugador en (x, z), o null si no pasa ninguna ruta lo bastante cerca. De las
	 * rutas dadas se toma el vértice de salida válido más cercano al jugador (a igual distancia, el de la ruta anterior
	 * en la lista y el índice menor: determinista); el sentido, hacia el vértice de esa ruta más cercano al jugador (si es
	 * el mismo, el que dice {@code seed}), y si en ese sentido no caben {@link #MIN} vértices, el otro.
	 */
	public static @Nullable Segment choose(List<RoadLayout.Route> routes, int x, int z, long seed) {
		Segment best = null;
		double bestD = Double.MAX_VALUE;
		for (RoadLayout.Route r : routes) {
			int n = r.vertices();
			int lo = VILLAGE_MARGIN, hi = n - 1 - VILLAGE_MARGIN;
			if (hi - lo < MIN) {
				continue;           // ruta demasiado corta para un tramo fuera de las aldeas
			}
			int near = 0;
			double nearD = Double.MAX_VALUE;
			for (int i = 0; i < n; i++) {
				double d = dist(r, i, x, z);
				if (d < nearD) {
					nearD = d;
					near = i;
				}
			}
			for (int i = lo; i <= hi; i++) {
				double d = dist(r, i, x, z);
				if (d < DIST_MIN || d > DIST_MAX || d >= bestD) {
					continue;
				}
				int step = near > i ? 1 : near < i ? -1 : ((seed & 1) == 0 ? 1 : -1);
				int fits = step > 0 ? hi - i : i - lo;
				if (fits < MIN) {
					step = -step;
					fits = step > 0 ? hi - i : i - lo;
				}
				if (fits < MIN) {
					continue;
				}
				bestD = d;
				best = new Segment(r, i, i + step * Math.min(LENGTH, fits), step);
			}
		}
		return best;
	}

	static double dist(RoadLayout.Route r, int i, int x, int z) {
		return Math.hypot(r.x(i) - x, r.z(i) - z);
	}

	/** Recorta el tramo para que acabe en su k-ésimo vértice (el camino no sigue más allá en un mundo existente). */
	public Segment until(int k) {
		return new Segment(route, start, vertex(k), step);
	}
}
