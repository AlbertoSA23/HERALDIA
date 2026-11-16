package io.github.albertosa23.heraldia.dificultad;

import java.util.Locale;
import java.util.Set;

/**
 * Lógica pura de la dificultad configurable (opción {@code dificultad.nivel}), sin clases del juego: multiplicadores de
 * vida, daño y botín de cada nivel, el extra de vida por jugadores cercanos y el reajuste de la vida actual cuando cambia
 * la máxima. La aplica {@link DificultadMobs}.
 */
public final class Dificultad {
	/** Extra de vida por cada jugador de más cerca del mob (dificultad.escalar_por_jugadores), y su tope. */
	public static final double EXTRA_POR_JUGADOR = 0.25, EXTRA_MAXIMO = 1.0;
	/** Radio (bloques) en el que se cuentan los jugadores que luchan contra el mob. */
	public static final double RADIO_JUGADORES = 32;
	/**
	 * Etiquetas (Tags) de los mobs a los que se aplica: anclados (comun/Anclaje), guardianes finales, refuerzos de los
	 * jefes y mobs de la arena de oleadas (arena/Arena).
	 */
	public static final String ANCLADO = "heraldia_anclado", GUARDIAN = "heraldia_guardian", REFUERZO = "heraldia_refuerzo",
			ARENA = "heraldia_arena";

	private Dificultad() {
	}

	/** Niveles de la opción dificultad.nivel; {@link #NORMAL} es el comportamiento de siempre (sin modificadores). */
	public enum Nivel {
		FACIL(0.75, 0.75, 0.75), NORMAL(1, 1, 1), DIFICIL(1.5, 1.25, 1.25), HEROICA(2, 1.5, 1.5);

		public final double vida, dano, botin;

		Nivel(double vida, double dano, double botin) {
			this.vida = vida;
			this.dano = dano;
			this.botin = botin;
		}

		/** Valor de la opción (facil, normal, dificil, heroica); uno desconocido es normal (la configuración ya lo valida). */
		public static Nivel de(String valor) {
			for (Nivel n : values()) {
				if (n.id().equals(valor)) {
					return n;
				}
			}
			return NORMAL;
		}

		public String id() {
			return name().toLowerCase(Locale.ROOT);
		}

		/** Cantidad del modificador de vida (operación ADD_MULTIPLIED_TOTAL: valor final x (1 + cantidad)); 0 = sin modificador. */
		public double modVida() {
			return vida - 1;
		}

		public double modDano() {
			return dano - 1;
		}
	}

	/** ¿Se le aplica la dificultad? Mobs hostiles anclados, guardianes, refuerzos de un jefe o de la arena (no los animales anclados). */
	public static boolean aplica(Set<String> tags, boolean hostil) {
		return hostil && !tags.isEmpty() && (tags.contains(ANCLADO) || tags.contains(GUARDIAN) || tags.contains(REFUERZO)
				|| tags.contains(ARENA));
	}

	/**
	 * Extra de vida (cantidad del modificador ADD_MULTIPLIED_TOTAL) por {@code jugadores} cerca: el primero no cuenta,
	 * cada uno de más suma {@link #EXTRA_POR_JUGADOR}, con tope {@link #EXTRA_MAXIMO}.
	 */
	public static double extraJugadores(int jugadores) {
		return Math.min(EXTRA_MAXIMO, Math.max(0, jugadores - 1) * EXTRA_POR_JUGADOR);
	}

	/**
	 * Vida tras cambiar la máxima de {@code antes} a {@code despues}: se conserva la proporción (un mob entero sigue entero,
	 * uno a media vida sigue a media vida), sin pasar de la nueva máxima ni bajar a 0 si estaba vivo.
	 */
	public static float reajustarVida(float vida, double antes, double despues) {
		if (antes <= 0 || despues <= 0 || antes == despues) {
			return (float) Math.min(vida, Math.max(despues, 0));
		}
		float nueva = (float) (vida * despues / antes);
		if (vida > 0 && nueva <= 0) {
			nueva = Float.MIN_NORMAL;
		}
		return (float) Math.min(nueva, despues);
	}

	/**
	 * Cantidad de un objeto del botín con el multiplicador {@code m}: la parte fraccionaria sale con su probabilidad
	 * ({@code azar} en [0, 1)), nunca menos de 1 ni más que el máximo de la pila. Con m = 1 no cambia.
	 */
	public static int cantidad(int n, double m, int maximo, double azar) {
		if (m == 1 || n <= 0) {
			return n;
		}
		double x = n * m;
		int base = (int) Math.floor(x);
		int out = base + (azar < x - base ? 1 : 0);
		return Math.max(1, Math.min(maximo, out));
	}
}
