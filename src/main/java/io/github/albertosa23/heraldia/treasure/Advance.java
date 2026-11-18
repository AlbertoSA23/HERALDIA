package io.github.albertosa23.heraldia.treasure;

import java.util.Set;

/**
 * Qué pasa al usar un mapa del tesoro: lógica pura (AvanceTest). Lejos de la marca, solo se dice hacia dónde queda; en una
 * estructura ({@value #STRUCTURE_ARRIVAL} bloques), la siguiente pista; en el tesoro ({@value #TREASURE_ARRIVAL}), se
 * entierra el cofre. Una cadena completada (o cuya semilla ya tiene cofre en el mundo, p. ej. una copia del mapa hecha
 * en la mesa de cartografía) no vuelve a dar nada: cada cadena se completa una sola vez.
 */
public final class Advance {
	public static final int STRUCTURE_ARRIVAL = 40, TREASURE_ARRIVAL = 32;

	private Advance() {
	}

	public enum Result {
		FAR, NEXT, CHEST, DONE
	}

	public static Result evaluateAt(Chain c, int px, int pz, Set<Long> completed) {
		if (c.completed() || completed.contains(c.seed())) {
			return Result.DONE;
		}
		Destination d = c.actual();
		int arrival = d.type() == Destination.Type.TREASURE ? TREASURE_ARRIVAL : STRUCTURE_ARRIVAL;
		if (d.distanceSq(px, pz) > (long) arrival * arrival) {
			return Result.FAR;
		}
		return d.type() == Destination.Type.TREASURE ? Result.CHEST : Result.NEXT;
	}

	/** Distancia redondeada a la decena (lo que se dice al jugador). */
	public static int approximateDistance(Destination d, int px, int pz) {
		return (int) (Math.round(Math.sqrt(d.distanceSq(px, pz)) / 10.0) * 10);
	}
}
