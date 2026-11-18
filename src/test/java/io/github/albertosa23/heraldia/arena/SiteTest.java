package io.github.albertosa23.heraldia.arena;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.Optional;
import org.junit.jupiter.api.Test;

/** Elección del sitio: a 200-300 bloques del spawn, en llano y sin agua. */
class SiteTest {
	private static final int SIDE = 57, LOW = 7, HIGH = 7, MIN_Y = -64, MAX_Y = 320;

	/** Terreno inventado: llano a 70, con lo que diga `alto` (altura) y `agua` (columnas con agua). */
	private record Terrain(java.util.function.IntBinaryOperator high, java.util.function.BiPredicate<Integer, Integer> water)
			implements Site.Heights {
		@Override
		public int surface(int x, int z) {
			return high.applyAsInt(x, z) + 1 + (water.test(x, z) ? 3 : 0);
		}

		@Override
		public int depth(int x, int z) {
			return high.applyAsInt(x, z) + 1;
		}
	}

	private static Optional<Site.Choice> choose(int sx, int sz, Site.Heights a) {
		return Site.choose(sx, sz, SIDE, LOW, HIGH, MIN_Y, MAX_Y, a);
	}

	@Test
	void flatBetweenTwoAndThreeHundred() {
		Site.Choice e = choose(40, -30, new Terrain((x, z) -> 70, (x, z) -> false)).orElseThrow();
		double d = Math.hypot(e.x() - 40, e.z() + 30);
		assertTrue(d >= 199.5 && d <= 300.5, "distancia " + d);
		assertEquals(Site.PREFERRED_RADIUS, e.distance(), 1, "en llano, a la distancia preferida");
		assertEquals(70, e.ground());
		assertEquals(0, e.drop());
	}

	@Test
	void avoidsSlopesAndWater() {
		// al este (x > 0) una ladera fuerte; al norte (z < 0), un lago; el llano, al oeste y al sur
		Terrain t = new Terrain((x, z) -> x > 0 ? 70 + x / 3 : 70, (x, z) -> z < -100);
		Site.Choice e = choose(0, 0, t).orElseThrow();
		assertTrue(e.x() + SIDE / 2 + Site.MARGIN <= 0 || e.drop() <= 2, "no en la ladera: " + e);
		assertTrue(e.z() - SIDE / 2 - Site.MARGIN >= -100, "no en el lago: " + e);
		assertTrue(e.drop() <= Site.MAX_DROP);
	}

	@Test
	void prefersSmallestDrop() {
		// ondulado con amplitud que crece hacia el sur: el mejor sitio, al norte
		Terrain t = new Terrain((x, z) -> 70 + (int) (Math.sin(x / 9.0) * Math.max(0, z + 320) / 60.0), (x, z) -> false);
		Site.Choice e = choose(0, 0, t).orElseThrow();
		assertTrue(e.z() < -150, "debería quedar al norte: " + e);
	}

	@Test
	void noSiteIfAllWaterOrMountain() {
		assertTrue(choose(0, 0, new Terrain((x, z) -> 70, (x, z) -> true)).isEmpty(), "todo agua");
		assertTrue(choose(0, 0, new Terrain((x, z) -> 70 + Math.abs(x + z), (x, z) -> false)).isEmpty(), "todo ladera");
	}

	@Test
	void fitInWorldHeight() {
		assertTrue(choose(0, 0, new Terrain((x, z) -> MAX_Y - 3, (x, z) -> false)).isEmpty(), "pegada al techo del mundo");
		assertTrue(choose(0, 0, new Terrain((x, z) -> MIN_Y + 2, (x, z) -> false)).isEmpty(), "pegada al fondo del mundo");
	}

	@Test
	void medianAsGround() {
		Site.Choice e = Site.evaluateAt(250, 0, 0, 0, SIDE, new Terrain((x, z) -> x > 250 ? 74 : 70, (x, z) -> false));
		assertEquals(4, e.drop());
		assertTrue(e.ground() == 70 || e.ground() == 74);
		assertEquals(250, e.distance());
	}

	@Test
	void avoidsAlreadyGeneratedStructures() {
		Site.Choice free = choose(0, 0, new Terrain((x, z) -> 70, (x, z) -> false)).orElseThrow();
		// la mejor posición sin estructuras pasa a estar ocupada (una aldea, una entrada de mina...): se elige otra
		int ocx = free.x() >> 4, ocz = free.z() >> 4;
		Site.Heights withVillage = new Terrain((x, z) -> 70, (x, z) -> false);
		Site.Heights occupied = new Site.Heights() {
			@Override
			public int surface(int x, int z) {
				return withVillage.surface(x, z);
			}

			@Override
			public int depth(int x, int z) {
				return withVillage.depth(x, z);
			}

			@Override
			public boolean occupied(int cx, int cz) {
				return Math.abs(cx - ocx) <= 1 && Math.abs(cz - ocz) <= 1;
			}
		};
		Site.Choice other = choose(0, 0, occupied).orElseThrow();
		assertTrue(Math.hypot(other.x() - free.x(), other.z() - free.z()) > 40, "no se aparta de la estructura: " + other);
		for (int cx = (other.x() - 33) >> 4; cx <= (other.x() + 33) >> 4; cx++) {
			for (int cz = (other.z() - 33) >> 4; cz <= (other.z() + 33) >> 4; cz++) {
				assertTrue(!occupied.occupied(cx, cz), "chunk ocupado en la huella: " + cx + ", " + cz);
			}
		}
		// todo ocupado: sin sitio
		Site.Heights everything = new Site.Heights() {
			@Override
			public int surface(int x, int z) {
				return 71;
			}

			@Override
			public int depth(int x, int z) {
				return 71;
			}

			@Override
			public boolean occupied(int cx, int cz) {
				return true;
			}
		};
		assertTrue(choose(0, 0, everything).isEmpty());
	}
}
