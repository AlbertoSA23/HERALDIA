package io.github.albertosa23.heraldia.quests;

import java.util.List;

/**
 * When each quest type is met (pure logic, T38). The game only provides the facts: a guardian killed (its unique
 * id and where), a player's position every so often, the arena wave cleared or what they carry in their
 * inventory on delivery.
 */
public final class Objectives {
	/** A guardian of the requested unique killed within this distance of the quest's site is the one (uniques of the same type
	 *  spawn thousands of blocks apart: there are no two that close). */
	public static final int GUARDIAN_RADIUS = 320;
	/** Horizontal distance to the site that counts as having arrived: at a medium structure or a mine, and at a village. */
	public static final int PLACE_RADIUS = 40, VILLAGE_RADIUS = 64;
	/** Players within this distance of the guardian when it dies count as participants (besides whoever kills it). */
	public static final int PARTICIPATE_RADIUS = 64;
	/** Every how many ticks the players with go-to-a-site quests are checked for arrival (2 s). */
	public static final int EVERY_TICKS = 40;

	private Objectives() {
	}

	static boolean near(int x, int z, int tx, int tz, int radius) {
		long dx = x - tx, dz = z - tz;
		return dx * dx + dz * dz <= (long) radius * radius;
	}

	/** Does the death of the guardian of unique {@code unique} at (x, z) meet the quest? */
	public static boolean guardian(Quest e, String unique, int x, int z) {
		return e.type() == Type.GUARDIAN && e.target().equals(unique) && near(x, z, e.x(), e.z(), GUARDIAN_RADIUS);
	}

	/** Does being at (x, z) meet the quest (explore or journey)? */
	public static boolean arrival(Quest e, int x, int z) {
		return switch (e.type()) {
			case EXPLORE -> near(x, z, e.x(), e.z(), PLACE_RADIUS);
			case JOURNEY -> near(x, z, e.x(), e.z(), VILLAGE_RADIUS);
			default -> false;
		};
	}

	/** Does clearing wave {@code wave} meet the quest? */
	public static boolean wave(Quest e, int wave) {
		return e.type() == Type.ARENA && wave >= e.amount();
	}

	/** Is there any unmet accepted quest that is met by reaching a site? (early exit of the periodic sweep) */
	public static boolean awaitsArrival(List<Data.Active> active) {
		for (Data.Active a : active) {
			if (!a.met() && (a.quest().type() == Type.EXPLORE || a.quest().type() == Type.JOURNEY)) {
				return true;
			}
		}
		return false;
	}

	/** Can it be delivered now? Bring quests, if they carry enough ({@code has}); the others, if they are met. */
	public static boolean deliverable(Data.Active a, int has) {
		return a.quest().type() == Type.BRING ? has >= a.quest().amount() : a.met();
	}

	/** 8-point heading from (x, z) to (tx, tz) (north = -z): "n", "ne", "e"... (the keys of heraldia.info.dir.*). */
	public static String bearing(int x, int z, int tx, int tz) {
		String[] dirs = {"s", "so", "o", "no", "n", "ne", "e", "se"};
		double angle = Math.toDegrees(Math.atan2(-(tx - x), tz - z));
		return dirs[Math.floorMod((int) Math.round(angle / 45.0), 8)];
	}

	/** Approximate distance (rounded to 100 blocks, at least 100): a hint, not coordinates. */
	public static int approximate(int x, int z, int tx, int tz) {
		double d = Math.hypot(tx - x, tz - z);
		return (int) Math.max(100, Math.round(d / 100.0) * 100);
	}
}
