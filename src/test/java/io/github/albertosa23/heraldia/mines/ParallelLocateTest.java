package io.github.albertosa23.heraldia.mines;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonParser;
import com.mojang.serialization.JsonOps;
import io.github.albertosa23.heraldia.config.GridPlacement;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import net.minecraft.SharedConstants;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.level.ChunkPos;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/**
 * /locate de minas en paralelo ({@link ParallelLocate}): las casillas de cada anillo en el orden de vanilla
 * (ChunkGenerator.getNearestGeneratedStructure: i de −r a r por fuera, j por dentro, solo el borde) y la casilla de la
 * candidata igual a la del chunk desde el que se pide (así el hilo del servidor espera la tarea que toca).
 */
class ParallelLocateTest {
	@BeforeAll
	static void bootstrap() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	@Test
	void ringsInVanillaOrder() {
		assertEquals(1, ParallelLocate.ring(5, 7, 0, 48).size());
		for (int r = 1; r <= 6; r++) {
			List<int[]> a = ParallelLocate.ring(5, 7, r, 48);
			assertEquals(8 * r, a.size());
			int k = 0;
			for (int i = -r; i <= r; i++) {
				for (int j = -r; j <= r; j++) {
					if (i == -r || i == r || j == -r || j == r) {
						assertArrayEquals(new int[] {5 + 48 * i, 7 + 48 * j}, a.get(k++));
					}
				}
			}
		}
	}

	@Test
	void candidateFallsInItsRingCell() {
		GridPlacement g = GridPlacement.CODEC.codec().parse(JsonOps.INSTANCE, JsonParser.parseString(
				"{\"grupo\": \"prueba\", \"spacing\": 48, \"separation\": 12, \"salt\": 4242}")).getOrThrow();
		Set<Long> cells = new HashSet<>();
		for (int r = 0; r <= 5; r++) {
			for (int[] c : ParallelLocate.ring(-37, 91, r, g.spacing())) {
				ChunkPos pos = g.getPotentialStructureChunk(20261116L, c[0], c[1]);
				long expected = ParallelLocate.cell(c[0], c[1], g.offsetX(), g.offsetZ(), g.spacing());
				assertEquals(expected, ParallelLocate.cell(pos.x(), pos.z(), g.offsetX(), g.offsetZ(), g.spacing()), "anillo " + r);
				assertTrue(cells.add(expected), "cada casilla una vez");
			}
		}
	}
}
