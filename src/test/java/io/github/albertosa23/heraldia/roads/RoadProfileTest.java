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
}
