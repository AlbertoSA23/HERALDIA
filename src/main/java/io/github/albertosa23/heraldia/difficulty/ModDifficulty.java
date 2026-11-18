package io.github.albertosa23.heraldia.difficulty;

import java.util.Locale;
import java.util.Set;

/**
 * Pure logic of the configurable difficulty (option {@code dificultad.nivel}), without game classes: health, damage
 * and loot multipliers of each level, the extra health per nearby player and the readjustment of current health when
 * the maximum changes. {@link MobDifficulty} applies it.
 */
public final class ModDifficulty {
	/** Extra health for each additional player near the mob (dificultad.escalar_por_jugadores), and its cap. */
	public static final double EXTRA_PER_PLAYER = 0.25, EXTRA_MAX = 1.0;
	/** Radius (blocks) in which the players fighting the mob are counted. */
	public static final double PLAYER_RADIUS = 32;
	/**
	 * Tags of the mobs it applies to: anchored ones (common/Anchoring), final guardians, boss reinforcements
	 * and wave arena mobs (arena/Arena).
	 */
	public static final String ANCHORED = "heraldia_anclado", GUARDIAN = "heraldia_guardian", REINFORCEMENT = "heraldia_refuerzo",
			ARENA = "heraldia_arena";

	private ModDifficulty() {
	}

	/** Levels of the option dificultad.nivel; {@link #NORMAL} is the usual behavior (no modifiers). */
	public enum Tier {
		EASY("facil", 0.75, 0.75, 0.75), NORMAL("normal", 1, 1, 1), HARD("dificil", 1.5, 1.25, 1.25), HEROIC("heroica", 2, 1.5, 1.5);

		public final double health, damage, loot;
		/** Option value: never renamed. */
		private final String id;

		Tier(String id, double health, double damage, double loot) {
			this.id = id;
			this.health = health;
			this.damage = damage;
			this.loot = loot;
		}

		/** Value of the option (facil, normal, dificil, heroica); an unknown one is normal (the configuration already validates it). */
		public static Tier of(String value) {
			for (Tier n : values()) {
				if (n.id().equals(value)) {
					return n;
				}
			}
			return NORMAL;
		}

		public String id() {
			return id;
		}

		/** Amount of the health modifier (ADD_MULTIPLIED_TOTAL operation: final value x (1 + amount)); 0 = no modifier. */
		public double healthMod() {
			return health - 1;
		}

		public double damageMod() {
			return damage - 1;
		}
	}

	/** Does the difficulty apply to it? Anchored hostile mobs, guardians, reinforcements of a boss or of the arena (not anchored animals). */
	public static boolean applies(Set<String> tags, boolean hostile) {
		return hostile && !tags.isEmpty() && (tags.contains(ANCHORED) || tags.contains(GUARDIAN) || tags.contains(REINFORCEMENT)
				|| tags.contains(ARENA));
	}

	/**
	 * Extra health (amount of the ADD_MULTIPLIED_TOTAL modifier) for {@code players} nearby: the first does not count,
	 * each extra one adds {@link #EXTRA_PER_PLAYER}, capped at {@link #EXTRA_MAX}.
	 */
	public static double extraPlayers(int players) {
		return Math.min(EXTRA_MAX, Math.max(0, players - 1) * EXTRA_PER_PLAYER);
	}

	/**
	 * Health after changing the maximum from {@code before} to {@code after}: the ratio is kept (a full-health mob stays full,
	 * one at half health stays at half), without exceeding the new maximum or dropping to 0 if it was alive.
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
	 * Amount of a loot item with multiplier {@code m}: the fractional part comes out with its probability
	 * ({@code rng} in [0, 1)), never less than 1 nor more than the stack maximum. With m = 1 it does not change.
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
