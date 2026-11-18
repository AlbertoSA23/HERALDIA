package io.github.albertosa23.heraldia.caravans;

import java.util.List;
import java.util.Set;
import java.util.UUID;

/**
 * Caravan rules (pure logic): when one spawns, what it is like (llamas, guard, ambush, bandits), what it pays and which
 * entities are leftovers. Random numbers come in as arguments in [0, 1) so the tests can fix them.
 */
public final class Rules {
	/** Every how many ticks a new caravan is rolled (1 min), and the wait after one ends (2 min). */
	public static final int DRAW_TICKS = 60 * 20, WAIT_TICKS = 2 * 60 * 20;
	/** Tags of all its entities and of each role. */
	public static final String TAG = "heraldia_caravana", MERCHANT = "heraldia_caravana.mercader", LLAMA = "heraldia_caravana.llama",
			GUARD = "heraldia_caravana.guardia", BANDIT = "heraldia_caravana.bandido";

	private Rules() {
	}

	/**
	 * Does a caravan spawn on this roll? With caravans enabled, below the active limit, after the wait
	 * since the last one and with probability {@code rate} % (0: never on its own, only with the command).
	 */
	public static boolean outcome(boolean enabled, int active, int maxActive, long tick, long lastEnd, int rate, double rng) {
		return enabled && active < maxActive && rate > 0 && tick - lastEnd >= WAIT_TICKS && rng * 100 < rate;
	}

	/** Is it ambushed? With probability {@code ambushProb} %. */
	public static boolean ambush(int ambushProb, double rng) {
		return ambushProb > 0 && rng * 100 < ambushProb;
	}

	/** Pack llamas: 1 to 3. */
	public static int llamas(double rng) {
		return 1 + Math.min(2, (int) (rng * 3));
	}

	/** Does it have a guard (an iron golem)? One in four. */
	public static boolean guard(double rng) {
		return rng < 0.25;
	}

	/** Ambush bandits: one more than the players nearby, 2 to 4; with 3 or more, one is the leader (vindicator). */
	public static int bandits(int players) {
		return Math.max(2, Math.min(4, players + 1));
	}

	public static boolean withBoss(int bandits) {
		return bandits >= 3;
	}

	/**
	 * What each player escorting it earns on arrival: emeralds (2 plus one per 4 vertices; 4 more and an item
	 * if it survived an ambush), reputation with the destination village (5, or 15 after an ambush) and, after an ambush, the advancement.
	 */
	public record Reward(int emeralds, int reputation, String item, int amount, boolean advancement) {
		public boolean withItem() {
			return item != null;
		}
	}

	/** Items of a defended caravan: (id, amount). Modest, like a medium structure's loot. */
	public static final List<Object[]> ITEMS = List.of(new Object[]{"minecraft:name_tag", 1}, new Object[]{"minecraft:spyglass", 1},
			new Object[]{"minecraft:lead", 2}, new Object[]{"minecraft:golden_carrot", 4}, new Object[]{"minecraft:honey_bottle", 3},
			new Object[]{"minecraft:map", 1}, new Object[]{"minecraft:bundle", 1}, new Object[]{"minecraft:saddle", 1});

	public static Reward reward(int vertices, boolean cleared, double rng) {
		int emeralds = 2 + vertices / 4 + (cleared ? 4 : 0);
		if (!cleared) {
			return new Reward(emeralds, 5, null, 0, false);
		}
		Object[] o = ITEMS.get(Math.min(ITEMS.size() - 1, (int) (rng * ITEMS.size())));
		return new Reward(emeralds, 15, (String) o[0], (Integer) o[1], true);
	}

	/**
	 * Chunk of the village start whose plaza the layout gives ({@code RoadLayout.pack(cx * 16 + 8, cz * 16 + 8)}): the one the
	 * quests' reputation uses ({@code Quests.addReputation}) to know which village is meant.
	 */
	public static int[] chunk(long village) {
		return new int[]{Math.floorDiv(io.github.albertosa23.heraldia.roads.RoadLayout.px(village), 16),
				Math.floorDiv(io.github.albertosa23.heraldia.roads.RoadLayout.pz(village), 16)};
	}

	/** Is this entity a leftover? It belongs to a caravan but to no active one (from before a restart, or an already finished one). */
	public static boolean orphan(Set<String> tags, UUID uuid, Set<UUID> active) {
		return !tags.isEmpty() && tags.contains(TAG) && !active.contains(uuid);
	}
}
