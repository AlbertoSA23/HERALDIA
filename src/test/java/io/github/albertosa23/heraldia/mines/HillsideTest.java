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
 * Búsqueda de ladera de las entradas a mina ({@link Hillside}, lógica pura) con terrenos sintéticos: la boca mira cuesta
 * abajo en las cuatro direcciones, el patio queda a la altura de la mediana de sus muestras, y no sale en llano, con agua
 * en el patio, con el monte demasiado bajo, con el casco de la galería al aire ni por debajo del fondo del mundo.
 */
class HillsideTest {
	/** Una forma como la de la boca pequeña: patio de 13 x 8 delante y la galería detrás, 14 bloques más abajo. */
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

	/** Llano a 70 hasta `borde` y luego sube 1 cada bloque hacia (dx, dz). */
	private static IntBinaryOperator ramp(int dx, int dz, int edge) {
		return (x, z) -> 70 + Math.max(0, x * dx + z * dz - edge);
	}

	@Test
	void worldMovesMouthToItsSiteAndRotatesLikeTemplate() {
		for (Rotation r : Rotation.values()) {
			assertArrayEquals(new int[] {100, -40}, Hillside.world(SHAPE, r, 100, -40, 14, 8), r.toString());
			BlockPos expected = new BlockPos(0, 0, 5).rotate(r);       // 5 bloques hacia el fondo de la plantilla
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
			// detrás de la boca, el monte; delante, el patio a la altura de la boca
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
		// el centro y los lados no ven subida de 5 en ningún sentido: se acaba con cinco columnas
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
		// sube 1 de cada 3 bloques: detrás de la boca no llega a SUBIDA_MIN de media
		assertNull(Hillside.search(terrain((x, z) -> 70 + Math.max(0, z) / 3), 0, 0, SHAPE, MIN_Y, false));
		// el patio mismo en cuesta: 13 bloques de fondo con pendiente 1 = desnivel > DESNIVEL
		assertNull(Hillside.search(terrain((x, z) -> 70 + z), 0, 0, SHAPE, MIN_Y, false));
	}

	@Test
	void shellCannotStickOut() {
		// monte detrás de la boca, pero un barranco sobre la galería (a más de 20 bloques)
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
		// llano entre z = -8 y z = 8; al sur sube 1 por bloque y al norte 2: gana la boca que mira al sur (monte al norte)
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
