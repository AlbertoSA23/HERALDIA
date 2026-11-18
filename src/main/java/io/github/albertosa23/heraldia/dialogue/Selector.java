package io.github.albertosa23.heraldia.dialogue;

import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.random.RandomGenerator;
import org.jspecify.annotations.Nullable;

/**
 * Picks a villager's line (P9a, pure logic): a pool by weight among those that still have a line the player has not
 * heard lately, then a line of that pool at random. If the player has heard every line of every pool lately (a tiny
 * language), the recent ones are allowed again, oldest first, so it never goes silent and never repeats the last one.
 */
public final class Selector {
	private Selector() {
	}

	/** A line from one pool (a greeting, a farewell, a hint...), avoiding the recent ones. Null if the pool is empty. */
	public static Lines.@Nullable Line one(Lines lines, String pool, List<String> recent, RandomGenerator r) {
		return body(lines, List.of(new Context.Weighted(pool, 1)), recent, r);
	}

	/** A line from the weighted pools. Null only if none of them has any line. */
	public static Lines.@Nullable Line body(Lines lines, List<Context.Weighted> pools, List<String> recent, RandomGenerator r) {
		List<Context.Weighted> fresh = new ArrayList<>();
		int total = 0;
		for (Context.Weighted w : pools) {
			if (w.weight() > 0 && !unheard(lines.pool(w.pool()), recent).isEmpty()) {
				fresh.add(w);
				total += w.weight();
			}
		}
		if (fresh.isEmpty()) {
			return oldest(lines, pools, recent);
		}
		int roll = r.nextInt(total);
		for (Context.Weighted w : fresh) {
			roll -= w.weight();
			if (roll < 0) {
				List<Lines.Line> l = unheard(lines.pool(w.pool()), recent);
				return l.get(r.nextInt(l.size()));
			}
		}
		throw new IllegalStateException("unreachable");
	}

	static List<Lines.Line> unheard(List<Lines.Line> pool, Collection<String> recent) {
		List<Lines.Line> out = new ArrayList<>(pool.size());
		for (Lines.Line l : pool) {
			if (!recent.contains(l.key())) {
				out.add(l);
			}
		}
		return out;
	}

	/** Every line heard lately: the one heard longest ago ({@code recent} goes from oldest to newest). */
	private static Lines.@Nullable Line oldest(Lines lines, List<Context.Weighted> pools, List<String> recent) {
		Lines.Line best = null;
		int bestAt = Integer.MAX_VALUE;
		for (Context.Weighted w : pools) {
			for (Lines.Line l : lines.pool(w.pool())) {
				int at = recent.indexOf(l.key());
				if (at < bestAt) {
					best = l;
					bestAt = at;
				}
			}
		}
		return best;
	}
}
