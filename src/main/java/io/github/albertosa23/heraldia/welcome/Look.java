package io.github.albertosa23.heraldia.welcome;

import io.github.albertosa23.heraldia.quests.Reputation;
import java.util.Collection;

/**
 * How a Heraldia village looks to everyone who walks in (pure logic). Reputation is per player, but the village is shared
 * and its blocks are the same for everyone, so the village shows the <b>best</b> reputation any player has with it: a
 * village that someone has helped is a helped village. Only when every player who has dealt with it is in negative
 * reputation does it close its shutters. In the declared order, from the coldest to the warmest.
 */
public enum Look {
	/** Everyone who has dealt with it has negative reputation: the watchtowers close their shutters. */
	SHUNNED("recelosa"),
	/** As it was generated: nobody has earned anything yet (or the option is off). */
	PLAIN("normal"),
	/** Best reputation "known": flowers on the fountain. */
	KNOWN("conocida"),
	/** Best reputation "friend": banners at the square's entrances, by the job board, at the gates and the towers. */
	FRIEND("amiga"),
	/** Best reputation "hero": more flowers, lanterns on the gates and a carpet in front of the job board. */
	HERO("heroica");

	/** Id used in the log and translation keys: never renamed. */
	private final String id;

	Look(String id) {
		this.id = id;
	}

	public String id() {
		return id;
	}

	/**
	 * The look of a village from the reputation of every player recorded with it (0 does not need to be recorded). With
	 * the option or reputation off, or nobody recorded, the village is as it was generated.
	 */
	public static Look of(Collection<Integer> points, boolean enabled) {
		if (!enabled || points.isEmpty()) {
			return PLAIN;
		}
		int best = Integer.MIN_VALUE;
		for (int p : points) {
			best = Math.max(best, p);
		}
		if (best < 0) {
			return SHUNNED;
		}
		return switch (Reputation.tier(best)) {
			case UNKNOWN -> PLAIN;
			case KNOWN -> KNOWN;
			case FRIEND -> FRIEND;
			case HERO -> HERO;
		};
	}

	/** Is this look within [min, max] (in the declared order)? */
	public boolean within(Look min, Look max) {
		return compareTo(min) >= 0 && compareTo(max) <= 0;
	}
}
