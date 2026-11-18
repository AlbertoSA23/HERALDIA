package io.github.albertosa23.heraldia.caravans;

/**
 * El viaje de una caravana por su tramo (lógica pura, sin el juego): una máquina de estados que el juego alimenta cada
 * {@link #EVERY} ticks con lo que ve ({@link View}) y que dice qué hacer ({@link Step}). Fases: en camino, asaltada y
 * terminada (con su {@link End}). Todo por vértices del tramo (0 = salida, {@code vertices - 1} = llegada).
 */
public final class Journey {
	/** Cada cuántos ticks se mira la caravana activa (1 s). */
	public static final int EVERY = 20;
	/** A cuántos bloques del vértice se da por alcanzado. */
	public static final double REACHES = 2.5;
	/** Sin ningún jugador a {@link Caravans#PLAYER_RADIUS} bloques durante este tiempo, la caravana se despide. */
	public static final int FAR_TICKS = 30 * 20;
	/** Lo más que dura un viaje (10 min) y un asalto (3 min). */
	public static final int MAX_TICKS = 10 * 60 * 20, AMBUSH_MAX_TICKS = 3 * 60 * 20;
	/** Sin acercarse al vértice siguiente durante este tiempo, se salta al siguiente; tras {@link #MAX_STUCK}, se despide. */
	public static final int STUCK_TICKS = 20 * 20, MAX_STUCK = 3;

	public enum Phase { ROAD, AMBUSH, END }

	/** Cómo acaba: llegada (con o sin asalto superado), el mercader muerto, o se despide (jugadores lejos, sin camino...). */
	public enum End {
		ARRIVAL("llegada"), LOST("perdida"), FAR("lejos"), NO_ROAD("sin_camino"), STUCK("atascada"),
		TIMEOUT("tiempo"), CLEANUP("limpieza");

		public final String id;

		End(String id) {
			this.id = id;
		}

		/** ¿Se despide sin más (ni premio ni pérdida)? */
		public boolean farewell() {
			return this != ARRIVAL && this != LOST;
		}
	}

	/** Qué tiene que hacer el juego tras un paso. */
	public enum Step {
		/** Nada nuevo: seguir hacia el vértice {@link #next()}. */
		CONTINUES,
		/** Ha alcanzado un vértice: el objetivo pasa a {@link #next()}. */
		ADVANCES,
		/** Empieza el asalto: que salgan los bandidos. */
		AMBUSH,
		/** Ya no queda ningún bandido vivo: sigue el viaje. */
		CLEARED,
		/** Se acabó ({@link #end()}): recompensa, pérdida o despedida, y quitar sus entidades. */
		END
	}

	/**
	 * Lo que ve el juego en un paso.
	 *
	 * @param mercaderVivo     el mercader sigue vivo (si murió, la caravana se pierde)
	 * @param cargado          el mercader y el vértice siguiente están en chunks cargados (si no, los jugadores se han ido)
	 * @param distSiguiente    distancia en el plano del mercader al vértice siguiente
	 * @param jugadores        jugadores a {@link Caravans#PLAYER_RADIUS} bloques del mercader
	 * @param bandidos         bandidos vivos (en el asalto)
	 * @param caminoSiguiente  hay camino en el vértice siguiente (false: en un mundo existente el camino acaba ahí)
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
	 * @param vertices vértices del tramo (al menos 2)
	 * @param asaltoEn vértice del tramo en el que la asaltan (entre 1 y {@code vertices - 2}), o -1 si no hay asalto
	 */
	public Journey(int vertices, int ambushAt) {
		if (vertices < 2) {
			throw new IllegalArgumentException("un tramo tiene al menos 2 vértices");
		}
		this.vertices = vertices;
		this.ambushAt = ambushAt;
	}

	/** Vértice del tramo en el que conviene poner el asalto: hacia la mitad (entre el 40 y el 60 % según {@code rng}). */
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

	/** Vértice del tramo hacia el que va. */
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

	/** Hubo asalto y no quedó ningún bandido vivo. */
	public boolean cleared() {
		return cleared;
	}

	public int ticks() {
		return ticks;
	}

	/** Un paso de {@link #EVERY} ticks. */
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

	/** Asalto ya (/heraldia caravan raid): solo en camino y si aún no la han asaltado. */
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

	/** Termina ya (el mercader muerto, una limpieza o el servidor que se para). */
	public Step finish(End f) {
		if (phase != Phase.END) {
			phase = Phase.END;
			end = f;
		}
		return Step.END;
	}
}
