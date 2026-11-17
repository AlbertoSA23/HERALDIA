package io.github.albertosa23.heraldia.encargos;

import java.util.Locale;

/**
 * Reputación de un jugador con una aldea de Heraldia (lógica pura, T38): sube con los encargos entregados y baja al
 * atacar a sus aldeanos o gólems. Por niveles mejora los tratos de sus aldeanos (un descuento como el de Héroe de la
 * aldea, calculado igual que vanilla) y da un saludo y un título. Nada de esto toca la progresión: el descuento máximo
 * es el de Héroe de la aldea I y nunca baja un precio de 1.
 */
public final class Reputacion {
	public static final int MIN = -100, MAX = 300;
	/** Umbrales de cada nivel (conocido, amigo, héroe). */
	public static final int CONOCIDO = 20, AMIGO = 75, HEROE = 200;
	/** Lo que cuesta atacar: por golpe y al matar, a un aldeano y a un gólem de hierro de la aldea. */
	public static final int GOLPE_ALDEANO = -5, MUERTE_ALDEANO = -40, GOLPE_GOLEM = -3, MUERTE_GOLEM = -20;

	public enum Nivel {
		DESCONOCIDO(0), CONOCIDO(10), AMIGO(20), HEROE(30);

		/** Descuento en los tratos de sus aldeanos, en % del precio base (como Héroe de la aldea: 30 % con el I). */
		public final int descuento;

		Nivel(int descuento) {
			this.descuento = descuento;
		}

		public String id() {
			return name().toLowerCase(Locale.ROOT);
		}
	}

	private Reputacion() {
	}

	/** Clave de una aldea en los datos: el chunk de su inicio («12,-40»). */
	public static String clave(int chunkX, int chunkZ) {
		return chunkX + "," + chunkZ;
	}

	/** Chunk de una clave (inverso de {@link #clave}); null si no es una clave válida. */
	public static int[] chunk(String clave) {
		int i = clave.indexOf(',');
		if (i <= 0) {
			return null;
		}
		try {
			return new int[]{Integer.parseInt(clave.substring(0, i)), Integer.parseInt(clave.substring(i + 1))};
		} catch (NumberFormatException e) {
			return null;
		}
	}

	public static Nivel nivel(int puntos) {
		return puntos >= HEROE ? Nivel.HEROE : puntos >= AMIGO ? Nivel.AMIGO : puntos >= CONOCIDO ? Nivel.CONOCIDO : Nivel.DESCONOCIDO;
	}

	/** Suma un cambio sin salirse de [MIN, MAX]. */
	public static int sumar(int puntos, int cambio) {
		return (int) Math.max(MIN, Math.min(MAX, (long) puntos + cambio));
	}

	/**
	 * Cuánto baja el precio de un trato con el coste base {@code base} (lo que se suma al «specialPrice» de la oferta,
	 * negativo o 0): la misma cuenta que Héroe de la aldea en vanilla ({@code max(floor(p × base), 1)}). Sin efecto con
	 * la reputación desactivada, en el nivel desconocido o si el jugador ya tiene Héroe de la aldea (no se acumulan).
	 */
	public static int rebaja(Nivel nivel, int base, boolean activado, boolean heroeVanilla) {
		if (!activado || heroeVanilla || nivel.descuento <= 0 || base <= 0) {
			return 0;
		}
		return -Math.max((int) Math.floor(nivel.descuento / 100.0 * base), 1);
	}

	/** Cambio de reputación al dañar ({@code muerte} = false) o matar a un aldeano o a un gólem de la aldea. */
	public static int ataque(boolean golem, boolean muerte) {
		return golem ? (muerte ? MUERTE_GOLEM : GOLPE_GOLEM) : (muerte ? MUERTE_ALDEANO : GOLPE_ALDEANO);
	}
}
