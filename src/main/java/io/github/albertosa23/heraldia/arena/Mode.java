package io.github.albertosa23.heraldia.arena;

import java.util.Locale;
import java.util.Optional;

/**
 * Arena match modes (T41), without game classes. They are chosen at the start (bell or
 * /heraldia arena start &lt;mode&gt;); all keep the usual rules (no loot, reduced experience, inventory
 * kept, mini-boss every 5 waves, difficulty and profile):
 * <ul>
 * <li>{@link #COOP}: the usual one (T31), unchanged: waves until everyone falls, with a pause between them; it scores
 * the wave cleared (and its record stays on the vanilla scoreboard).</li>
 * <li>{@link #TIME_TRIAL}: N fixed waves (arena.modos.oleadas_contrarreloj) against the clock, with a short pause;
 * it ends when the last one is cleared and scores the time.</li>
 * <li>{@link #SURVIVAL}: waves without a pause between them until everyone falls; it scores the highest wave cleared.</li>
 * </ul>
 * The {@link #id()} is the command argument (English, lowercase, ASCII); {@link #key()}, the configuration one
 * (arena.modos.&lt;key&gt;) and the texts' (heraldia.arena.modo.&lt;id&gt;).
 */
public enum Mode {
	COOP("coop", "cooperativo", Match.PAUSE_TICKS),
	TIME_TRIAL("timeattack", "contrarreloj", 100),
	SURVIVAL("survival", "supervivencia", 0);

	private final String id, key;
	private final int pause;

	Mode(String id, String key, int pause) {
		this.id = id;
		this.key = key;
		this.pause = pause;
	}

	/** Command argument and key of the saved data (never changes). */
	public String id() {
		return id;
	}

	/** Name in the configuration (arena.modos.&lt;key&gt;). */
	public String key() {
		return key;
	}

	/** Pause ticks between waves (0: the next one starts on the tick after the previous one is cleared). */
	public int pause() {
		return pause;
	}

	public String option() {
		return "arena.modos." + key;
	}

	public String text() {
		return "heraldia.arena.modo." + id;
	}

	/** The mode of a command or saved-data id ({@code coop}, {@code timeattack}, {@code survival}). */
	public static Optional<Mode> fromId(String id) {
		if (id == null) {
			return Optional.empty();
		}
		String s = id.toLowerCase(Locale.ROOT);
		for (Mode m : values()) {
			if (m.id.equals(s)) {
				return Optional.of(m);
			}
		}
		return Optional.empty();
	}
}
