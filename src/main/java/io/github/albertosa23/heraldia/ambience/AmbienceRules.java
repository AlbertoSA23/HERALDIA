package io.github.albertosa23.heraldia.ambience;

/**
 * Pure logic of the ambient effects (no game classes, for the tests): when the village bell rings, when a player may hear
 * an effect again, where a distant sound is played from and how long until the next drip in a mine gallery. The game side
 * is {@link Ambience}.
 */
public final class AmbienceRules {
	/** Ticks between two checks (5 s): nothing runs on the other ticks. */
	public static final int PERIOD = 100;
	/** One in-game day and half of it, in world-clock ticks: 0 is sunrise, 12,000 sunset. */
	public static final long DAY = 24_000, HALF_DAY = 12_000;
	/**
	 * The bell rings in the first {@code BELL_WINDOW} ticks of the morning or the evening; wider than {@link #PERIOD} so
	 * that one check always falls inside, and {@link #bellHalfDay} keeps it to one peal per half-day.
	 */
	public static final long BELL_WINDOW = 2L * PERIOD;
	/** Strikes of a peal and ticks between them. */
	public static final int BELL_STRIKES = 3, BELL_GAP = 30;
	/** A player does not hear the bell again before this (ticks): twice a day at most, even with /time set. */
	public static final long BELL_COOLDOWN = 5 * 60 * 20;
	/** The bell is heard from at most this far (blocks): beyond it, it is played this far away, quieter. */
	public static final double BELL_REACH = 24;
	/** Lighthouse siren: heard within this distance (blocks, horizontal) of the lighthouse. */
	public static final int SIREN_RADIUS = 160;
	/** A player does not hear the siren again before this (ticks). */
	public static final long SIREN_COOLDOWN = 3 * 60 * 20;
	/** With no lighthouse near a player, the next search for one waits this long (ticks). */
	public static final long SIREN_SEARCH_COOLDOWN = 30 * 20;
	/** Below sea level minus this a player is in a cave or under water: no siren. */
	public static final int SIREN_DEPTH = 4;
	/** Mine galleries: ticks between two drips heard by a player (random between both). */
	public static final int DRIP_MIN = 20 * 20, DRIP_MAX = 45 * 20;
	/** A player does not hear the echo again before this (ticks). */
	public static final long ECHO_COOLDOWN = 4 * 60 * 20;
	/** Chance (%) that a mine cue is the echo instead of a drip, when the echo is ready. */
	public static final int ECHO_PERCENT = 25;
	/** How far (blocks) above the player's head a ceiling is looked for, and how far the echo comes from. */
	public static final int CEILING_SEARCH = 6, ECHO_DISTANCE = 12;
	/** Random columns tried for the drip before the player's own. */
	public static final int CEILING_TRIES = 3;
	/** "Never heard" in the per-player times. */
	public static final long NEVER = Long.MIN_VALUE;

	/** What a mine gallery plays. */
	public enum MineCue {
		NONE, DRIP, ECHO
	}

	private AmbienceRules() {
	}

	/** Is this tick a check? */
	public static boolean checkTick(long tick) {
		return tick % PERIOD == 0;
	}

	/**
	 * The half-day (clock / 12,000) whose bell rings now, or -1: the clock is in the first {@link #BELL_WINDOW} ticks of a
	 * morning or an evening and that half-day has not rung yet ({@code lastHalfDay}). Waking up after sleeping puts the
	 * clock on a sunrise, so the bell greets the morning; with the daylight cycle stopped it rings once and no more.
	 */
	public static long bellHalfDay(long clock, long lastHalfDay) {
		long half = Math.floorDiv(clock, HALF_DAY);
		return Math.floorMod(clock, HALF_DAY) < BELL_WINDOW && half != lastHalfDay ? half : -1;
	}

	/** Morning (true) or evening of a half-day. */
	public static boolean morning(long halfDay) {
		return Math.floorMod(halfDay, 2L) == 0;
	}

	/** May a player hear an effect again at {@code now}, if they last heard it at {@code last}? */
	public static boolean ready(long now, long last, long cooldown) {
		return last == NEVER || now - last >= cooldown || now < last;      // now < last: the tick count started over
	}

	/** The siren sounds in bad weather: rain or a thunderstorm (vanilla has no fog weather; rain is its low visibility). */
	public static boolean sirenWeather(boolean raining, boolean thundering) {
		return raining || thundering;
	}

	/**
	 * Where a sound coming from {@code (sx, sy, sz)} is played for a listener at {@code (px, py, pz)}: at the source if it is
	 * within {@code reach}; otherwise on the line to it, {@code reach} blocks from the listener (the same direction, quieter).
	 */
	public static double[] source(double px, double py, double pz, double sx, double sy, double sz, double reach) {
		double dx = sx - px, dy = sy - py, dz = sz - pz;
		double d = Math.sqrt(dx * dx + dy * dy + dz * dz);
		if (d <= reach || d == 0) {
			return new double[] {sx, sy, sz};
		}
		double k = reach / d;
		return new double[] {px + dx * k, py + dy * k, pz + dz * k};
	}

	/** Horizontal distance squared. */
	public static double horizontal2(double ax, double az, double bx, double bz) {
		double dx = ax - bx, dz = az - bz;
		return dx * dx + dz * dz;
	}

	/** Ticks until the next mine cue for a player, from a uniform roll in [0, 1). */
	public static int nextMineCue(double roll) {
		return DRIP_MIN + (int) Math.floor(Math.clamp(roll, 0, 0.999999) * (DRIP_MAX - DRIP_MIN + 1));
	}

	/**
	 * Which mine cue plays when it is a player's turn: the echo now and then ({@link #ECHO_PERCENT}, if it is ready), else a
	 * drip if there is a ceiling to drip from, else nothing. {@code roll} in [0, 100).
	 */
	public static MineCue mineCue(int roll, boolean echoReady, boolean ceiling) {
		if (echoReady && roll < ECHO_PERCENT) {
			return MineCue.ECHO;
		}
		return ceiling ? MineCue.DRIP : MineCue.NONE;
	}
}
