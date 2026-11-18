package io.github.albertosa23.heraldia.arena;

import java.util.Arrays;
import java.util.Optional;

/**
 * Elección del sitio de la arena, sin clases del juego (lo prueban los tests con un terreno inventado): candidatos en
 * anillos de {@link #RADIUS_MIN} a {@link #RADIUS_MAX} bloques del spawn, cada {@link #DEGREE_STEP}°, y en cada uno una
 * malla de {@link #SAMPLES}² alturas sobre la huella de la arena y un margen. Vale el que no tiene agua y menos desnivel
 * (como mucho {@link #MAX_DROP}) y ninguna estructura ya generada en sus chunks; a igualdad, el más cercano a {@link #PREFERRED_RADIUS} y luego el primero en orden.
 * Las alturas salen del generador del mundo ({@code ChunkGenerator.getBaseHeight}: solo ruido, sin cargar chunks), así
 * que la búsqueda puede ir fuera del hilo del servidor.
 */
public final class Site {
	public static final int RADIUS_MIN = 200, RADIUS_MAX = 300, RADIUS_STEP = 25, PREFERRED_RADIUS = 250, DEGREE_STEP = 15;
	public static final int SAMPLES = 5, MARGIN = 4, MAX_DROP = 12;

	private Site() {
	}

	/** Alturas del terreno natural en una columna. */
	public interface Heights {
		/** Primer bloque libre sobre la superficie (agua incluida). */
		int surface(int x, int z);

		/** Primer bloque libre o con agua sobre el suelo sólido. */
		int depth(int x, int z);

		/** ¿Hay ya en ese chunk alguna pieza de una estructura de superficie (aldea, entrada de mina...)? */
		default boolean occupied(int chunkX, int chunkZ) {
			return false;
		}
	}

	/**
	 * Un sitio: columna del centro, y del bloque de suelo (la mediana de las alturas: lo que se nivela), desnivel y
	 * distancia al spawn.
	 */
	public record Choice(int x, int z, int ground, int drop, int distance) {
	}

	/**
	 * El mejor sitio para una arena de {@code side} bloques alrededor del spawn, o vacío si no hay ninguno llano y sin agua.
	 * {@code minY} y {@code maxY}: alturas del mundo; la arena (de {@code low} bloques bajo el suelo a {@code high} por
	 * encima) tiene que caber.
	 */
	public static Optional<Choice> choose(int spawnX, int spawnZ, int side, int low, int high, int minY, int maxY, Heights a) {
		Choice best = null;
		for (int r = RADIUS_MIN; r <= RADIUS_MAX; r += RADIUS_STEP) {
			for (int g = 0; g < 360; g += DEGREE_STEP) {
				double rad = Math.toRadians(g);
				int cx = spawnX + (int) Math.round(r * Math.cos(rad));
				int cz = spawnZ + (int) Math.round(r * Math.sin(rad));
				Choice e = evaluateAt(cx, cz, spawnX, spawnZ, side, a);
				if (e == null || e.ground() - low <= minY || e.ground() + high >= maxY) {
					continue;
				}
				if ((best == null || best(e, best)) && free(e, side, a)) {
					best = e;
				}
			}
		}
		return Optional.ofNullable(best);
	}

	/** El sitio con centro en (cx, cz), o null si hay agua o demasiado desnivel. */
	static Choice evaluateAt(int cx, int cz, int spawnX, int spawnZ, int side, Heights a) {
		int width = side + 2 * MARGIN;
		int[] heights = new int[SAMPLES * SAMPLES];
		int i = 0;
		for (int u = 0; u < SAMPLES; u++) {
			for (int v = 0; v < SAMPLES; v++) {
				int x = cx - width / 2 + u * (width - 1) / (SAMPLES - 1);
				int z = cz - width / 2 + v * (width - 1) / (SAMPLES - 1);
				int s = a.surface(x, z);
				if (s > a.depth(x, z)) {
					return null;                // agua
				}
				heights[i++] = s - 1;
			}
		}
		Arrays.sort(heights);
		int drop = heights[heights.length - 1] - heights[0];
		if (drop > MAX_DROP) {
			return null;
		}
		int dist = (int) Math.round(Math.hypot(cx - spawnX, cz - spawnZ));
		return new Choice(cx, cz, heights[heights.length / 2], drop, dist);
	}

	/** ¿Ningún chunk de la huella y su margen tiene ya una estructura? (solo se mira si el sitio mejora al elegido) */
	static boolean free(Choice e, int side, Heights a) {
		int m = side / 2 + MARGIN;
		for (int cx = (e.x() - m) >> 4; cx <= (e.x() + m) >> 4; cx++) {
			for (int cz = (e.z() - m) >> 4; cz <= (e.z() + m) >> 4; cz++) {
				if (a.occupied(cx, cz)) {
					return false;
				}
			}
		}
		return true;
	}

	/** ¿{@code a} es mejor que {@code b}? Menos desnivel; a igualdad, más cerca de {@link #PREFERRED_RADIUS}. */
	static boolean best(Choice a, Choice b) {
		if (a.drop() != b.drop()) {
			return a.drop() < b.drop();
		}
		return Math.abs(a.distance() - PREFERRED_RADIUS) < Math.abs(b.distance() - PREFERRED_RADIUS);
	}
}
