package io.github.albertosa23.heraldia.comando;

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
public final class Seguro {
	/** Radio de búsqueda por defecto alrededor de la columna pedida, en bloques. */
	public static final int RADIO = 8;

	private Seguro() {
	}

	/** Qué hay en una celda, a efectos de quedarse en ella. */
	public enum Celda {
		/** Sin colisión ni daño (aire, hierba, flores, nieve fina...). */
		LIBRE,
		/** Bloque que sostiene y que asfixia si se está dentro. */
		SOLIDO,
		/** Agua: se puede flotar encima; no asfixia al instante, pero no se aparece dentro. */
		AGUA,
		/** Daña o atrapa: lava, fuego, magma, cactus, nieve polvo, bayas... */
		PELIGRO
	}

	/** Lo que hace falta del mundo. Solo se pregunta por columnas ya cargadas. */
	public interface Mundo {
		Celda en(int x, int y, int z);

		/** Primera y libre encima del bloque más alto que impide moverse en la columna (el heightmap). */
		int altura(int x, int z);

		int minY();

		/** Primera y fuera del mundo (por arriba). */
		int maxY();
	}

	/** (x, y, z) de los pies. */
	public record Sitio(int x, int y, int z) {
	}

	/** Desplazamientos de la espiral hasta {@code radio}, del centro hacia fuera (orden fijo: distancia, x, z). */
	static List<int[]> espiral(int radio) {
		List<int[]> out = new ArrayList<>();
		for (int dx = -radio; dx <= radio; dx++) {
			for (int dz = -radio; dz <= radio; dz++) {
				if (dx * dx + dz * dz <= radio * radio) {
					out.add(new int[] {dx, dz});
				}
			}
		}
		out.sort(Comparator.<int[]>comparingInt(o -> o[0] * o[0] + o[1] * o[1]).thenComparingInt(o -> o[0]).thenComparingInt(o -> o[1]));
		return out;
	}

	/** El sitio seguro más cercano a la columna (x, z), o vacío si no hay ninguno a {@code radio} bloques. */
	public static Optional<Sitio> buscar(Mundo m, int x, int z, int radio) {
		for (int[] d : espiral(radio)) {
			int cx = x + d[0], cz = z + d[1];
			Optional<Sitio> s = columna(m, cx, cz);
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
	static Optional<Sitio> columna(Mundo m, int x, int z) {
		int y = m.altura(x, z);
		if (y <= m.minY() || y + 1 >= m.maxY()) {
			return Optional.empty();       // columna vacía (vacío) o hasta el techo del mundo
		}
		return valido(m, x, y, z) ? Optional.of(new Sitio(x, y, z)) : Optional.empty();
	}

	/**
	 * Mundos con techo (el Nether): el heightmap da el techo de bedrock, así que la «altura» de una columna es la primera
	 * y, de {@code desde} hacia abajo hasta {@code hasta}, con los pies y la cabeza libres y suelo firme debajo; si no hay
	 * ninguna, la mínima del mundo (la columna no vale). La usa /heraldia review para las paradas del Nether.
	 */
	public static int bajoTecho(Mundo m, int x, int z, int desde, int hasta) {
		for (int y = desde; y > hasta; y--) {
			if (m.en(x, y, z) == Celda.LIBRE && m.en(x, y + 1, z) == Celda.LIBRE && m.en(x, y - 1, z) == Celda.SOLIDO) {
				return y;
			}
		}
		return m.minY();
	}

	/** ¿Se puede estar de pie con los pies en y? Pies y cabeza libres; debajo, suelo firme o agua. */
	static boolean valido(Mundo m, int x, int y, int z) {
		Celda abajo = m.en(x, y - 1, z);
		return m.en(x, y, z) == Celda.LIBRE && m.en(x, y + 1, z) == Celda.LIBRE
				&& (abajo == Celda.SOLIDO || abajo == Celda.AGUA);
	}
}
