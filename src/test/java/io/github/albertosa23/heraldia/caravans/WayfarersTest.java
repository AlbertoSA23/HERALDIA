package io.github.albertosa23.heraldia.caravans;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import io.github.albertosa23.heraldia.quests.Reputation;
import io.github.albertosa23.heraldia.roads.RoadLayout;
import java.util.ArrayList;
import java.util.EnumMap;
import java.util.EnumSet;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.junit.jupiter.api.Test;

/** The wayfarers' rules (pure logic): which one sets off where and when, what it brings, what it sells and what attacking it costs. */
class WayfarersTest {
	static final Set<Wayfarers.Kind> ALL = EnumSet.allOf(Wayfarers.Kind.class);

	@Test
	void everyKindCanSetOffWhereItFits() {
		Map<Wayfarers.Kind, Integer> seen = new EnumMap<>(Wayfarers.Kind.class);
		for (int i = 0; i < 1000; i++) {
			Wayfarers.Kind k = Wayfarers.choose(ALL, "llanuras", true, true, i / 1000.0);
			assertNotNull(k);
			seen.merge(k, 1, Integer::sum);
		}
		assertEquals(ALL, seen.keySet(), "by day in the plains, with a shrine nearby, all of them: " + seen);
		// weighted: the pilgrim (2) less than the shepherd (3)
		assertTrue(seen.get(Wayfarers.Kind.PILGRIM) < seen.get(Wayfarers.Kind.SHEPHERD), seen.toString());
	}

	@Test
	void thePilgrimNeedsAShrine() {
		for (int i = 0; i < 200; i++) {
			assertFalse(Wayfarers.choose(ALL, "bosque", true, false, i / 200.0) == Wayfarers.Kind.PILGRIM);
		}
		assertNull(Wayfarers.choose(EnumSet.of(Wayfarers.Kind.PILGRIM), "bosque", true, false, 0.5), "only the pilgrim and no shrine: nobody");
		assertEquals(Wayfarers.Kind.PILGRIM, Wayfarers.choose(EnumSet.of(Wayfarers.Kind.PILGRIM), "bosque", true, true, 0.99));
	}

	@Test
	void byNightOnlyThePatrol() {
		for (int i = 0; i < 200; i++) {
			assertEquals(Wayfarers.Kind.PATROL, Wayfarers.choose(ALL, "taiga", false, true, i / 200.0));
		}
		assertNull(Wayfarers.choose(EnumSet.complementOf(EnumSet.of(Wayfarers.Kind.PATROL)), "taiga", false, true, 0.3));
	}

	@Test
	void noShepherdWithoutPasture() {
		for (String z : List.of("desierto", "badlands", "jungla", "pantano")) {
			assertFalse(Wayfarers.fits(Wayfarers.Kind.SHEPHERD, z), z);
			for (int i = 0; i < 200; i++) {
				assertFalse(Wayfarers.choose(ALL, z, true, true, i / 200.0) == Wayfarers.Kind.SHEPHERD, z);
			}
		}
		for (String z : List.of("llanuras", "taiga", "nieve", "cerezos", "costa")) {
			assertTrue(Wayfarers.fits(Wayfarers.Kind.SHEPHERD, z), z);
		}
		assertTrue(Wayfarers.fits(Wayfarers.Kind.SHEPHERD, null), "outside every family: as in vanilla");
		for (Wayfarers.Kind k : ALL) {
			if (k != Wayfarers.Kind.SHEPHERD) {
				for (String z : Wayfarers.FAMILIES) {
					assertTrue(Wayfarers.fits(k, z), k + " in " + z);
				}
			}
		}
	}

	@Test
	void disabledKindsNeverSetOff() {
		Set<Wayfarers.Kind> some = EnumSet.of(Wayfarers.Kind.MESSENGER, Wayfarers.Kind.HUNTER);
		for (int i = 0; i < 300; i++) {
			assertTrue(some.contains(Wayfarers.choose(some, "llanuras", true, true, i / 300.0)));
		}
		assertNull(Wayfarers.choose(EnumSet.noneOf(Wayfarers.Kind.class), "llanuras", true, true, 0.5));
		// and the roll itself: disabled, at the limit, resting or at 0 % nobody sets off
		assertFalse(Wayfarers.outcome(false, 0, 1, 1_000_000, 0, 100, 0));
		assertFalse(Wayfarers.outcome(true, 1, 1, 1_000_000, 0, 100, 0), "one at a time");
		assertFalse(Wayfarers.outcome(true, 0, 1, Rules.WAIT_TICKS - 1, 0, 100, 0), "the rest after the previous one");
		assertFalse(Wayfarers.outcome(true, 0, 1, 1_000_000, 0, 0, 0), "0 %: only the command");
		assertTrue(Wayfarers.outcome(true, 0, 1, Rules.WAIT_TICKS, 0, 30, 0.29));
		assertFalse(Wayfarers.outcome(true, 0, 1, Rules.WAIT_TICKS, 0, 30, 0.31));
	}

	@Test
	void flockAndItsColorsByZone() {
		Set<Integer> sizes = new HashSet<>();
		for (int i = 0; i < 100; i++) {
			sizes.add(Wayfarers.flock(i / 100.0));
		}
		assertEquals(Set.of(3, 4, 5), sizes);
		Set<String> dyes = Set.of("white", "orange", "magenta", "light_blue", "yellow", "lime", "pink", "gray", "light_gray", "cyan", "purple",
				"blue", "brown", "green", "red", "black");
		for (String z : new ArrayList<>(Wayfarers.FAMILIES) {{ add(null); }}) {
			Map<String, Integer> colors = new java.util.HashMap<>();
			for (int i = 0; i < 1000; i++) {
				String c = Wayfarers.woolColor(z, i / 1000.0);
				assertTrue(dyes.contains(c), c);
				colors.merge(c, 1, Integer::sum);
			}
			for (Map.Entry<String, Integer> e : colors.entrySet()) {
				assertTrue(e.getKey().equals("white") || e.getValue() < colors.get("white"), "white the most common in " + z + ": " + colors);
			}
			assertTrue(colors.get("white") >= 350, "white at least a third in " + z + ": " + colors);
			assertTrue(colors.size() >= 2, "some variety in " + z + ": " + colors);
		}
		assertTrue(colorsOf("cerezos").contains("pink"));
		assertFalse(colorsOf("llanuras").contains("pink"));
		assertTrue(colorsOf("oscuro").contains("black"));
	}

	static Set<String> colorsOf(String zone) {
		Set<String> out = new HashSet<>();
		for (int i = 0; i < 1000; i++) {
			out.add(Wayfarers.woolColor(zone, i / 1000.0));
		}
		return out;
	}

	@Test
	void preyByZone() {
		assertEquals(Wayfarers.Prey.RABBIT, Wayfarers.prey("llanuras"));
		assertEquals(Wayfarers.Prey.RABBIT, Wayfarers.prey("desierto"));
		assertEquals(Wayfarers.Prey.RABBIT, Wayfarers.prey(null));
		assertEquals(Wayfarers.Prey.BOAR, Wayfarers.prey("taiga"));
		assertEquals(Wayfarers.Prey.BOAR, Wayfarers.prey("oscuro"));
		assertEquals(Wayfarers.Prey.FOWL, Wayfarers.prey("jungla"));
		assertEquals(Wayfarers.Prey.FOWL, Wayfarers.prey("pantano"));
		assertEquals("minecraft:porkchop", Wayfarers.held(Wayfarers.Kind.HUNTER, "taiga"));
		assertEquals("minecraft:stick", Wayfarers.held(Wayfarers.Kind.PILGRIM, "nieve"));
		assertNull(Wayfarers.held(Wayfarers.Kind.PATROL, "nieve"), "the golems carry nothing");
	}

	@Test
	void whoTradesAndWithWhat() {
		for (String z : Wayfarers.FAMILIES) {
			assertTrue(Wayfarers.trades(Wayfarers.Kind.PILGRIM, z, List.of()).isEmpty(), "the pilgrim carries nothing to sell");
			assertTrue(Wayfarers.trades(Wayfarers.Kind.MESSENGER, z, List.of()).isEmpty(), "the messenger does not stop");
			assertTrue(Wayfarers.trades(Wayfarers.Kind.PATROL, z, List.of()).isEmpty(), "the guards are on duty");
			assertFalse(Wayfarers.trades(Wayfarers.Kind.HUNTER, z, List.of()).isEmpty());
		}
		List<Wayfarers.Trade> sheep = Wayfarers.trades(Wayfarers.Kind.SHEPHERD, "taiga", List.of("white", "brown", "white", "black"));
		assertEquals(List.of("minecraft:white_wool", "minecraft:brown_wool", "minecraft:cooked_mutton", "minecraft:emerald"),
				sheep.stream().map(Wayfarers.Trade::result).toList(), "the wool of its flock (two colors at most), mutton, and it buys wheat");
		assertEquals("minecraft:wheat", sheep.get(3).cost());
		assertTrue(Wayfarers.trades(Wayfarers.Kind.HUNTER, "llanuras", List.of()).stream().anyMatch(t -> t.result().equals("minecraft:rabbit_foot")));
		assertTrue(Wayfarers.trades(Wayfarers.Kind.HUNTER, "taiga", List.of()).stream().noneMatch(t -> t.result().equals("minecraft:rabbit_foot")));
	}

	@Test
	void tradesDoNotBreakTheProgression() {
		Set<String> forbidden = Set.of("netherite", "elytra", "enchanted", "totem", "diamond", "trident", "mending", "golden_apple");
		for (Wayfarers.Kind k : ALL) {
			for (String z : Wayfarers.FAMILIES) {
				for (Wayfarers.Trade t : Wayfarers.trades(k, z, List.of("white", "pink"))) {
					for (String f : forbidden) {
						assertFalse(t.result().contains(f), t.toString());
					}
					assertTrue(t.uses() >= 1 && t.uses() <= 4, "few uses: it passes once " + t);
					assertTrue(t.amount() >= 1 && t.amount() <= 8 && t.count() >= 1 && t.count() <= 18, t.toString());
					if (t.cost().equals("minecraft:emerald")) {
						assertTrue(t.count() <= 3, "cheap: " + t);
					} else {
						assertEquals("minecraft:emerald", t.result(), "what it buys pays one emerald: " + t);
						assertEquals(1, t.amount());
					}
				}
			}
		}
	}

	@Test
	void attackingCostsReputationAsInTheVillage() {
		assertEquals(Reputation.VILLAGER_HIT, Wayfarers.penalty(Wayfarers.Role.PERSON, false));
		assertEquals(Reputation.VILLAGER_DEATH, Wayfarers.penalty(Wayfarers.Role.PERSON, true));
		assertEquals(Reputation.GOLEM_HIT, Wayfarers.penalty(Wayfarers.Role.GUARD, false));
		assertEquals(Reputation.GOLEM_DEATH, Wayfarers.penalty(Wayfarers.Role.GUARD, true));
		assertTrue(Wayfarers.penalty(Wayfarers.Role.ANIMAL, false) < 0 && Wayfarers.penalty(Wayfarers.Role.ANIMAL, false) > Reputation.VILLAGER_HIT);
		assertTrue(Wayfarers.penalty(Wayfarers.Role.ANIMAL, true) < 0 && Wayfarers.penalty(Wayfarers.Role.ANIMAL, true) > Reputation.VILLAGER_DEATH);
		assertEquals(Wayfarers.Role.PERSON, Wayfarers.role(Set.of(Rules.TAG, Wayfarers.LEADER, Wayfarers.Kind.HUNTER.tag()), false));
		assertEquals(Wayfarers.Role.GUARD, Wayfarers.role(Set.of(Rules.TAG, Wayfarers.LEADER), true));
		assertEquals(Wayfarers.Role.GUARD, Wayfarers.role(Set.of(Rules.TAG, Wayfarers.PARTNER), true));
		assertEquals(Wayfarers.Role.ANIMAL, Wayfarers.role(Set.of(Rules.TAG, Wayfarers.SHEEP), false));
		assertEquals(Wayfarers.Role.ANIMAL, Wayfarers.role(Set.of(Rules.TAG, Wayfarers.DOG), false));
	}

	@Test
	void entitiesPerEncounterAndCleanupTags() {
		assertEquals(1, Wayfarers.entities(Wayfarers.Kind.PILGRIM, 0));
		assertEquals(1, Wayfarers.entities(Wayfarers.Kind.MESSENGER, 0));
		assertEquals(2, Wayfarers.entities(Wayfarers.Kind.PATROL, 0));
		assertEquals(2, Wayfarers.entities(Wayfarers.Kind.HUNTER, 0));
		assertEquals(6, Wayfarers.entities(Wayfarers.Kind.SHEPHERD, Wayfarers.flock(0.99)), "the most: a shepherd with 5 sheep");
		// all their entities carry the caravans' tag: leftovers are removed on load, nothing drops (not bandits)
		for (String role : List.of(Wayfarers.LEADER, Wayfarers.SHEEP, Wayfarers.DOG, Wayfarers.PARTNER)) {
			Set<String> tags = Set.of(Rules.TAG, role);
			assertTrue(Caravans.noLoot(tags), role);
			assertTrue(Rules.orphan(tags, java.util.UUID.randomUUID(), Set.of()), role);
			assertTrue(role.startsWith(Rules.TAG + "."), role);
		}
	}

	@Test
	void kindsByCommandAndOptions() {
		Set<String> commands = new HashSet<>(), options = new HashSet<>();
		for (Wayfarers.Kind k : ALL) {
			assertEquals(k, Wayfarers.Kind.byCommand(k.command));
			assertEquals(k, Wayfarers.Kind.byCommand(k.command.toUpperCase()));
			assertTrue(k.command.matches("[a-z]+"), "commands in English, lowercase ASCII: " + k.command);
			assertTrue(k.option().startsWith("viajeros.") && k.option().endsWith(".activado"));
			assertTrue(k.tag().startsWith(Wayfarers.LEADER + "."));
			commands.add(k.command);
			options.add(k.option());
		}
		assertEquals(5, commands.size());
		assertEquals(5, options.size());
		assertNull(Wayfarers.Kind.byCommand("peregrino"));
		assertEquals(List.of("pilgrim", "shepherd", "messenger", "patrol", "hunter"), java.util.Arrays.stream(Wayfarers.Kind.values()).map(k -> k.command).toList());
	}

	@Test
	void thePilgrimWalksTowardsItsShrine() {
		RoadLayout.Route r = SegmentTest.route();
		int[] p = SegmentTest.beside(r, r.vertices() / 2, 30);
		Segment t = Segment.choose(List.of(r), p[0], p[1], 0);
		assertNotNull(t);
		Segment back = t.reversed();
		assertEquals(t.vertices(), back.vertices());
		assertEquals(t.x(0), back.x(back.vertices() - 1));
		assertEquals(t.z(t.vertices() - 1), back.z(0));
		assertEquals(t.origin(), back.destination(), "the other way round it goes to the other village");
		assertEquals(t, back.reversed());
		// a shrine beyond the arrival: the stretch as it is; beyond the start: reversed
		int sx = t.x(t.vertices() - 1) + 600 * Integer.signum(t.x(t.vertices() - 1) - t.x(0)), sz = t.z(t.vertices() - 1);
		assertTrue(Wayfarers.towards(t, sx, sz));
		assertFalse(Wayfarers.towards(back, sx, sz));
		// the shrine closest to the journey's direction
		assertTrue(Wayfarers.towards(back, t.x(0) - 600 * Integer.signum(t.x(t.vertices() - 1) - t.x(0)), t.z(0)));
	}
}
