package io.github.albertosa23.heraldia.treasure;

import java.util.Set;

/**
 * What happens when a treasure map is used: pure logic (AdvanceTest). Far from the mark, it only says which way it is; at a
 * structure ({@value #STRUCTURE_ARRIVAL} blocks), the next clue; at the treasure ({@value #TREASURE_ARRIVAL}), the chest is
 * buried. A completed chain (or one whose seed already has a chest in the world, e.g. a copy of the map made
 * at the cartography table) gives nothing again: each chain is completed only once.
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

	/** Distance rounded to the ten (what the player is told). */
	public static int approximateDistance(Destination d, int px, int pz) {
		return (int) (Math.round(Math.sqrt(d.distanceSq(px, pz)) / 10.0) * 10);
	}
}
