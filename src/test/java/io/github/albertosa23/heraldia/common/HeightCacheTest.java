package io.github.albertosa23.heraldia.common;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.concurrent.atomic.AtomicInteger;
import net.minecraft.SharedConstants;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.level.levelgen.Heightmap;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/** Shared height cache ({@link HeightCache}): same values as {@link Heights}, bounded and without repeating columns. */
class HeightCacheTest {
	@BeforeAll
	static void bootstrap() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	/** Synthetic terrain: a floor rising diagonally; water (surface at 63) where the floor is below the sea. */
	private static int height(int x, int z, Heightmap.Types t) {
		int depth = 40 + Math.floorMod(x * 7 + z * 3, 50);
		return t == Heightmap.Types.OCEAN_FLOOR_WG ? depth : Math.max(depth, 63);
	}

	@Test
	void sameValuesAsHeights() {
		HeightCache c = new HeightCache(HeightCacheTest::height, 63, 1 << 12);
		Heights a = new Heights(HeightCacheTest::height, 63);
		for (int x = -40; x <= 40; x += 3) {
			for (int z = -40; z <= 40; z += 5) {
				assertEquals(a.floor(x, z), c.floor(x, z));
				assertEquals(a.water(x, z), c.water(x, z));
				assertEquals(a.surface(x, z), c.surface(x, z));
				assertEquals(a.floor(x, z), c.floor(x, z), "el fondo no cambia al pedir la superficie");
			}
		}
	}

	@Test
	void eachColumnEvaluatedOnceAndSurfaceOnlyOnRequest() {
		AtomicInteger depth = new AtomicInteger(), surface = new AtomicInteger();
		HeightCache c = new HeightCache((x, z, t) -> {
			(t == Heightmap.Types.OCEAN_FLOOR_WG ? depth : surface).incrementAndGet();
			return height(x, z, t);
		}, 63, 1 << 12);
		for (int once = 0; once < 3; once++) {
			for (int x = 0; x < 10; x++) {
				c.floor(x, 5);
			}
		}
		assertEquals(10, depth.get());
		assertEquals(0, surface.get());
		for (int once = 0; once < 3; once++) {
			c.surface(1, 5);
		}
		assertEquals(1, surface.get());
		assertEquals(10, depth.get());
	}

	@Test
	void boundedSize() {
		HeightCache c = new HeightCache(HeightCacheTest::height, 63, 1 << 10);
		assertEquals(1 << 10, c.capacity());
		for (int x = 0; x < 300; x++) {
			for (int z = 0; z < 300; z++) {
				c.floor(x, z);
			}
			assertTrue(c.size() <= c.capacity(), "columnas: " + c.size());
		}
		assertTrue(c.size() > c.capacity() / 2, "se llena casi entera: " + c.size());
		// after emptying again and again, it still gives the same
		Heights a = new Heights(HeightCacheTest::height, 63);
		for (int x = 0; x < 300; x += 7) {
			assertEquals(a.floor(x, 11), c.floor(x, 11));
			assertEquals(a.water(x, 11), c.water(x, 11));
		}
		assertTrue(c.size() <= c.capacity());
		assertTrue(HeightCache.CAPACITY <= 1 << 16, "la del juego cabe en unos MB");
	}

	@Test
	void negativeAndFarCoordinatesDoNotMix() {
		HeightCache c = new HeightCache(HeightCacheTest::height, 63, 1 << 12);
		int[][] points = {{-29_999_984, 29_999_984}, {29_999_984, -29_999_984}, {-1, -1}, {0, 0}, {-1, 0}, {0, -1}, {123_456, -654_321}};
		for (int[] p : points) {
			assertEquals(height(p[0], p[1], Heightmap.Types.OCEAN_FLOOR_WG), c.floor(p[0], p[1]));
		}
		for (int[] p : points) {
			assertEquals(height(p[0], p[1], Heightmap.Types.WORLD_SURFACE_WG), c.surface(p[0], p[1]));
		}
	}
}
