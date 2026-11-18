package io.github.albertosa23.heraldia.arena;

import java.time.DayOfWeek;
import java.time.Instant;
import java.time.LocalDate;
import java.time.LocalTime;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.time.temporal.TemporalAdjusters;
import java.util.List;
import java.util.Locale;

/**
 * Computing the week of the arena leaderboard (T41), pure logic: the week starts on day
 * arena.temporada.dia_reinicio at hour arena.temporada.hora_reinicio (server time) and is identified by that day's
 * date (its "start"). With local dates, not instants, the clock change (summer/winter) and the year change do not
 * move the week; an hour that does not exist because of the clock change (e.g. 2:00 on the night of the change) is taken
 * as the first valid hour after it (like {@link LocalDate#atTime} with {@link ZonedDateTime#of}).
 */
public final class Week {
	/** Values of arena.temporada.dia_reinicio, Monday to Sunday (the order of {@link DayOfWeek}). */
	public static final List<String> DAYS = List.of("lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo");

	private Week() {
	}

	/** The day of arena.temporada.dia_reinicio (Monday if not recognized). */
	public static DayOfWeek day(String value) {
		int i = value == null ? -1 : DAYS.indexOf(value.toLowerCase(Locale.ROOT));
		return DayOfWeek.of(i < 0 ? 1 : i + 1);
	}

	/** The moment the week starting on day {@code start} begins (at hour {@code hour} in {@code zone}). */
	public static ZonedDateTime limit(LocalDate start, int hour, ZoneId zone) {
		return ZonedDateTime.of(start, LocalTime.of(Math.clamp(hour, 0, 23), 0), zone);
	}

	/**
	 * Start (date of the reset day) of the current week at instant {@code now}: the last day {@code day} at
	 * hour {@code hour} that is not after {@code now}.
	 */
	public static LocalDate start(Instant now, ZoneId zone, DayOfWeek day, int hour) {
		ZonedDateTime z = now.atZone(zone);
		LocalDate d = z.toLocalDate().with(TemporalAdjusters.previousOrSame(day));
		if (limit(d, hour, zone).toInstant().isAfter(now)) {
			d = d.minusWeeks(1);
		}
		return d;
	}

	/** Start of the week after the one starting at {@code start} (with reset day {@code day}). */
	public static LocalDate next(LocalDate start, DayOfWeek day) {
		return start.plusDays(1).with(TemporalAdjusters.nextOrSame(day));
	}

	/** Moment the current week ends (the next one starts). */
	public static Instant nextReset(Instant now, ZoneId zone, DayOfWeek day, int hour) {
		return limit(next(start(now, zone, day, hour), day), hour, zone).toInstant();
	}
}
