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
public final class Partida {
	/** Cuenta atrás antes de la primera oleada y pausa entre oleadas del cooperativo, en ticks (cada modo, la suya: {@link Modo#pausa()}). */
	public static final int CUENTA_TICKS = 100, PAUSA_TICKS = 200;

	public enum Estado { LIBRE, CUENTA_ATRAS, OLEADA, PAUSA }

	/** Lo que ha pasado en un tick (lo que tiene que hacer quien mueve la partida). */
	public enum Paso { NADA, SEGUNDO, EMPIEZA_OLEADA }

	private final int mobsPct;
	private Estado estado = Estado.LIBRE;
	private final Set<UUID> participantes = new LinkedHashSet<>();
	private int oleada, total, pendientes, vivos, contador;
	private boolean jefePendiente;
	/** Modo (T41) y, en el contrarreloj, cuántas oleadas hay que superar (0 en los demás). */
	private Modo modo = Modo.COOPERATIVO;
	private int objetivo;
	/** Ticks de partida (desde que empieza la primera oleada) y los que llevaba al superar la última oleada superada. */
	private long ticks, ticksSuperada;

	public Partida(int mobsPct) {
		this.mobsPct = mobsPct;
	}

	/** Toca la campana: empieza la cuenta atrás de una partida cooperativa (solo si no hay partida). */
	public boolean empezar() {
		return empezar(Modo.COOPERATIVO, 0);
	}

	/**
	 * Empieza la cuenta atrás de una partida del modo {@code modo} (solo si no hay partida); {@code oleadas}: las del
	 * contrarreloj (al menos 1; en los demás modos no cuenta).
	 */
	public boolean empezar(Modo modo, int oleadas) {
		if (estado != Estado.LIBRE) {
			return false;
		}
		this.modo = modo;
		this.objetivo = modo == Modo.CONTRARRELOJ ? Math.max(1, oleadas) : 0;
		ticks = ticksSuperada = 0;
		estado = Estado.CUENTA_ATRAS;
		contador = CUENTA_TICKS;
		return true;
	}

	/** Los que juegan (los que están en el ruedo al acabar la cuenta atrás). Falso si no hay nadie. */
	public boolean participantes(Collection<UUID> jugadores) {
		participantes.clear();
		participantes.addAll(jugadores);
		return !participantes.isEmpty();
	}

	/**
	 * Un tick. En la cuenta atrás y en la pausa, {@link Paso#SEGUNDO} cada segundo y {@link Paso#EMPIEZA_OLEADA} al
	 * llegar a cero (la partida ya está en la oleada siguiente, con sus enemigos pendientes).
	 */
	public Paso tick() {
		if (enJuego()) {
			ticks++;
		}
		if (estado != Estado.CUENTA_ATRAS && estado != Estado.PAUSA) {
			return Paso.NADA;
		}
		contador--;
		if (contador <= 0) {
			oleada++;
			total = Oleadas.total(oleada, mobsPct);
			pendientes = total;
			vivos = 0;
			jefePendiente = Oleadas.conJefe(oleada);
			estado = Estado.OLEADA;
			return Paso.EMPIEZA_OLEADA;
		}
		return contador % 20 == 0 ? Paso.SEGUNDO : Paso.NADA;
	}

	/** Cuántos enemigos salen ahora (sin pasar de {@code maxVivos} vivos); quedan contados como vivos. */
	public int aparecer(int maxVivos) {
		if (estado != Estado.OLEADA) {
			return 0;
		}
		int n = Oleadas.aparecen(vivos, pendientes, maxVivos);
		pendientes -= n;
		vivos += n;
		return n;
	}

	/** El mini-jefe sale con la primera tanda de su oleada: true una sola vez. */
	public boolean tomarJefe() {
		boolean j = jefePendiente;
		jefePendiente = false;
		return j;
	}

	/** Un enemigo que no se pudo crear: vuelve a pendientes. */
	public void fallo() {
		if (vivos > 0) {
			vivos--;
			pendientes++;
		}
	}

	/** Un enemigo más que no estaba en la cuenta (los refuerzos que llama el mini-jefe). */
	public void extra() {
		if (estado == Estado.OLEADA) {
			vivos++;
			total++;
		}
	}

	/**
	 * Muere (o desaparece) un enemigo. True si con él se supera la oleada: empieza la pausa del modo (en la supervivencia,
	 * de 0 ticks: la siguiente oleada empieza en el tick siguiente). En el contrarreloj, tras la última oleada la partida
	 * queda {@link #completada()} (en pausa, hasta que quien la mueve la termine).
	 */
	public boolean muere() {
		if (estado != Estado.OLEADA || vivos <= 0) {
			return false;
		}
		vivos--;
		if (vivos == 0 && pendientes == 0) {
			estado = Estado.PAUSA;
			contador = modo.pausa();
			ticksSuperada = ticks;
			return true;
		}
		return false;
	}

	/** ¿Contrarreloj acabado (superadas todas sus oleadas)? */
	public boolean completada() {
		return modo == Modo.CONTRARRELOJ && superadas() >= objetivo;
	}

	/** Un participante cae o sale del ruedo. True si ya no queda ninguno (la partida acaba). */
	public boolean sale(UUID jugador) {
		participantes.remove(jugador);
		return enJuego() && participantes.isEmpty();
	}

	/** Acaba la partida y deja la arena libre para la siguiente. */
	public void terminar() {
		estado = Estado.LIBRE;
		participantes.clear();
		oleada = total = pendientes = vivos = contador = 0;
		jefePendiente = false;
		modo = Modo.COOPERATIVO;
		objetivo = 0;
		ticks = ticksSuperada = 0;
	}

	public boolean enJuego() {
		return estado == Estado.OLEADA || estado == Estado.PAUSA;
	}

	public Estado estado() {
		return estado;
	}

	public int oleada() {
		return oleada;
	}

	public Modo modo() {
		return modo;
	}

	/** Oleadas del contrarreloj (0 en los demás modos). */
	public int objetivo() {
		return objetivo;
	}

	/** Ticks de partida desde que empezó la primera oleada (la cuenta atrás no cuenta). */
	public long ticks() {
		return ticks;
	}

	/** Ticks de partida al superar la última oleada superada (lo que puntúa: el tiempo del contrarreloj). */
	public long ticksSuperada() {
		return ticksSuperada;
	}

	/** Oleadas ya superadas: en la pausa, la actual; durante una oleada, la anterior. */
	public int superadas() {
		return estado == Estado.PAUSA ? oleada : Math.max(0, oleada - 1);
	}

	public int total() {
		return total;
	}

	/** Enemigos que quedan: los vivos y los que faltan por salir. */
	public int restantes() {
		return vivos + pendientes;
	}

	public int vivos() {
		return vivos;
	}

	public int pendientes() {
		return pendientes;
	}

	/** Segundos que faltan de cuenta atrás o pausa (redondeando hacia arriba). */
	public int segundos() {
		return (contador + 19) / 20;
	}

	public Set<UUID> participantes() {
		return Set.copyOf(participantes);
	}

	public boolean participa(UUID jugador) {
		return participantes.contains(jugador);
	}
}
