package io.github.albertosa23.heraldia.events;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import io.github.albertosa23.heraldia.events.Layout.Figure;
import io.github.albertosa23.heraldia.events.Layout.Placed;
import io.github.albertosa23.heraldia.events.Layout.Plan;
import io.github.albertosa23.heraldia.events.Layout.Prop;
import io.github.albertosa23.heraldia.events.Layout.Role;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.UUID;
import java.util.function.BiPredicate;
import org.junit.jupiter.api.Test;

/** The pure logic of the village events: the caps, when one starts and ends, where it goes in the square and what it keeps clear. */
class EventsLogicTest {
	/** A square with nothing on it: paving everywhere, air above, no entity. */
	static Layout.Ground open() {
		return ground((x, z) -> false, (x, z) -> false);
	}

	/** A square where {@code blocked} cells are not air at any height and {@code reserved} ones are kept. */
	static Layout.Ground ground(BiPredicate<Integer, Integer> blocked, BiPredicate<Integer, Integer> reserved) {
		return new Layout.Ground() {
			@Override
			public boolean air(int x, int y, int z) {
				return !blocked.test(x, z);
			}

			@Override
			public boolean floor(int x, int z) {
				return true;
			}

			@Override
			public boolean occupied(int x, int y, int z) {
				return false;
			}

			@Override
			public boolean reserved(int x, int z) {
				return reserved.test(x, z);
			}
		};
	}

	static final List<Integer> ALL = List.of(0, 1, 2, 3);

	// --- the owner's caps ---

	@Test
	void everyEventStaysWithinTheEntityCap() {
		for (Kind k : Kind.values()) {
			int peak = Rules.peakEntities(k);
			assertTrue(peak <= Rules.MAX_ENTITIES, k + ": " + peak + " entities at its peak");
			Plan p = Layout.plan(k, open(), ALL);
			assertNotNull(p, k.id);
			assertTrue(p.figures().size() <= Layout.maxFigures(k), k.id);
			assertEquals(k.bays, p.bays().size(), k.id + " uses its bays on an open square");
		}
		assertEquals(25, Rules.MAX_ENTITIES);
		// the figures per kind, as documented (CONTENT.md): market 12, wedding 15 + 3 fireworks, funeral 10, festival 12 + 3
		assertEquals(12, Rules.peakEntities(Kind.MARKET));
		assertEquals(18, Rules.peakEntities(Kind.WEDDING));
		assertEquals(10, Rules.peakEntities(Kind.FUNERAL));
		assertEquals(15, Rules.peakEntities(Kind.FESTIVAL));
	}

	@Test
	void startDecision() {
		long wait = 20 * 60 * 20L;
		assertTrue(Rules.starts(true, 0, 2, 20, 1000, -1, 20, 0.1), "never had one, roll in favour");
		assertFalse(Rules.starts(true, 0, 2, 20, 1000, -1, 20, 0.2), "20 %: the roll must be below 0.20");
		assertFalse(Rules.starts(false, 0, 2, 100, 1000, -1, 20, 0), "disabled");
		assertFalse(Rules.starts(true, 2, 2, 100, 1000, -1, 20, 0), "server limit reached");
		assertFalse(Rules.starts(true, 0, 2, 0, 1000, -1, 20, 0), "frequency 0: only by command");
		assertFalse(Rules.starts(true, 0, 2, 100, 5000 + wait - 1, 5000, 20, 0), "the village is still resting");
		assertTrue(Rules.starts(true, 0, 2, 100, 5000 + wait, 5000, 20, 0), "rested exactly the wait");
		assertTrue(Rules.waited(100, 5000, 20), "a clock that went back (another world copied in): no wait");
	}

	@Test
	void endDecision() {
		assertNull(Rules.end(0, Kind.WEDDING, 0, true, true));
		assertNull(Rules.end(Kind.WEDDING.ticks() - 1, Kind.WEDDING, Rules.IDLE_SECONDS - 1, true, true));
		assertEquals(Rules.End.DONE, Rules.end(Kind.WEDDING.ticks(), Kind.WEDDING, 0, true, true));
		assertEquals(Rules.End.ABANDONED, Rules.end(100, Kind.MARKET, Rules.IDLE_SECONDS, true, true), "nobody near for a minute");
		assertEquals(Rules.End.ABANDONED, Rules.end(100, Kind.MARKET, 0, false, true), "its square unloaded");
		assertEquals(Rules.End.CLEANUP, Rules.end(100, Kind.MARKET, 0, true, false), "turned off with /heraldia reload");
		for (Kind k : Kind.values()) {
			assertTrue(k.seconds >= 3 * 60 && k.seconds <= 6 * 60, k.id + " lasts 3 to 6 minutes");
		}
	}

	@Test
	void leftoversAndRemoval() {
		UUID a = UUID.randomUUID(), b = UUID.randomUUID();
		assertTrue(Rules.orphan(Set.of(Rules.TAG), a, Set.of(b)), "an event entity with no event running");
		assertFalse(Rules.orphan(Set.of(Rules.TAG), a, Set.of(a)), "one of a running event");
		assertFalse(Rules.orphan(Set.of("heraldia"), a, Set.of()), "a village's own villager");
		assertFalse(Rules.orphan(Set.of(), a, Set.of()));
		assertTrue(Rules.removable(true, true));
		assertFalse(Rules.removable(false, true), "no longer ours: it stays");
		assertFalse(Rules.removable(true, false), "something rests on it: it stays");
	}

	@Test
	void kindsByHourAndWeather() {
		assertTrue(Kind.MARKET.fits(3000, false) && Kind.MARKET.fits(3000, true), "a market in the morning, rain or not");
		assertFalse(Kind.MARKET.fits(9000, false), "not in the afternoon");
		assertFalse(Kind.WEDDING.fits(5000, true), "no wedding in the rain");
		assertTrue(Kind.FUNERAL.fits(5000, true), "a funeral in the rain");
		assertTrue(Kind.FESTIVAL.fits(13000, false) && !Kind.FESTIVAL.fits(13000, true), "a festival at dusk, if it does not rain");
		assertTrue(Kind.possible(20000, false, null).isEmpty(), "nothing in the middle of the night");
		assertFalse(Kind.possible(3000, false, Kind.MARKET).contains(Kind.MARKET), "not the same twice in a row");
		assertEquals(List.of(Kind.FUNERAL), Kind.possible(2500 + 24000, true, null).stream().filter(k -> k != Kind.MARKET).toList(),
				"rainy morning: market or funeral (the clock wraps by day)");
		assertEquals(List.of(Kind.FESTIVAL), Kind.possible(16000, false, Kind.FESTIVAL), "the only one that fits may repeat");
		// the weighted pick covers every candidate and respects the weights
		int[] n = new int[Kind.values().length];
		java.util.Random r = new java.util.Random(7);
		for (int i = 0; i < 100_000; i++) {
			n[Kind.pick(List.of(Kind.values()), r.nextDouble()).ordinal()]++;
		}
		assertTrue(n[Kind.MARKET.ordinal()] > n[Kind.FUNERAL.ordinal()] * 2, "the market is picked more than twice as often as a funeral");
		assertNull(Kind.pick(List.of(), 0.5));
		for (Kind k : Kind.values()) {
			assertEquals(k, Kind.byId(k.id));
		}
	}

	@Test
	void stepsAndRepeats() {
		List<Rules.Step> w = Rules.steps(Kind.WEDDING);
		assertEquals(List.of("1", "2", "3"), w.stream().filter(s -> s.pool().equals("ceremony")).map(Rules.Step::line).toList());
		assertTrue(w.stream().anyMatch(s -> s.beat() == Rules.Beat.VOWS), "the couple say yes");
		for (Kind k : Kind.values()) {
			for (Rules.Step s : Rules.steps(k)) {
				assertTrue(s.second() < k.seconds, k.id + ": every beat happens before it ends");
			}
		}
		Rules.Repeat toll = Rules.repeats(Kind.FUNERAL).getFirst();
		assertTrue(Rules.due(toll, 1) && Rules.due(toll, 9) && !Rules.due(toll, 8) && !Rules.due(toll, 0));
	}

	@Test
	void tunesArePlayable() {
		assertTrue(Rules.TUNES.size() >= 2, "asking for another song changes it");
		for (int[] t : Rules.TUNES) {
			assertEquals(0, t.length % 8, "whole bars");
			for (int n : t) {
				assertTrue(n == -1 || (n >= 0 && n <= 24), "note block range");
			}
		}
		assertEquals(0.5f, Rules.pitch(0), 1e-6);
		assertEquals(1.0f, Rules.pitch(12), 1e-6);
		assertEquals(2.0f, Rules.pitch(24), 1e-6);
		assertEquals(0, Rules.bass(0));
		assertEquals(7, Rules.bass(4));
		assertEquals(-1, Rules.bass(1));
	}

	// --- where it goes ---

	@Test
	void baysAreRotationsOfTheNorthOne() {
		assertEquals(List.of(Layout.C, 2), List.of(Layout.toSquare(0, 0, 2)[0], Layout.toSquare(0, 0, 2)[1]));
		assertEquals(List.of(Layout.N - 3, Layout.C), List.of(Layout.toSquare(1, 0, 2)[0], Layout.toSquare(1, 0, 2)[1]));
		assertEquals(List.of(Layout.C, Layout.N - 3), List.of(Layout.toSquare(2, 0, 2)[0], Layout.toSquare(2, 0, 2)[1]));
		assertEquals(List.of(2, Layout.C), List.of(Layout.toSquare(3, 0, 2)[0], Layout.toSquare(3, 0, 2)[1]));
		// the bay facing a player comes first
		assertEquals(1, Layout.facing(40, Layout.C).getFirst());
		assertEquals(3, Layout.facing(-40, Layout.C).getFirst());
		assertEquals(0, Layout.facing(Layout.C, -40).getFirst());
	}

	@Test
	void nothingOnTheReputationSpotsTheFountainOrOutsideTheBays() {
		for (Kind k : Kind.values()) {
			for (int first = 0; first < 4; first++) {
				List<Integer> order = List.of(first, (first + 1) % 4, (first + 2) % 4, (first + 3) % 4);
				Plan p = Layout.plan(k, open(), order);
				assertNotNull(p);
				assertEquals(first, p.bays().getFirst(), "the preferred bay is used when it fits");
				Set<String> cells = new HashSet<>();
				for (Placed c : p.props()) {
					assertFalse(Layout.keptForWelcome(c.x(), c.z()), k + " prop on a reputation spot at " + c);
					int r = Layout.ring(c.x(), c.z());
					assertTrue(r >= 4 && r <= 9, k + " prop outside the bays at " + c);
					assertTrue(cells.add(c.x() + "," + c.y() + "," + c.z()), "two props in one cell: " + c);
				}
				for (Figure f : p.figures()) {
					assertFalse(Layout.keptForWelcome(f.x(), f.z()), k + " figure on a reputation spot");
					assertTrue(cells.add(f.x() + ",1," + f.z()) && cells.add(f.x() + ",2," + f.z()), k + ": a figure inside a prop or another figure " + f);
				}
				// lower props first (a post before the awning on it)
				for (int i = 1; i < p.props().size(); i++) {
					assertTrue(p.props().get(i - 1).y() <= p.props().get(i).y());
				}
			}
		}
		// the banners at the avenue entrances and the fountain's rim are kept
		assertTrue(Layout.keptForWelcome(Layout.C - 3, 1) && Layout.keptForWelcome(1, Layout.C + 3) && Layout.keptForWelcome(Layout.C, Layout.C + 3));
		assertFalse(Layout.keptForWelcome(Layout.C, 2));
	}

	@Test
	void aBlockedCellMakesItSmallerOrMovesItOrStopsIt() {
		// a player's block where the west stall's post goes (bay 0, dx -3, dz 3): that stall and its trader are dropped
		int[] post = Layout.toSquare(0, -3, 3);
		Plan m = Layout.plan(Kind.MARKET, ground((x, z) -> x == post[0] && z == post[1], (x, z) -> false), List.of(0));
		assertNotNull(m);
		assertEquals(1, m.count(Role.MERCHANT), "one stall left, one trader");
		assertTrue(m.props().stream().noneMatch(c -> c.x() == post[0]), "nothing of the west stall");
		// the wedding's arch is required: blocked in bay 0, it goes to the next bay
		int[] arch = Layout.toSquare(0, 0, 2);
		BiPredicate<Integer, Integer> archBlocked = (x, z) -> Layout.ring(x, z) == 9 && Math.abs(x - arch[0]) <= 2 && z == arch[1];
		Plan w = Layout.plan(Kind.WEDDING, ground(archBlocked, (x, z) -> false), ALL);
		assertNotNull(w);
		assertEquals(List.of(1), w.bays());
		// every bay's arch blocked: no wedding at all
		assertNull(Layout.plan(Kind.WEDDING, ground((x, z) -> Layout.ring(x, z) == 9, (x, z) -> false), ALL));
		// a reserved area (the job board) is never used
		Plan f = Layout.plan(Kind.FESTIVAL, ground((x, z) -> false, (x, z) -> z < 8), List.of(0, 1));
		assertNotNull(f);
		assertEquals(List.of(1), f.bays());
		assertTrue(f.props().stream().allMatch(c -> c.z() >= 8) && f.figures().stream().allMatch(c -> c.z() >= 8));
		// the bonfire and the band fit but no dancer does: no festival in that bay
		BiPredicate<Integer, Integer> noDancers = (x, z) -> Layout.ring(x, z) >= 4 && Layout.ring(x, z) <= 8 && !(x == Layout.C && z == 5);
		assertNull(Layout.plan(Kind.FESTIVAL, ground(noDancers, (x, z) -> false), List.of(0)));
	}

	@Test
	void theReputationDecorationsKeepTheirSpots() {
		// every spot welcome/Spots may decorate in the square is kept clear by every event, in every bay (the square is
		// symmetric, so the template's frame is the world's up to a rotation that maps spots onto spots)
		int n = 0;
		for (io.github.albertosa23.heraldia.welcome.Spots.Spot spot
				: io.github.albertosa23.heraldia.welcome.Spots.of(io.github.albertosa23.heraldia.welcome.Spots.Piece.PLAZA)) {
			assertTrue(Layout.keptForWelcome(spot.x(), spot.z()), "spot " + spot);
			n++;
			for (Kind k : Kind.values()) {
				for (int b = 0; b < 4; b++) {
					Plan p = Layout.plan(k, open(), List.of(b));
					for (Placed c : p.props()) {
						assertFalse(c.x() == spot.x() && c.z() == spot.z(), k + " on " + spot);
					}
					for (Figure f : p.figures()) {
						assertFalse(f.x() == spot.x() && f.z() == spot.z(), k + " figure on " + spot);
					}
				}
			}
		}
		assertTrue(n >= 16, "the square's spots: " + n);
		// the job board's spots are one block from its lectern: inside the area kept around the board's piece (± 2)
		for (io.github.albertosa23.heraldia.welcome.Spots.Spot spot
				: io.github.albertosa23.heraldia.welcome.Spots.of(io.github.albertosa23.heraldia.welcome.Spots.Piece.BOARD)) {
			assertTrue(Math.abs(spot.x()) <= 2 && Math.abs(spot.z()) <= 2, "board spot " + spot);
		}
	}

	@Test
	void nothingIsPutUpUnderABlock() {
		// terrain over the north edge at the height of the wedding arch's lintel (y 5): the arch cannot go there, it moves
		Layout.Ground overhang = new Layout.Ground() {
			@Override
			public boolean air(int x, int y, int z) {
				return !(y == 5 && z <= 3);
			}

			@Override
			public boolean floor(int x, int z) {
				return true;
			}

			@Override
			public boolean occupied(int x, int y, int z) {
				return false;
			}

			@Override
			public boolean reserved(int x, int z) {
				return false;
			}
		};
		Plan w = Layout.plan(Kind.WEDDING, overhang, ALL);
		assertNotNull(w);
		assertFalse(w.bays().contains(0), "the arch under the overhang");
		// every prop has air above it, or another prop of its own piece
		Set<String> cells = new HashSet<>();
		for (Placed c : w.props()) {
			cells.add(c.x() + "," + c.y() + "," + c.z());
		}
		for (Placed c : w.props()) {
			assertTrue(overhang.air(c.x(), c.y() + 1, c.z()) || cells.contains(c.x() + "," + (c.y() + 1) + "," + c.z()), c.toString());
		}
	}

	@Test
	void theMarketTradersMatchTheirStalls() {
		Plan p = Layout.plan(Kind.MARKET, open(), List.of(0, 2));
		assertEquals(4, p.count(Role.MERCHANT));
		Set<Integer> goods = new HashSet<>(), traders = new HashSet<>();
		for (Placed c : p.props()) {
			if (c.prop() == Prop.GOODS) {
				goods.add(c.variant());
			}
		}
		for (Figure f : p.figures()) {
			if (f.role() == Role.MERCHANT) {
				traders.add(f.variant());
			}
		}
		assertEquals(Set.of(0, 1, 2, 3), goods, "four different stalls");
		assertEquals(goods, traders, "each trader sells what its stall shows");
	}

	@Test
	void theBierLiesAlongTheBay() {
		for (int b = 0; b < 4; b++) {
			Plan p = Layout.plan(Kind.FUNERAL, open(), List.of(b));
			for (Placed c : p.props()) {
				if (c.prop() == Prop.BIER) {
					assertEquals(b % 2 == 1, c.alongX(), "bay " + b);
				}
			}
		}
	}
}
