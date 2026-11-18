package io.github.albertosa23.heraldia.bosses;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.HashSet;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.Test;

/** Pure logic of the phases: thresholds, per-phase idempotency (tags), reinforcement limit, options and bar. */
class PhasesTest {
	private static final Set<String> GUARDIAN = Set.of(Phases.GUARDIAN, "heraldia_guardian.castillo", "heraldia_anclado");

	@Test
	void thresholds() {
		assertEquals(1, Phases.healthPhase(100, 100));
		assertEquals(1, Phases.healthPhase(66, 100));          // "drop below 66 %": at exactly 66 not yet
		assertEquals(2, Phases.healthPhase(65.9f, 100));
		assertEquals(2, Phases.healthPhase(33, 100));
		assertEquals(3, Phases.healthPhase(32.9f, 100));
		assertEquals(3, Phases.healthPhase(0.5f, 100));
		assertEquals(2, Phases.healthPhase(39, 60));           // 65 %
		assertEquals(1, Phases.healthPhase(10, 0));            // odd maximum health: no phases
		assertEquals(1, Phases.healthPhase(10, Float.NaN));
	}

	@Test
	void recognizesGuardianAndUnique() {
		assertTrue(Phases.isGuardian(GUARDIAN));
		assertFalse(Phases.isGuardian(Set.of()));
		assertFalse(Phases.isGuardian(Set.of("heraldia_guardian.castillo")));   // the unique's tag alone is not enough
		assertFalse(Phases.isGuardian(Set.of(Phases.REINFORCEMENT, "heraldia_anclado")));
		assertEquals("castillo", Phases.unique(GUARDIAN));
		assertNull(Phases.unique(Set.of(Phases.GUARDIAN)));                    // guardian from an old world without an id
		assertNull(Phases.unique(Set.of(Phases.GUARDIAN, Phases.UNIQUE)));
	}

	@Test
	void pendingInOrderAndOnce() {
		Set<String> tags = new HashSet<>(GUARDIAN);
		assertEquals(List.of(), Phases.pending(tags, 80, 100, true, true));
		assertEquals(List.of(2), Phases.pending(tags, 60, 100, true, true));
		tags.add(Phases.PHASE + 2);
		assertEquals(2, Phases.reached(tags));
		// already in phase 2: another hit in the same band does not repeat it (nor after healing above 66 %)
		assertEquals(List.of(), Phases.pending(tags, 50, 100, true, true));
		assertEquals(List.of(), Phases.pending(tags, 90, 100, true, true));
		assertEquals(List.of(3), Phases.pending(tags, 20, 100, true, true));
		tags.add(Phases.PHASE + 3);
		assertEquals(3, Phases.reached(tags));
		assertEquals(List.of(), Phases.pending(tags, 1, 100, true, true));
	}

	@Test
	void bigHitTriggersBothPhases() {
		assertEquals(List.of(2, 3), Phases.pending(GUARDIAN, 10, 100, true, false));
		assertEquals(List.of(3), Phases.pending(Set.of(Phases.GUARDIAN, Phases.PHASE + 2), 10, 100, false, true));
		// a guardian loaded with the phase 3 tag but not the phase 2 one (edited file): only phase 2 is missing
		assertEquals(List.of(2), Phases.pending(Set.of(Phases.GUARDIAN, Phases.PHASE + 3), 10, 100, true, true));
		assertEquals(3, Phases.reached(Set.of(Phases.PHASE + 3)));
	}

	@Test
	void disabledOptionsAndDead() {
		assertEquals(List.of(), Phases.pending(GUARDIAN, 10, 100, false, false));
		assertEquals(List.of(), Phases.pending(GUARDIAN, 0, 100, true, true));      // the hit that kills it
		assertEquals(List.of(), Phases.pending(GUARDIAN, -3, 100, true, true));
		assertEquals(List.of(2, 3), Phases.pending(GUARDIAN, 10, 100, false, true));  // only reinforcements
		assertEquals(List.of(2, 3), Phases.pending(GUARDIAN, 10, 100, true, false));  // only phases
	}

	@Test
	void aliveReinforcementsLimit() {
		assertEquals(3, Phases.howMany(3, 0));
		assertEquals(2, Phases.howMany(2, 0));
		assertEquals(1, Phases.howMany(3, 3));
		assertEquals(0, Phases.howMany(3, Phases.MAX_ALIVE));
		assertEquals(0, Phases.howMany(3, Phases.MAX_ALIVE + 5));
		assertEquals(0, Phases.howMany(0, 0));
		// two phases in a row with 3 reinforcements each: never more than MAX_ALIVE
		int alive = 0;
		for (int f = 0; f < 2; f++) {
			alive += Phases.howMany(3, alive);
		}
		assertEquals(Phases.MAX_ALIVE, alive);
	}

	@Test
	void messages() {
		assertEquals("heraldia.jefes.fase.2", Phases.key(2, true, 0));
		assertEquals("heraldia.jefes.fase.2.refuerzos", Phases.key(2, true, 3));
		assertEquals("heraldia.jefes.fase.3.refuerzos", Phases.key(3, true, 1));
		assertEquals("heraldia.jefes.refuerzos", Phases.key(3, false, 2));
		assertNull(Phases.key(2, false, 0));
	}

	@Test
	void bar() {
		assertEquals(Boolean.TRUE, Phases.sees(0));
		assertEquals(Boolean.TRUE, Phases.sees(32.0 * 32));
		assertNull(Phases.sees(40.0 * 40));                     // between the two radii: it stays as it was
		assertEquals(Boolean.FALSE, Phases.sees(48.1 * 48.1));
		assertEquals(1f, Phases.progress(100, 100));
		assertEquals(0.5f, Phases.progress(30, 60));
		assertEquals(0f, Phases.progress(5, 0));
		assertEquals(1f, Phases.progress(120, 100));
		assertEquals(net.minecraft.world.BossEvent.BossBarColor.YELLOW, Bars.color(1));
		assertEquals(net.minecraft.world.BossEvent.BossBarColor.RED, Bars.color(2));
		assertEquals(net.minecraft.world.BossEvent.BossBarColor.PURPLE, Bars.color(3));
	}

	@Test
	void reinforcementsConfigurableDefaultAsBefore() {
		for (int listed = 0; listed <= 5; listed++) {
			for (int alive = 0; alive <= 6; alive++) {
				assertEquals(Math.max(0, Math.min(listed, Phases.MAX_ALIVE - alive)), Phases.howMany(listed, alive, 100, 4));
				assertEquals(Phases.howMany(listed, alive), Phases.howMany(listed, alive, 100, Phases.MAX_ALIVE));
			}
		}
		assertEquals(5, Phases.howMany(3, 0, 150, 6), "hardcore: 3 x 1,5 = 4,5 -> 5");
		assertEquals(1, Phases.howMany(3, 5, 150, 6), "con el tope de vivos");
		assertEquals(2, Phases.howMany(3, 0, 50, 2), "casual: 1,5 -> 2, tope 2");
		assertEquals(0, Phases.howMany(3, 0, 0, 4));
		assertEquals(0, Phases.howMany(3, 9, 300, 4), "nunca negativo");
	}
}
