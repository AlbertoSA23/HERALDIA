package io.github.albertosa23.heraldia.quests;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import net.minecraft.SharedConstants;
import net.minecraft.server.Bootstrap;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/** Reputation levels, rises, drops and their effect on prices. */
class ReputationTest {
	@BeforeAll
	static void game() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	@Test
	void levels() {
		assertEquals(Reputation.Tier.UNKNOWN, Reputation.tier(Reputation.MIN));
		assertEquals(Reputation.Tier.UNKNOWN, Reputation.tier(0));
		assertEquals(Reputation.Tier.UNKNOWN, Reputation.tier(Reputation.KNOWN - 1));
		assertEquals(Reputation.Tier.KNOWN, Reputation.tier(Reputation.KNOWN));
		assertEquals(Reputation.Tier.KNOWN, Reputation.tier(Reputation.FRIEND - 1));
		assertEquals(Reputation.Tier.FRIEND, Reputation.tier(Reputation.FRIEND));
		assertEquals(Reputation.Tier.FRIEND, Reputation.tier(Reputation.HERO - 1));
		assertEquals(Reputation.Tier.HERO, Reputation.tier(Reputation.HERO));
		assertEquals(Reputation.Tier.HERO, Reputation.tier(Reputation.MAX));
		assertTrue(Reputation.KNOWN < Reputation.FRIEND && Reputation.FRIEND < Reputation.HERO && Reputation.HERO <= Reputation.MAX);
	}

	@Test
	void riseAndFallWithoutLeavingRange() {
		assertEquals(25, Reputation.add(15, 10));
		assertEquals(Reputation.MAX, Reputation.add(Reputation.MAX - 1, 50));
		assertEquals(Reputation.MIN, Reputation.add(-90, -40));
		assertEquals(Reputation.MAX, Reputation.add(Reputation.MAX, Integer.MAX_VALUE));
		assertEquals(Reputation.MIN, Reputation.add(Reputation.MIN, Integer.MIN_VALUE));
		// two quests (bring and guardian) are enough to be known; a killed villager takes it away
		int r = Reputation.add(Reputation.add(0, Type.BRING.reputation), Type.GUARDIAN.reputation);
		assertEquals(Reputation.Tier.KNOWN, Reputation.tier(r));
		assertEquals(Reputation.Tier.UNKNOWN, Reputation.tier(Reputation.add(r, Reputation.attack(false, true))));
	}

	@Test
	void attacks() {
		assertEquals(Reputation.VILLAGER_HIT, Reputation.attack(false, false));
		assertEquals(Reputation.VILLAGER_DEATH, Reputation.attack(false, true));
		assertEquals(Reputation.GOLEM_HIT, Reputation.attack(true, false));
		assertEquals(Reputation.GOLEM_DEATH, Reputation.attack(true, true));
		assertTrue(Reputation.VILLAGER_DEATH < Reputation.VILLAGER_HIT && Reputation.VILLAGER_HIT < 0);
		assertTrue(Reputation.GOLEM_DEATH < Reputation.GOLEM_HIT && Reputation.GOLEM_HIT < 0);
	}

	@Test
	void discountAsVillageHero() {
		assertEquals(0, Reputation.discountFor(Reputation.Tier.UNKNOWN, 10, true, false));
		assertEquals(-1, Reputation.discountFor(Reputation.Tier.KNOWN, 10, true, false));
		assertEquals(-1, Reputation.discountFor(Reputation.Tier.KNOWN, 1, true, false), "al menos 1, como vanilla");
		assertEquals(-4, Reputation.discountFor(Reputation.Tier.FRIEND, 20, true, false));
		assertEquals(-19, Reputation.discountFor(Reputation.Tier.HERO, 64, true, false));
		assertEquals(Reputation.Tier.HERO.discount, 30, "como Héroe de la aldea I (0,3 + 0,0625 × 0)");
		assertEquals(0, Reputation.discountFor(Reputation.Tier.HERO, 64, false, false), "reputación desactivada");
		assertEquals(0, Reputation.discountFor(Reputation.Tier.HERO, 64, true, true), "no se suma a Héroe de la aldea");
		assertEquals(0, Reputation.discountFor(Reputation.Tier.FRIEND, 0, true, false));
	}

	/** The price a trade charges: {@code MerchantOffer.getCostA} (without demand), never below 1. */
	static int price(int base, int diff) {
		return Math.max(1, base + diff);
	}

	@Test
	void tradePrice() {
		assertEquals(9, price(10, Reputation.discountFor(Reputation.Tier.KNOWN, 10, true, false)));
		assertEquals(8, price(10, Reputation.discountFor(Reputation.Tier.FRIEND, 10, true, false)));
		assertEquals(7, price(10, Reputation.discountFor(Reputation.Tier.HERO, 10, true, false)));
		assertEquals(1, price(1, Reputation.discountFor(Reputation.Tier.HERO, 1, true, false)), "nunca por debajo de 1");
		assertEquals(10, price(10, Reputation.discountFor(Reputation.Tier.UNKNOWN, 10, true, false)));
	}

	@Test
	void villageKey() {
		assertEquals("12,-40", Reputation.key(12, -40));
		assertArrayEquals(new int[]{12, -40}, Reputation.chunk("12,-40"));
		assertNull(Reputation.chunk("x"));
		assertNull(Reputation.chunk(",3"));
		assertNull(Reputation.chunk("a,b"));
	}
}
