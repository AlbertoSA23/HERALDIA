package io.github.albertosa23.heraldia.events;

import java.util.ArrayList;
import java.util.List;
import org.jspecify.annotations.Nullable;

/**
 * The village events (pure data): what each one is, how long it lasts, when in the day it may happen and how often it is
 * picked. The ids are the command literals ({@code /heraldia event start <id>}) and the middle of the line pools
 * ({@code event.<id>.*}, tools/gen/dialogue/&lt;code&gt;/events.json) and of the texts ({@code heraldia.eventos.<id>.*}).
 * <ul>
 * <li><b>Market day</b>: two to four stalls with striped awnings on either side of the square's avenues, a merchant
 * behind each one (real trades: the village's produce) and shoppers in front. A morning thing.</li>
 * <li><b>Wedding</b>: a white arch at the head of an aisle of carpet, the couple and the cleric under it, the guests in
 * two rows, children at the back; a firework when it starts, three when they say "yes". Fine weather only.</li>
 * <li><b>Funeral</b>: a bier with a black pall between two soul lanterns, the cleric at its head, the widow beside it and
 * the mourners around; the bell tolls slowly the whole time. Rain suits it.</li>
 * <li><b>Festival</b>: a bonfire, two maypoles, a band of three playing a folk tune and a ring of dancers; the host
 * sells festival food and fireworks. At dusk, in fine weather.</li>
 * </ul>
 * The four fit every style (they are vanilla blocks in neutral colours) and each one has a figure the player can deal
 * with: buy at the market, give a gift at the wedding or the funeral, ask the band for a song at the festival.
 */
public enum Kind {
	MARKET("market", 6 * 60, 35, 0, 7000, true, 2),
	WEDDING("wedding", 4 * 60, 25, 1000, 11000, false, 1),
	FUNERAL("funeral", 3 * 60, 15, 2000, 12000, true, 1),
	FESTIVAL("festival", 5 * 60, 25, 10500, 17000, false, 1);

	/** Command literal and id in the line pools and the texts. */
	public final String id;
	/** How long it lasts, in seconds (ticks: × 20). */
	public final int seconds;
	/** Weight when several kinds are possible. */
	public final int weight;
	/** Overworld clock window ([from, to) within the day, 0 = sunrise) in which it may start. */
	public final int from, to;
	/** May start while it rains. */
	public final boolean inRain;
	/** Bays of the square it uses (see {@link Layout}). */
	public final int bays;

	Kind(String id, int seconds, int weight, int from, int to, boolean inRain, int bays) {
		this.id = id;
		this.seconds = seconds;
		this.weight = weight;
		this.from = from;
		this.to = to;
		this.inRain = inRain;
		this.bays = bays;
	}

	public long ticks() {
		return seconds * 20L;
	}

	public static @Nullable Kind byId(String id) {
		for (Kind k : values()) {
			if (k.id.equals(id)) {
				return k;
			}
		}
		return null;
	}

	/** May it start at this clock time and weather? */
	public boolean fits(long clock, boolean raining) {
		long t = Math.floorMod(clock, 24000L);
		return t >= from && t < to && (inRain || !raining);
	}

	/** The kinds that fit now, without repeating the village's last one (unless it is the only one). */
	public static List<Kind> possible(long clock, boolean raining, @Nullable Kind last) {
		List<Kind> out = new ArrayList<>();
		for (Kind k : values()) {
			if (k.fits(clock, raining) && k != last) {
				out.add(k);
			}
		}
		if (out.isEmpty() && last != null && last.fits(clock, raining)) {
			out.add(last);
		}
		return out;
	}

	/** A weighted pick among {@code kinds} with {@code rng} in [0, 1); null if there is none. */
	public static @Nullable Kind pick(List<Kind> kinds, double rng) {
		int total = 0;
		for (Kind k : kinds) {
			total += k.weight;
		}
		if (total <= 0) {
			return null;
		}
		double r = rng * total;
		for (Kind k : kinds) {
			r -= k.weight;
			if (r < 0) {
				return k;
			}
		}
		return kinds.getLast();
	}
}
