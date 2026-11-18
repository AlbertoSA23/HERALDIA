package io.github.albertosa23.heraldia.arena;

import java.util.Collection;
import java.util.LinkedHashSet;
import java.util.Set;
import java.util.UUID;

/**
 * Estado de una partida de la arena, sin clases del juego (lo prueban los tests): cuenta atrás, oleadas, pausas,
 * participantes y enemigos que faltan. Solo en memoria: al reiniciar el servidor no queda ninguna partida (la arena
 * quita sus mobs al cargarlos). La mueve {@link Arena} una vez por tick y con los eventos (mob muerto, jugador que cae o
 * sale del ruedo).
 */
public final class Match {
	/** Cuenta atrás antes de la primera oleada y pausa entre oleadas del cooperativo, en ticks (cada modo, la suya: {@link Mode#pause()}). */
	public static final int COUNTDOWN_TICKS = 100, PAUSE_TICKS = 200;

	public enum State { FREE, COUNTDOWN, WAVE, PAUSE }

	/** Lo que ha pasado en un tick (lo que tiene que hacer quien mueve la partida). */
	public enum Step { NOTHING, SECOND, WAVE_STARTS }

	private final int mobsPct;
	private State state = State.FREE;
	private final Set<UUID> participants = new LinkedHashSet<>();
	private int wave, total, pending, alive, counter;
	private boolean bossPending;
	/** Modo (T41) y, en el contrarreloj, cuántas oleadas hay que superar (0 en los demás). */
	private Mode mode = Mode.COOP;
	private int target;
	/** Ticks de partida (desde que empieza la primera oleada) y los que llevaba al superar la última oleada superada. */
	private long ticks, clearedTicks;

	public Match(int mobsPct) {
		this.mobsPct = mobsPct;
	}

	/** Toca la campana: empieza la cuenta atrás de una partida cooperativa (solo si no hay partida). */
	public boolean start() {
		return start(Mode.COOP, 0);
	}

	/**
	 * Empieza la cuenta atrás de una partida del modo {@code mode} (solo si no hay partida); {@code waves}: las del
	 * contrarreloj (al menos 1; en los demás modos no cuenta).
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

	/** Los que juegan (los que están en el ruedo al acabar la cuenta atrás). Falso si no hay nadie. */
	public boolean participants(Collection<UUID> players) {
		participants.clear();
		participants.addAll(players);
		return !participants.isEmpty();
	}

	/**
	 * Un tick. En la cuenta atrás y en la pausa, {@link Step#SECOND} cada segundo y {@link Step#WAVE_STARTS} al
	 * llegar a cero (la partida ya está en la oleada siguiente, con sus enemigos pendientes).
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

	/** Cuántos enemigos salen ahora (sin pasar de {@code maxAlive} vivos); quedan contados como vivos. */
	public int spawn(int maxAlive) {
		if (state != State.WAVE) {
			return 0;
		}
		int n = Waves.spawned(alive, pending, maxAlive);
		pending -= n;
		alive += n;
		return n;
	}

	/** El mini-jefe sale con la primera tanda de su oleada: true una sola vez. */
	public boolean takeBoss() {
		boolean j = bossPending;
		bossPending = false;
		return j;
	}

	/** Un enemigo que no se pudo crear: vuelve a pendientes. */
	public void fail() {
		if (alive > 0) {
			alive--;
			pending++;
		}
	}

	/** Un enemigo más que no estaba en la cuenta (los refuerzos que llama el mini-jefe). */
	public void extra() {
		if (state == State.WAVE) {
			alive++;
			total++;
		}
	}

	/**
	 * Muere (o desaparece) un enemigo. True si con él se supera la oleada: empieza la pausa del modo (en la supervivencia,
	 * de 0 ticks: la siguiente oleada empieza en el tick siguiente). En el contrarreloj, tras la última oleada la partida
	 * queda {@link #completed()} (en pausa, hasta que quien la mueve la termine).
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

	/** ¿Contrarreloj acabado (superadas todas sus oleadas)? */
	public boolean completed() {
		return mode == Mode.TIME_TRIAL && cleared() >= target;
	}

	/** Un participante cae o sale del ruedo. True si ya no queda ninguno (la partida acaba). */
	public boolean outcome(UUID player) {
		participants.remove(player);
		return inGame() && participants.isEmpty();
	}

	/** Acaba la partida y deja la arena libre para la siguiente. */
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

	/** Oleadas del contrarreloj (0 en los demás modos). */
	public int target() {
		return target;
	}

	/** Ticks de partida desde que empezó la primera oleada (la cuenta atrás no cuenta). */
	public long ticks() {
		return ticks;
	}

	/** Ticks de partida al superar la última oleada superada (lo que puntúa: el tiempo del contrarreloj). */
	public long clearedTicks() {
		return clearedTicks;
	}

	/** Oleadas ya superadas: en la pausa, la actual; durante una oleada, la anterior. */
	public int cleared() {
		return state == State.PAUSE ? wave : Math.max(0, wave - 1);
	}

	public int total() {
		return total;
	}

	/** Enemigos que quedan: los vivos y los que faltan por salir. */
	public int remaining() {
		return alive + pending;
	}

	public int alive() {
		return alive;
	}

	public int pending() {
		return pending;
	}

	/** Segundos que faltan de cuenta atrás o pausa (redondeando hacia arriba). */
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
