package io.github.albertosa23.heraldia.difficulty;

import java.util.Locale;
import java.util.Set;

/**
 * Lógica pura de la dificultad configurable (opción {@code dificultad.tier}), sin clases del juego: multiplicadores de
 * vida, daño y botín de cada nivel, el extra de vida por jugadores cercanos y el reajuste de la vida actual cuando cambia
 * la máxima. La aplica {@link MobDifficulty}.
 */
public final class ModDifficulty {
	/** Extra de vida por cada jugador de más cerca del mob (dificultad.escalar_por_jugadores), y su tope. */
	public static final double EXTRA_PER_PLAYER = 0.25, EXTRA_MAX = 1.0;
	/** Radio (bloques) en el que se cuentan los jugadores que luchan contra el mob. */
	public static final double PLAYER_RADIUS = 32;
	/**
	 * Etiquetas (Tags) de los mobs a los que se aplica: anclados (comun/Anclaje), guardianes finales, refuerzos de los
	 * jefes y mobs de la arena de oleadas (arena/Arena).
	 */
	public static final String ANCHORED = "heraldia_anclado", GUARDIAN = "heraldia_guardian", REINFORCEMENT = "heraldia_refuerzo",
			ARENA = "heraldia_arena";

	private ModDifficulty() {
	}

	/** Niveles de la opción dificultad.nivel; {@link #NORMAL} es el comportamiento de siempre (sin modificadores). */
	public enum Tier {
		EASY(0.75, 0.75, 0.75), NORMAL(1, 1, 1), HARD(1.5, 1.25, 1.25), HEROIC(2, 1.5, 1.5);

		public final double health, damage, loot;

		Tier(double health, double damage, double loot) {
			this.health = health;
			this.damage = damage;
			this.loot = loot;
		}

		/** Valor de la opción (facil, normal, dificil, heroica); uno desconocido es normal (la configuración ya lo valida). */
		public static Tier of(String value) {
			for (Tier n : values()) {
				if (n.id().equals(value)) {
					return n;
				}
			}
			return NORMAL;
		}

		public String id() {
			return name().toLowerCase(Locale.ROOT);
		}

		/** Cantidad del modificador de vida (operación ADD_MULTIPLIED_TOTAL: valor final x (1 + cantidad)); 0 = sin modificador. */
		public double healthMod() {
			return health - 1;
		}

		public double damageMod() {
			return damage - 1;
		}
	}

	/** ¿Se le aplica la dificultad? Mobs hostiles anclados, guardianes, refuerzos de un jefe o de la arena (no los animales anclados). */
	public static boolean applies(Set<String> tags, boolean hostile) {
		return hostile && !tags.isEmpty() && (tags.contains(ANCHORED) || tags.contains(GUARDIAN) || tags.contains(REINFORCEMENT)
				|| tags.contains(ARENA));
	}

	/**
	 * Extra de vida (cantidad del modificador ADD_MULTIPLIED_TOTAL) por {@code players} cerca: el primero no cuenta,
	 * cada uno de más suma {@link #EXTRA_PER_PLAYER}, con tope {@link #EXTRA_MAX}.
	 */
	public static double extraPlayers(int players) {
		return Math.min(EXTRA_MAX, Math.max(0, players - 1) * EXTRA_PER_PLAYER);
	}

	/**
	 * Vida tras cambiar la máxima de {@code before} a {@code after}: se conserva la proporción (un mob entero sigue entero,
	 * uno a media vida sigue a media vida), sin pasar de la nueva máxima ni bajar a 0 si estaba vivo.
	 */
	public static float readjustHealth(float health, double before, double after) {
		if (before <= 0 || after <= 0 || before == after) {
			return (float) Math.min(health, Math.max(after, 0));
		}
		float fresh = (float) (health * after / before);
		if (health > 0 && fresh <= 0) {
			fresh = Float.MIN_NORMAL;
		}
		return (float) Math.min(fresh, after);
	}

	/**
	 * Cantidad de un objeto del botín con el multiplicador {@code m}: la parte fraccionaria sale con su probabilidad
	 * ({@code rng} en [0, 1)), nunca menos de 1 ni más que el máximo de la pila. Con m = 1 no cambia.
	 */
	public static int amount(int n, double m, int maximum, double rng) {
		if (m == 1 || n <= 0) {
			return n;
		}
		double x = n * m;
		int base = (int) Math.floor(x);
		int out = base + (rng < x - base ? 1 : 0);
		return Math.max(1, Math.min(maximum, out));
	}
}
