package io.github.albertosa23.heraldia.tesoro;

import java.util.Set;

/**
 * Qué pasa al usar un mapa del tesoro: lógica pura (AvanceTest). Lejos de la marca, solo se dice hacia dónde queda; en una
 * estructura ({@value #LLEGADA_ESTRUCTURA} bloques), la siguiente pista; en el tesoro ({@value #LLEGADA_TESORO}), se
 * entierra el cofre. Una cadena completada (o cuya semilla ya tiene cofre en el mundo, p. ej. una copia del mapa hecha
 * en la mesa de cartografía) no vuelve a dar nada: cada cadena se completa una sola vez.
 */
public final class Avance {
	public static final int LLEGADA_ESTRUCTURA = 40, LLEGADA_TESORO = 32;

	private Avance() {
	}

	public enum Resultado {
		LEJOS, SIGUIENTE, COFRE, HECHA
	}

	public static Resultado evaluar(Cadena c, int px, int pz, Set<Long> completadas) {
		if (c.completada() || completadas.contains(c.semilla())) {
			return Resultado.HECHA;
		}
		Destino d = c.actual();
		int llegada = d.tipo() == Destino.Tipo.TESORO ? LLEGADA_TESORO : LLEGADA_ESTRUCTURA;
		if (d.distanciaSq(px, pz) > (long) llegada * llegada) {
			return Resultado.LEJOS;
		}
		return d.tipo() == Destino.Tipo.TESORO ? Resultado.COFRE : Resultado.SIGUIENTE;
	}

	/** Distancia redondeada a la decena (lo que se dice al jugador). */
	public static int distanciaAproximada(Destino d, int px, int pz) {
		return (int) (Math.round(Math.sqrt(d.distanciaSq(px, pz)) / 10.0) * 10);
	}
}
