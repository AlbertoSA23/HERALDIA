package io.github.albertosa23.heraldia.bosses;

import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import org.jspecify.annotations.Nullable;

/**
 * Pure logic of the guardian phases (no game classes, for the tests). The state lives in the guardian's own
 * tags, which the game saves with it: {@code heraldia_fase.2} and {@code heraldia_fase.3}. So an
 * already generated guardian (with {@link #GUARDIAN}) gains the phases without extra data, and each phase happens only
 * once even if it heals, the chunk reloads or the server restarts.
 */
public final class Phases {
	/** Tag of the final guardians (piezas.GUARDIAN_TAG). */
	public static final String GUARDIAN = "heraldia_guardian";
	/** Prefix of the tag with the id of its unique (pack.tag_guardians): {@code heraldia_guardian.<id>}. */
	public static final String UNIQUE = GUARDIAN + ".";
	/** Prefix of the tag of each phase reached: {@code heraldia_fase.<n>}. */
	public static final String PHASE = "heraldia_fase.";
	/** Tag of the reinforcements (they are not guardians: they do not change phase nor drop their loot). */
	public static final String REINFORCEMENT = "heraldia_refuerzo";
	/** Phase 2 when dropping below 66 % health; phase 3 below 33 %. */
	public static final float THRESHOLD_2 = 0.66f;
	public static final float THRESHOLD_3 = 0.33f;
	public static final int MAX_PHASE = 3;
	/** Reinforcements alive at once near a guardian, at most. */
	public static final int MAX_ALIVE = 4;

	private Phases() {
	}

	/** Final guardian? (early exit: almost no entity has tags). */
	public static boolean isGuardian(Set<String> tags) {
		return !tags.isEmpty() && tags.contains(GUARDIAN);
	}

	/** Id of the guardian's unique ({@code heraldia_guardian.<id>}), or null if it has none. */
	public static @Nullable String unique(Set<String> tags) {
		for (String t : tags) {
			if (t.startsWith(UNIQUE) && t.length() > UNIQUE.length()) {
				return t.substring(UNIQUE.length());
			}
		}
		return null;
	}

	/** Phase that matches the health: 1 above 66 %, 2 below, 3 below 33 %. */
	public static int healthPhase(float health, float max) {
		if (!(max > 0)) {
			return 1;
		}
		float r = health / max;
		return r < THRESHOLD_3 ? 3 : r < THRESHOLD_2 ? 2 : 1;
	}

	/** Highest phase already reached according to its tags (1 if none). */
	public static int reached(Set<String> tags) {
		for (int f = MAX_PHASE; f >= 2; f--) {
			if (tags.contains(PHASE + f)) {
				return f;
			}
		}
		return 1;
	}

	/**
	 * Phases to apply now, in order: those matching the health that do not have their tag yet. A hit
	 * that drops from 100 % to 20 % gives both. Empty if phases and reinforcements are disabled or if it already died.
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

	/** How many of the {@code listed} reinforcements are called with {@code alive} already nearby (cap {@link #MAX_ALIVE}). */
	public static int howMany(int listed, int alive) {
		return howMany(listed, alive, 100, MAX_ALIVE);
	}

	/**
	 * With the options jefes.refuerzos.porcentaje (of the listed ones, rounding; 100 = the usual) and
	 * jefes.refuerzos.maximo_vivos (the cap; 4 = the usual). With 100 and 4, the same as {@link #howMany(int, int)}.
	 */
	public static int howMany(int listed, int alive, int percent, int maximum) {
		int requested = (int) Math.round(listed * percent / 100.0);
		return Math.max(0, Math.min(requested, maximum - alive));
	}

	/**
	 * Key of the action bar message when entering {@code phase}: with phases enabled, the phase's (with
	 * "calls its reinforcements" if it called them); with reinforcements only, the reinforcements'; if there is nothing to tell, null.
	 */
	public static @Nullable String key(int phase, boolean phases, int called) {
		if (phases) {
			return "heraldia.jefes.fase." + phase + (called > 0 ? ".refuerzos" : "");
		}
		return called > 0 ? "heraldia.jefes.refuerzos" : null;
	}

	/** Radius (blocks) in which a player sees the bar and gets the notices; they lose it when farther than {@link #OUTSIDE_RADIUS}. */
	public static final int RADIUS = 32;
	public static final int OUTSIDE_RADIUS = 48;

	/** Is the bar shown to a player at that squared distance? true: add; false: remove; null: leave as is. */
	public static @Nullable Boolean sees(double distance2) {
		if (distance2 <= (double) RADIUS * RADIUS) {
			return Boolean.TRUE;
		}
		return distance2 > (double) OUTSIDE_RADIUS * OUTSIDE_RADIUS ? Boolean.FALSE : null;
	}

	/** Bar progress (0-1). */
	public static float progress(float health, float max) {
		return max > 0 ? Math.clamp(health / max, 0f, 1f) : 0f;
	}
}
