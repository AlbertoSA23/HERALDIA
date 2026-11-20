package io.github.albertosa23.heraldia.herald;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;
import java.util.function.IntBinaryOperator;
import org.junit.jupiter.api.Test;

/**
 * OutskirtsPlan: the grounds' heights on made-up terrain. Walkable where the caps allow it (no two side by side columns
 * more than a block apart), within the caps everywhere, the town's ground at its footprint, the edge as it was, the
 * shore never under the water, the houses on flat pads, the trees on gentle ground.
 */
class OutskirtsPlanTest {
	static final int RING = 50, SIDE = 128, N = SIDE + 2 * RING, GROUND = 70;
	static final OutskirtsPlan.Params P = new OutskirtsPlan.Params(10, 10, 6, 1, 5);
	/** The rows by the area's edge where two fixed points (the natural edge, a road cut into it) may not be joined walking. */
	static final int BLEND = 8;

	/** A grid from a height function (world x, z from 0 at the area's corner), the town in the middle. */
	static OutskirtsPlan grid(IntBinaryOperator height, byte[] kind, int[] h) {
		for (int x = 0; x < N; x++) {
			for (int z = 0; z < N; z++) {
				int i = x * N + z;
				boolean town = x >= RING && z >= RING && x < RING + SIDE && z < RING + SIDE;
				if (kind[i] == 0 && !town) {
					kind[i] = OutskirtsPlan.LAND;
				}
				if (town) {
					kind[i] = OutskirtsPlan.TOWN;
				}
				h[i] = town ? GROUND : height.applyAsInt(x, z);
			}
		}
		return new OutskirtsPlan(0, 0, N, kind, h, GROUND, P);
	}

	static OutskirtsPlan.Result plan(OutskirtsPlan p, List<OutskirtsPlan.Slot> slots, int houses, List<int[]> sites) {
		return p.plan(slots, houses, sites, 10, new boolean[N * N]);
	}

	static int steps(byte[] kind, int[] t) {
		int out = 0;
		for (int x = 0; x < N; x++) {
			for (int z = 0; z < N; z++) {
				int i = x * N + z;
				if (kind[i] != OutskirtsPlan.LAND) {
					continue;
				}
				if (x + 1 < N && kind[i + N] != OutskirtsPlan.WATER && Math.abs(t[i + N] - t[i]) > 1) {
					out++;
				}
				if (z + 1 < N && kind[i + 1] != OutskirtsPlan.WATER && Math.abs(t[i + 1] - t[i]) > 1) {
					out++;
				}
			}
		}
		return out;
	}

	static void caps(byte[] kind, int[] h, int[] t) {
		for (int i = 0; i < N * N; i++) {
			if (kind[i] == OutskirtsPlan.LAND) {
				assertTrue(t[i] >= h[i] - P.cut() && t[i] <= h[i] + P.fill(), "a cut or fill over the caps at " + i);
			} else {
				assertEquals(h[i], t[i], "a column that is not natural ground was changed");
			}
		}
	}

	static void edge(int[] h, int[] t) {
		for (int k = 0; k < N; k++) {
			for (int i : new int[] {k, (N - 1) * N + k, k * N, k * N + N - 1}) {
				assertEquals(h[i], t[i], "the edge moved");
			}
		}
	}

	/**
	 * The ground as the owner asked for it: no ramps (hardly a one-block step after another), every step of more than a
	 * block a terrace's riser (at most RISE + 1: two levels' rounding), and walkable next to every kept column.
	 */
	static void terraced(byte[] kind, int[] h, OutskirtsPlan.Result res) {
		int[] t = res.target();
		int land = 0;
		for (byte k : kind) {
			land += k == OutskirtsPlan.LAND ? 1 : 0;
		}
		assertTrue(res.ramps() <= land / 100, res.ramps() + " one-block steps in ramps (of " + land + " columns)");
		for (int x = 0; x < N; x++) {
			for (int z = 0; z < N; z++) {
				int i = x * N + z;
				if (kind[i] != OutskirtsPlan.LAND) {
					continue;
				}
				for (int j : new int[] {i + N, i + 1}) {
					if (j < N * N && kind[j] == OutskirtsPlan.LAND) {
						assertTrue(Math.abs(t[j] - t[i]) <= OutskirtsPlan.RISE + 1, "a riser of " + (t[j] - t[i]) + " at " + x + " " + z);
					}
				}
				// the blend into the natural edge (which keeps its own height, a road cut into it too) is the edge's
				boolean edge = x < BLEND || z < BLEND || x >= N - BLEND || z >= N - BLEND;
				for (int j : new int[] {i + N, i - N, i + 1, i - 1}) {
					if (!edge && j >= 0 && j < N * N && kind[j] == OutskirtsPlan.KEPT) {
						assertTrue(Math.abs(t[i] - h[j]) <= 1, "the ground beside a kept column is not walkable at " + x + " " + z);
					}
				}
			}
		}
	}

	/** Steps of more than a block between LAND columns at least {@code from} columns in from the area's edge. */
	static int stepsInside(byte[] kind, int[] t, int from) {
		int out = 0;
		for (int x = from; x < N - from; x++) {
			for (int z = from; z < N - from; z++) {
				int i = x * N + z;
				if (kind[i] != OutskirtsPlan.LAND) {
					continue;
				}
				if (x + 1 < N - from && kind[i + N] == OutskirtsPlan.LAND && Math.abs(t[i + N] - t[i]) > 1
						|| z + 1 < N - from && kind[i + 1] == OutskirtsPlan.LAND && Math.abs(t[i + 1] - t[i]) > 1) {
					out++;
				}
			}
		}
		return out;
	}

	/** Gentle natural ground (no step over a block, as most of a plain): it stays so, and its bumps go. */
	@Test
	void bumpyPlainBecomesWalkable() {
		Random r = new Random(1);
		int[] base = new int[N];
		for (int k = 1; k < N; k++) {
			base[k] = Math.clamp(base[k - 1] + r.nextInt(3) - 1, -4, 4);
		}
		byte[] kind = new byte[N * N];
		int[] h = new int[N * N];
		OutskirtsPlan.Result res = plan(grid((x, z) -> GROUND + (base[x] + base[z]) / 2, kind, h), List.of(), 0, List.of());
		assertEquals(0, steps(kind, res.target()), "steps left on a plain");
		assertEquals(0, res.steep());
		caps(kind, h, res.target());
		edge(h, res.target());
	}

	/**
	 * Rough natural ground (lone humps and pits of 3, steps of 2 everywhere): every step it had goes but those of the blend
	 * into the natural ground at the edge (which keeps its own) in the outermost rows.
	 */
	@Test
	void roughGroundKeepsStepsOnlyWhereItMeetsTheNaturalEdge() {
		Random r = new Random(2);
		int[] noise = new int[N * N];
		for (int i = 0; i < N * N; i++) {
			noise[i] = r.nextInt(3) + (r.nextInt(30) == 0 ? 3 : 0) - (r.nextInt(30) == 0 ? 3 : 0);
		}
		byte[] kind = new byte[N * N];
		int[] h = new int[N * N];
		OutskirtsPlan.Result res = plan(grid((x, z) -> GROUND + noise[x * N + z], kind, h), List.of(), 0, List.of());
		assertTrue(res.before() > 1000, "the made-up ground is rough: " + res.before());
		assertEquals(0, stepsInside(kind, res.target(), 4), "steps further in than the edge's blend");
		assertTrue(res.steps() < res.before() / 20, res.steps() + " steps left of " + res.before());
		caps(kind, h, res.target());
		edge(h, res.target());
	}

	@Test
	void hillsideIsGentleAndMeetsTheTown() {
		byte[] kind = new byte[N * N];
		int[] h = new int[N * N];
		// a slope of a block every eight along x (the site the search picks: its median at the town's ground)
		OutskirtsPlan p = grid((x, z) -> GROUND + (x - N / 2) / 8 + (int) (3 * Math.sin(z / 7.0)), kind, h);
		OutskirtsPlan.Result res = plan(p, List.of(), 0, List.of());
		int[] t = res.target();
		terraced(kind, h, res);                            // the cone down from the town to the low side: terraces, not a ramp
		caps(kind, h, t);
		edge(h, t);
		for (int z = RING; z < RING + SIDE; z++) {          // beside the wall: within a block of the town's ground
			assertTrue(Math.abs(t[(RING - 1) * N + z] - GROUND) <= 1 && Math.abs(t[(RING + SIDE) * N + z] - GROUND) <= 1);
		}
	}

	@Test
	void aCliffTooHighIsDoneAsWellAsTheCapsAllowAndCounted() {
		byte[] kind = new byte[N * N];
		int[] h = new int[N * N];
		OutskirtsPlan p = grid((x, z) -> x < 20 ? GROUND + 40 : GROUND, kind, h);   // a 40-block cliff in the ring
		OutskirtsPlan.Result res = plan(p, List.of(), 0, List.of());
		assertTrue(res.steep() > 0, "a cliff no cap can soften is reported");
		caps(kind, h, res.target());                       // and never cut or filled over the caps
		edge(h, res.target());
	}

	@Test
	void theShoreStaysOverTheWater() {
		byte[] kind = new byte[N * N];
		int[] h = new int[N * N];
		for (int x = 10; x < 30; x++) {
			for (int z = 10; z < 40; z++) {
				kind[x * N + z] = OutskirtsPlan.WATER;
			}
		}
		OutskirtsPlan p = grid((x, z) -> x >= 10 && x < 30 && z >= 10 && z < 40 ? GROUND - 2 : GROUND + 1 + (x / 9 + z / 13) % 2, kind, h);
		int[] t = plan(p, List.of(), 0, List.of()).target();
		for (int x = 9; x <= 30; x++) {
			for (int z = 9; z <= 40; z++) {
				int i = x * N + z;
				if (kind[i] == OutskirtsPlan.LAND && (kind[i + N] == OutskirtsPlan.WATER || kind[i - N] == OutskirtsPlan.WATER
						|| kind[i + 1] == OutskirtsPlan.WATER || kind[i - 1] == OutskirtsPlan.WATER)) {
					assertTrue(t[i] >= GROUND - 2, "a shore column under the water's surface at " + x + " " + z);
				}
			}
		}
		assertEquals(0, steps(kind, t));
	}

	@Test
	void keptColumnsStayAndTheGroundMeetsThem() {
		byte[] kind = new byte[N * N];
		int[] h = new int[N * N];
		for (int z = 0; z < RING; z++) {                    // a built road out of the north gate, 5 wide, as it was laid
			for (int x = N / 2 - 2; x <= N / 2 + 2; x++) {
				kind[x * N + z] = OutskirtsPlan.KEPT;
			}
		}
		OutskirtsPlan p = grid((x, z) -> x >= N / 2 - 2 && x <= N / 2 + 2 && z < RING ? GROUND - (RING - z) / 8 : GROUND + 3
				+ (x / 5 + z / 7) % 2, kind, h);
		OutskirtsPlan.Result res = plan(p, List.of(), 0, List.of());
		int[] t = res.target();
		caps(kind, h, t);
		// the road reaches the area's edge cut 6 blocks into ground that stays natural there: the ground climbs from it in
		// a walkable ramp by the road and then in terraces
		terraced(kind, h, res);
	}

	@Test
	void housesSitOnFlatPadsAndTreesOnGentleGround() {
		byte[] kind = new byte[N * N];
		int[] h = new int[N * N];
		OutskirtsPlan p = grid((x, z) -> GROUND + (int) (4 * Math.sin(x / 15.0) + 3 * Math.cos(z / 11.0)), kind, h);
		List<OutskirtsPlan.Slot> slots = List.of(new OutskirtsPlan.Slot(0, 20, 20, 28, 29), new OutskirtsPlan.Slot(1, 190, 30, 199, 38),
				new OutskirtsPlan.Slot(2, 100, 190, 110, 199), new OutskirtsPlan.Slot(3, 20, 100, 29, 108));
		List<int[]> sites = new ArrayList<>(List.of(new int[] {40, 12}, new int[] {12, 160}, new int[] {215, 120}, new int[] {24, 24}));
		OutskirtsPlan.Result res = plan(p, slots, 3, sites);
		assertEquals(3, res.houses().size(), "three asked for, three fit");
		int[] t = res.target();
		for (OutskirtsPlan.House hs : res.houses()) {
			OutskirtsPlan.Slot s = hs.slot();
			for (int x = s.x0() - 1; x <= s.x1() + 1; x++) {
				for (int z = s.z0() - 1; z <= s.z1() + 1; z++) {
					assertEquals(hs.y(), t[x * N + z], "a pad that is not flat");
				}
			}
		}
		terraced(kind, h, res);
		caps(kind, h, t);
		assertFalse(res.cherries().stream().anyMatch(c -> c[0] == 24 && c[1] == 24), "a tree on a house's plot");
		assertEquals(3, res.cherries().size());
	}

	@Test
	void aSlotOnWaterOrTooSteepIsSkipped() {
		byte[] kind = new byte[N * N];
		int[] h = new int[N * N];
		for (int x = 18; x < 32; x++) {
			for (int z = 18; z < 32; z++) {
				kind[x * N + z] = OutskirtsPlan.WATER;
			}
		}
		OutskirtsPlan p = grid((x, z) -> z > 170 ? GROUND + (z - 170) * 2 : GROUND, kind, h);
		List<OutskirtsPlan.Slot> slots = List.of(new OutskirtsPlan.Slot(0, 20, 20, 28, 29), new OutskirtsPlan.Slot(1, 100, 200, 110, 210),
				new OutskirtsPlan.Slot(2, 20, 100, 29, 108));
		OutskirtsPlan.Result res = plan(p, slots, 3, List.of());
		assertEquals(List.of(2), res.houses().stream().map(hs -> hs.slot().index()).toList());
	}

	/** A cave's mouth 40 deep in a plain: covered with a lid at the plain's height, no crater dug round it, not counted steep. */
	@Test
	void aNarrowPitIsCoveredNotCratered() {
		byte[] kind = new byte[N * N];
		int[] h = new int[N * N];
		OutskirtsPlan p = grid((x, z) -> x >= 20 && x < 24 && z >= 100 && z < 104 ? GROUND - 40 : GROUND, kind, h);
		OutskirtsPlan.Result res = plan(p, List.of(), 0, List.of());
		int[] t = res.target();
		assertEquals(0, res.steep());
		assertEquals(16, res.lids());
		for (int x = 15; x < 30; x++) {
			for (int z = 95; z < 110; z++) {
				assertEquals(GROUND, t[x * N + z], "the plain round the pit (and its lid) at " + x + " " + z);
				assertEquals(x >= 20 && x < 24 && z >= 100 && z < 104, p.lid(x * N + z, t[x * N + z]));
			}
		}
		assertEquals(0, steps(kind, t));
	}

	/** Two places of one house (a group): the second only if the first does not fit, never both. */
	@Test
	void oneHousePerGroup() {
		byte[] kind = new byte[N * N];
		int[] h = new int[N * N];
		for (int x = 18; x < 32; x++) {
			for (int z = 18; z < 32; z++) {
				kind[x * N + z] = OutskirtsPlan.WATER;
			}
		}
		OutskirtsPlan p = grid((x, z) -> GROUND, kind, h);
		List<OutskirtsPlan.Slot> slots = List.of(new OutskirtsPlan.Slot(0, 20, 20, 28, 29, 0), new OutskirtsPlan.Slot(1, 190, 30, 199, 38, 1),
				new OutskirtsPlan.Slot(2, 20, 60, 29, 68, 0), new OutskirtsPlan.Slot(3, 190, 60, 199, 68, 1));
		OutskirtsPlan.Result res = plan(p, slots, 4, List.of());
		assertEquals(List.of(1, 2), res.houses().stream().map(hs -> hs.slot().index()).sorted().toList());
	}

	/** The ramp count: runs of three or more one-block steps the same way, each within two columns of the next. */
	@Test
	void rampsAreRunsOfOneBlockStepsOneAfterAnother() {
		int n = 12;
		boolean[] in = new boolean[n * n];
		java.util.Arrays.fill(in, true);
		int[] y = new int[n * n];
		for (int u = 0; u < n; u++) {
			for (int v = 0; v < n; v++) {
				y[u * n + v] = u == 0 ? v : u == 1 ? v / 3 : u == 2 ? (v < 6 ? v : 20 + v) : u == 3 ? (v % 2) : 0;
			}
		}
		// row 0: a staircase of 11 one-block steps (11); row 1: a step every 3 columns (none); row 2: 5 steps, a wall, 5 steps
		// (5 + 5); row 3: up and down (none); down the columns (v, v / 3, v or 20 + v, v % 2, then 0) no four steps go the same way
		assertEquals(11 + 5 + 5, OutskirtsPlan.ramps(n, y, in));
		in[5] = false;                                        // a column not counted (a road's, water) ends a run: 4, then 5
		assertEquals(4 + 5 + 5 + 5, OutskirtsPlan.ramps(n, y, in));
	}

	/**
	 * The town on a hilltop (the ground falls a block every two columns all round it, 25 blocks over the ring, as at the
	 * owner's spawn): a walkable plan would be concentric "rice terraces", dozens of one-block steps one after another
	 * all round the wall. Planned as terraces instead: hardly a ramp left, each terrace's riser at most RISE blocks
	 * (the cone the caps cannot soften aside), the caps and the edge kept, and next to the kept road a walkable ramp.
	 */
	@Test
	void aSteepHillsideBecomesTerracesNotRiceTerraces() {
		byte[] kind = new byte[N * N];
		int[] h = new int[N * N];
		for (int z = 0; z < RING; z++) {                    // a built road out of the north gate, 5 wide
			for (int x = N / 2 - 2; x <= N / 2 + 2; x++) {
				kind[x * N + z] = OutskirtsPlan.KEPT;
			}
		}
		IntBinaryOperator hill = (x, z) -> {
			int d = Math.max(Math.max(RING - x, x - (RING + SIDE - 1)), Math.max(RING - z, z - (RING + SIDE - 1)));
			return GROUND - Math.max(0, d) / 2;
		};
		OutskirtsPlan p = grid(hill, kind, h);
		OutskirtsPlan.Result res = plan(p, List.of(), 0, List.of());
		int[] t = res.target();
		int land = 0;
		for (byte k : kind) {
			land += k == OutskirtsPlan.LAND ? 1 : 0;
		}
		assertTrue(res.rampsBefore() > land / 4, "the hillside is a ramp all round: " + res.rampsBefore());
		assertTrue(res.ramps() < land / 50, res.ramps() + " one-block steps in ramps left (of " + land + " columns)");
		assertTrue(res.walls() > 0, "terraces' walls");
		caps(kind, h, t);
		edge(h, t);
		for (int x = 0; x < N; x++) {
			for (int z = 0; z < N; z++) {
				int i = x * N + z;
				if (kind[i] != OutskirtsPlan.LAND) {
					continue;
				}
				for (int j : new int[] {i + N, i + 1}) {
					if (j < N * N && kind[j] == OutskirtsPlan.LAND) {
						assertTrue(Math.abs(t[j] - t[i]) <= OutskirtsPlan.RISE + 1, "a riser of " + (t[j] - t[i]) + " at " + x + " " + z);
					}
				}
				for (int j : new int[] {i + N, i - N, i + 1, i - 1}) {
					if (j >= 0 && j < N * N && kind[j] == OutskirtsPlan.KEPT) {
						assertTrue(Math.abs(t[i] - h[j]) <= 1, "the ground beside the road is not walkable at " + x + " " + z);
					}
				}
			}
		}
	}

	/**
	 * A pond high up beside the town, in ground the caps cannot bring down to the town's (too steep): the plan does what
	 * it can there, and before this it could put a shore column under the pond's surface (with nothing beside it, still
	 * water stands in the air for good). Never: every shore column stays at least as high as the water beside it.
	 */
	@Test
	void theShoreHoldsEvenWhereTheGroundIsTooSteep() {
		byte[] kind = new byte[N * N];
		int[] h = new int[N * N];
		for (int x = 30; x < 42; x++) {
			for (int z = 100; z < 112; z++) {
				kind[x * N + z] = OutskirtsPlan.WATER;
			}
		}
		OutskirtsPlan p = grid((x, z) -> x >= 30 && x < 42 && z >= 100 && z < 112 ? GROUND + 24 : x < RING ? GROUND + 25 : GROUND, kind, h);
		OutskirtsPlan.Result res = plan(p, List.of(), 0, List.of());
		assertTrue(res.steep() > 0, "too steep to level there");
		int[] t = res.target();
		for (int x = 28; x <= 43; x++) {
			for (int z = 98; z <= 113; z++) {
				int i = x * N + z;
				if (kind[i] == OutskirtsPlan.LAND && (kind[i + N] == OutskirtsPlan.WATER || kind[i - N] == OutskirtsPlan.WATER
						|| kind[i + 1] == OutskirtsPlan.WATER || kind[i - 1] == OutskirtsPlan.WATER)) {
					assertTrue(t[i] >= GROUND + 24, "a shore column under the pond's surface at " + x + " " + z + ": " + t[i]);
				}
			}
		}
	}
}
