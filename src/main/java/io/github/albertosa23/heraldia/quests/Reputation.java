package io.github.albertosa23.heraldia.quests;

import java.util.Locale;

/**
 * A player's reputation with a Heraldia village (pure logic, T38): rises with delivered quests and drops when
 * attacking its villagers or golems. By levels it improves the trades of its villagers (a discount like Hero of the
 * Village, computed the same way as vanilla) and gives a greeting and a title. None of this touches progression: the maximum discount
 * is that of Hero of the Village I and a price never drops below 1.
 */
public final class Reputation {
	public static final int MIN = -100, MAX = 300;
	/** Thresholds of each level (known, friend, hero). */
	public static final int KNOWN = 20, FRIEND = 75, HERO = 200;
	/** What attacking costs: per hit and on killing, a villager and an iron golem of the village. */
	public static final int VILLAGER_HIT = -5, VILLAGER_DEATH = -40, GOLEM_HIT = -3, GOLEM_DEATH = -20;

	public enum Tier {
		UNKNOWN("desconocido", 0), KNOWN("conocido", 10), FRIEND("amigo", 20), HERO("heroe", 30);

		/** Discount on its villagers' trades, in % of the base price (like Hero of the Village: 30 % with level I). */
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

	/** Key of a village in the data: its start chunk ("12,-40"). */
	public static String key(int chunkX, int chunkZ) {
		return chunkX + "," + chunkZ;
	}

	/** Chunk of a key (inverse of {@link #key}); null if it is not a valid key. */
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

	/** Adds a change without leaving [MIN, MAX]. */
	public static int add(int points, int change) {
		return (int) Math.max(MIN, Math.min(MAX, (long) points + change));
	}

	/**
	 * How much the price of a trade with base cost {@code base} drops (what is added to the offer's "specialPrice",
	 * negative or 0): the same computation as Hero of the Village in vanilla ({@code max(floor(p × base), 1)}). No effect with
	 * reputation disabled, at the unknown level or if the player already has Hero of the Village (they do not stack).
	 */
	public static int discountFor(Tier tier, int base, boolean enabled, boolean vanillaHero) {
		if (!enabled || vanillaHero || tier.discount <= 0 || base <= 0) {
			return 0;
		}
		return -Math.max((int) Math.floor(tier.discount / 100.0 * base), 1);
	}

	/** Reputation change on hurting ({@code death} = false) or killing a villager or a golem of the village. */
	public static int attack(boolean golem, boolean death) {
		return golem ? (death ? GOLEM_DEATH : GOLEM_HIT) : (death ? VILLAGER_DEATH : VILLAGER_HIT);
	}
}
