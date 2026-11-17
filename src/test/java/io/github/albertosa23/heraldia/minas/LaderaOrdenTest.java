package io.github.albertosa23.heraldia.minas;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import io.github.albertosa23.heraldia.comun.Alturas;
import io.github.albertosa23.heraldia.comun.CacheAlturas;
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
 * ({@link Ladera}, comprobaciones reordenadas, sobre la caché compartida) da lo mismo que la de la 0.1.0
 * ({@link LaderaAntigua}, con una caché por búsqueda), también forzada y con la caché llena que se vacía.
 */
class LaderaOrdenTest {
	private static final List<Ladera.Forma> FORMAS = List.of(
			new Ladera.Forma(new BlockPos(14, 16, 8), 8, 0, 20, 7, List.of(new int[] {14, 30, -6}, new int[] {6, 37, -6}, new int[] {22, 37, -6})),
			new Ladera.Forma(new BlockPos(22, 18, 16), 11, 0, 33, 15, List.of(new int[] {22, 40, -6}, new int[] {10, 50, -8})),
			new Ladera.Forma(new BlockPos(30, 34, 22), 15, 0, 45, 21, List.of(new int[] {30, 60, -10}, new int[] {12, 70, -10}, new int[] {48, 70, -4})));

	@BeforeAll
	static void bootstrap() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	/** Montes y valles: suma de ondas con amplitudes y fases de la semilla; agua (a 63) bajo el nivel del mar. */
	private static CacheAlturas.Fuente terreno(long seed) {
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
		return (x, z, tipo) -> {
			double h = base;
			for (int i = 0; i < n; i++) {
				h += amp[i] * Math.sin(ax[i] + x * fx[i] + z * fz[i]);
			}
			int fondo = (int) Math.floor(h);
			return tipo == Heightmap.Types.OCEAN_FLOOR_WG ? fondo : Math.max(fondo, 63);
		};
	}

	@Test
	void mismaLaderaQueLaBusquedaAntigua() {
		int comparadas = 0, encontradas = 0;
		for (long seed = 0; seed < 60; seed++) {
			CacheAlturas.Fuente f = terreno(seed);
			CacheAlturas compartida = new CacheAlturas(f, 63, seed % 3 == 0 ? 256 : CacheAlturas.CAPACIDAD);
			Random r = new Random(~seed);
			for (int i = 0; i < 40; i++) {
				int x = r.nextInt(20000) - 10000, z = r.nextInt(20000) - 10000;
				for (Ladera.Forma forma : FORMAS) {
					for (boolean forzada : new boolean[] {false, true}) {
						Ladera.Sitio viejo = LaderaAntigua.buscar(MinaEntradaStructure.terreno(new Alturas(f, 63)), x, z, forma, -64, forzada);
						Ladera.Sitio nuevo = Ladera.buscar(MinaEntradaStructure.terreno(compartida), x, z, forma, -64, forzada);
						final long s = seed;
						assertEquals(viejo, nuevo, () -> "semilla " + s + " en " + x + ", " + z);
						comparadas++;
						encontradas += !forzada && nuevo != null ? 1 : 0;
					}
				}
			}
			assertTrue(compartida.tamano() <= compartida.capacidad());
		}
		assertTrue(encontradas >= 100, "laderas encontradas: " + encontradas + " de " + comparadas);
	}
}
