package io.github.albertosa23.heraldia.command;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import io.github.albertosa23.heraldia.command.SafeSpot.Cell;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import org.junit.jupiter.api.Test;

/** Safe teleport (pure logic): on top of the ground, without suffocation, never in lava, floating on water. */
class SafeSpotTest {
	/** Test world: stone ground up to y = 63 (free space starts at 64) and whatever is put on top. */
	static class World implements SafeSpot.World {
		final Map<Long, Cell> cells = new HashMap<>();
		final Map<Long, Integer> heights = new HashMap<>();
		int ground = 64;

		static long k(int x, int y, int z) {
			return ((long) x & 0xFFFFF) << 40 | ((long) y & 0xFFF) << 20 | ((long) z & 0xFFFFF);
		}

		static long k(int x, int z) {
			return k(x, 0, z);
		}

		World put(int x, int y, int z, Cell c) {
			cells.put(k(x, y, z), c);
			if (c != Cell.FREE) {
				heights.merge(k(x, z), y + 1, Math::max);
			}
			return this;
		}

		@Override
		public Cell en(int x, int y, int z) {
			Cell c = cells.get(k(x, y, z));
			return c != null ? c : y < ground ? Cell.SOLID : Cell.FREE;
		}

		@Override
		public int height(int x, int z) {
			return heights.getOrDefault(k(x, z), ground);
		}

		@Override
		public int minY() {
			return -64;
		}

		@Override
		public int maxY() {
			return 320;
		}
	}

	@Test
	void flatGroundInTheCenter() {
		assertEquals(Optional.of(new SafeSpot.Site(10, 64, -5)), SafeSpot.search(new World(), 10, -5, SafeSpot.RADIUS));
	}

	@Test
	void neverInLavaOrFire() {
		World m = new World().put(0, 63, 0, Cell.DANGER);     // a lava puddle in the center
		SafeSpot.Site s = SafeSpot.search(m, 0, 0, SafeSpot.RADIUS).orElseThrow();
		assertEquals(64, s.y());
		assertEquals(1, Math.abs(s.x()) + Math.abs(s.z()), "la columna de al lado");
		World fire = new World().put(0, 64, 0, Cell.DANGER); // fire on top of the ground
		assertTrue(Math.abs(SafeSpot.search(fire, 0, 0, SafeSpot.RADIUS).orElseThrow().x())
				+ Math.abs(SafeSpot.search(fire, 0, 0, SafeSpot.RADIUS).orElseThrow().z()) > 0);
	}

	@Test
	void noSuffocationUnderOverhang() {
		// the column has a low ceiling: the heightmap gives the top of the ceiling, which is a valid spot (in the open air)
		World m = new World().put(0, 65, 0, Cell.SOLID);
		assertEquals(Optional.of(new SafeSpot.Site(0, 66, 0)), SafeSpot.search(m, 0, 0, SafeSpot.RADIUS));
		// a suffocating block at head height (no heightmap that sees it: e.g. leaves) discards the column
		World leaves = new World();
		leaves.cells.put(World.k(0, 65, 0), Cell.SOLID);
		SafeSpot.Site s = SafeSpot.search(leaves, 0, 0, SafeSpot.RADIUS).orElseThrow();
		assertTrue(s.x() != 0 || s.z() != 0);
		assertTrue(SafeSpot.valid(leaves, s.x(), s.y(), s.z()));
	}

	@Test
	void floatsOnTheSea() {
		World m = new World();
		m.ground = 40;
		for (int x = -10; x <= 10; x++) {
			for (int z = -10; z <= 10; z++) {
				for (int y = 40; y < 63; y++) {
					m.put(x, y, z, Cell.WATER);
				}
			}
		}
		assertEquals(Optional.of(new SafeSpot.Site(0, 63, 0)), SafeSpot.search(m, 0, 0, SafeSpot.RADIUS), "en la superficie del agua");
	}

	@Test
	void noSpotIfEverythingIsDangerous() {
		World m = new World();
		for (int x = -3; x <= 3; x++) {
			for (int z = -3; z <= 3; z++) {
				m.put(x, 63, z, Cell.DANGER);
			}
		}
		assertEquals(Optional.empty(), SafeSpot.search(m, 0, 0, 3));
		assertTrue(SafeSpot.search(m, 0, 0, 4).isPresent(), "un poco más lejos ya hay suelo");
	}

	@Test
	void emptyColumnsOrUpToTheCeiling() {
		World empty = new World() {
			@Override
			public int height(int x, int z) {
				return minY();
			}
		};
		assertEquals(Optional.empty(), SafeSpot.search(empty, 0, 0, 2));
		World ceiling = new World() {
			@Override
			public int height(int x, int z) {
				return maxY() - 1;
			}
		};
		assertEquals(Optional.empty(), SafeSpot.search(ceiling, 0, 0, 2));
	}

	@Test
	void spiralFromCenterOutAndDeterministic() {
		List<int[]> e = SafeSpot.spiral(2);
		assertArrayEquals(new int[] {0, 0}, e.getFirst());
		for (int i = 1; i < e.size(); i++) {
			int a = e.get(i - 1)[0] * e.get(i - 1)[0] + e.get(i - 1)[1] * e.get(i - 1)[1];
			int b = e.get(i)[0] * e.get(i)[0] + e.get(i)[1] * e.get(i)[1];
			assertTrue(a <= b);
		}
		assertEquals(13, e.size(), "círculo de radio 2");
		assertEquals(e.stream().map(x -> x[0] + "," + x[1]).toList(), SafeSpot.spiral(2).stream().map(x -> x[0] + "," + x[1]).toList());
	}
}
