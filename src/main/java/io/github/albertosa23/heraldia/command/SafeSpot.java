package io.github.albertosa23.heraldia.command;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Optional;

/**
 * Teletransporte seguro (lógica pura, sin clases del juego): busca, desde una columna y en espiral, un sitio donde
 * quedar de pie encima del suelo y sin asfixia. Un sitio vale si los pies y la cabeza quedan en celdas libres y debajo
 * hay suelo firme o agua (flotar en el agua es seguro: la Atlántida y la isla están en el mar). Nunca encima ni dentro
 * de lava, fuego, magma, cactus o nieve polvo.
 */
public final class SafeSpot {
	/** Radio de búsqueda por defecto alrededor de la columna pedida, en bloques. */
	public static final int RADIUS = 8;

	private SafeSpot() {
	}

	/** Qué hay en una celda, a efectos de quedarse en ella. */
	public enum Cell {
		/** Sin colisión ni daño (aire, hierba, flores, nieve fina...). */
		FREE,
		/** Bloque que sostiene y que asfixia si se está dentro. */
		SOLID,
		/** Agua: se puede flotar encima; no asfixia al instante, pero no se aparece dentro. */
		WATER,
		/** Daña o atrapa: lava, fuego, magma, cactus, nieve polvo, bayas... */
		DANGER
	}

	/** Lo que hace falta del mundo. Solo se pregunta por columnas ya cargadas. */
	public interface World {
		Cell en(int x, int y, int z);

		/** Primera y libre encima del bloque más alto que impide moverse en la columna (el heightmap). */
		int height(int x, int z);

		int minY();

		/** Primera y fuera del mundo (por arriba). */
		int maxY();
	}

	/** (x, y, z) de los pies. */
	public record Site(int x, int y, int z) {
	}

	/** Desplazamientos de la espiral hasta {@code radius}, del centro hacia fuera (orden fijo: distancia, x, z). */
	static List<int[]> spiral(int radius) {
		List<int[]> out = new ArrayList<>();
		for (int dx = -radius; dx <= radius; dx++) {
			for (int dz = -radius; dz <= radius; dz++) {
				if (dx * dx + dz * dz <= radius * radius) {
					out.add(new int[] {dx, dz});
				}
			}
		}
		out.sort(Comparator.<int[]>comparingInt(o -> o[0] * o[0] + o[1] * o[1]).thenComparingInt(o -> o[0]).thenComparingInt(o -> o[1]));
		return out;
	}

	/** El sitio seguro más cercano a la columna (x, z), o vacío si no hay ninguno a {@code radius} bloques. */
	public static Optional<Site> search(World m, int x, int z, int radius) {
		for (int[] d : spiral(radius)) {
			int cx = x + d[0], cz = z + d[1];
			Optional<Site> s = column(m, cx, cz);
			if (s.isPresent()) {
				return s;
			}
		}
		return Optional.empty();
	}

	/**
	 * Sitio seguro de una columna: encima de lo más alto (el heightmap) y, si ahí no vale (bajo un saliente, entre hojas),
	 * nada más; las cuevas no se buscan (se aparece siempre al aire libre).
	 */
	static Optional<Site> column(World m, int x, int z) {
		int y = m.height(x, z);
		if (y <= m.minY() || y + 1 >= m.maxY()) {
			return Optional.empty();       // columna vacía (vacío) o hasta el techo del mundo
		}
		return valid(m, x, y, z) ? Optional.of(new Site(x, y, z)) : Optional.empty();
	}

	/**
	 * Mundos con techo (el Nether): el heightmap da el techo de bedrock, así que la «altura» de una columna es la primera
	 * y, de {@code from} hacia abajo hasta {@code until}, con los pies y la cabeza libres y suelo firme debajo; si no hay
	 * ninguna, la mínima del mundo (la columna no vale). La usa /heraldia review para las paradas del Nether.
	 */
	public static int underCeiling(World m, int x, int z, int from, int until) {
		for (int y = from; y > until; y--) {
			if (m.en(x, y, z) == Cell.FREE && m.en(x, y + 1, z) == Cell.FREE && m.en(x, y - 1, z) == Cell.SOLID) {
				return y;
			}
		}
		return m.minY();
	}

	/** ¿Se puede estar de pie con los pies en y? Pies y cabeza libres; debajo, suelo firme o agua. */
	static boolean valid(World m, int x, int y, int z) {
		Cell below = m.en(x, y - 1, z);
		return m.en(x, y, z) == Cell.FREE && m.en(x, y + 1, z) == Cell.FREE
				&& (below == Cell.SOLID || below == Cell.WATER);
	}
}
