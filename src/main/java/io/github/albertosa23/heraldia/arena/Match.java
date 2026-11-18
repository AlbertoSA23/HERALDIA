package io.github.albertosa23.heraldia.arena;

import java.util.Collection;
import java.util.LinkedHashSet;
import java.util.Set;
import java.util.UUID;

/**
 * State of an arena match, without game classes (the tests check it): countdown, waves, pauses,
 * participants and enemies left. In memory only: when the server restarts there is no match left (the arena
 * removes its mobs when they load). {@link Arena} moves it once per tick and with the events (mob killed, player who
 * falls or leaves the ring).
 */
public final class Match {
	/** Countdown before the first wave and pause between coop waves, in ticks (each mode has its own: {@link Mode#pause()}). */
	public static final int COUNTDOWN_TICKS = 100, PAUSE_TICKS = 200;

	public enum State { FREE, COUNTDOWN, WAVE, PAUSE }

	/** What happened in a tick (what whoever moves the match has to do). */
	public enum Step { NOTHING, SECOND, WAVE_STARTS }

	private final int mobsPct;
	private State state = State.FREE;
	private final Set<UUID> participants = new LinkedHashSet<>();
	private int wave, total, pending, alive, counter;
	private boolean bossPending;
	/** Mode (T41) and, in the time trial, how many waves must be cleared (0 in the others). */
	private Mode mode = Mode.COOP;
	private int target;
	/** Match ticks (since the first wave started) and the ones it had when the last cleared wave was cleared. */
	private long ticks, clearedTicks;

	public Match(int mobsPct) {
		this.mobsPct = mobsPct;
	}

	/** Rings the bell: starts the countdown of a coop match (only if there is no match). */
	public boolean start() {
		return start(Mode.COOP, 0);
	}

	/**
	 * Starts the countdown of a match in mode {@code mode} (only if there is no match); {@code waves}: the time
	 * trial's (at least 1; in the other modes it does not count).
	 */
	public boolean start(Mode mode, int waves) {
		if (state != State.FREE) {
			return false;
		}
		this.mode = mode;
		this.target = mode == Mode.TIME_TRIAL ? Math.max(1, waves) : 0;
		ticks = clearedTicks = 0;
		state = State.COUNTDOWN;
		counter = COUNTDOWN_TICKS;
		return true;
	}

	/** Those who play (those in the ring when the countdown ends). False if nobody is there. */
	public boolean participants(Collection<UUID> players) {
		participants.clear();
		participants.addAll(players);
		return !participants.isEmpty();
	}

	/**
	 * One tick. During the countdown and the pause, {@link Step#SECOND} every second and {@link Step#WAVE_STARTS} on
	 * reaching zero (the match is already on the next wave, with its enemies pending).
	 */
	public Step tick() {
		if (inGame()) {
			ticks++;
		}
		if (state != State.COUNTDOWN && state != State.PAUSE) {
			return Step.NOTHING;
		}
		counter--;
		if (counter <= 0) {
			wave++;
			total = Waves.total(wave, mobsPct);
			pending = total;
			alive = 0;
			bossPending = Waves.withBoss(wave);
			state = State.WAVE;
			return Step.WAVE_STARTS;
		}
		return counter % 20 == 0 ? Step.SECOND : Step.NOTHING;
	}

	/** How many enemies spawn now (without going over {@code maxAlive} alive); they are counted as alive. */
	public int spawn(int maxAlive) {
		if (state != State.WAVE) {
			return 0;
		}
		int n = Waves.spawned(alive, pending, maxAlive);
		pending -= n;
		alive += n;
		return n;
	}

	/** The mini-boss spawns with the first batch of its wave: true only once. */
	public boolean takeBoss() {
		boolean j = bossPending;
		bossPending = false;
		return j;
	}

	/** An enemy that could not be created: back to pending. */
	public void fail() {
		if (alive > 0) {
			alive--;
			pending++;
		}
	}

	/** One more enemy that was not in the count (the reinforcements the mini-boss calls). */
	public void extra() {
		if (state == State.WAVE) {
			alive++;
			total++;
		}
	}

	/**
	 * An enemy dies (or disappears). True if that clears the wave: the mode's pause starts (in survival, of 0 ticks: the
	 * next wave starts on the next tick). In the time trial, after the last wave the match is
	 * {@link #completed()} (paused, until whoever moves it ends it).
	 */
	public boolean dies() {
		if (state != State.WAVE || alive <= 0) {
			return false;
		}
		alive--;
		if (alive == 0 && pending == 0) {
			state = State.PAUSE;
			counter = mode.pause();
			clearedTicks = ticks;
			return true;
		}
		return false;
	}

	/** Time trial finished (all its waves cleared)? */
	public boolean completed() {
		return mode == Mode.TIME_TRIAL && cleared() >= target;
	}

	/** A participant falls or leaves the ring. True if none is left (the match ends). */
	public boolean outcome(UUID player) {
		participants.remove(player);
		return inGame() && participants.isEmpty();
	}

	/** Ends the match and leaves the arena free for the next one. */
	public void finish() {
		state = State.FREE;
		participants.clear();
		wave = total = pending = alive = counter = 0;
		bossPending = false;
		mode = Mode.COOP;
		target = 0;
		ticks = clearedTicks = 0;
	}

	public boolean inGame() {
		return state == State.WAVE || state == State.PAUSE;
	}

	public State state() {
		return state;
	}

	public int wave() {
		return wave;
	}

	public Mode mode() {
		return mode;
	}

	/** Time trial waves (0 in the other modes). */
	public int target() {
		return target;
	}

	/** Match ticks since the first wave started (the countdown does not count). */
	public long ticks() {
		return ticks;
	}

	/** Match ticks when the last cleared wave was cleared (what scores: the time trial's time). */
	public long clearedTicks() {
		return clearedTicks;
	}

	/** Waves already cleared: during the pause, the current one; during a wave, the previous one. */
	public int cleared() {
		return state == State.PAUSE ? wave : Math.max(0, wave - 1);
	}

	public int total() {
		return total;
	}

	/** Enemies left: the alive ones and those still to spawn. */
	public int remaining() {
		return alive + pending;
	}

	public int alive() {
		return alive;
	}

	public int pending() {
		return pending;
	}

	/** Seconds left of countdown or pause (rounded up). */
	public int seconds() {
		return (counter + 19) / 20;
	}

	public Set<UUID> participants() {
		return Set.copyOf(participants);
	}

	public boolean participates(UUID player) {
		return participants.contains(player);
	}
}
