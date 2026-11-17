package io.github.albertosa23.heraldia.config;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonParser;
import com.mojang.serialization.JsonOps;
import java.util.concurrent.atomic.AtomicLong;
import net.minecraft.SharedConstants;
import net.minecraft.core.QuartPos;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.level.ChunkPos;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/**
 * La búsqueda de la candidata en su bioma de heraldia:rejilla (T36: cada punto de la retícula se mira una vez por
 * búsqueda) elige exactamente la misma candidata que la de la 0.1.0 (copiada aquí, {@link #antigua}), con biomas en
 * manchas al azar, varias semillas, ventanas y vecinos mínimos, y mira menos puntos.
 */
class BusquedaBiomaTest {
	private static final int STEP = 8, HALF = 4;

	@BeforeAll
	static void bootstrap() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	@AfterEach
	void restore() {
		GridPlacement.testContext(0, null);
	}

	/** Manchas de bioma: celdas de `tam` chunks dentro o fuera según un hash de la semilla. */
	private static boolean mancha(long seed, int chunkX, int chunkZ, int tam, int pct) {
		long h = UniqueSeparation.mix(seed ^ ChunkPos.pack(Math.floorDiv(chunkX, tam), Math.floorDiv(chunkZ, tam)) * 0x9E3779B97F4A7C15L);
		return Math.floorMod(h, 100) < pct;
	}

	/** La búsqueda de la 0.1.0, tal cual: cada vecino se mira cada vez. */
	private static long antigua(GridPlacement g, long seed, int salt, int minScore, int x0, int z0, java.util.function.BiPredicate<Integer, Integer> in) {
		int win = g.spacing() - g.separation(), n = Math.max(1, win / STEP), first = win >= STEP ? HALF : win / 2;
		long best = Long.MIN_VALUE, bestKey = Long.MIN_VALUE;
		for (int a = 0; a < n; a++) {
			for (int b = 0; b < n; b++) {
				int cx = x0 + first + a * STEP, cz = z0 + first + b * STEP;
				if (!in.test(cx, cz)) {
					continue;
				}
				int score = 1;
				for (int dx = -HALF; dx <= HALF; dx += HALF) {
					for (int dz = -HALF; dz <= HALF; dz += HALF) {
						if ((dx != 0 || dz != 0) && in.test(cx + dx, cz + dz)) {
							score++;
						}
					}
				}
				if (score < minScore) {
					continue;
				}
				long key = (long) score << 56 | (UniqueSeparation.mix(seed ^ ChunkPos.pack(cx, cz) ^ salt) >>> 8);
				if (best == Long.MIN_VALUE || key > bestKey) {
					best = (long) cx << 32 | (cz & 0xFFFFFFFFL);
					bestKey = key;
				}
			}
		}
		return best;
	}

	@Test
	void mismaCandidataQueLaBusquedaAntiguaYMenosMuestras() {
		int[][] rejillas = {{40, 8, 6}, {48, 12, 6}, {94, 62, 6}, {250, 190, 4}, {30, 26, 2}, {120, 30, 9}, {64, 0, 6}};
		int casillas = 0, conCandidata = 0;
		long antes = 0;
		AtomicLong ahora = new AtomicLong();
		for (long seed = 1; seed <= 5; seed++) {
			for (int[] r : rejillas) {
				for (int tam : new int[] {3, 7, 20}) {
					for (int pct : new int[] {30, 70}) {
						final long sd = seed;
						int salt = (int) (seed * 7919 + r[0]);
						GridPlacement g = GridPlacement.CODEC.codec().parse(JsonOps.INSTANCE, JsonParser.parseString("{\"grupo\": \"prueba\", \"spacing\": "
								+ r[0] + ", \"separation\": " + r[1] + ", \"salt\": " + salt + ", \"bioma\": \"minecraft:is_forest\", \"bioma_vecinos\": " + r[2]
								+ "}")).getOrThrow();
						GridPlacement.testContext(seed, (tag, qx, qy, qz) -> {
							ahora.incrementAndGet();
							return mancha(sd, QuartPos.toSection(qx), QuartPos.toSection(qz), tam, pct);
						});
						for (int gx = -3; gx < 3; gx++) {
							for (int gz = -3; gz < 3; gz++) {
								int x0 = gx * g.spacing() + g.offsetX(), z0 = gz * g.spacing() + g.offsetZ();
								long[] n = {0};
								long esperado = antigua(g, seed, salt, r[2], x0, z0, (x, z) -> {
									n[0]++;
									return mancha(sd, x, z, tam, pct);
								});
								antes += n[0];
								ChunkPos c = g.getPotentialStructureChunk(seed, x0, z0);
								if (esperado != Long.MIN_VALUE) {
									assertEquals(new ChunkPos((int) (esperado >> 32), (int) esperado), c, "rejilla " + r[0] + "/" + r[1] + ", casilla " + gx + "," + gz);
									conCandidata++;
								} else {
									assertTrue(!g.applyAdditionalChunkRestrictions(c.x(), c.z(), seed), "sin sitio en el bioma: /locate no debe verla");
								}
								casillas++;
							}
						}
					}
				}
			}
		}
		assertTrue(conCandidata > casillas / 4 && conCandidata < casillas, "con candidata " + conCandidata + " de " + casillas);
		assertTrue(ahora.get() < antes, "muestras de bioma: " + antes + " antes, " + ahora.get() + " ahora");
	}
}
