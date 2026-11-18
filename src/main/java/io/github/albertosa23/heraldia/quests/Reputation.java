package io.github.albertosa23.heraldia.quests;

import java.util.Locale;

/**
 * Reputación de un jugador con una aldea de Heraldia (lógica pura, T38): sube con los encargos entregados y baja al
 * atacar a sus aldeanos o gólems. Por niveles mejora los tratos de sus aldeanos (un descuento como el de Héroe de la
 * aldea, calculado igual que vanilla) y da un saludo y un título. Nada de esto toca la progresión: el descuento máximo
 * es el de Héroe de la aldea I y nunca baja un precio de 1.
 */
public final class Reputation {
	public static final int MIN = -100, MAX = 300;
	/** Umbrales de cada nivel (conocido, amigo, héroe). */
	public static final int KNOWN = 20, FRIEND = 75, HERO = 200;
	/** Lo que cuesta atacar: por golpe y al matar, a un aldeano y a un gólem de hierro de la aldea. */
	public static final int VILLAGER_HIT = -5, VILLAGER_DEATH = -40, GOLEM_HIT = -3, GOLEM_DEATH = -20;

	public enum Tier {
		UNKNOWN("desconocido", 0), KNOWN("conocido", 10), FRIEND("amigo", 20), HERO("heroe", 30);

		/** Descuento en los tratos de sus aldeanos, en % del precio base (como Héroe de la aldea: 30 % con el I). */
		public final int discount;

		/** Id used in translation keys: never renamed. */
		private final String id;

		Tier(String id, int discount) {
			this.id = id;
			this.discount = discount;
		}

		public String id() {
			return id;
		}
	}

	private Reputation() {
	}

	/** Clave de una aldea en los datos: el chunk de su inicio («12,-40»). */
	public static String key(int chunkX, int chunkZ) {
		return chunkX + "," + chunkZ;
	}

	/** Chunk de una clave (inverso de {@link #key}); null si no es una clave válida. */
	public static int[] chunk(String key) {
		int i = key.indexOf(',');
		if (i <= 0) {
			return null;
		}
		try {
			return new int[]{Integer.parseInt(key.substring(0, i)), Integer.parseInt(key.substring(i + 1))};
		} catch (NumberFormatException e) {
			return null;
		}
	}

	public static Tier tier(int points) {
		return points >= HERO ? Tier.HERO : points >= FRIEND ? Tier.FRIEND : points >= KNOWN ? Tier.KNOWN : Tier.UNKNOWN;
	}

	/** Suma un cambio sin salirse de [MIN, MAX]. */
	public static int add(int points, int change) {
		return (int) Math.max(MIN, Math.min(MAX, (long) points + change));
	}

	/**
	 * Cuánto baja el precio de un trato con el coste base {@code base} (lo que se suma al «specialPrice» de la oferta,
	 * negativo o 0): la misma cuenta que Héroe de la aldea en vanilla ({@code max(floor(p × base), 1)}). Sin efecto con
	 * la reputación desactivada, en el nivel desconocido o si el jugador ya tiene Héroe de la aldea (no se acumulan).
	 */
	public static int discountFor(Tier tier, int base, boolean enabled, boolean vanillaHero) {
		if (!enabled || vanillaHero || tier.discount <= 0 || base <= 0) {
			return 0;
		}
		return -Math.max((int) Math.floor(tier.discount / 100.0 * base), 1);
	}

	/** Cambio de reputación al dañar ({@code death} = false) o matar a un aldeano o a un gólem de la aldea. */
	public static int attack(boolean golem, boolean death) {
		return golem ? (death ? GOLEM_DEATH : GOLEM_HIT) : (death ? VILLAGER_DEATH : VILLAGER_HIT);
	}
}
