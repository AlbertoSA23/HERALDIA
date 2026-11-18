package io.github.albertosa23.heraldia.dialogue;

import io.github.albertosa23.heraldia.quests.Reputation;

/**
 * What a villager's line depends on (P9a, pure logic): its profession, the family of its village (the biome group of
 * the style: llanuras, taiga, desierto...), the moment of the day, the weather and the player's reputation level with
 * the village. Each one names a pool of lines ({@link #pools}); the {@link Selector} draws among them.
 *
 * @param profession path of the vanilla profession ("farmer", "none", "nitwit"...)
 * @param family     village family (aldeas.estilos in the configuration), "" if unknown
 * @param moment     {@link #moment(long)}
 * @param weather    "clear", "rain", "snow" or "thunder"
 * @param tier       the player's reputation level with the village (UNKNOWN with reputation disabled)
 */
public record Context(String profession, String family, String moment, String weather, Reputation.Tier tier) {
	/** Clock ticks in a day (the overworld clock: 0 is sunrise). */
	static final long DAY = 24000;

	/** A weighted pool of body lines. */
	public record Weighted(String pool, int weight) {
	}

	/**
	 * The moment of the day of an overworld clock time: "morning" (sunrise to noon), "afternoon", "evening" (sunset,
	 * 12,000-13,999) or "night".
	 */
	public static String moment(long clock) {
		long t = Math.floorMod(clock, DAY);
		return t < 6000 ? "morning" : t < 12000 ? "afternoon" : t < 14000 ? "evening" : "night";
	}

	/** The weather name from the level's state at the villager: thunder wins, then rain or snow (cold biome). */
	public static String weather(boolean raining, boolean thundering, boolean snow) {
		if (thundering && raining) {
			return "thunder";
		}
		if (raining) {
			return snow ? "snow" : "rain";
		}
		return "clear";
	}

	/**
	 * The pools a body line can come from, with their weights: the profession weighs most (it is who they are), then
	 * the village and its land, then the rest. Bad weather is talked about more than good weather.
	 */
	public java.util.List<Weighted> pools() {
		return java.util.List.of(
				new Weighted("profession." + profession, 40),
				new Weighted("family." + family, 20),
				new Weighted("time." + moment, 10),
				new Weighted("weather." + weather, "clear".equals(weather) ? 5 : 15),
				new Weighted("reputation." + tier.id(), 8),
				new Weighted("general", 12));
	}

	/** Pool of the greeting that opens a conversation. */
	public String greeting() {
		return "greeting." + tier.id();
	}
}
