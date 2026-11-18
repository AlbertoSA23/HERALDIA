package io.github.albertosa23.heraldia.caravans;

/**
 * A caravan's journey along its segment (pure logic, without the game): a state machine that the game feeds every
 * {@link #EVERY} ticks with what it sees ({@link View}) and that says what to do ({@link Step}). Phases: on the way,
 * ambushed and finished (with its {@link End}). Everything by segment vertices (0 = start, {@code vertices - 1} = arrival).
 */
public final class Journey {
	/** Every how many ticks the active caravan is checked (1 s). */
	public static final int EVERY = 20;
	/** How many blocks from the vertex count as reaching it. */
	public static final double REACHES = 2.5;
	/** With no player within {@link Caravans#PLAYER_RADIUS} blocks for this long, the caravan says goodbye. */
	public static final int FAR_TICKS = 30 * 20;
	/** The longest a journey (10 min) and an ambush (3 min) last. */
	public static final int MAX_TICKS = 10 * 60 * 20, AMBUSH_MAX_TICKS = 3 * 60 * 20;
	/** Without getting closer to the next vertex for this long, it skips to the following one; after {@link #MAX_STUCK}, it says goodbye. */
	public static final int STUCK_TICKS = 20 * 20, MAX_STUCK = 3;

	public enum Phase { ROAD, AMBUSH, END }

	/** How it ends: arrival (with or without a cleared ambush), the merchant dead, or it says goodbye (players far, no road...). */
	public enum End {
		ARRIVAL("llegada"), LOST("perdida"), FAR("lejos"), NO_ROAD("sin_camino"), STUCK("atascada"),
		TIMEOUT("tiempo"), CLEANUP("limpieza");

		public final String id;

		End(String id) {
			this.id = id;
		}

		/** Does it just say goodbye (no reward, no loss)? */
		public boolean farewell() {
			return this != ARRIVAL && this != LOST;
		}
	}

	/** What the game has to do after a step. */
	public enum Step {
		/** Nothing new: keep going towards vertex {@link #next()}. */
		CONTINUES,
		/** It has reached a vertex: the target becomes {@link #next()}. */
		ADVANCES,
		/** The ambush starts: spawn the bandits. */
		AMBUSH,
		/** No bandit is left alive: the journey goes on. */
		CLEARED,
		/** It is over ({@link #end()}): reward, loss or goodbye, and remove its entities. */
		END
	}

	/**
	 * What the game sees in a step.
	 *
	 * @param merchantAlive the merchant is still alive (if it died, the caravan is lost)
	 * @param loaded        the merchant and the next vertex are in loaded chunks (if not, the players have left)
	 * @param distNext      horizontal distance from the merchant to the next vertex
	 * @param players       players within {@link Caravans#PLAYER_RADIUS} blocks of the merchant
	 * @param bandits       bandits alive (during the ambush)
	 * @param nextRoad      there is a road at the next vertex (false: in an existing world the road ends there)
	 */
	public record View(boolean merchantAlive, boolean loaded, double distNext, int players, int bandits, boolean nextRoad) {
	}

	private final int vertices;
	private final int ambushAt;
	private Phase phase = Phase.ROAD;
	private End end;
	private int next = 1;
	private int ticks, noPlayers, inAmbush, stuck, stuckCount;
	private double best = Double.MAX_VALUE;
	private boolean ambushed, cleared;

	/**
	 * @param vertices vertices of the segment (at least 2)
	 * @param ambushAt vertex of the segment where it is ambushed (between 1 and {@code vertices - 2}), or -1 if there is no ambush
	 */
	public Journey(int vertices, int ambushAt) {
		if (vertices < 2) {
			throw new IllegalArgumentException("un tramo tiene al menos 2 vértices");
		}
		this.vertices = vertices;
		this.ambushAt = ambushAt;
	}

	/** Vertex of the segment where the ambush should go: towards the middle (between 40 and 60 % depending on {@code rng}). */
	public static int ambushPoint(int vertices, double rng) {
		int k = (int) Math.round((vertices - 1) * (0.4 + 0.2 * rng));
		return Math.max(1, Math.min(vertices - 2, k));
	}

	public Phase phase() {
		return phase;
	}

	public End end() {
		return end;
	}

	/** Vertex of the segment it is heading to. */
	public int next() {
		return next;
	}

	public int vertices() {
		return vertices;
	}

	public int ambushAt() {
		return ambushAt;
	}

	public boolean ambushed() {
		return ambushed;
	}

	/** There was an ambush and no bandit was left alive. */
	public boolean cleared() {
		return cleared;
	}

	public int ticks() {
		return ticks;
	}

	/** One step of {@link #EVERY} ticks. */
	public Step step(View v) {
		if (phase == Phase.END) {
			return Step.END;
		}
		if (!v.merchantAlive()) {
			return finish(End.LOST);
		}
		if (!v.loaded()) {
			return finish(End.FAR);
		}
		ticks += EVERY;
		noPlayers = v.players() > 0 ? 0 : noPlayers + EVERY;
		if (noPlayers >= FAR_TICKS) {
			return finish(End.FAR);
		}
		if (phase == Phase.AMBUSH) {
			if (v.bandits() <= 0) {
				cleared = true;
				phase = Phase.ROAD;
				best = Double.MAX_VALUE;
				stuck = 0;
				return Step.CLEARED;
			}
			inAmbush += EVERY;
			return inAmbush >= AMBUSH_MAX_TICKS ? finish(End.TIMEOUT) : Step.CONTINUES;
		}
		if (ticks >= MAX_TICKS) {
			return finish(End.TIMEOUT);
		}
		if (!v.nextRoad()) {
			return finish(End.NO_ROAD);
		}
		if (v.distNext() <= REACHES) {
			if (next >= vertices - 1) {
				return finish(End.ARRIVAL);
			}
			int reached = next;
			next++;
			best = Double.MAX_VALUE;
			stuck = 0;
			if (reached == ambushAt && !ambushed) {
				return startAmbush();
			}
			return Step.ADVANCES;
		}
		if (v.distNext() < best - 0.5) {
			best = v.distNext();
			stuck = 0;
			return Step.CONTINUES;
		}
		stuck += EVERY;
		if (stuck >= STUCK_TICKS) {
			stuckCount++;
			if (stuckCount > MAX_STUCK || next >= vertices - 1) {
				return finish(End.STUCK);
			}
			next++;
			best = Double.MAX_VALUE;
			stuck = 0;
			return Step.ADVANCES;
		}
		return Step.CONTINUES;
	}

	/** Ambush now (/heraldia caravan raid): only on the way and if it has not been ambushed yet. */
	public boolean forceAmbush() {
		if (phase != Phase.ROAD || ambushed) {
			return false;
		}
		startAmbush();
		return true;
	}

	private Step startAmbush() {
		ambushed = true;
		phase = Phase.AMBUSH;
		inAmbush = 0;
		return Step.AMBUSH;
	}

	/** Ends now (the merchant dead, a cleanup or the server stopping). */
	public Step finish(End f) {
		if (phase != Phase.END) {
			phase = Phase.END;
			end = f;
		}
		return Step.END;
	}
}
