package io.github.albertosa23.heraldia.mines;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.IntBinaryOperator;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.block.Rotation;
import org.junit.jupiter.api.Test;

/**
 * Hillside search of the mine entrances ({@link Hillside}, pure logic) with synthetic terrains: the mouth faces downhill
 * in the four directions, the yard sits at the height of its samples' median, and it does not spawn on flat land, with water
 * in the yard, with the hill too low, with the gallery's shell exposed nor below the world's bottom.
 */
class HillsideTest {
	/** A shape like the small mouth's: a 13 x 8 yard in front and the gallery behind, 14 blocks lower. */
	private static final Hillside.Shape SHAPE = new Hillside.Shape(new BlockPos(14, 16, 8), 8, 0, 20, 7,
			List.of(new int[] {14, 30, -6}, new int[] {6, 37, -6}, new int[] {22, 37, -6}));
	private static final int MIN_Y = -64;

	private static Hillside.Terrain terrain(IntBinaryOperator height) {
		return terrain(height, (x, z) -> 0);
	}

	private static Hillside.Terrain terrain(IntBinaryOperator height, IntBinaryOperator water) {
		return new Hillside.Terrain() {
			@Override
			public int ground(int x, int z) {
				return height.applyAsInt(x, z);
			}

			@Override
			public boolean water(int x, int z) {
				return water.applyAsInt(x, z) != 0;
			}
		};
	}

	/** Flat at 70 up to `edge` and then it rises 1 per block towards (dx, dz). */
	private static IntBinaryOperator ramp(int dx, int dz, int edge) {
		return (x, z) -> 70 + Math.max(0, x * dx + z * dz - edge);
	}

	@Test
	void worldMovesMouthToItsSiteAndRotatesLikeTemplate() {
		for (Rotation r : Rotation.values()) {
			assertArrayEquals(new int[] {100, -40}, Hillside.world(SHAPE, r, 100, -40, 14, 8), r.toString());
			BlockPos expected = new BlockPos(0, 0, 5).rotate(r);       // 5 blocks towards the back of the template
			assertArrayEquals(new int[] {100 + expected.getX(), -40 + expected.getZ()}, Hillside.world(SHAPE, r, 100, -40, 14, 13));
		}
	}

	@Test
	void mouthFacesDownhill() {
		int[][] dirs = {{0, 1}, {-1, 0}, {0, -1}, {1, 0}};
		Rotation[] rotations = {Rotation.NONE, Rotation.CLOCKWISE_90, Rotation.CLOCKWISE_180, Rotation.COUNTERCLOCKWISE_90};
		for (int k = 0; k < 4; k++) {
			Hillside.Site s = Hillside.search(terrain(ramp(dirs[k][0], dirs[k][1], 4)), 0, 0, SHAPE, MIN_Y, false);
			assertNotNull(s, "sube hacia " + k);
			assertEquals(rotations[k], s.rotation(), "el fondo de la plantilla (+z) mira cuesta arriba");
			assertTrue(s.feet() >= 70 && s.feet() <= 74, "patio casi llano en el pie del monte: " + s.feet());
			// behind the mouth, the hill; in front, the yard at the mouth's height
			int[] behind = Hillside.world(SHAPE, s.rotation(), s.x(), s.z(), 14, 18);
			assertTrue(ramp(dirs[k][0], dirs[k][1], 4).applyAsInt(behind[0], behind[1]) >= s.feet() + Hillside.RISE_MIN);
		}
	}

	@Test
	void onFlatDoesNotSpawnExceptWithPlace() {
		Hillside.Terrain flat = terrain((x, z) -> 64);
		assertNull(Hillside.search(flat, 0, 0, SHAPE, MIN_Y, false));
		Hillside.Site s = Hillside.search(flat, 0, 0, SHAPE, MIN_Y, true);
		assertNotNull(s, "/place la coloca igualmente");
		assertEquals(64, s.feet());
		assertEquals(0, s.x());
	}

	@Test
	void flatButWithFarWallIsNotEnough() {
		// the center and the sides see no rise of 5 in any direction: it ends with five columns
		AtomicInteger columns = new AtomicInteger();
		Hillside.Terrain t = terrain((x, z) -> {
			columns.incrementAndGet();
			return 64 + (z > 40 ? 30 : 0);
		});
		assertNull(Hillside.search(t, 0, 0, SHAPE, MIN_Y, false));
		assertEquals(5, columns.get(), "sin pendiente no se mira más terreno");
	}

	@Test
	void waterInYardDiscardsIt() {
		assertNull(Hillside.search(terrain(ramp(0, 1, 4), (x, z) -> z < 8 ? 1 : 0), 0, 0, SHAPE, MIN_Y, false));
	}

	@Test
	void lowHillOrBigDropDoNotWork() {
		// rises 1 every 3 blocks: behind the mouth it does not reach RISE_MIN on average
		assertNull(Hillside.search(terrain((x, z) -> 70 + Math.max(0, z) / 3), 0, 0, SHAPE, MIN_Y, false));
		// the yard itself on a slope: 13 blocks deep with slope 1 = drop > DROP
		assertNull(Hillside.search(terrain((x, z) -> 70 + z), 0, 0, SHAPE, MIN_Y, false));
	}

	@Test
	void shellCannotStickOut() {
		// a hill behind the mouth, but a ravine over the gallery (more than 20 blocks away)
		IntBinaryOperator ravine = (x, z) -> z > 20 ? 40 : ramp(0, 1, 4).applyAsInt(x, z);
		assertNull(Hillside.search(terrain(ravine), 0, 0, SHAPE, MIN_Y, false));
		assertNotNull(Hillside.search(terrain(ravine), 0, 0, SHAPE, MIN_Y, true));
	}

	@Test
	void doesNotGoBelowWorldBottom() {
		assertNull(Hillside.search(terrain((x, z) -> -60 + Math.max(0, z - 4)), 0, 0, SHAPE, MIN_Y, false));
		assertNotNull(Hillside.search(terrain((x, z) -> -40 + Math.max(0, z - 4)), 0, 0, SHAPE, MIN_Y, false));
	}

	@Test
	void highestRiseAndLeastDropWins() {
		// flat between z = -8 and z = 8; to the south it rises 1 per block and to the north 2: the mouth facing south wins (hill to the north)
		IntBinaryOperator twice = (x, z) -> 70 + Math.max(0, z - 8) + 2 * Math.max(0, -z - 8);
		Hillside.Terrain t = terrain(twice);
		Hillside.Site north = Hillside.evaluateAt(t, SHAPE, Rotation.CLOCKWISE_180, 0, -8, MIN_Y, Double.NEGATIVE_INFINITY);
		Hillside.Site south = Hillside.evaluateAt(t, SHAPE, Rotation.NONE, 0, 8, MIN_Y, Double.NEGATIVE_INFINITY);
		assertNotNull(north);
		assertNotNull(south);
		assertTrue(north.note() > south.note(), north + " frente a " + south);
		assertNull(Hillside.evaluateAt(t, SHAPE, Rotation.NONE, 0, 8, MIN_Y, north.note()), "la que no puede ganar se deja a medias");
		Hillside.Site s = Hillside.search(t, 0, 0, SHAPE, MIN_Y, false);
		assertNotNull(s);
		assertEquals(Rotation.CLOCKWISE_180, s.rotation());
		assertEquals(70, s.feet());
	}
}
