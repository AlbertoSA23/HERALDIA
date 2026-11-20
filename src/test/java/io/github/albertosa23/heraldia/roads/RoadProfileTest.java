package io.github.albertosa23.heraldia.roads;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.Test;

/** RoadProfile: a built road's height and paving along it, level and in regular steps, the same from any chunk. */
class RoadProfileTest {
	private static RoadLayout.Route straight(int length) {
		List<double[]> pts = new ArrayList<>();
		for (int x = 0; x <= length; x += 16) {
			pts.add(new double[] {x + 0.5, 0.5});
		}
		return SpawnRoadLayout.toRoute(pts);
	}

	/** Bumpy ground along x (a trunk's hole, a lone hump), all of it dirt but for sand from x = 60. */
	private static RoadProfile.Sample ground(int x, int z) {
		int y = 64 + (x % 7 == 3 ? 2 : 0) - (x % 11 == 5 ? 1 : 0);
		return new RoadProfile.Sample(x >= 60 && x % 5 != 0 ? RoadProfile.Ground.SAND : RoadProfile.Ground.DIRT, y);
	}

	@Test
	void levelOverBumps() {
		RoadProfile p = new RoadProfile(straight(96));
		for (int a = 0; a <= 96; a++) {
			assertEquals(64, p.height(a, RoadProfileTest::ground), "the bumps are smoothed out at " + a);
		}
	}

	@Test
	void slopeClimbsInSteps() {
		RoadProfile p = new RoadProfile(straight(96));
		RoadProfile.Sampler steep = (x, z) -> new RoadProfile.Sample(RoadProfile.Ground.DIRT, 64 + 2 * x);   // two up per block
		int before = p.height(0, steep);
		for (int a = 1; a <= 96; a++) {
			int h = p.height(a, steep);
			assertTrue(Math.abs(h - before) <= 1, "a step of " + (h - before) + " at " + a);
			before = h;
		}
	}

	@Test
	void sameFromAnyOrder() {
		RoadProfile.Sampler hilly = (x, z) -> new RoadProfile.Sample(RoadProfile.Ground.DIRT, 64 + (int) (6 * Math.sin(x / 9.0)));
		RoadProfile forward = new RoadProfile(straight(96)), backward = new RoadProfile(straight(96));
		int[] f = new int[97], b = new int[97];
		for (int a = 0; a <= 96; a++) {
			f[a] = forward.height(a, hilly);
		}
		for (int a = 96; a >= 0; a--) {
			b[a] = backward.height(a, hilly);
		}
		for (int a = 0; a < 96; a++) {
			assertTrue(Math.abs(f[a + 1] - f[a]) <= 1 && Math.abs(b[a + 1] - b[a]) <= 1, "a step at " + a);
			assertTrue(Math.abs(f[a] - b[a]) <= 1, "the two orders differ by more than one at " + a);
		}
	}

	@Test
	void scatteredAsksKeepOneBlockSteps() {
		RoadProfile.Sampler steep = (x, z) -> new RoadProfile.Sample(RoadProfile.Ground.DIRT, 64 + 3 * x);   // three up per block
		RoadProfile p = new RoadProfile(straight(96));
		for (int a : new int[] {0, 60, 30, 90, 15, 45, 75}) {     // as chunks (or their halves) ask, out of order
			p.height(a, steep);
		}
		for (int a = 0; a < 96; a++) {
			int d = p.height(a + 1, steep) - p.height(a, steep);
			assertTrue(Math.abs(d) <= 1, "a step of " + d + " at " + a);
		}
	}

	@Test
	void groundChangesAtOneLine() {
		RoadProfile p = new RoadProfile(straight(96));
		Set<Integer> changes = new HashSet<>();
		RoadProfile.Ground last = p.ground(0, RoadProfileTest::ground);
		for (int a = 1; a <= 96; a++) {
			RoadProfile.Ground g = p.ground(a, RoadProfileTest::ground);
			if (g != last) {
				changes.add(a);
			}
			last = g;
		}
		assertEquals(1, changes.size(), "dirt turns to sand once (the dirt spots in the sand do not show): " + changes);
		assertEquals(RoadProfile.Ground.DIRT, p.ground(10, RoadProfileTest::ground));
		assertEquals(RoadProfile.Ground.SAND, p.ground(90, RoadProfileTest::ground));
	}

	@Test
	void missingChunksAreAskedAgain() {
		RoadProfile p = new RoadProfile(straight(96));
		assertEquals(RoadProfile.MISSING, p.height(40, (x, z) -> null));
		assertEquals(64, p.height(40, RoadProfileTest::ground));
	}

	/**
	 * A cliff across the road (the ground 18 up in two blocks, on a road at least 3 wide): no cut or fill of 10 alone
	 * keeps a road walkable there. Worked out block by block as each chunk asks (as before), the road meets the cliff at
	 * its own pace and the columns' clamp (the ground cut or filled at most 10) leaves a step of several blocks; worked
	 * out whole ({@link RoadProfile#prepare}), the climb starts early enough that every column stays within the caps and
	 * one block of the next: what the owner's spawn (drop 29, 27 steps on its roads) needed.
	 */
	@Test
	void aCliffIsClimbedFromAfarWhenTheWholeRoadIsKnown() {
		RoadProfile.Sampler cliff = (x, z) -> new RoadProfile.Sample(RoadProfile.Ground.DIRT, x < 40 ? 64 : x < 42 ? 64 + 9 * (x - 39) : 82);
		RoadProfile lazy = new RoadProfile(straight(96));
		int worstLazy = 0;
		for (int a : new int[] {0, 60, 30, 90, 15, 45, 75}) {
			lazy.height(a, cliff);
		}
		for (int a = 0; a < 96; a++) {
			worstLazy = Math.max(worstLazy, Math.abs(column(lazy.height(a + 1, cliff), a + 1, cliff, 10, 10) - column(lazy.height(a, cliff), a, cliff, 10, 10)));
		}
		assertTrue(worstLazy > 1, "block by block the cliff leaves a step (the old way): " + worstLazy);
		RoadProfile whole = new RoadProfile(straight(96));
		assertTrue(whole.prepare(cliff, 1.5, 10, 10));
		assertTrue(whole.prepared());
		assertEquals(10, whole.cut());
		assertEquals(10, whole.fill());
		for (int a = 0; a < 96; a++) {
			int h0 = column(whole.height(a, cliff), a, cliff, whole.cut(), whole.fill());
			int h1 = column(whole.height(a + 1, cliff), a + 1, cliff, whole.cut(), whole.fill());
			assertTrue(Math.abs(h1 - h0) <= 1, "a step of " + (h1 - h0) + " at " + a);
			assertEquals(whole.height(a, cliff), h0, "a column clamped off the road's height at " + a);
		}
	}

	/** A cliff higher than both caps and the run together: the caps widen only as far as that cliff needs, and no step is left. */
	@Test
	void aCliffTooHighForTheCapsWidensThemJustEnough() {
		RoadProfile.Sampler wall = (x, z) -> new RoadProfile.Sample(RoadProfile.Ground.STONE, x < 48 ? 64 : 100);   // 36 up at once
		RoadProfile whole = new RoadProfile(straight(96));
		assertTrue(whole.prepare(wall, 1.5, 10, 10));
		assertTrue(whole.cut() > 10 && whole.cut() <= RoadProfile.MAX_CAP, "caps widened: " + whole.cut());
		for (int a = 0; a < 96; a++) {
			int h0 = column(whole.height(a, wall), a, wall, whole.cut(), whole.fill());
			int h1 = column(whole.height(a + 1, wall), a + 1, wall, whole.cut(), whole.fill());
			assertTrue(Math.abs(h1 - h0) <= 1, "a step of " + (h1 - h0) + " at " + a);
		}
	}

	/** Not every chunk loaded yet: nothing kept, the road is worked out later. */
	@Test
	void prepareWaitsForEveryColumn() {
		RoadProfile p = new RoadProfile(straight(96));
		assertTrue(!p.prepare((x, z) -> x > 50 ? null : new RoadProfile.Sample(RoadProfile.Ground.DIRT, 64), 1.5, 10, 10));
		assertTrue(!p.prepared());
		assertTrue(p.columns(1.5).size() >= 97);
	}

	/** A road column's paving height as BuiltRoads lays it: the road's height, cut or filled at most so much. */
	private static int column(int t, int a, RoadProfile.Sampler f, int cut, int fill) {
		int g = f.at(a, 0).y();
		return Math.clamp(t, g - cut, g + fill);
	}
}
