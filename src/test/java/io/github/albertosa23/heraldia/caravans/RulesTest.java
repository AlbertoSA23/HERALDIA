package io.github.albertosa23.heraldia.caravans;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import io.github.albertosa23.heraldia.roads.RoadLayout;
import io.github.albertosa23.heraldia.quests.Data;
import io.github.albertosa23.heraldia.quests.Reputation;
import java.util.HashSet;
import java.util.Set;
import java.util.UUID;
import org.junit.jupiter.api.Test;

/** Cuándo sale una caravana, cómo es, qué paga, la reputación con su aldea de destino y qué entidades sobran. */
class RulesTest {
	static final long WAIT = Rules.WAIT_TICKS;

	@Test
	void spawnDecision() {
		// activada, sin ninguna en camino, pasada la espera y con el sorteo a favor
		assertTrue(Rules.outcome(true, 0, 1, WAIT, 0, 10, 0.05));
		assertFalse(Rules.outcome(true, 0, 1, WAIT, 0, 10, 0.10), "10 %: sale con azar < 0,10");
		assertFalse(Rules.outcome(false, 0, 1, WAIT, 0, 100, 0), "desactivadas: nunca");
		assertFalse(Rules.outcome(true, 1, 1, WAIT, 0, 100, 0), "límite de activas");
		assertTrue(Rules.outcome(true, 1, 2, WAIT, 0, 100, 0), "con 2 de máximo, sale la segunda");
		assertFalse(Rules.outcome(true, 0, 1, WAIT - 1, 0, 100, 0), "la espera tras la anterior");
		assertFalse(Rules.outcome(true, 0, 1, 1_000_000, 0, 0, 0), "frecuencia 0: solo con el comando");
		assertTrue(Rules.outcome(true, 0, 1, 1_000_000, 0, 100, 0.999), "frecuencia 100: siempre");
		// al arrancar no hay espera (la última terminó «hace» ESPERA ticks)
		assertTrue(Rules.outcome(true, 0, 1, 0, -WAIT, 100, 0));
	}

	@Test
	void averageFrequency() {
		java.util.Random r = new java.util.Random(1);
		int n = 0;
		for (int i = 0; i < 100_000; i++) {
			n += Rules.outcome(true, 0, 1, WAIT, 0, 10, r.nextDouble()) ? 1 : 0;
		}
		assertEquals(10_000, n, 400, "10 % de los sorteos");
	}

	@Test
	void ambushAndComposition() {
		assertTrue(Rules.ambush(35, 0.34));
		assertFalse(Rules.ambush(35, 0.35));
		assertFalse(Rules.ambush(0, 0), "sin asaltos");
		assertTrue(Rules.ambush(100, 0.999));
		assertEquals(1, Rules.llamas(0));
		assertEquals(2, Rules.llamas(0.5));
		assertEquals(3, Rules.llamas(0.999));
		assertTrue(Rules.guard(0.1));
		assertFalse(Rules.guard(0.3));
		assertEquals(2, Rules.bandits(0));
		assertEquals(2, Rules.bandits(1));
		assertEquals(3, Rules.bandits(2));
		assertEquals(4, Rules.bandits(10), "como mucho 4");
		assertFalse(Rules.withBoss(2));
		assertTrue(Rules.withBoss(3));
	}

	@Test
	void reward() {
		Rules.Reward without = Rules.reward(9, false, 0.5);
		assertEquals(4, without.emeralds());
		assertEquals(5, without.reputation());
		assertFalse(without.withItem());
		assertNull(without.item());
		assertFalse(without.advancement(), "sin asalto no hay logro");
		Rules.Reward with = Rules.reward(9, true, 0.0);
		assertEquals(8, with.emeralds());
		assertEquals(15, with.reputation());
		assertTrue(with.withItem());
		assertEquals("minecraft:name_tag", with.item());
		assertEquals(1, with.amount());
		assertTrue(with.advancement());
		for (double a : new double[]{0, 0.3, 0.6, 0.999}) {
			Rules.Reward r = Rules.reward(5, true, a);
			assertTrue(r.item().startsWith("minecraft:") && r.amount() >= 1);
		}
		// modesto: nada de netherita, diamantes ni élitros (como el botín de una mediana)
		for (Object[] o : Rules.ITEMS) {
			String id = (String) o[0];
			assertFalse(id.contains("netherite") || id.contains("diamond") || id.contains("elytra") || id.contains("totem"), id);
		}
	}

	@Test
	void reputationWithDestinationVillage() {
		// el trazado da la plaza de la aldea (chunk del inicio * 16 + 8): la reputación es la de ese chunk
		long village = RoadLayout.pack(-37 * 16 + 8, 12 * 16 + 8);
		assertArrayEquals(new int[]{-37, 12}, Rules.chunk(village));
		String key = Reputation.key(-37, 12);
		// lo que suma Encargos.sumarReputacion: con una caravana defendida y dos acompañadas, de desconocido a conocido
		Data d = Data.EMPTY.addReputation(key, Rules.reward(9, true, 0).reputation());
		assertEquals(15, d.reputation(key));
		assertEquals(Reputation.Tier.UNKNOWN, d.tier(key));
		d = d.addReputation(key, Rules.reward(9, false, 0).reputation());
		assertEquals(Reputation.Tier.KNOWN, d.tier(key));
		assertEquals(0, d.reputation(Reputation.key(-36, 12)), "solo con la aldea de destino");
	}

	@Test
	void leftoverEntitiesOnRestart() {
		UUID mine = UUID.randomUUID(), old = UUID.randomUUID();
		Set<UUID> active = new HashSet<>(Set.of(mine));
		assertFalse(Rules.orphan(Set.of(Rules.TAG, Rules.MERCHANT), mine, active), "de una caravana en camino");
		assertTrue(Rules.orphan(Set.of(Rules.TAG, Rules.LLAMA), old, active), "de una que ya no está");
		// tras reiniciar no hay ninguna activa: todas sobran
		for (String paper : new String[]{Rules.MERCHANT, Rules.LLAMA, Rules.GUARD, Rules.BANDIT}) {
			assertTrue(Rules.orphan(Set.of(Rules.TAG, paper), mine, Set.of()), paper);
		}
		assertFalse(Rules.orphan(Set.of(), old, Set.of()), "una entidad cualquiera no se toca");
		assertFalse(Rules.orphan(Set.of("heraldia_anclado"), old, Set.of()));
	}

	@Test
	void noFarmableLoot() {
		assertTrue(Caravans.noLoot(Set.of(Rules.TAG, Rules.MERCHANT)));
		assertTrue(Caravans.noLoot(Set.of(Rules.TAG, Rules.LLAMA)));
		assertTrue(Caravans.noLoot(Set.of(Rules.TAG, Rules.GUARD)));
		assertFalse(Caravans.noLoot(Set.of(Rules.TAG, Rules.BANDIT)), "los bandidos, lo suyo");
		assertFalse(Caravans.noLoot(Set.of()));
	}
}
