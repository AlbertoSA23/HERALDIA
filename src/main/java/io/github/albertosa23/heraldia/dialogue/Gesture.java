package io.github.albertosa23.heraldia.dialogue;

/**
 * When a right click on a villager opens a conversation instead of its trades (P9a, pure logic; the owner's decision,
 * narrowed so vanilla trading and trading automation keep working): only with the system on, only a Heraldia villager
 * (the generator's "heraldia" tag) standing inside a Heraldia village, never the job board's bailiff, never while
 * sneaking (sneak + right click always goes straight to the trades), only with the main hand and only when the click
 * would have done something vanilla with the villager (not a baby, not asleep, not already trading). Holding a name
 * tag, a lead or a spawn egg keeps the vanilla use of the item.
 */
public final class Gesture {
	private Gesture() {
	}

	/** The facts of a click on a villager, read by the game side (dialogue/Dialogue). */
	public record Click(boolean enabled, boolean mainHand, boolean sneaking, boolean spectator, boolean heraldiaVillager,
			boolean bailiff, boolean baby, boolean sleeping, boolean trading, boolean itemWithUse) {
	}

	/** Everything except the village, which is the only costly check (a structure lookup): done last, only if this passes. */
	public static boolean mayTalk(Click c) {
		return c.enabled() && c.mainHand() && !c.sneaking() && !c.spectator() && c.heraldiaVillager() && !c.bailiff()
				&& !c.baby() && !c.sleeping() && !c.trading() && !c.itemWithUse();
	}
}
