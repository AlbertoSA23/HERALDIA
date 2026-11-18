package io.github.albertosa23.heraldia.config;

import static org.junit.jupiter.api.Assertions.assertEquals;

import io.github.albertosa23.heraldia.common.SearchCache;
import java.util.Random;
import net.minecraft.SharedConstants;
import net.minecraft.server.Bootstrap;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/** A grid cell's biome candidate as a value of the world's search memory: it comes back exactly, or it is not stored. */
class GridCandidateMemoryTest {
	@BeforeAll
	static void bootstrap() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	private static long packed(int x, int z) {
		return ((long) x << 32) | (z & 0xFFFFFFFFL);
	}

	@Test
	void everyCandidateOfTheWindowComesBackExactly() {
		Random r = new Random(3);
		for (int i = 0; i < 100_000; i++) {
			int ox = r.nextInt(4_000_000) - 2_000_000, oz = r.nextInt(4_000_000) - 2_000_000;
			int dx = r.nextInt(1023), dz = r.nextInt(1023);
			long c = packed(ox + dx, oz + dz);
			int code = GridPlacement.encodeCandidate(c, ox, oz);
			assertEquals(true, code > 0 && code <= SearchCache.MAX_VALUE, "fits in an answer: " + code);
			assertEquals(c, GridPlacement.decodeCandidate(code, ox, oz));
		}
	}

	@Test
	void noSpotIsZeroAndWhatDoesNotFitIsNotStored() {
		assertEquals(0, GridPlacement.encodeCandidate(Long.MIN_VALUE, 10, 10));
		assertEquals(Long.MIN_VALUE, GridPlacement.decodeCandidate(0, 10, 10));
		assertEquals(-1, GridPlacement.encodeCandidate(packed(10 + 1023, 10), 10, 10), "a window wider than 1,022 chunks");
		assertEquals(-1, GridPlacement.encodeCandidate(packed(9, 10), 10, 10), "before the cell's origin");
		assertEquals(GridPlacement.INVALID, GridPlacement.decodeCandidate(1 + 1023 * 1024, 10, 10));
		assertEquals(GridPlacement.INVALID, GridPlacement.decodeCandidate(-5, 10, 10));
	}
}
