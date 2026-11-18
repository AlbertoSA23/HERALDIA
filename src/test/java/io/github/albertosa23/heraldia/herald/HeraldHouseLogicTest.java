package io.github.albertosa23.heraldia.herald;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import io.github.albertosa23.heraldia.arena.Site;
import java.util.Optional;
import org.junit.jupiter.api.Test;

/**
 * The Herald's House pure logic: the blueprint in the .jar, the protected area (footprint and a ring of at least 50
 * blocks), who may change what, the stall rent (lazy, with warning and grace) and the site choice near spawn.
 */
class HeraldHouseLogicTest {
	private static final HousePlan PLAN = HousePlan.fromJar();
	private static final Grounds G = new Grounds(1000, 60, -2000, PLAN);

	@Test
	void blueprintFromTheJar() {
		assertEquals(96, PLAN.size()[0]);
		assertEquals(96, PLAN.size()[2]);
		assertEquals(8, PLAN.stalls().size());
		assertEquals(12, PLAN.returns().size());
		assertEquals(4, PLAN.gates().size());
		assertNotNull(PLAN.stall(1));
		assertEquals("llanuras_castellana", PLAN.style());
	}

	@Test
	void protectedAreaIsTheFootprintAndFiftyBlocks() {
		assertTrue(Grounds.RING >= 50);
		assertTrue(G.inArea(1000 - 50, -2000 - 50));
		assertFalse(G.inArea(1000 - 51, -2000));
		assertTrue(G.inArea(1000 + 95 + 50, -2000 + 95 + 50));
		assertFalse(G.inArea(1000 + 95 + 51, -2000));
		int side = PLAN.size()[0] + 2 * Grounds.RING;
		assertEquals(196, side, "about 196 x 196 in all");
		// every height: no tunnelling under it, no towering over it
		assertTrue(G.isProtected(1000 - 20, -60, -2000, false, 0));
		assertTrue(G.isProtected(1000 - 20, 300, -2000, false, 0));
	}

	@Test
	void onlyOperatorsAndTenantsInTheirStall() {
		HousePlan.Stall s = PLAN.stall(3);
		int[] in = G.world(s.min());
		assertEquals(3, G.stallAt(in[0], in[1], in[2]));
		assertTrue(G.isProtected(in[0], in[1], in[2], false, 0), "a player without a stall");
		assertTrue(G.isProtected(in[0], in[1], in[2], false, 4), "the tenant of another stall");
		assertFalse(G.isProtected(in[0], in[1], in[2], false, 3), "its tenant");
		assertFalse(G.isProtected(in[0], in[1], in[2], true, 0), "an operator");
		int[] c = G.world(PLAN.bell());
		assertTrue(G.isProtected(c[0], c[1], c[2], false, 3), "the tenant outside their stall");
		assertFalse(G.isProtected(5000, 70, 5000, false, 0), "outside the area");
	}

	@Test
	void portalSignsAndBarrels() {
		int[] a = G.world(PLAN.portal()[0]);
		assertTrue(G.inPortal(a[0], a[1], a[2]));
		assertTrue(G.inPortal(a[0] + 1, a[1] + 1, a[2]), "inside the frame, where the fire would go");
		assertFalse(G.inPortal(a[0] - 1, a[1], a[2]));
		int[] sign = G.world(PLAN.stall(5).sign());
		assertEquals(5, G.signAt(sign[0], sign[1], sign[2]));
		int[] b = G.world(PLAN.returns().get(7));
		assertEquals(7, G.barrelAt(b[0], b[1], b[2]));
		assertEquals(-1, G.barrelAt(b[0], b[1] + 5, b[2]));
	}

	@Test
	void usableBlocks() {
		for (String ok : new String[] {"crimson_door", "spruce_trapdoor", "crimson_fence_gate", "stone_button", "red_bed", "bell",
				"crafting_table", "cartography_table"}) {
			assertTrue(Grounds.usable(ok), ok);
		}
		for (String no : new String[] {"iron_door", "iron_trapdoor", "chest", "barrel", "lectern", "crimson_sign", "anvil",
				"composter", "flower_pot", "obsidian", "furnace", "cauldron"}) {
			assertFalse(Grounds.usable(no), no);
		}
	}

	@Test
	void centeredOnTheSpawn() {
		Grounds g = Grounds.centered(10, -20, 70, PLAN);
		assertEquals(10, g.centerX());
		assertEquals(-20, g.centerZ());
		assertEquals(70, g.groundY());
		assertTrue(g.areaOverlaps(g.maxX() + 50, g.maxZ() + 50, g.maxX() + 60, g.maxZ() + 60));
		assertFalse(g.areaOverlaps(g.maxX() + 51, g.oz(), g.maxX() + 60, g.maxZ()));
	}

	// --- rent ---

	private static final Rent.Terms T = new Rent.Terms(16, 4, 7, 3);
	private static final long D = Rent.DAY;

	@Test
	void rentStatesAreComputedNotCounted() {
		long until = 10 * D;
		assertEquals(Rent.Status.PAID, Rent.status(0, until, T));
		assertEquals(Rent.Status.PAID, Rent.status(9 * D - 1, until, T));
		assertEquals(Rent.Status.DUE_SOON, Rent.status(9 * D, until, T), "a day before: warned");
		assertEquals(Rent.Status.GRACE, Rent.status(10 * D, until, T));
		assertEquals(Rent.Status.GRACE, Rent.status(13 * D - 1, until, T));
		assertEquals(Rent.Status.EXPIRED, Rent.status(13 * D, until, T), "after the grace: lost");
		assertEquals(Rent.Status.PAID, Rent.status(1000 * D, until, new Rent.Terms(16, 0, 7, 3)), "no rent: never expires");
	}

	@Test
	void claimingAndPaying() {
		assertEquals(20, Rent.claimCost(T), "entry fee and the first period");
		long until = Rent.claimUntil(5 * D, T);
		assertEquals(12 * D, until);
		assertEquals(3, Rent.payable(5 * D, until, T), "up to four periods from now");
		assertEquals(12 * D + 3 * 7 * D, Rent.pay(until, 3, T));
		assertEquals(0, Rent.payable(5 * D, Rent.pay(until, 3, T), T));
		// in the grace, paying settles the arrears: the new period starts where the old one ended
		long late = 13 * D;
		assertEquals(Rent.Status.GRACE, Rent.status(late, until, T));
		assertEquals(until + 7 * D, Rent.pay(until, 1, T));
		assertEquals(0, Rent.payable(16 * D, until, T), "expired: nothing to pay, the stall is lost");
		assertTrue(Rent.affordable(20, 20));
		assertFalse(Rent.affordable(19, 20));
		assertEquals(3, Rent.daysLeft(9 * D + 1, 12 * D));
		assertEquals(0, Rent.daysLeft(12 * D, 12 * D));
	}

	// --- site ---

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

	private static Optional<Siting.Choice> choose(Site.Heights h, Siting.Forbidden f) {
		return Siting.choose(0, 0, 96, PLAN.ground(), PLAN.size()[1] - PLAN.ground(), -64, 320, h, f);
	}

	@Test
	void flatSpawnIsTheSpawn() {
		Siting.Choice c = choose(new Terrain((x, z) -> 70, (x, z) -> false), (a, b, c2, d) -> false).orElseThrow();
		assertEquals(0, c.x());
		assertEquals(0, c.z());
		assertEquals(70, c.ground());
	}

	@Test
	void avoidsWaterAndTheArena() {
		// a lake east of spawn: the house moves west
		Siting.Choice c = choose(new Terrain((x, z) -> 70, (x, z) -> x > 30), (a, b, c2, d) -> false).orElseThrow();
		assertTrue(c.x() < 0, "x " + c.x());
		assertEquals(0, c.water());
		// all of it water: still a site (the house brings its foundation)
		assertTrue(choose(new Terrain((x, z) -> 50, (x, z) -> true), (a, b, c2, d) -> false).isPresent());
		// an arena everywhere: none
		assertTrue(choose(new Terrain((x, z) -> 70, (x, z) -> false), (a, b, c2, d) -> true).isEmpty());
		// never further than RADIUS, so the ring stays clear of the arena's search (200-300 blocks)
		assertTrue(Siting.RADIUS + 48 + Grounds.RING < Site.RADIUS_MIN - 57 / 2);
	}

	@Test
	void prefersLessDrop() {
		Siting.Choice c = choose(new Terrain((x, z) -> x > 0 ? 70 + x / 2 : 70, (x, z) -> false), (a, b, c2, d) -> false).orElseThrow();
		assertTrue(c.x() < 0, "the flat side");
	}

	@Test
	void blendingIsASlope() {
		assertEquals(70, Building.blend(70, 70, 3));
		assertEquals(70, Building.blend(70, 79, 0));
		assertEquals(79, Building.blend(70, 79, Siting.MARGIN + 1));
		int prev = 70;
		for (int k = 1; k <= Siting.MARGIN; k++) {
			int y = Building.blend(70, 88, k);
			assertTrue(y >= prev && y - prev <= 2, "step " + k);
			prev = y;
		}
	}
}
