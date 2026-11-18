package io.github.albertosa23.heraldia.config;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonParser;
import com.mojang.serialization.JsonOps;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashSet;
import java.util.Set;
import net.minecraft.SharedConstants;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.level.ChunkPos;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * GridPlacement (heraldia:rejilla) con semillas, sin servidor: lo que se lee de la configuración (rejilla, separación
 * interna, activada, máximo de casillas de las aldeas) y que la candidata de cada casilla cae en su ventana y es
 * determinista. Solo invariantes: los números concretos los mide UniqueSeparationTest.
 */
class GridPlacementTest {
	@TempDir
	Path dir;

	@BeforeAll
	static void bootstrap() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	@AfterEach
	void restore() {
		HeraldiaConfig.load(null);
	}

	private GridPlacement grid(String config, String placement) throws IOException {
		Path file = dir.resolve("heraldia.json");
		Files.writeString(file, config);
		HeraldiaConfig.load(file);
		return GridPlacement.CODEC.codec().parse(JsonOps.INSTANCE, JsonParser.parseString(placement)).getOrThrow();
	}

	private static final String CASTLE = "{\"grupo\": \"unicas/castillo\", \"spacing\": 250, \"separation\": 190, \"salt\": 123}";

	@Test
	void uniqueReadsItsSeparationAndMinDistance() throws IOException {
		GridPlacement g = grid("{\"unicas\": {\"castillo\": {\"separacion_bloques\": 5000}, \"distancia_minima\": {\"bloques\": 1200}}}", CASTLE);
		assertEquals(Math.round(5000 / 16.0F), g.spacing());
		assertEquals((1200 + 15) / 16, g.separation());
		assertTrue(g.offsetX() >= 0 && g.offsetX() < g.spacing() && g.offsetZ() >= 0 && g.offsetZ() < g.spacing());
	}

	@Test
	void candidateInItsWindowAndDeterministic() throws IOException {
		GridPlacement g = grid("{}", CASTLE);
		int s = g.spacing(), window = s - g.separation();
		for (long seed : new long[]{0, 1, -7, 123456789L}) {
			for (int gx = -3; gx <= 3; gx++) {
				for (int gz = -3; gz <= 3; gz++) {
					int x0 = gx * s + g.offsetX(), z0 = gz * s + g.offsetZ();
					ChunkPos c = g.getPotentialStructureChunk(seed, x0, z0);
					// cualquier chunk de la casilla da la misma candidata
					assertEquals(c, g.getPotentialStructureChunk(seed, x0 + s - 1, z0 + s / 2));
					assertTrue(c.x() - x0 >= 0 && c.x() - x0 < window && c.z() - z0 >= 0 && c.z() - z0 < window,
							"candidata " + c + " fuera de la ventana de la casilla " + gx + "," + gz);
					assertTrue(g.applyAdditionalChunkRestrictions(c.x(), c.z(), seed));
				}
			}
		}
	}

	@Test
	void differentSaltsShiftTheGrid() throws IOException {
		Set<Long> offsets = new HashSet<>();
		for (int salt = 1; salt <= 20; salt++) {
			GridPlacement g = grid("{}", "{\"grupo\": \"unicas/castillo\", \"spacing\": 250, \"separation\": 190, \"salt\": " + salt + "}");
			offsets.add(ChunkPos.pack(g.offsetX(), g.offsetZ()));
		}
		assertTrue(offsets.size() >= 18, "desfases repetidos: " + offsets.size() + " de 20");
	}

	@Test
	void disabledAllowsNone() throws IOException {
		GridPlacement g = grid("{\"unicas\": {\"castillo\": {\"activada\": false}}}", CASTLE);
		ChunkPos c = g.getPotentialStructureChunk(5, 0, 0);
		assertTrue(!g.applyAdditionalChunkRestrictions(c.x(), c.z(), 5));
	}

	@Test
	void villagesOnlyInNearestCells() throws IOException {
		GridPlacement g = grid("{\"aldeas\": {\"maximo\": 4, \"separacion_bloques\": 1504}}",
				"{\"grupo\": \"aldeas\", \"spacing\": 94, \"separation\": 62, \"salt\": 261112013}");
		assertEquals(94, g.spacing());
		assertEquals(62, g.separation());
		assertEquals(0, g.offsetX());
		int allowed = 0;
		for (int gx = -3; gx <= 3; gx++) {
			for (int gz = -3; gz <= 3; gz++) {
				ChunkPos c = g.getPotentialStructureChunk(9, gx * 94, gz * 94);
				boolean ok = g.applyAdditionalChunkRestrictions(c.x(), c.z(), 9);
				assertEquals(gx >= -1 && gx <= 0 && gz >= -1 && gz <= 0, ok, "casilla " + gx + "," + gz);
				allowed += ok ? 1 : 0;
			}
		}
		assertEquals(4, allowed);
	}
}
