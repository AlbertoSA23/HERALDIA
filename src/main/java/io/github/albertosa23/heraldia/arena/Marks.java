package io.github.albertosa23.heraldia.arena;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/**
 * Pure logic of the arena marks (T41), without game classes: how a time is written and which advancements a finished
 * match grants. The generator writes the advancements (tools/gen/arena_waves.py, ADVANCEMENTS_MODES) with the same figures.
 */
public final class Marks {
	/** Minimum time trial waves for its advancements (with fewer, by configuration, they do not count). */
	public static final int TIME_TRIAL_WAVES = 10;
	/** Time for the fast time trial advancement: 15 minutes of play. */
	public static final long TIME_TRIAL_FAST_TICKS = 15 * 60 * 20;
	/** Survival wave with an advancement. */
	public static final int SURVIVAL_WAVES = 15;

	private Marks() {
	}

	/** Ticks as "m:ss" (or "h:mm:ss" from one hour); "-" if unknown (negative). */
	public static String time(long ticks) {
		if (ticks < 0) {
			return "-";
		}
		long s = ticks / 20, h = s / 3600, m = (s % 3600) / 60, ss = s % 60;
		return h > 0 ? String.format(Locale.ROOT, "%d:%02d:%02d", h, m, ss) : String.format(Locale.ROOT, "%d:%02d", m, ss);
	}

	/** Id of the advancement for winning a week in a mode (heraldia:arena/campeon_&lt;id&gt;). */
	public static String championAdvancement(Mode m) {
		return "arena/campeon_" + m.id();
	}

	/** Advancements (ids under heraldia:) a player earns with this mark when their match in mode {@code m} ends. */
	public static List<String> advancements(Mode m, int waves, long ticks, int target) {
		List<String> out = new ArrayList<>();
		if (m == Mode.TIME_TRIAL && target >= TIME_TRIAL_WAVES && waves >= target) {
			out.add("arena/contrarreloj");
			if (ticks >= 0 && ticks <= TIME_TRIAL_FAST_TICKS) {
				out.add("arena/contrarreloj_rapido");
			}
		}
		if (m == Mode.SURVIVAL && waves >= SURVIVAL_WAVES) {
			out.add("arena/supervivencia_" + SURVIVAL_WAVES);
		}
		return out;
	}

	/**
	 * The mark to show it (text key and its arguments): a finished time trial, by its time; half-done, by its
	 * waves out of how many; coop and survival, by their waves.
	 */
	public static Object[] points(Mode m, Season.Entry e) {
		if (m == Mode.TIME_TRIAL) {
			return e.complete() ? new Object[] {"heraldia.arena.puntos.tiempo", time(e.ticks()), e.waves()}
					: new Object[] {"heraldia.arena.puntos.parcial", e.waves(), Math.max(e.target(), e.waves())};
		}
		return new Object[] {"heraldia.arena.puntos.oleadas", e.waves()};
	}
}
