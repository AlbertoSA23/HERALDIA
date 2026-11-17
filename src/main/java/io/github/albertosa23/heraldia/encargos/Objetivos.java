package io.github.albertosa23.heraldia.encargos;

import java.util.List;

/**
 * Cuándo se cumple cada tipo de encargo (lógica pura, T38). El juego solo aporta los hechos: un guardián muerto (su id
 * de única y dónde), la posición de un jugador cada cierto tiempo, la oleada de la arena superada o lo que lleva en el
 * inventario al entregar.
 */
public final class Objetivos {
	/** Un guardián de la única pedida muerto a menos de esto del sitio del encargo es el suyo (las únicas del mismo tipo
	 *  salen a miles de bloques: no hay dos tan cerca). */
	public static final int RADIO_GUARDIAN = 320;
	/** Distancia horizontal al sitio que cuenta como haber llegado: a una estructura mediana o una mina, y a una aldea. */
	public static final int RADIO_LUGAR = 40, RADIO_ALDEA = 64;
	/** Jugadores a esta distancia del guardián cuando muere cuentan como participantes (además de quien lo mata). */
	public static final int RADIO_PARTICIPA = 64;
	/** Cada cuántos ticks se mira si los jugadores con encargos de ir a un sitio han llegado (2 s). */
	public static final int CADA_TICKS = 40;

	private Objetivos() {
	}

	static boolean cerca(int x, int z, int tx, int tz, int radio) {
		long dx = x - tx, dz = z - tz;
		return dx * dx + dz * dz <= (long) radio * radio;
	}

	/** ¿La muerte del guardián de la única {@code unica} en (x, z) cumple el encargo? */
	public static boolean guardian(Encargo e, String unica, int x, int z) {
		return e.tipo() == Tipo.GUARDIAN && e.objetivo().equals(unica) && cerca(x, z, e.x(), e.z(), RADIO_GUARDIAN);
	}

	/** ¿Estar en (x, z) cumple el encargo (explorar o viajar)? */
	public static boolean llegada(Encargo e, int x, int z) {
		return switch (e.tipo()) {
			case EXPLORAR -> cerca(x, z, e.x(), e.z(), RADIO_LUGAR);
			case VIAJE -> cerca(x, z, e.x(), e.z(), RADIO_ALDEA);
			default -> false;
		};
	}

	/** ¿Superar la oleada {@code oleada} cumple el encargo? */
	public static boolean oleada(Encargo e, int oleada) {
		return e.tipo() == Tipo.ARENA && oleada >= e.cantidad();
	}

	/** ¿Hay algún aceptado sin cumplir que se cumpla llegando a un sitio? (salida temprana del repaso periódico) */
	public static boolean esperaLlegada(List<Datos.Activo> activos) {
		for (Datos.Activo a : activos) {
			if (!a.cumplido() && (a.encargo().tipo() == Tipo.EXPLORAR || a.encargo().tipo() == Tipo.VIAJE)) {
				return true;
			}
		}
		return false;
	}

	/** ¿Se puede entregar ya? Los de traer, si lleva bastantes ({@code tiene}); los demás, si están cumplidos. */
	public static boolean entregable(Datos.Activo a, int tiene) {
		return a.encargo().tipo() == Tipo.TRAER ? tiene >= a.encargo().cantidad() : a.cumplido();
	}

	/** Rumbo de 8 puntos de (x, z) a (tx, tz) (norte = -z): «n», «ne», «e»... (las claves de heraldia.info.dir.*). */
	public static String rumbo(int x, int z, int tx, int tz) {
		String[] dirs = {"s", "so", "o", "no", "n", "ne", "e", "se"};
		double angle = Math.toDegrees(Math.atan2(-(tx - x), tz - z));
		return dirs[Math.floorMod((int) Math.round(angle / 45.0), 8)];
	}

	/** Distancia aproximada (redondeada a 100 bloques, al menos 100): una pista, no unas coordenadas. */
	public static int aproximada(int x, int z, int tx, int tz) {
		double d = Math.hypot(tx - x, tz - z);
		return (int) Math.max(100, Math.round(d / 100.0) * 100);
	}
}
