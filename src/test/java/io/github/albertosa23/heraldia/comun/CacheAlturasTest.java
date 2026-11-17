package io.github.albertosa23.heraldia.comun;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.concurrent.atomic.AtomicInteger;
import net.minecraft.SharedConstants;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.level.levelgen.Heightmap;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/** Caché compartida de alturas ({@link CacheAlturas}): mismos valores que {@link Alturas}, acotada y sin repetir columnas. */
class CacheAlturasTest {
	@BeforeAll
	static void bootstrap() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	/** Terreno sintético: fondo que sube en diagonal; agua (superficie a 63) donde el fondo queda bajo el mar. */
	private static int altura(int x, int z, Heightmap.Types t) {
		int fondo = 40 + Math.floorMod(x * 7 + z * 3, 50);
		return t == Heightmap.Types.OCEAN_FLOOR_WG ? fondo : Math.max(fondo, 63);
	}

	@Test
	void mismosValoresQueAlturas() {
		CacheAlturas c = new CacheAlturas(CacheAlturasTest::altura, 63, 1 << 12);
		Alturas a = new Alturas(CacheAlturasTest::altura, 63);
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
	void cadaColumnaSeEvaluaUnaVezYLaSuperficieSoloSiSePide() {
		AtomicInteger fondo = new AtomicInteger(), superficie = new AtomicInteger();
		CacheAlturas c = new CacheAlturas((x, z, t) -> {
			(t == Heightmap.Types.OCEAN_FLOOR_WG ? fondo : superficie).incrementAndGet();
			return altura(x, z, t);
		}, 63, 1 << 12);
		for (int vez = 0; vez < 3; vez++) {
			for (int x = 0; x < 10; x++) {
				c.floor(x, 5);
			}
		}
		assertEquals(10, fondo.get());
		assertEquals(0, superficie.get());
		for (int vez = 0; vez < 3; vez++) {
			c.surface(1, 5);
		}
		assertEquals(1, superficie.get());
		assertEquals(10, fondo.get());
	}

	@Test
	void tamanoAcotado() {
		CacheAlturas c = new CacheAlturas(CacheAlturasTest::altura, 63, 1 << 10);
		assertEquals(1 << 10, c.capacidad());
		for (int x = 0; x < 300; x++) {
			for (int z = 0; z < 300; z++) {
				c.floor(x, z);
			}
			assertTrue(c.tamano() <= c.capacidad(), "columnas: " + c.tamano());
		}
		assertTrue(c.tamano() > c.capacidad() / 2, "se llena casi entera: " + c.tamano());
		// tras vaciarse una y otra vez, sigue dando lo mismo
		Alturas a = new Alturas(CacheAlturasTest::altura, 63);
		for (int x = 0; x < 300; x += 7) {
			assertEquals(a.floor(x, 11), c.floor(x, 11));
			assertEquals(a.water(x, 11), c.water(x, 11));
		}
		assertTrue(c.tamano() <= c.capacidad());
		assertTrue(CacheAlturas.CAPACIDAD <= 1 << 16, "la del juego cabe en unos MB");
	}

	@Test
	void coordenadasNegativasYLejanasNoSeMezclan() {
		CacheAlturas c = new CacheAlturas(CacheAlturasTest::altura, 63, 1 << 12);
		int[][] puntos = {{-29_999_984, 29_999_984}, {29_999_984, -29_999_984}, {-1, -1}, {0, 0}, {-1, 0}, {0, -1}, {123_456, -654_321}};
		for (int[] p : puntos) {
			assertEquals(altura(p[0], p[1], Heightmap.Types.OCEAN_FLOOR_WG), c.floor(p[0], p[1]));
		}
		for (int[] p : puntos) {
			assertEquals(altura(p[0], p[1], Heightmap.Types.WORLD_SURFACE_WG), c.surface(p[0], p[1]));
		}
	}
}
