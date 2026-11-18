package io.github.albertosa23.heraldia.arena;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.HashSet;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.Test;

/** Curva de oleadas, tandas con el límite de vivos, rotación de tipos y mini-jefe, experiencia y recompensas. */
class WavesTest {
	private static final int MOBS = 50, STATS = 10;

	@Test
	void defaultFiftyAndTen() {
		assertEquals(List.of(4, 6, 8, 10, 12, 14), List.of(Waves.mobs(1, MOBS), Waves.mobs(2, MOBS), Waves.mobs(3, MOBS),
				Waves.mobs(4, MOBS), Waves.mobs(5, MOBS), Waves.mobs(6, MOBS)));
		assertEquals(1.0, Waves.stats(1, STATS), 1e-9);
		assertEquals(1.1, Waves.stats(2, STATS), 1e-9);
		assertEquals(1.2, Waves.stats(3, STATS), 1e-9);
		assertEquals(0.0, Waves.modifier(1, STATS), 1e-9);
		assertEquals(0.5, Waves.modifier(6, STATS), 1e-9);
	}

	@Test
	void bothThingsAlwaysRise() {
		for (int mobs = 10; mobs <= 200; mobs += 5) {
			for (int stats = 1; stats <= 100; stats += 3) {
				int s = Waves.effectiveStats(mobs, stats);
				for (int n = 1; n < 60; n++) {
					assertTrue(Waves.mobs(n + 1, mobs) > Waves.mobs(n, mobs), "mobs " + mobs + " oleada " + n);
					assertTrue(Waves.stats(n + 1, s) > Waves.stats(n, s), "stats " + s + " oleada " + n);
				}
			}
		}
	}

	@Test
	void mobsGrowProportionallyMore() {
		for (int mobs = 10; mobs <= 200; mobs += 5) {
			for (int stats = 1; stats <= 100; stats += 3) {
				int s = Waves.effectiveStats(mobs, stats);
				assertTrue(s <= mobs, "stats efectivo " + s + " > mobs " + mobs);
				for (int n = 2; n < 60; n++) {
					double mobGrowth = (double) Waves.mobs(n, mobs) / Waves.mobs(1, mobs);
					assertTrue(mobGrowth + 1e-9 >= Waves.stats(n, s), "mobs " + mobs + " stats " + s + " oleada " + n);
				}
			}
		}
		// por defecto, estrictamente más
		for (int n = 2; n < 60; n++) {
			assertTrue((double) Waves.mobs(n, MOBS) / Waves.mobs(1, MOBS) > Waves.stats(n, STATS));
		}
	}

	@Test
	void effectiveStatsClampToMobs() {
		assertEquals(10, Waves.effectiveStats(50, 10));
		assertEquals(30, Waves.effectiveStats(30, 80));
		assertEquals(1, Waves.effectiveStats(50, 0));
	}

	@Test
	void wavesOutOfRange() {
		assertEquals(Waves.BASE, Waves.mobs(0, MOBS));
		assertEquals(Waves.BASE, Waves.mobs(-5, MOBS));
		assertEquals(Waves.mobs(Waves.MAX_WAVE, MOBS), Waves.mobs(Waves.MAX_WAVE + 50, MOBS));
	}

	@Test
	void batchesWithAliveLimit() {
		assertEquals(14, Waves.spawned(0, 14, 20));
		assertEquals(20, Waves.spawned(0, 30, 20));
		assertEquals(5, Waves.spawned(15, 30, 20));
		assertEquals(0, Waves.spawned(20, 30, 20));
		assertEquals(0, Waves.spawned(25, 30, 20));
		assertEquals(0, Waves.spawned(3, 0, 20));
	}

	@Test
	void typeRotation() {
		assertEquals(Waves.Batch.ZOMBIES, Waves.batch(1));
		assertEquals(Waves.Batch.SKELETONS_SPIDERS, Waves.batch(2));
		assertEquals(Waves.Batch.MIX, Waves.batch(3));
		assertEquals(Waves.Batch.HARD_MIX, Waves.batch(4));
		assertEquals(Waves.Batch.ZOMBIES, Waves.batch(5));
		assertTrue(Set.copyOf(Waves.types(1, MOBS)).stream().allMatch(t -> t.contains("zombie") || t.contains("husk")));
		assertEquals(Set.of("minecraft:skeleton", "minecraft:spider"), Set.copyOf(Waves.types(2, MOBS)));
		for (int n = 1; n < 30; n++) {
			List<String> t = Waves.types(n, MOBS);
			assertEquals(Waves.mobs(n, MOBS), t.size());
			assertTrue(Waves.batch(n).mobs().containsAll(t));
			// repartidos por turnos: con mobs de sobra salen todos los tipos de la tanda
			if (t.size() >= Waves.batch(n).mobs().size()) {
				assertEquals(new HashSet<>(Waves.batch(n).mobs()), new HashSet<>(t));
			}
		}
	}

	@Test
	void miniBossEveryFive() {
		for (int n = 1; n <= 40; n++) {
			assertEquals(n % 5 == 0, Waves.withBoss(n), "oleada " + n);
			assertEquals(Waves.mobs(n, MOBS) + (n % 5 == 0 ? 1 : 0), Waves.total(n, MOBS));
		}
		assertEquals(0, Waves.boss(5).index());
		assertEquals(1, Waves.boss(10).index());
		assertEquals(2, Waves.boss(15).index());
		assertEquals(3, Waves.boss(20).index());
		assertEquals(0, Waves.boss(25).index());
		assertFalse(Waves.withBoss(0));
	}

	@Test
	void experienceAtFifteenPercent() {
		// 15 % de 5 (un zombi) = 0,75: 1 con azar < 0,75, 0 si no
		assertEquals(1, Waves.experience(5, 15, 0.0));
		assertEquals(1, Waves.experience(5, 15, 0.74));
		assertEquals(0, Waves.experience(5, 15, 0.75));
		assertEquals(3, Waves.experience(20, 15, 0.5));
		assertEquals(0, Waves.experience(5, 0, 0.0));
		assertEquals(5, Waves.experience(5, 100, 0.99));
		assertEquals(0, Waves.experience(0, 15, 0.0));
		// de media, exactamente el porcentaje
		double sum = 0;
		int n = 10000;
		for (int i = 0; i < n; i++) {
			sum += Waves.experience(5, 15, (i + 0.5) / n);
		}
		assertEquals(0.75, sum / n, 1e-3);
	}

	@Test
	void rewardsAndAdvancements() {
		assertEquals(0, Waves.reward(4));
		assertEquals(1, Waves.reward(5));
		assertEquals(2, Waves.reward(10));
		assertEquals(3, Waves.reward(15));
		assertEquals(4, Waves.reward(20));
		assertEquals(4, Waves.reward(35));
		assertEquals(0, Waves.reward(21));
		assertTrue(Waves.advancement(5) && Waves.advancement(10) && Waves.advancement(20));
		assertFalse(Waves.advancement(15) || Waves.advancement(1) || Waves.advancement(25));
	}
}
