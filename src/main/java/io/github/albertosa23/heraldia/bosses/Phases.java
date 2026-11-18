package io.github.albertosa23.heraldia.bosses;

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
public final class Phases {
	/** Etiqueta de los guardianes finales (piezas.GUARDIAN_TAG). */
	public static final String GUARDIAN = "heraldia_guardian";
	/** Prefijo de la etiqueta con el id de su única (pack.tag_guardians): {@code heraldia_guardian.<id>}. */
	public static final String UNIQUE = GUARDIAN + ".";
	/** Prefijo de la etiqueta de cada fase alcanzada: {@code heraldia_fase.<n>}. */
	public static final String PHASE = "heraldia_fase.";
	/** Etiqueta de los refuerzos (no son guardianes: no pasan de fase ni sueltan su botín). */
	public static final String REINFORCEMENT = "heraldia_refuerzo";
	/** Fase 2 al bajar del 66 % de vida; fase 3 al bajar del 33 %. */
	public static final float THRESHOLD_2 = 0.66f;
	public static final float THRESHOLD_3 = 0.33f;
	public static final int MAX_PHASE = 3;
	/** Refuerzos vivos a la vez cerca de un guardián, como mucho. */
	public static final int MAX_ALIVE = 4;

	private Phases() {
	}

	/** ¿Guardián final? (salida temprana: casi todas las entidades no llevan etiquetas). */
	public static boolean isGuardian(Set<String> tags) {
		return !tags.isEmpty() && tags.contains(GUARDIAN);
	}

	/** Id de la única del guardián ({@code heraldia_guardian.<id>}), o null si no la lleva. */
	public static @Nullable String unique(Set<String> tags) {
		for (String t : tags) {
			if (t.startsWith(UNIQUE) && t.length() > UNIQUE.length()) {
				return t.substring(UNIQUE.length());
			}
		}
		return null;
	}

	/** Fase que corresponde a la vida: 1 por encima del 66 %, 2 por debajo, 3 por debajo del 33 %. */
	public static int healthPhase(float health, float max) {
		if (!(max > 0)) {
			return 1;
		}
		float r = health / max;
		return r < THRESHOLD_3 ? 3 : r < THRESHOLD_2 ? 2 : 1;
	}

	/** Fase más alta ya alcanzada según sus etiquetas (1 si ninguna). */
	public static int reached(Set<String> tags) {
		for (int f = MAX_PHASE; f >= 2; f--) {
			if (tags.contains(PHASE + f)) {
				return f;
			}
		}
		return 1;
	}

	/**
	 * Fases que hay que aplicar ahora, en orden: las que corresponden a la vida y aún no tienen su etiqueta. Un golpe
	 * que baje del 100 % al 20 % da las dos. Vacía si las fases y los refuerzos están desactivados o si ya murió.
	 */
	public static List<Integer> pending(Set<String> tags, float health, float max, boolean phases, boolean reinforcements) {
		List<Integer> out = new ArrayList<>(2);
		if ((!phases && !reinforcements) || !(health > 0)) {
			return out;
		}
		int target = healthPhase(health, max);
		for (int f = 2; f <= target; f++) {
			if (!tags.contains(PHASE + f)) {
				out.add(f);
			}
		}
		return out;
	}

	/** Cuántos refuerzos de los {@code listed} se llaman con {@code alive} ya cerca (tope {@link #MAX_ALIVE}). */
	public static int howMany(int listed, int alive) {
		return howMany(listed, alive, 100, MAX_ALIVE);
	}

	/**
	 * Con las opciones jefes.refuerzos.porcentaje (de los listados, redondeando; 100 = los de siempre) y
	 * jefes.refuerzos.maximo_vivos (el tope; 4 = el de siempre). Con 100 y 4, lo mismo que {@link #howMany(int, int)}.
	 */
	public static int howMany(int listed, int alive, int percent, int maximum) {
		int requested = (int) Math.round(listed * percent / 100.0);
		return Math.max(0, Math.min(requested, maximum - alive));
	}

	/**
	 * Clave del mensaje de la barra de acción al pasar a {@code phase}: con las fases activadas, el de la fase (con
	 * «llama a sus refuerzos» si los ha llamado); solo con refuerzos, el de los refuerzos; si no hay nada que contar, null.
	 */
	public static @Nullable String key(int phase, boolean phases, int called) {
		if (phases) {
			return "heraldia.jefes.fase." + phase + (called > 0 ? ".refuerzos" : "");
		}
		return called > 0 ? "heraldia.jefes.refuerzos" : null;
	}

	/** Radio (bloques) en el que un jugador ve la barra y recibe los avisos; la pierde al alejarse más de {@link #OUTSIDE_RADIUS}. */
	public static final int RADIUS = 32;
	public static final int OUTSIDE_RADIUS = 48;

	/** ¿Se le muestra la barra a un jugador a esa distancia al cuadrado? true: añadir; false: quitar; null: dejar como esté. */
	public static @Nullable Boolean sees(double distance2) {
		if (distance2 <= (double) RADIUS * RADIUS) {
			return Boolean.TRUE;
		}
		return distance2 > (double) OUTSIDE_RADIUS * OUTSIDE_RADIUS ? Boolean.FALSE : null;
	}

	/** Progreso de la barra (0-1). */
	public static float progress(float health, float max) {
		return max > 0 ? Math.clamp(health / max, 0f, 1f) : 0f;
	}
}
