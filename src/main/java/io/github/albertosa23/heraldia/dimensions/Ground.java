package io.github.albertosa23.heraldia.dimensions;

import java.util.function.IntPredicate;

/**
 * Dónde se apoya una estructura de Heraldia en el Nether o en el End (lógica pura, sin clases del juego: la prueban
 * {@code GroundTest} y la usa {@link DimensionStructure}).
 * <ul>
 * <li><b>Nether</b>: no hay heightmap de superficie útil (WORLD_SURFACE_WG da el techo de bedrock). Se recorre la
 * columna de ruido de arriba abajo, desde {@link #NETHER_FROM} hasta {@link #NETHER_TO} (encima del mar de lava,
 * que está a y = 31), y vale la primera y con suelo firme debajo (ni lava ni aire) y {@code free} celdas de aire
 * encima: la estructura cabe bajo el techo. Las esquinas de la huella deben tener su suelo a ±{@link #DROP} de esa
 * altura (si no, cuelga sobre un barranco o se mete en la pared).</li>
 * <li><b>End</b>: el heightmap sí sirve, pero el vacío da la altura mínima del mundo. El centro y las cuatro esquinas
 * deben estar sobre una isla de verdad (altura &ge; {@link #END_MIN}) y a ±{@link #DROP} entre sí, y el sitio
 * lejos de la isla central ({@link #END_CENTRAL_RADIUS}: ni su isla ni el combate del dragón).</li>
 * </ul>
 */
public final class Ground {
	/** Ninguna altura válida. */
	public static final int DRY = Integer.MIN_VALUE;
	/** Nether: de dónde a dónde se busca el suelo (el techo de bedrock empieza en 123; el mar de lava llega a 31). */
	public static final int NETHER_FROM = 112, NETHER_TO = 34;
	/** Desnivel máximo entre el suelo del centro y el de cada esquina de la huella (bloques). */
	public static final int DROP = 5;
	/** End: altura mínima de la superficie de una isla (el vacío da la mínima del mundo) y radio de la isla central. */
	public static final int END_MIN = 45, END_CENTRAL_RADIUS = 1024;

	private Ground() {
	}

	/**
	 * Primera y (de {@code from} hacia abajo, hasta {@code until}) con suelo firme en y - 1 y {@code free} celdas de aire
	 * de y a y + libre - 1, o {@link #DRY}. {@code solid}: bloque que sostiene (ni aire ni líquido); {@code air}:
	 * celda vacía (sin bloque ni líquido).
	 */
	public static int nether(IntPredicate solid, IntPredicate air, int from, int until, int free) {
		int placeholders = 0; // celdas de aire seguidas encima de la y que se mira
		for (int y = from + free; y >= until; y--) {
			if (y <= from && placeholders >= free && solid.test(y - 1)) {
				return y;
			}
			placeholders = air.test(y - 1) ? placeholders + 1 : 0;
		}
		return DRY;
	}

	/** Suelo de una esquina cerca de la altura del centro: el primero a ±DESNIVEL con aire encima, o NINGUNO. */
	public static int netherNear(IntPredicate solid, IntPredicate air, int center) {
		return nether(solid, air, center + DROP, center - DROP, 2);
	}

	/** Todas las esquinas tienen suelo a ±DESNIVEL del centro. */
	public static boolean flat(int center, int... corners) {
		for (int e : corners) {
			if (e == DRY || Math.abs(e - center) > DROP) {
				return false;
			}
		}
		return true;
	}

	/**
	 * End: la altura (la del centro) si el centro y las esquinas están sobre una isla (&ge; END_MINIMO), llanas entre sí,
	 * y el sitio fuera de la isla central; si no, NINGUNO. {@code heights}: centro primero y luego las esquinas (la
	 * primera y libre del heightmap WORLD_SURFACE_WG).
	 */
	public static int end(int x, int z, int... heights) {
		if ((long) x * x + (long) z * z < (long) END_CENTRAL_RADIUS * END_CENTRAL_RADIUS) {
			return DRY;
		}
		int center = heights[0];
		for (int h : heights) {
			if (h < END_MIN || Math.abs(h - center) > DROP) {
				return DRY;
			}
		}
		return center;
	}
}
