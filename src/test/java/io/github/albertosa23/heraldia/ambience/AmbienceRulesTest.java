package io.github.albertosa23.heraldia.ambience;

import static io.github.albertosa23.heraldia.ambience.AmbienceRules.MineCue;
import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

/** When each ambient effect plays, and that it does not repeat or pile up. */
class AmbienceRulesTest {
	@Test
	void checksOnlyEveryFiveSeconds() {
		int checks = 0;
		for (long t = 0; t < 20 * 60; t++) {
			checks += AmbienceRules.checkTick(t) ? 1 : 0;
		}
		assertEquals(12, checks, "one check every 100 ticks: 12 per minute");
	}

	/** Simulates a world clock that advances one tick per server tick, sampled at every check. */
	private static int peals(long from, long ticks, long step) {
		long last = -1;
		int n = 0;
		for (long t = 0; t < ticks; t += AmbienceRules.PERIOD) {
			long h = AmbienceRules.bellHalfDay(from + t * step, last);
			if (h >= 0) {
				last = h;
				n++;
			}
		}
		return n;
	}

	@Test
	void ringsAtSunriseAndNightfallOnly() {
		assertEquals(0, AmbienceRules.bellHalfDay(0, -1));
		assertEquals(1, AmbienceRules.bellHalfDay(12_000, -1));
		assertEquals(-1, AmbienceRules.bellHalfDay(6_000, -1), "noon: no bell");
		assertEquals(-1, AmbienceRules.bellHalfDay(18_000, -1), "midnight: no bell");
		assertEquals(-1, AmbienceRules.bellHalfDay(12_000 + AmbienceRules.BELL_WINDOW, -1));
		assertTrue(AmbienceRules.morning(0) && !AmbienceRules.morning(1) && AmbienceRules.morning(48));
		// ten in-game days from any time of day: two peals per day, never more
		for (long start : new long[] {0, 1, 99, 5_000, 11_950, 23_999}) {
			int n = peals(start, 10 * AmbienceRules.DAY, 1);
			assertTrue(n == 20 || n == 21, "from " + start + ": " + n + " peals in 10 days");
		}
	}

	@Test
	void stoppedClockRingsOnce() {
		assertEquals(1, peals(12_010, 20 * 60 * 20, 0), "doDaylightCycle false at nightfall: one peal, not one every 5 s");
		assertEquals(0, peals(6_000, 20 * 60 * 20, 0));
	}

	@Test
	void wakingUpRingsTheMorningBell() {
		long last = AmbienceRules.bellHalfDay(36_000, -1);        // the evening of day 1 rang
		assertEquals(3, last);
		assertEquals(4, AmbienceRules.bellHalfDay(48_000, last), "after sleeping the clock jumps to sunrise");
		assertEquals(-1, AmbienceRules.bellHalfDay(48_100, 4));
	}

	@Test
	void cooldowns() {
		assertTrue(AmbienceRules.ready(0, AmbienceRules.NEVER, AmbienceRules.SIREN_COOLDOWN));
		assertFalse(AmbienceRules.ready(1000, 0, AmbienceRules.SIREN_COOLDOWN));
		assertTrue(AmbienceRules.ready(AmbienceRules.SIREN_COOLDOWN, 0, AmbienceRules.SIREN_COOLDOWN));
		assertTrue(AmbienceRules.ready(50, 100_000, AmbienceRules.SIREN_COOLDOWN), "the tick count started over");
		// the siren, sampled every check through a two-hour storm: at most one every 3 min
		long last = AmbienceRules.NEVER;
		int n = 0;
		for (long t = 0; t < 2 * 60 * 60 * 20; t += AmbienceRules.PERIOD) {
			if (AmbienceRules.ready(t, last, AmbienceRules.SIREN_COOLDOWN)) {
				last = t;
				n++;
			}
		}
		assertEquals(40, n);
		assertTrue(AmbienceRules.BELL_COOLDOWN < AmbienceRules.HALF_DAY, "the cooldown never hides the next peal");
		assertTrue(AmbienceRules.BELL_COOLDOWN > AmbienceRules.BELL_WINDOW, "but it keeps one peal per window");
	}

	@Test
	void sirenWeather() {
		assertTrue(AmbienceRules.sirenWeather(true, false));
		assertTrue(AmbienceRules.sirenWeather(true, true));
		assertTrue(AmbienceRules.sirenWeather(false, true));
		assertFalse(AmbienceRules.sirenWeather(false, false));
	}

	@Test
	void distantSoundsComeFromTheirDirection() {
		assertArrayEquals(new double[] {10, 64, 0}, AmbienceRules.source(0, 64, 0, 10, 64, 0, 24), 1e-9);
		assertArrayEquals(new double[] {24, 64, 0}, AmbienceRules.source(0, 64, 0, 100, 64, 0, 24), 1e-9);
		double[] s = AmbienceRules.source(5, 70, 5, 5 + 300, 70 + 40, 5 - 400, AmbienceRules.SIREN_RADIUS);
		double d = Math.sqrt(Math.pow(s[0] - 5, 2) + Math.pow(s[1] - 70, 2) + Math.pow(s[2] - 5, 2));
		assertEquals(AmbienceRules.SIREN_RADIUS, d, 1e-6);
		assertTrue(s[0] > 5 && s[2] < 5, "same direction");
		assertArrayEquals(new double[] {1, 2, 3}, AmbienceRules.source(1, 2, 3, 1, 2, 3, 24), 1e-9);
		assertEquals(25, AmbienceRules.horizontal2(0, 0, 3, -4), 1e-9);
	}

	@Test
	void minesDripNowAndThenAndEchoRarely() {
		assertEquals(AmbienceRules.DRIP_MIN, AmbienceRules.nextMineCue(0));
		assertEquals(AmbienceRules.DRIP_MAX, AmbienceRules.nextMineCue(0.9999999));
		for (double r = 0; r < 1; r += 0.01) {
			int n = AmbienceRules.nextMineCue(r);
			assertTrue(n >= AmbienceRules.DRIP_MIN && n <= AmbienceRules.DRIP_MAX);
			assertTrue(n >= AmbienceRules.PERIOD, "never more often than the checks");
		}
		assertEquals(MineCue.ECHO, AmbienceRules.mineCue(0, true, true));
		assertEquals(MineCue.ECHO, AmbienceRules.mineCue(AmbienceRules.ECHO_PERCENT - 1, true, false));
		assertEquals(MineCue.DRIP, AmbienceRules.mineCue(AmbienceRules.ECHO_PERCENT, true, true));
		assertEquals(MineCue.DRIP, AmbienceRules.mineCue(0, false, true), "the echo is not ready: a drip");
		assertEquals(MineCue.NONE, AmbienceRules.mineCue(50, true, false), "no ceiling to drip from");
		int echoes = 0;
		for (int roll = 0; roll < 100; roll++) {
			echoes += AmbienceRules.mineCue(roll, true, true) == MineCue.ECHO ? 1 : 0;
		}
		assertEquals(AmbienceRules.ECHO_PERCENT, echoes);
	}
}
