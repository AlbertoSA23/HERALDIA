package io.github.albertosa23.heraldia.arena;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.time.DayOfWeek;
import java.time.Instant;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import org.junit.jupiter.api.Test;

/** The arena leaderboard week: reset day and hour, time zones, year change and clock change. */
class WeekTest {
	private static final ZoneId MADRID = ZoneId.of("Europe/Madrid"), UTC = ZoneId.of("UTC"), AUCKLAND = ZoneId.of("Pacific/Auckland");

	private static Instant en(String dateTime, ZoneId z) {
		return LocalDateTime.parse(dateTime).atZone(z).toInstant();
	}

	@Test
	void mondayAtMidnight() {
		// Tuesday 17-11-2026: the week started on Monday 16
		assertEquals(LocalDate.of(2026, 11, 16), Week.start(en("2026-11-17T15:00", MADRID), MADRID, DayOfWeek.MONDAY, 0));
		// Monday itself at 00:00 is already the new week; one second earlier, the previous one
		assertEquals(LocalDate.of(2026, 11, 16), Week.start(en("2026-11-16T00:00", MADRID), MADRID, DayOfWeek.MONDAY, 0));
		assertEquals(LocalDate.of(2026, 11, 9), Week.start(en("2026-11-15T23:59:59", MADRID), MADRID, DayOfWeek.MONDAY, 0));
		// Sunday is still the week of the previous Monday
		assertEquals(LocalDate.of(2026, 11, 16), Week.start(en("2026-11-22T23:00", MADRID), MADRID, DayOfWeek.MONDAY, 0));
	}

	@Test
	void resetHour() {
		// reset on Monday at 6:00: on Monday at 5:59 it is still the previous week
		assertEquals(LocalDate.of(2026, 11, 9), Week.start(en("2026-11-16T05:59", MADRID), MADRID, DayOfWeek.MONDAY, 6));
		assertEquals(LocalDate.of(2026, 11, 16), Week.start(en("2026-11-16T06:00", MADRID), MADRID, DayOfWeek.MONDAY, 6));
		assertEquals(en("2026-11-23T06:00", MADRID), Week.nextReset(en("2026-11-16T06:00", MADRID), MADRID, DayOfWeek.MONDAY, 6));
		// hour out of range: it is clamped
		assertEquals(Week.limit(LocalDate.of(2026, 11, 16), 23, MADRID), Week.limit(LocalDate.of(2026, 11, 16), 99, MADRID));
	}

	@Test
	void anotherDay() {
		// reset on Friday: Thursday 19-11 is the week of Friday 13
		assertEquals(LocalDate.of(2026, 11, 13), Week.start(en("2026-11-19T12:00", MADRID), MADRID, DayOfWeek.FRIDAY, 0));
		assertEquals(LocalDate.of(2026, 11, 20), Week.start(en("2026-11-20T00:00", MADRID), MADRID, DayOfWeek.FRIDAY, 0));
		assertEquals(LocalDate.of(2026, 11, 20), Week.next(LocalDate.of(2026, 11, 13), DayOfWeek.FRIDAY));
		// if the reset day changes, the next one is the first new day after the saved start
		assertEquals(LocalDate.of(2026, 11, 18), Week.next(LocalDate.of(2026, 11, 16), DayOfWeek.WEDNESDAY));
		assertEquals(LocalDate.of(2026, 11, 23), Week.next(LocalDate.of(2026, 11, 16), DayOfWeek.MONDAY));
	}

	@Test
	void yearChange() {
		// Thursday 31-12-2026: the week started on Monday 28-12-2026; on Monday 4-1-2027 another starts
		assertEquals(LocalDate.of(2026, 12, 28), Week.start(en("2026-12-31T23:30", MADRID), MADRID, DayOfWeek.MONDAY, 0));
		assertEquals(LocalDate.of(2026, 12, 28), Week.start(en("2027-01-03T23:59", MADRID), MADRID, DayOfWeek.MONDAY, 0));
		assertEquals(LocalDate.of(2027, 1, 4), Week.start(en("2027-01-04T00:00", MADRID), MADRID, DayOfWeek.MONDAY, 0));
		assertEquals(LocalDate.of(2027, 1, 4), Week.next(LocalDate.of(2026, 12, 28), DayOfWeek.MONDAY));
		// leap year: from Monday 26-2-2024 to Monday 4-3-2024 (passing through 29-2)
		assertEquals(LocalDate.of(2024, 3, 4), Week.next(LocalDate.of(2024, 2, 26), DayOfWeek.MONDAY));
	}

	@Test
	void timeZones() {
		// the same instant (Monday 16-11-2026 at 00:30 in Madrid = Sunday 23:30 in UTC) is a different week in each zone
		Instant i = en("2026-11-16T00:30", MADRID);
		assertEquals(LocalDate.of(2026, 11, 16), Week.start(i, MADRID, DayOfWeek.MONDAY, 0));
		assertEquals(LocalDate.of(2026, 11, 9), Week.start(i, UTC, DayOfWeek.MONDAY, 0));
		// in Auckland (UTC+13 in November) it is already Monday at noon
		assertEquals(LocalDate.of(2026, 11, 16), Week.start(i, AUCKLAND, DayOfWeek.MONDAY, 0));
		assertNotEquals(Week.nextReset(i, MADRID, DayOfWeek.MONDAY, 0), Week.nextReset(i, UTC, DayOfWeek.MONDAY, 0));
	}

	@Test
	void dstChange() {
		// Madrid moves the clock forward on Sunday 29-3-2026 at 2:00 (2:00 to 3:00 does not exist): a reset on Sunday at
		// 2:00 falls at 3:00 summer time, and a week with the change lasts 167 hours
		ZonedDateTime l = Week.limit(LocalDate.of(2026, 3, 29), 2, MADRID);
		assertEquals(3, l.getHour());
		assertEquals(LocalDate.of(2026, 3, 22), Week.start(en("2026-03-29T01:59", MADRID), MADRID, DayOfWeek.SUNDAY, 2));
		assertEquals(LocalDate.of(2026, 3, 29), Week.start(l.toInstant(), MADRID, DayOfWeek.SUNDAY, 2));
		Instant a = Week.limit(LocalDate.of(2026, 3, 23), 0, MADRID).toInstant(), b = Week.limit(LocalDate.of(2026, 3, 30), 0, MADRID).toInstant();
		assertEquals(167, java.time.Duration.between(a, b).toHours());
		assertEquals(LocalDate.of(2026, 3, 30), Week.start(b, MADRID, DayOfWeek.MONDAY, 0));
		// and the October setback (25-10-2026): 169 hours, the week does not move
		Instant c = Week.limit(LocalDate.of(2026, 10, 19), 0, MADRID).toInstant(), d = Week.limit(LocalDate.of(2026, 10, 26), 0, MADRID).toInstant();
		assertEquals(169, java.time.Duration.between(c, d).toHours());
		assertEquals(LocalDate.of(2026, 10, 19), Week.start(d.minusSeconds(1), MADRID, DayOfWeek.MONDAY, 0));
	}

	@Test
	void optionDays() {
		assertEquals(DayOfWeek.MONDAY, Week.day("lunes"));
		assertEquals(DayOfWeek.WEDNESDAY, Week.day("miercoles"));
		assertEquals(DayOfWeek.SUNDAY, Week.day("DOMINGO"));
		assertEquals(DayOfWeek.MONDAY, Week.day("otro"));
		assertEquals(DayOfWeek.MONDAY, Week.day(null));
		assertEquals(7, Week.DAYS.size());
		for (int i = 0; i < 7; i++) {
			assertEquals(DayOfWeek.of(i + 1), Week.day(Week.DAYS.get(i)));
			assertTrue(Week.DAYS.get(i).matches("[a-z]+"));
		}
	}

	@Test
	void nextResetIsStartOfNextWeek() {
		for (int h = 0; h < 24 * 14; h += 5) {
			Instant i = en("2026-11-10T00:00", MADRID).plusSeconds(h * 3600L);
			Instant p = Week.nextReset(i, MADRID, DayOfWeek.MONDAY, 0);
			assertTrue(p.isAfter(i));
			assertEquals(Week.start(i, MADRID, DayOfWeek.MONDAY, 0).plusWeeks(1), Week.start(p, MADRID, DayOfWeek.MONDAY, 0));
		}
	}
}
