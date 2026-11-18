package io.github.albertosa23.heraldia.quests;

import java.util.List;

/**
 * Cuándo se cumple cada tipo de encargo (lógica pura, T38). El juego solo aporta los hechos: un guardián muerto (su id
 * de única y dónde), la posición de un jugador cada cierto tiempo, la oleada de la arena superada o lo que lleva en el
 * inventario al entregar.
 */
public final class Objectives {
	/** Un guardián de la única pedida muerto a menos de esto del sitio del encargo es el suyo (las únicas del mismo tipo
	 *  salen a miles de bloques: no hay dos tan cerca). */
	public static final int GUARDIAN_RADIUS = 320;
	/** Distancia horizontal al sitio que cuenta como haber llegado: a una estructura mediana o una mina, y a una aldea. */
	public static final int PLACE_RADIUS = 40, VILLAGE_RADIUS = 64;
	/** Jugadores a esta distancia del guardián cuando muere cuentan como participantes (además de quien lo mata). */
	public static final int PARTICIPATE_RADIUS = 64;
	/** Cada cuántos ticks se mira si los jugadores con encargos de ir a un sitio han llegado (2 s). */
	public static final int EVERY_TICKS = 40;

	private Objectives() {
	}

	static boolean near(int x, int z, int tx, int tz, int radius) {
		long dx = x - tx, dz = z - tz;
		return dx * dx + dz * dz <= (long) radius * radius;
	}

	/** ¿La muerte del guardián de la única {@code unique} en (x, z) cumple el encargo? */
	public static boolean guardian(Quest e, String unique, int x, int z) {
		return e.type() == Type.GUARDIAN && e.target().equals(unique) && near(x, z, e.x(), e.z(), GUARDIAN_RADIUS);
	}

	/** ¿Estar en (x, z) cumple el encargo (explorar o viajar)? */
	public static boolean arrival(Quest e, int x, int z) {
		return switch (e.type()) {
			case EXPLORE -> near(x, z, e.x(), e.z(), PLACE_RADIUS);
			case JOURNEY -> near(x, z, e.x(), e.z(), VILLAGE_RADIUS);
			default -> false;
		};
	}

	/** ¿Superar la oleada {@code wave} cumple el encargo? */
	public static boolean wave(Quest e, int wave) {
		return e.type() == Type.ARENA && wave >= e.amount();
	}

	/** ¿Hay algún aceptado sin cumplir que se cumpla llegando a un sitio? (salida temprana del repaso periódico) */
	public static boolean awaitsArrival(List<Data.Active> active) {
		for (Data.Active a : active) {
			if (!a.met() && (a.quest().type() == Type.EXPLORE || a.quest().type() == Type.JOURNEY)) {
				return true;
			}
		}
		return false;
	}

	/** ¿Se puede entregar ya? Los de traer, si lleva bastantes ({@code has}); los demás, si están cumplidos. */
	public static boolean deliverable(Data.Active a, int has) {
		return a.quest().type() == Type.BRING ? has >= a.quest().amount() : a.met();
	}

	/** Rumbo de 8 puntos de (x, z) a (tx, tz) (norte = -z): «n», «ne», «e»... (las claves de heraldia.info.dir.*). */
	public static String bearing(int x, int z, int tx, int tz) {
		String[] dirs = {"s", "so", "o", "no", "n", "ne", "e", "se"};
		double angle = Math.toDegrees(Math.atan2(-(tx - x), tz - z));
		return dirs[Math.floorMod((int) Math.round(angle / 45.0), 8)];
	}

	/** Distancia aproximada (redondeada a 100 bloques, al menos 100): una pista, no unas coordenadas. */
	public static int approximate(int x, int z, int tx, int tz) {
		double d = Math.hypot(tx - x, tz - z);
		return (int) Math.max(100, Math.round(d / 100.0) * 100);
	}
}
