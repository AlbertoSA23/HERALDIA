package io.github.albertosa23.heraldia.arena;

import com.mojang.serialization.Codec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import java.time.DayOfWeek;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.EnumMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import org.jspecify.annotations.Nullable;

/**
 * Weekly arena leaderboard per mode (T41), immutable and without game classes (the tests check it): what is
 * saved in the overworld (persistent attachment heraldia:arena_temporada, see {@link Fame}).
 * <ul>
 * <li>{@link #week}: start (epoch day, {@link LocalDate#toEpochDay()}) of the current week, or {@link #NO_WEEK}
 * before the first one; {@link #actual}: its leaderboard per mode ({@link Mode} id → the best marks, one per
 * player, sorted with {@link #ORDER}, at most {@link #MAX_PER_MODE}).</li>
 * <li>{@link #history}: the last closed weeks, most recent first (arena.temporada.historico).</li>
 * <li>{@link #records}: the all-time best mark of each mode; {@link #migrated}: the pre-T41 vanilla scoreboard record
 * (the coop one) has already been copied.</li>
 * </ul>
 * All modes sort the same way (more waves cleared, then less time, then earlier): in the time trial, finished
 * matches have all the waves and are decided by time; in coop and survival, by the wave.
 */
public record Season(long week, Map<String, List<Entry>> actual, List<Closed> history, Map<String, Entry> records,
		boolean migrated) {
	public static final long NO_WEEK = Long.MIN_VALUE;
	/** Marks kept per mode and week (the leaderboard shows the top 10). */
	public static final int MAX_PER_MODE = 10;
	/** Cap on weeks in the history, whatever the option. */
	public static final int MAX_HISTORY = 52;
	/** Player of the marks migrated from the vanilla scoreboard (only their name was known). */
	public static final UUID NO_PLAYER = new UUID(0L, 0L);
	public static final Season EMPTY = new Season(NO_WEEK, Map.of(), List.of(), Map.of(), false);

	/**
	 * A mark: who, how many waves they cleared, in how many match ticks (from the start of the first wave until they
	 * cleared the last; -1 if unknown, in the migrated ones), when (epoch milliseconds) and, in the time trial, how many
	 * waves had to be cleared (0 in the other modes).
	 */
	public record Entry(UUID player, String name, int waves, long ticks, long date, int target) {
		static final Codec<UUID> UUID_CODEC = Codec.STRING.xmap(UUID::fromString, UUID::toString);
		public static final Codec<Entry> CODEC = RecordCodecBuilder.create(i -> i.group(
				UUID_CODEC.fieldOf("jugador").forGetter(Entry::player),
				Codec.STRING.fieldOf("nombre").forGetter(Entry::name),
				Codec.INT.fieldOf("oleadas").forGetter(Entry::waves),
				Codec.LONG.optionalFieldOf("ticks", -1L).forGetter(Entry::ticks),
				Codec.LONG.optionalFieldOf("fecha", 0L).forGetter(Entry::date),
				Codec.INT.optionalFieldOf("objetivo", 0).forGetter(Entry::target)).apply(i, Entry::new));

		/** Did the time trial finish (all waves cleared)? */
		public boolean complete() {
			return target > 0 && waves >= target;
		}

		/** Key to keep one mark per player (the migrated ones, by name). */
		String who() {
			return NO_PLAYER.equals(player) ? "nombre:" + name : player.toString();
		}
	}

	/** A closed week: its start, the day it closed (the start of the next one, or today if forced) and its leaderboard. */
	public record Closed(long start, long closing, Map<String, List<Entry>> ranking) {
		static final Codec<Map<String, List<Entry>>> RANKING = Codec.unboundedMap(Codec.STRING, Entry.CODEC.listOf());
		public static final Codec<Closed> CODEC = RecordCodecBuilder.create(i -> i.group(
				Codec.LONG.fieldOf("inicio").forGetter(Closed::start),
				Codec.LONG.fieldOf("cierre").forGetter(Closed::closing),
				RANKING.optionalFieldOf("clasificacion", Map.of()).forGetter(Closed::ranking)).apply(i, Closed::new));

		public Closed {
			ranking = backup(ranking);
		}

		/** The first of a mode, if any. */
		public Optional<Entry> champion(Mode m) {
			List<Entry> l = ranking.get(m.id());
			return l == null || l.isEmpty() ? Optional.empty() : Optional.of(l.get(0));
		}
	}

	public static final Codec<Season> CODEC = RecordCodecBuilder.create(i -> i.group(
			Codec.LONG.optionalFieldOf("semana", NO_WEEK).forGetter(Season::week),
			Closed.RANKING.optionalFieldOf("actual", Map.of()).forGetter(Season::actual),
			Closed.CODEC.listOf().optionalFieldOf("historico", List.of()).forGetter(Season::history),
			Codec.unboundedMap(Codec.STRING, Entry.CODEC).optionalFieldOf("records", Map.of()).forGetter(Season::records),
			Codec.BOOL.optionalFieldOf("migrada", false).forGetter(Season::migrated)).apply(i, Season::new));

	/** Best first: more waves, then fewer ticks (unknown ones last), then earlier and by name. */
	public static final Comparator<Entry> ORDER = Comparator.comparingInt(Entry::waves).reversed()
			.thenComparingLong(e -> e.ticks() < 0 ? Long.MAX_VALUE : e.ticks())
			.thenComparingLong(Entry::date)
			.thenComparing(Entry::name);

	public Season {
		actual = backup(actual);
		history = List.copyOf(history);
		records = Map.copyOf(records);
	}

	private static Map<String, List<Entry>> backup(Map<String, List<Entry>> m) {
		Map<String, List<Entry>> out = new LinkedHashMap<>();
		m.forEach((k, v) -> out.put(k, List.copyOf(v)));
		return java.util.Collections.unmodifiableMap(out);
	}

	/** Is {@code a} a better mark than {@code b} (or there is no {@code b})? */
	public static boolean best(Entry a, @Nullable Entry b) {
		return b == null || ORDER.compare(a, b) < 0;
	}

	/** The list with {@code e} added: one mark per player (the best), sorted and trimmed to {@link #MAX_PER_MODE}. */
	static List<Entry> with(List<Entry> list, Entry e) {
		Map<String, Entry> best = new LinkedHashMap<>();
		for (Entry x : list) {
			best.merge(x.who(), x, (a, b) -> best(b, a) ? b : a);
		}
		best.merge(e.who(), e, (a, b) -> best(b, a) ? b : a);
		List<Entry> out = new ArrayList<>(best.values());
		out.sort(ORDER);
		return List.copyOf(out.subList(0, Math.min(out.size(), MAX_PER_MODE)));
	}

	/** Adds a mark from a finished match (to the current week and, if it is one, to the mode's record). */
	public Season register(Mode m, Entry e) {
		Map<String, List<Entry>> a = new LinkedHashMap<>(actual);
		a.put(m.id(), with(a.getOrDefault(m.id(), List.of()), e));
		Map<String, Entry> r = new LinkedHashMap<>(records);
		if (best(e, r.get(m.id()))) {
			r.put(m.id(), e);
		}
		return new Season(week, a, history, r, migrated);
	}

	/** A mode's leaderboard in the current week. */
	public List<Entry> ranking(Mode m) {
		return actual.getOrDefault(m.id(), List.of());
	}

	public Optional<Entry> record(Mode m) {
		return Optional.ofNullable(records.get(m.id()));
	}

	/** Result of {@link #advance} and {@link #force}: the new state and the week that closed (if one did). */
	public record Closing(Season season, @Nullable Closed closed) {
	}

	/**
	 * At startup and every so often: if the current week is no longer the saved one (the reset day has passed, also with
	 * the server off), the saved one closes (goes to the history, at most {@code max} weeks) and an empty one starts.
	 * If the server was off for more than a week, the closed one is not the previous week's: its {@code closing} is the
	 * start of the one that followed it, and it has no previous-week champions ({@link #champions}). Before the first
	 * week it only records its start. A {@code currentStart} earlier than the saved one (reset day changed) closes
	 * nothing until it passes it.
	 */
	public Closing advance(LocalDate currentStart, DayOfWeek day, int max) {
		long today = currentStart.toEpochDay();
		if (week == NO_WEEK) {
			return new Closing(new Season(today, actual, history, records, migrated), null);
		}
		if (today <= week) {
			return new Closing(this, null);
		}
		long closing = Math.min(today, Week.next(LocalDate.ofEpochDay(week), day).toEpochDay());
		return close(closing, today, max);
	}

	/**
	 * /heraldia arena season reset: closes the current week now (its {@code closing} is today) and starts an empty one with
	 * the same calendar start: the automatic reset keeps falling on the usual day.
	 */
	public Closing force(LocalDate today, LocalDate currentStart, int max) {
		long ini = week == NO_WEEK ? currentStart.toEpochDay() : week;
		return new Season(ini, actual, history, records, migrated).close(today.toEpochDay(), currentStart.toEpochDay(), max);
	}

	private Closing close(long closing, long fresh, int max) {
		Closed c = new Closed(week, closing, actual);
		List<Closed> h = new ArrayList<>(history.size() + 1);
		h.add(c);
		h.addAll(history);
		Season t = new Season(fresh, Map.of(), h, records, migrated).trim(max);
		return new Closing(t, c);
	}

	/** The history trimmed to {@code max} weeks (between 1 and {@link #MAX_HISTORY}). */
	public Season trim(int max) {
		int n = Math.clamp(max, 1, MAX_HISTORY);
		return history.size() <= n ? this : new Season(week, actual, history.subList(0, n), records, migrated);
	}

	/**
	 * Champions of the week before the one starting at {@code currentStart}, per mode: the first of each mode of the
	 * last closed week, if it closed when this one started (or later, if forced); empty if none or if the last closed one
	 * is older (the server was off the whole previous week: nobody played).
	 */
	public Map<Mode, Entry> champions(LocalDate currentStart) {
		Map<Mode, Entry> out = new EnumMap<>(Mode.class);
		if (history.isEmpty() || history.get(0).closing() < currentStart.toEpochDay()) {
			return out;
		}
		Closed c = history.get(0);
		for (Mode m : Mode.values()) {
			c.champion(m).ifPresent(e -> out.put(m, e));
		}
		return out;
	}

	/** The closed week from {@code ago} weeks ago (1 = the previous one), if it is kept. */
	public Optional<Closed> closed(int ago) {
		return ago >= 1 && ago <= history.size() ? Optional.of(history.get(ago - 1)) : Optional.empty();
	}

	/** Modes in which this player won one of the kept weeks (for their advancements, even if absent at the close). */
	public Set<Mode> won(UUID player) {
		Set<Mode> out = new HashSet<>();
		for (Closed c : history) {
			for (Mode m : Mode.values()) {
				c.champion(m).filter(e -> e.player().equals(player)).ifPresent(e -> out.add(m));
			}
		}
		return out;
	}

	/**
	 * One-time migration of the pre-T41 vanilla scoreboard (objective heraldia_arena: waves cleared per player and
	 * the server's, {@code server}): the best player becomes the coop record, if better than any existing one,
	 * without a time (it was not known). The scoreboard is untouched: it is still the coop one.
	 */
	public Season migrate(Map<String, Integer> points, String server, long date) {
		if (migrated) {
			return this;
		}
		Entry best = null;
		for (Map.Entry<String, Integer> p : new java.util.TreeMap<>(points).entrySet()) {
			if (p.getKey().equals(server) || p.getValue() == null || p.getValue() <= 0) {
				continue;
			}
			Entry e = new Entry(NO_PLAYER, p.getKey(), p.getValue(), -1, date, 0);
			if (best(e, best)) {
				best = e;
			}
		}
		Map<String, Entry> r = new LinkedHashMap<>(records);
		String c = Mode.COOP.id();
		if (best != null && best(best, r.get(c))) {
			r.put(c, best);
		}
		return new Season(week, actual, history, r, true);
	}
}
