package io.github.albertosa23.heraldia.welcome;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import io.github.albertosa23.heraldia.welcome.Spots.Action;
import io.github.albertosa23.heraldia.welcome.Spots.Piece;
import io.github.albertosa23.heraldia.welcome.Spots.Spot;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.Test;

/** The pure logic of the reputation shown in the village: the look, the spots and the rule that protects players' blocks. */
class WelcomeLogicTest {
	@Test
	void theVillageShowsTheBestReputation() {
		assertEquals(Look.PLAIN, Look.of(List.of(), true), "nobody has dealt with it");
		assertEquals(Look.PLAIN, Look.of(List.of(5, 19), true));
		assertEquals(Look.KNOWN, Look.of(List.of(20), true));
		assertEquals(Look.FRIEND, Look.of(List.of(-100, 80, 3), true), "one friend is enough, whatever the others did");
		assertEquals(Look.HERO, Look.of(List.of(200, -40), true));
		assertEquals(Look.SHUNNED, Look.of(List.of(-5, -40), true), "only when everyone recorded is negative");
		assertEquals(Look.PLAIN, Look.of(List.of(-5, 0), true), "a 0 next to a negative is not shunned");
		assertEquals(Look.PLAIN, Look.of(List.of(300), false), "option off: as generated");
		assertEquals(Look.PLAIN, Look.of(List.of(-100), false));
	}

	@Test
	void looksAreOrderedAndRangesWork() {
		assertTrue(Look.HERO.within(Look.FRIEND, Look.HERO));
		assertFalse(Look.KNOWN.within(Look.FRIEND, Look.HERO));
		assertTrue(Look.SHUNNED.within(Look.SHUNNED, Look.SHUNNED));
		assertFalse(Look.PLAIN.within(Look.SHUNNED, Look.SHUNNED));
		for (Spot s : Spots.all()) {
			assertFalse(s.shownIn(Look.PLAIN), "as generated, nothing is added: " + s);
			assertTrue(s.min().compareTo(s.max()) <= 0, s.toString());
		}
	}

	@Test
	void eachWarmerLookAddsAndKeepsWhatTheColderOneHad() {
		int before = 0;
		for (Look l : new Look[] {Look.KNOWN, Look.FRIEND, Look.HERO}) {
			int n = (int) Spots.all().stream().filter(s -> s.shownIn(l)).count();
			assertTrue(n > before, l + " shows more than the look below it: " + n);
			before = n;
		}
		for (Spot s : Spots.all()) {
			if (s.shownIn(Look.KNOWN) || s.shownIn(Look.FRIEND)) {
				assertTrue(s.shownIn(Look.HERO), "a hero village keeps everything below: " + s);
			}
			if (s.item() == Spots.Item.SHUTTER) {
				assertTrue(s.shownIn(Look.SHUNNED) && !s.shownIn(Look.KNOWN), s.toString());
			}
		}
	}

	@Test
	void templatePathsSelectThePieces() {
		assertEquals(Piece.GATE, Piece.of("llanuras_castellana/terminators/gate"));
		assertEquals(Piece.TOWER, Piece.of("taiga_nordica/terminators/tower"));
		assertEquals(Piece.TOWER, Piece.of("taiga_nordica/terminators/tower_b"));
		assertEquals(Piece.PLAZA, Piece.of("costa_mercante/plaza/std"));
		assertEquals(Piece.PLAZA, Piece.of("costa_mercante/plaza/grande"));
		assertEquals(Piece.BOARD, Piece.of("jungla_bambu/tablon"));
		assertNull(Piece.of("jungla_bambu/houses/casa_1"));
		assertNull(Piece.of("jungla_bambu/terminators/end"));
		assertNull(Piece.of("villagers/farmer"));
	}

	@Test
	void noTwoSpotsOfAPieceShareACellAndNoneSitsOnItsSupport() {
		for (Piece p : Piece.values()) {
			Set<List<Integer>> cells = new HashSet<>();
			for (Spot s : Spots.of(p)) {
				assertTrue(cells.add(List.of(s.x(), s.y(), s.z())), "two spots on the same cell: " + s);
				int d = Math.abs(s.x() - s.sx()) + Math.abs(s.y() - s.sy()) + Math.abs(s.z() - s.sz());
				assertEquals(1, d, "the support is the neighbouring block: " + s);
			}
			for (Spot s : Spots.of(p)) {
				assertFalse(cells.contains(List.of(s.sx(), s.sy(), s.sz())), "a decoration never rests on another one: " + s);
			}
		}
	}

	// --- the rule: never destroy or overwrite a player's block ---

	@Test
	void placesOnlyOnAirWithItsSupport() {
		assertEquals(Action.PLACE, Spots.decide(true, null, "air", true, true, false, true));
		assertEquals(Action.NONE, Spots.decide(true, null, "air", true, false, false, true), "support missing or changed");
		assertEquals(Action.NONE, Spots.decide(false, null, "air", true, true, false, true), "not wanted in this look");
		assertEquals(Action.NONE, Spots.decide(true, null, "air", true, true, true, true), "declined before");
	}

	@Test
	void aPlayersBlockWhereTheVillageWouldDecorateIsLeftAlone() {
		// a player has built where a banner would go: it is not air, nothing is placed, and it stays so in every look
		for (boolean wanted : new boolean[] {true, false}) {
			assertEquals(Action.NONE, Spots.decide(wanted, null, "oak_planks", false, true, false, true));
		}
		// what was put up has been replaced by a player's block: never removed, and the spot is forgotten for good
		assertEquals(Action.DECLINE, Spots.decide(false, "red_banner", "oak_planks", false, true, false, true));
		assertEquals(Action.DECLINE, Spots.decide(true, "red_banner", "oak_planks", false, true, false, true));
		// the player took the banner down: not put back (declined), so the village does not fight them
		assertEquals(Action.DECLINE, Spots.decide(true, "red_banner", "air", true, true, false, true));
		// the flower was taken out of the pot (another state): not ours any more
		assertEquals(Action.DECLINE, Spots.decide(false, "potted_poppy", "flower_pot", false, true, false, true));
		// something rests on what was put up (a block on the carpet): it is not taken down, it would drop
		assertEquals(Action.DECLINE, Spots.decide(false, "red_carpet", "red_carpet", false, true, false, false));
	}

	@Test
	void removesOnlyExactlyWhatItPlaced() {
		assertEquals(Action.REMOVE, Spots.decide(false, "red_banner", "red_banner", false, true, false, true));
		assertEquals(Action.KEEP, Spots.decide(true, "red_banner", "red_banner", false, true, false, true));
		assertEquals(Action.KEEP, Spots.decide(true, "red_banner", "red_banner", false, false, false, false),
				"kept even if its support were checked again");
	}

	// --- materials ---

	@Test
	void materialsFromBlockIds() {
		assertEquals("red", Spots.bannerColour("minecraft:red_wall_banner"));
		assertEquals("light_blue", Spots.bannerColour("minecraft:light_blue_banner"));
		assertNull(Spots.bannerColour("minecraft:lantern"));
		assertNull(Spots.bannerColour("minecraft:_banner"));
		assertEquals("dark_oak", Spots.fenceWood("minecraft:dark_oak_fence"));
		assertNull(Spots.fenceWood("minecraft:nether_brick_fence"));
		assertNull(Spots.fenceWood("minecraft:oak_fence_gate"));
	}

	@Test
	void everyFamilyHasFlowersOfItsLand() {
		assertEquals("llanuras", Spots.family("llanuras_castellana"));
		assertEquals("cerezos", Spots.family("cerezos_japonesa"));
		for (String f : List.of("llanuras", "bosque", "oscuro", "taiga", "nieve", "desierto", "sabana", "jungla", "pantano",
				"cerezos", "badlands", "costa")) {
			assertTrue(Spots.flowerFamilies().contains(f), f);
			for (int i = 0; i < 2; i++) {
				assertTrue(Spots.flower(f + "_x", i).startsWith("potted_"), f);
			}
		}
		assertEquals("potted_cactus", Spots.flower("desierto_andalusi", 0));
		assertEquals(Spots.flower("x", 0), Spots.flower("x", 2));
	}
}
