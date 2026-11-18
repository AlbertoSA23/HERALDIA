package io.github.albertosa23.heraldia.quests;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;
import org.junit.jupiter.api.Test;

/** When each objective type is met. */
class ObjectivesTest {
	static Quest of(Type t, String target, int amount, int x, int z) {
		return new Quest(1, 2, 0, 0, t, target, amount, x, z, 3, 20);
	}

	@Test
	void guardianOfRequestedUniqueAndNear() {
		Quest e = of(Type.GUARDIAN, "castillo", 0, 1000, -500);
		assertTrue(Objectives.guardian(e, "castillo", 1000, -500));
		assertTrue(Objectives.guardian(e, "castillo", 1000 + Objectives.GUARDIAN_RADIUS, -500));
		assertFalse(Objectives.guardian(e, "castillo", 1000 + Objectives.GUARDIAN_RADIUS + 1, -500), "otro castillo, lejos");
		assertFalse(Objectives.guardian(e, "catedral", 1000, -500), "otra única");
		assertFalse(Objectives.guardian(of(Type.EXPLORE, "castillo", 0, 1000, -500), "castillo", 1000, -500), "no es de guardián");
	}

	@Test
	void reachAPlaceOrAVillage() {
		Quest place = of(Type.EXPLORE, "heraldia:medianas/posada/llanuras", 0, 100, 100);
		assertTrue(Objectives.arrival(place, 100 + Objectives.PLACE_RADIUS, 100));
		assertFalse(Objectives.arrival(place, 100 + Objectives.PLACE_RADIUS, 101));
		Quest village = of(Type.JOURNEY, "Torre del Roble", 0, -800, 0);
		assertTrue(Objectives.arrival(village, -800 + Objectives.VILLAGE_RADIUS, 0));
		assertFalse(Objectives.arrival(village, -800 + Objectives.VILLAGE_RADIUS + 1, 0));
		assertFalse(Objectives.arrival(of(Type.GUARDIAN, "castillo", 0, 0, 0), 0, 0), "llegar no vence a nadie");
		assertFalse(Objectives.arrival(of(Type.BRING, "minecraft:bread", 16, 0, 0), 0, 0));
	}

	@Test
	void arenaWave() {
		Quest e = of(Type.ARENA, "", 5, 0, 0);
		assertFalse(Objectives.wave(e, 4));
		assertTrue(Objectives.wave(e, 5));
		assertTrue(Objectives.wave(e, 9));
		assertFalse(Objectives.wave(of(Type.BRING, "minecraft:bread", 5, 0, 0), 9));
	}

	@Test
	void deliverable() {
		Data.Active bring = new Data.Active(of(Type.BRING, "minecraft:bread", 16, 0, 0), false);
		assertFalse(Objectives.deliverable(bring, 15));
		assertTrue(Objectives.deliverable(bring, 16));
		assertTrue(Objectives.deliverable(bring, 64));
		Data.Active guardian = new Data.Active(of(Type.GUARDIAN, "castillo", 0, 0, 0), false);
		assertFalse(Objectives.deliverable(guardian, 99));
		assertTrue(Objectives.deliverable(new Data.Active(guardian.quest(), true), 0));
	}

	@Test
	void awaitsArrivalOnlyWithUnmetPlaces() {
		assertFalse(Objectives.awaitsArrival(List.of()));
		assertFalse(Objectives.awaitsArrival(List.of(new Data.Active(of(Type.BRING, "minecraft:bread", 1, 0, 0), false),
				new Data.Active(of(Type.GUARDIAN, "castillo", 0, 0, 0), false))));
		assertTrue(Objectives.awaitsArrival(List.of(new Data.Active(of(Type.JOURNEY, "X", 0, 0, 0), false))));
		assertFalse(Objectives.awaitsArrival(List.of(new Data.Active(of(Type.EXPLORE, "X", 0, 0, 0), true))));
	}

	@Test
	void bearingAndRoundedDistanceHint() {
		assertEquals("n", Objectives.bearing(0, 0, 0, -500));
		assertEquals("s", Objectives.bearing(0, 0, 0, 500));
		assertEquals("e", Objectives.bearing(0, 0, 500, 0));
		assertEquals("o", Objectives.bearing(0, 0, -500, 0));
		assertEquals("ne", Objectives.bearing(0, 0, 400, -400));
		assertEquals("so", Objectives.bearing(0, 0, -400, 400));
		assertEquals(100, Objectives.approximate(0, 0, 10, 0), "al menos 100");
		assertEquals(1200, Objectives.approximate(0, 0, 1234, 0));
		assertEquals(1300, Objectives.approximate(0, 0, 1251, 0));
		assertEquals(0, Objectives.approximate(0, 0, 777, 333) % 100);
	}
}
