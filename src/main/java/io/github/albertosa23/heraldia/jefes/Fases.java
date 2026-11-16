package io.github.albertosa23.heraldia.jefes;

import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import org.jspecify.annotations.Nullable;

/**
 * Lógica pura de las fases de los guardianes (sin clases del juego, para los tests). El estado vive en las etiquetas
 * (Tags) del propio guardián, que el juego guarda con él: {@code heraldia_fase.2} y {@code heraldia_fase.3}. Así un
 * guardián ya generado (con {@link #GUARDIAN}) gana las fases sin datos aparte, y cada fase ocurre una sola vez aunque
 * se cure, se recargue el chunk o se reinicie el servidor.
 */
public final class Fases {
	/** Etiqueta de los guardianes finales (piezas.GUARDIAN_TAG). */
	public static final String GUARDIAN = "heraldia_guardian";
	/** Prefijo de la etiqueta con el id de su única (pack.tag_guardians): {@code heraldia_guardian.<id>}. */
	public static final String UNICA = GUARDIAN + ".";
	/** Prefijo de la etiqueta de cada fase alcanzada: {@code heraldia_fase.<n>}. */
	public static final String FASE = "heraldia_fase.";
	/** Etiqueta de los refuerzos (no son guardianes: no pasan de fase ni sueltan su botín). */
	public static final String REFUERZO = "heraldia_refuerzo";
	/** Fase 2 al bajar del 66 % de vida; fase 3 al bajar del 33 %. */
	public static final float UMBRAL_2 = 0.66f;
	public static final float UMBRAL_3 = 0.33f;
	public static final int MAX_FASE = 3;
	/** Refuerzos vivos a la vez cerca de un guardián, como mucho. */
	public static final int MAX_VIVOS = 4;

	private Fases() {
	}

	/** ¿Guardián final? (salida temprana: casi todas las entidades no llevan etiquetas). */
	public static boolean esGuardian(Set<String> tags) {
		return !tags.isEmpty() && tags.contains(GUARDIAN);
	}

	/** Id de la única del guardián ({@code heraldia_guardian.<id>}), o null si no la lleva. */
	public static @Nullable String unica(Set<String> tags) {
		for (String t : tags) {
			if (t.startsWith(UNICA) && t.length() > UNICA.length()) {
				return t.substring(UNICA.length());
			}
		}
		return null;
	}

	/** Fase que corresponde a la vida: 1 por encima del 66 %, 2 por debajo, 3 por debajo del 33 %. */
	public static int faseDeVida(float vida, float max) {
		if (!(max > 0)) {
			return 1;
		}
		float r = vida / max;
		return r < UMBRAL_3 ? 3 : r < UMBRAL_2 ? 2 : 1;
	}

	/** Fase más alta ya alcanzada según sus etiquetas (1 si ninguna). */
	public static int alcanzada(Set<String> tags) {
		for (int f = MAX_FASE; f >= 2; f--) {
			if (tags.contains(FASE + f)) {
				return f;
			}
		}
		return 1;
	}

	/**
	 * Fases que hay que aplicar ahora, en orden: las que corresponden a la vida y aún no tienen su etiqueta. Un golpe
	 * que baje del 100 % al 20 % da las dos. Vacía si las fases y los refuerzos están desactivados o si ya murió.
	 */
	public static List<Integer> pendientes(Set<String> tags, float vida, float max, boolean fases, boolean refuerzos) {
		List<Integer> out = new ArrayList<>(2);
		if ((!fases && !refuerzos) || !(vida > 0)) {
			return out;
		}
		int objetivo = faseDeVida(vida, max);
		for (int f = 2; f <= objetivo; f++) {
			if (!tags.contains(FASE + f)) {
				out.add(f);
			}
		}
		return out;
	}

	/** Cuántos refuerzos de los {@code listados} se llaman con {@code vivos} ya cerca (tope {@link #MAX_VIVOS}). */
	public static int cuantos(int listados, int vivos) {
		return Math.max(0, Math.min(listados, MAX_VIVOS - vivos));
	}

	/**
	 * Clave del mensaje de la barra de acción al pasar a {@code fase}: con las fases activadas, el de la fase (con
	 * «llama a sus refuerzos» si los ha llamado); solo con refuerzos, el de los refuerzos; si no hay nada que contar, null.
	 */
	public static @Nullable String clave(int fase, boolean fases, int llamados) {
		if (fases) {
			return "heraldia.jefes.fase." + fase + (llamados > 0 ? ".refuerzos" : "");
		}
		return llamados > 0 ? "heraldia.jefes.refuerzos" : null;
	}

	/** Radio (bloques) en el que un jugador ve la barra y recibe los avisos; la pierde al alejarse más de {@link #RADIO_FUERA}. */
	public static final int RADIO = 32;
	public static final int RADIO_FUERA = 48;

	/** ¿Se le muestra la barra a un jugador a esa distancia al cuadrado? true: añadir; false: quitar; null: dejar como esté. */
	public static @Nullable Boolean ve(double distancia2) {
		if (distancia2 <= (double) RADIO * RADIO) {
			return Boolean.TRUE;
		}
		return distancia2 > (double) RADIO_FUERA * RADIO_FUERA ? Boolean.FALSE : null;
	}

	/** Progreso de la barra (0-1). */
	public static float progreso(float vida, float max) {
		return max > 0 ? Math.clamp(vida / max, 0f, 1f) : 0f;
	}
}
