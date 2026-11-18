package io.github.albertosa23.heraldia.mines;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import io.github.albertosa23.heraldia.common.Heights;
import io.github.albertosa23.heraldia.common.HeightCache;
import java.util.List;
import java.util.Random;
import net.minecraft.SharedConstants;
import net.minecraft.core.BlockPos;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.level.levelgen.Heightmap;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/**
 * Determinismo rápido de la búsqueda de ladera (el de verdad, con el terreno de 26.3, es MinasDeterminismoTest, en
 * testPesado): con terrenos sintéticos de montes, valles y agua, en muchas semillas y chunks, la búsqueda de ahora
 * ({@link Hillside}, comprobaciones reordenadas, sobre la caché compartida) da lo mismo que la de la 0.1.0
 * ({@link OldHillside}, con una caché por búsqueda), también forzada y con la caché llena que se vacía.
 */
class HillsideOrderTest {
	private static final List<Hillside.Shape> SHAPES = List.of(
			new Hillside.Shape(new BlockPos(14, 16, 8), 8, 0, 20, 7, List.of(new int[] {14, 30, -6}, new int[] {6, 37, -6}, new int[] {22, 37, -6})),
			new Hillside.Shape(new BlockPos(22, 18, 16), 11, 0, 33, 15, List.of(new int[] {22, 40, -6}, new int[] {10, 50, -8})),
			new Hillside.Shape(new BlockPos(30, 34, 22), 15, 0, 45, 21, List.of(new int[] {30, 60, -10}, new int[] {12, 70, -10}, new int[] {48, 70, -4})));

	@BeforeAll
	static void bootstrap() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	/** Montes y valles: suma de ondas con amplitudes y fases de la semilla; agua (a 63) bajo el nivel del mar. */
	private static HeightCache.Source terrain(long seed) {
		Random r = new Random(seed);
		int n = 5;
		double[] ax = new double[n], az = new double[n], fx = new double[n], fz = new double[n], amp = new double[n];
		for (int i = 0; i < n; i++) {
			ax[i] = r.nextDouble() * Math.PI * 2;
			az[i] = r.nextDouble() * Math.PI * 2;
			fx[i] = (r.nextDouble() - 0.5) / (8 + r.nextInt(60));
			fz[i] = (r.nextDouble() - 0.5) / (8 + r.nextInt(60));
			amp[i] = 4 + r.nextDouble() * 30;
		}
		double base = 55 + r.nextInt(30);
		return (x, z, type) -> {
			double h = base;
			for (int i = 0; i < n; i++) {
				h += amp[i] * Math.sin(ax[i] + x * fx[i] + z * fz[i]);
			}
			int depth = (int) Math.floor(h);
			return type == Heightmap.Types.OCEAN_FLOOR_WG ? depth : Math.max(depth, 63);
		};
	}

	@Test
	void sameHillsideAsOldSearch() {
		int compared = 0, found = 0;
		for (long seed = 0; seed < 60; seed++) {
			HeightCache.Source f = terrain(seed);
			HeightCache shared = new HeightCache(f, 63, seed % 3 == 0 ? 256 : HeightCache.CAPACITY);
			Random r = new Random(~seed);
			for (int i = 0; i < 40; i++) {
				int x = r.nextInt(20000) - 10000, z = r.nextInt(20000) - 10000;
				for (Hillside.Shape shape : SHAPES) {
					for (boolean forced : new boolean[] {false, true}) {
						Hillside.Site oldValue = OldHillside.search(MineEntranceStructure.terrain(new Heights(f, 63)), x, z, shape, -64, forced);
						Hillside.Site newValue = Hillside.search(MineEntranceStructure.terrain(shared), x, z, shape, -64, forced);
						final long s = seed;
						assertEquals(oldValue, newValue, () -> "semilla " + s + " en " + x + ", " + z);
						compared++;
						found += !forced && newValue != null ? 1 : 0;
					}
				}
			}
			assertTrue(shared.size() <= shared.capacity());
		}
		assertTrue(found >= 100, "laderas encontradas: " + found + " de " + compared);
	}
}
