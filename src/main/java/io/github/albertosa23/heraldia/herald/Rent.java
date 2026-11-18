package io.github.albertosa23.heraldia.herald;

/**
 * Stall rent, pure logic over the world's game time (it only advances while the server runs, so an offline server
 * charges nobody). Nothing counts down: the state of a tenancy is computed when it is looked at, from the tick it is
 * paid until ({@code paidUntil}).
 */
public final class Rent {
	/** Ticks in a game day. */
	public static final long DAY = 24000;
	/** Periods that can be paid in advance (counted from now). */
	public static final int MAX_AHEAD = 4;

	private Rent() {
	}

	/** The options in use: entry fee and rent (emeralds), period and grace (game days). */
	public record Terms(int entry, int rent, int periodDays, int graceDays) {
		public long period() {
			return periodDays * DAY;
		}
	}

	/** PAID; DUE_SOON (less than a day left); GRACE (overdue, still the tenant's); EXPIRED (lost). */
	public enum Status { PAID, DUE_SOON, GRACE, EXPIRED }

	public static Status status(long now, long paidUntil, Terms t) {
		if (t.rent() == 0 || now < paidUntil - DAY) {
			return Status.PAID;
		}
		if (now < paidUntil) {
			return Status.DUE_SOON;
		}
		return now < paidUntil + t.graceDays() * DAY ? Status.GRACE : Status.EXPIRED;
	}

	/** What claiming a free stall costs: the entry fee and the first period. */
	public static int claimCost(Terms t) {
		return t.entry() + t.rent();
	}

	/** Paid until after claiming now. */
	public static long claimUntil(long now, Terms t) {
		return now + t.period();
	}

	/**
	 * How many periods can be paid now: enough to bring it up to {@link #MAX_AHEAD} periods from now (overdue periods
	 * count: paying in the grace pays the arrears first). 0 for an expired stall.
	 */
	public static int payable(long now, long paidUntil, Terms t) {
		if (status(now, paidUntil, t) == Status.EXPIRED || t.rent() == 0) {
			return 0;
		}
		long room = now + MAX_AHEAD * t.period() - paidUntil;
		return (int) Math.max(0, room / t.period());
	}

	/** Paid until after paying {@code n} periods. */
	public static long pay(long paidUntil, int n, Terms t) {
		return paidUntil + n * t.period();
	}

	/** Whole game days (rounded up) from now to {@code until}; 0 if it has passed. */
	public static long daysLeft(long now, long until) {
		return until <= now ? 0 : (until - now + DAY - 1) / DAY;
	}

	/** The day the grace of {@code paidUntil} ends. */
	public static long graceEnd(long paidUntil, Terms t) {
		return paidUntil + t.graceDays() * DAY;
	}

	/** Emeralds held, counted from the stack sizes, and how to take {@code cost} of them: pure arithmetic for tests. */
	public static boolean affordable(int held, int cost) {
		return cost <= 0 || held >= cost;
	}
}
