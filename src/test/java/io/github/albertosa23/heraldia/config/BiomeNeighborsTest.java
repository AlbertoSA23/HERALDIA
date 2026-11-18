package io.github.albertosa23.heraldia.config;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonParser;
import com.mojang.serialization.JsonOps;
import java.util.function.IntPredicate;
import net.minecraft.SharedConstants;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.level.ChunkPos;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/**
 * "bioma_vecinos" of heraldia:rejilla: with the default biome search (6 of 9 lattice points in the biome) a
 * biome in a narrow strip (beaches) almost never gives a candidate; asking for fewer neighbors, it does, and always inside the biome.
 */
class BiomeNeighborsTest {
	private static final long SEED = 7L;
	private static final int CELLS = 24;

	@BeforeAll
	static void bootstrap() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	@AfterEach
	void restore() {
		GridPlacement.testContext(0, null);
	}

	/**
	 * Strip 3 chunks wide every 40 (a point and its neighbors 4 chunks away never fall in it at once), centered on
	 * a lattice column (with spacing 40 and separation 8, x = 40 g + 4 + 8 a).
	 */
	private static boolean band(int chunkX) {
		int m = Math.floorMod(chunkX, 40);
		return m >= 11 && m <= 13;
	}

	private static GridPlacement grid(String extra) {
		String json = "{\"grupo\": \"prueba\", \"spacing\": 40, \"separation\": 8, \"salt\": 1, \"bioma\": \"minecraft:is_beach\"" + extra + "}";
		return GridPlacement.CODEC.codec().parse(JsonOps.INSTANCE, JsonParser.parseString(json)).getOrThrow();
	}

	/** Cells with a candidate in the biome (and checks that /locate does not see the ones that have none). */
	private static int withCandidate(GridPlacement g, IntPredicate biome) {
		int n = 0;
		for (int gx = 0; gx < CELLS; gx++) {
			for (int gz = 0; gz < CELLS; gz++) {
				ChunkPos c = g.getPotentialStructureChunk(SEED, gx * g.spacing(), gz * g.spacing());
				if (g.applyAdditionalChunkRestrictions(c.x(), c.z(), SEED)) {
					assertTrue(biome.test(c.x()), "candidata fuera del bioma: " + c);
					n++;
				}
			}
		}
		return n;
	}

	@Test
	void narrowBandOnlyWithFewerNeighbors() {
		GridPlacement.testContext(SEED, (tag, qx, qy, qz) -> band(Math.floorDiv(qx, 4)));
		assertEquals(0, withCandidate(grid(""), BiomeNeighborsTest::band), "con 6 vecinos una franja de 3 chunks no debería valer");
		int narrow = withCandidate(grid(", \"bioma_vecinos\": 2"), BiomeNeighborsTest::band);
		assertEquals(CELLS * CELLS, narrow, "con 2 vecinos, toda casilla cruzada por la franja tiene candidata");
	}

	@Test
	void defaultSixAndOutOfRangeFails() {
		GridPlacement.testContext(SEED, (tag, qx, qy, qz) -> true);
		assertEquals(CELLS * CELLS, withCandidate(grid(", \"bioma_vecinos\": 9"), x -> true));
		assertTrue(GridPlacement.CODEC.codec().parse(JsonOps.INSTANCE, JsonParser.parseString(
				"{\"grupo\": \"prueba\", \"spacing\": 40, \"separation\": 8, \"salt\": 1, \"bioma_vecinos\": 0}")).isError());
	}
}
