package io.github.albertosa23.heraldia.dialogue;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.UUID;
import org.jspecify.annotations.Nullable;

/**
 * The wayfarers among the villagers (P9a, pure logic): about one in ten Heraldia villagers has travelled and knows a
 * place. Who is one comes from the villager's UUID (stable for its whole life, nothing saved); what it knows is one of
 * the structures that really exist around its village (the same search as the job board: /locate rules, no chunks
 * loaded), chosen from the UUID too among the nearest ones. It only tells it to a player with enough reputation with
 * the village, and only once in its life ({@link Memory.Villager#hintTold()}).
 */
public final class Hints {
	/** Among how many of the nearest places a wayfarer's knowledge is chosen (so that not every wayfarer of a village
	 *  knows the same one, but none sends you to the far end of the search). */
	static final int NEAREST = 6;

	/** A place a wayfarer can tell about: its kind ("unique", "medium" or "mine": the hint.&lt;kind&gt; pool), its id and where. */
	public record Place(String kind, String id, int x, int z, int distance) {
	}

	private Hints() {
	}

	/** A well-mixed 64-bit value of the UUID (the two halves through SplitMix64's finalizer). */
	static long mix(UUID id) {
		long z = id.getMostSignificantBits() ^ Long.rotateLeft(id.getLeastSignificantBits(), 32) ^ 0x9E3779B97F4A7C15L;
		z = (z ^ (z >>> 30)) * 0xBF58476D1CE4E5B9L;
		z = (z ^ (z >>> 27)) * 0x94D049BB133111EBL;
		return z ^ (z >>> 31);
	}

	/** Is this villager a wayfarer? {@code percent} of 100 are (dialogos.viajeros_porcentaje). */
	public static boolean wayfarer(UUID villager, int percent) {
		return percent > 0 && Math.floorMod(mix(villager), 100L) < percent;
	}

	/** May it tell the player? With reputation disabled there is no reputation to earn, so it always may. */
	public static boolean trusts(boolean reputationOn, int points, int minimum) {
		return !reputationOn || points >= minimum;
	}

	/** The place this wayfarer knows among {@code places}: one of the {@link #NEAREST} nearest, from its UUID. Null if there is none. */
	public static @Nullable Place choose(UUID villager, List<Place> places) {
		if (places.isEmpty()) {
			return null;
		}
		List<Place> l = new ArrayList<>(places);
		l.sort(Comparator.comparingInt(Place::distance).thenComparing(Place::id).thenComparingInt(Place::x).thenComparingInt(Place::z));
		int n = Math.min(NEAREST, l.size());
		return l.get((int) Math.floorMod(mix(villager) >>> 17, (long) n));
	}
}
