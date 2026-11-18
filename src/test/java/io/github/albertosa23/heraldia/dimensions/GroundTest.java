package io.github.albertosa23.heraldia.dimensions;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import io.github.albertosa23.heraldia.command.SafeSpot;
import java.util.function.IntPredicate;
import org.junit.jupiter.api.Test;

/** Where the Nether and End structures rest ({@link Ground}) and the safe spot under the ceiling ({@link SafeSpot#underCeiling}). */
class GroundTest {
	/** Fake Nether column: bedrock on top (123 to 127), air except the solid stretches [a, b] and lava below 32. */
	private record Column(int[][] SOLIDS) {
		boolean solid(int y) {
			if (y >= 123 || y <= 0) {
				return true;
			}
			for (int[] m : SOLIDS) {
				if (m[0] <= y && y <= m[1]) {
					return true;
				}
			}
			return false;
		}

		boolean lava(int y) {
			return y <= 31 && !solid(y);
		}

		boolean air(int y) {
			return !solid(y) && !lava(y);
		}

		IntPredicate s() {
			return this::solid;
		}

		IntPredicate a() {
			return this::air;
		}
	}

	@Test
	void netherFindsFirstGroundWithAirAboveTopDown() {
		// ground at 40 (solid from 1 to 39) and a ledge at 100 with only 4 of air up to another solid block at 104
		Column c = new Column(new int[][] {{1, 39}, {95, 99}, {104, 122}});
		assertEquals(40, Ground.nether(c.s(), c.a(), Ground.NETHER_FROM, Ground.NETHER_TO, 30), "con 30 de aire, la repisa no cabe");
		assertEquals(100, Ground.nether(c.s(), c.a(), Ground.NETHER_FROM, Ground.NETHER_TO, 4), "la repisa, con 4 de aire");
		assertEquals(40, Ground.nether(c.s(), c.a(), Ground.NETHER_FROM, Ground.NETHER_TO, 5), "con 5 de aire, el suelo de abajo");
		assertEquals(40, Ground.nether(c.s(), c.a(), Ground.NETHER_FROM, Ground.NETHER_TO, 55));
		assertEquals(Ground.NONE, Ground.nether(c.s(), c.a(), Ground.NETHER_FROM, Ground.NETHER_TO, 56), "no cabe en ningún sitio");
	}

	@Test
	void netherNeverOnLavaOrUnderCeiling() {
		Column seaSide = new Column(new int[][] {{1, 10}});              // all lava up to 31 and air up to the ceiling
		assertEquals(Ground.NONE, Ground.nether(seaSide.s(), seaSide.a(), Ground.NETHER_FROM, Ground.NETHER_TO, 4), "el mar de lava no sostiene");
		Column high = new Column(new int[][] {{1, 118}});             // solid up to 118: air from 119 to 122
		assertEquals(Ground.NONE, Ground.nether(high.s(), high.a(), Ground.NETHER_FROM, Ground.NETHER_TO, 3),
				"un suelo por encima de NETHER_DESDE (pegado al techo) no vale");
		Column island = new Column(new int[][] {{1, 20}, {32, 32}});    // a slab at 32 over the lava
		assertEquals(Ground.NONE, Ground.nether(island.s(), island.a(), Ground.NETHER_FROM, Ground.NETHER_TO, 4),
				"por debajo de NETHER_HASTA no se busca");
		for (int free = 2; free <= 40; free++) {
			int y = Ground.nether(new Column(new int[][] {{1, 60}}).s(), new Column(new int[][] {{1, 60}}).a(),
					Ground.NETHER_FROM, Ground.NETHER_TO, free);
			assertEquals(61, y, "libre " + free);
		}
	}

	@Test
	void netherCornersAndDrop() {
		Column c = new Column(new int[][] {{1, 63}});
		assertEquals(64, Ground.netherNear(c.s(), c.a(), 60), "a +4 del centro");
		assertEquals(64, Ground.netherNear(c.s(), c.a(), 64));
		assertEquals(Ground.NONE, Ground.netherNear(c.s(), c.a(), 50), "a +14: fuera del desnivel");
		assertTrue(Ground.flat(64, 64, 60, 69, 59));
		assertFalse(Ground.flat(64, 64, 64, 70, 64), "una esquina a +6");
		assertFalse(Ground.flat(64, 64, Ground.NONE, 64, 64), "una esquina sin suelo (barranco)");
	}

	@Test
	void endOnlyOnOuterFlatIslands() {
		int far = Ground.END_CENTRAL_RADIUS + 100;
		assertEquals(62, Ground.end(far, 0, 62, 60, 64, 63, 61));
		assertEquals(Ground.NONE, Ground.end(far, 0, 62, 0, 64, 63, 61), "una esquina sobre el vacío");
		assertEquals(Ground.NONE, Ground.end(far, 0, 0, 0, 0, 0, 0), "todo vacío");
		assertEquals(Ground.NONE, Ground.end(far, 0, 62, 62, 62, 62, 70), "desnivel de 8");
		assertEquals(Ground.NONE, Ground.end(Ground.END_CENTRAL_RADIUS - 1, 0, 62, 62, 62, 62, 62), "la isla central (y el dragón)");
		assertEquals(Ground.NONE, Ground.end(700, 700, 62, 62, 62, 62, 62), "a 990 bloques del centro");
		assertEquals(62, Ground.end(-800, -800, 62, 62, 62, 62, 62), "a 1.131 bloques");
		assertEquals(Ground.NONE, Ground.end(far, 0, Ground.END_MIN - 1, 44, 44, 44, 44), "demasiado bajo: un islote suelto");
	}

	/** A {@link SafeSpot} world with a ceiling: bedrock at 123-127, solid up to {@code ground} - 1 and lava at y = ground if asked. */
	private static SafeSpot.World world(int ground, boolean lava) {
		return new SafeSpot.World() {
			@Override
			public SafeSpot.Cell en(int x, int y, int z) {
				if (y >= 123 || y < ground) {
					return SafeSpot.Cell.SOLID;
				}
				return lava && y == ground ? SafeSpot.Cell.DANGER : SafeSpot.Cell.FREE;
			}

			@Override
			public int height(int x, int z) {
				return 128;
			}

			@Override
			public int minY() {
				return 0;
			}

			@Override
			public int maxY() {
				return 256;
			}
		};
	}

	@Test
	void underCeilingFindsGroundNotCeiling() {
		assertEquals(70, SafeSpot.underCeiling(world(70, false), 0, 0, 120, 32));
		assertEquals(0, SafeSpot.underCeiling(world(70, true), 0, 0, 120, 32), "sobre lava no: la mínima del mundo");
		assertEquals(0, SafeSpot.underCeiling(world(20, false), 0, 0, 120, 32), "por debajo de hasta no se busca");
	}
}
