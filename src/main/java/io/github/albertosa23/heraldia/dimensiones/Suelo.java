package io.github.albertosa23.heraldia.dimensiones;

import java.util.function.IntPredicate;

/**
 * Dónde se apoya una estructura de Heraldia en el Nether o en el End (lógica pura, sin clases del juego: la prueban
 * {@code SueloTest} y la usa {@link DimensionStructure}).
 * <ul>
 * <li><b>Nether</b>: no hay heightmap de superficie útil (WORLD_SURFACE_WG da el techo de bedrock). Se recorre la
 * columna de ruido de arriba abajo, desde {@link #NETHER_DESDE} hasta {@link #NETHER_HASTA} (encima del mar de lava,
 * que está a y = 31), y vale la primera y con suelo firme debajo (ni lava ni aire) y {@code libre} celdas de aire
 * encima: la estructura cabe bajo el techo. Las esquinas de la huella deben tener su suelo a ±{@link #DESNIVEL} de esa
 * altura (si no, cuelga sobre un barranco o se mete en la pared).</li>
 * <li><b>End</b>: el heightmap sí sirve, pero el vacío da la altura mínima del mundo. El centro y las cuatro esquinas
 * deben estar sobre una isla de verdad (altura &ge; {@link #END_MINIMO}) y a ±{@link #DESNIVEL} entre sí, y el sitio
 * lejos de la isla central ({@link #END_RADIO_CENTRAL}: ni su isla ni el combate del dragón).</li>
 * </ul>
 */
public final class Suelo {
	/** Ninguna altura válida. */
	public static final int NINGUNO = Integer.MIN_VALUE;
	/** Nether: de dónde a dónde se busca el suelo (el techo de bedrock empieza en 123; el mar de lava llega a 31). */
	public static final int NETHER_DESDE = 112, NETHER_HASTA = 34;
	/** Desnivel máximo entre el suelo del centro y el de cada esquina de la huella (bloques). */
	public static final int DESNIVEL = 5;
	/** End: altura mínima de la superficie de una isla (el vacío da la mínima del mundo) y radio de la isla central. */
	public static final int END_MINIMO = 45, END_RADIO_CENTRAL = 1024;

	private Suelo() {
	}

	/**
	 * Primera y (de {@code desde} hacia abajo, hasta {@code hasta}) con suelo firme en y - 1 y {@code libre} celdas de aire
	 * de y a y + libre - 1, o {@link #NINGUNO}. {@code solido}: bloque que sostiene (ni aire ni líquido); {@code aire}:
	 * celda vacía (sin bloque ni líquido).
	 */
	public static int nether(IntPredicate solido, IntPredicate aire, int desde, int hasta, int libre) {
		int huecos = 0; // celdas de aire seguidas encima de la y que se mira
		for (int y = desde + libre; y >= hasta; y--) {
			if (y <= desde && huecos >= libre && solido.test(y - 1)) {
				return y;
			}
			huecos = aire.test(y - 1) ? huecos + 1 : 0;
		}
		return NINGUNO;
	}

	/** Suelo de una esquina cerca de la altura del centro: el primero a ±DESNIVEL con aire encima, o NINGUNO. */
	public static int netherCerca(IntPredicate solido, IntPredicate aire, int centro) {
		return nether(solido, aire, centro + DESNIVEL, centro - DESNIVEL, 2);
	}

	/** Todas las esquinas tienen suelo a ±DESNIVEL del centro. */
	public static boolean llano(int centro, int... esquinas) {
		for (int e : esquinas) {
			if (e == NINGUNO || Math.abs(e - centro) > DESNIVEL) {
				return false;
			}
		}
		return true;
	}

	/**
	 * End: la altura (la del centro) si el centro y las esquinas están sobre una isla (&ge; END_MINIMO), llanas entre sí,
	 * y el sitio fuera de la isla central; si no, NINGUNO. {@code alturas}: centro primero y luego las esquinas (la
	 * primera y libre del heightmap WORLD_SURFACE_WG).
	 */
	public static int end(int x, int z, int... alturas) {
		if ((long) x * x + (long) z * z < (long) END_RADIO_CENTRAL * END_RADIO_CENTRAL) {
			return NINGUNO;
		}
		int centro = alturas[0];
		for (int h : alturas) {
			if (h < END_MINIMO || Math.abs(h - centro) > DESNIVEL) {
				return NINGUNO;
			}
		}
		return centro;
	}
}
