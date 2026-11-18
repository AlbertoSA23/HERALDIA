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
 * «bioma_vecinos» de heraldia:rejilla: con la búsqueda de bioma por defecto (6 de 9 puntos de la malla en el bioma) un
 * bioma en franja estrecha (las playas) casi nunca da candidata; pidiendo menos vecinos, sí, y siempre dentro del bioma.
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
	 * Franja de 3 chunks de ancho cada 40 (un punto y sus vecinos a 4 chunks nunca caen a la vez en ella), centrada en
	 * una columna de la malla (con spacing 40 y separation 8, x = 40 g + 4 + 8 a).
	 */
	private static boolean band(int chunkX) {
		int m = Math.floorMod(chunkX, 40);
		return m >= 11 && m <= 13;
	}

	private static GridPlacement grid(String extra) {
		String json = "{\"grupo\": \"prueba\", \"spacing\": 40, \"separation\": 8, \"salt\": 1, \"bioma\": \"minecraft:is_beach\"" + extra + "}";
		return GridPlacement.CODEC.codec().parse(JsonOps.INSTANCE, JsonParser.parseString(json)).getOrThrow();
	}

	/** Casillas con candidata en el bioma (y comprueba que /locate no ve las que no la tienen). */
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
