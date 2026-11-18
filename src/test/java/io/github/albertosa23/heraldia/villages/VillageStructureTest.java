package io.github.albertosa23.heraldia.villages;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.level.block.Rotation;
import net.minecraft.world.level.levelgen.structure.BoundingBox;
import net.minecraft.SharedConstants;
import net.minecraft.server.Bootstrap;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/** Pure parts of the coastal villages' port: which pieces it displaces, which can be removed and its rotation. */
class VillageStructureTest {
	@BeforeAll
	static void bootstrap() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	/** Test piece: name, box, street (terrain_matching) and template path. */
	private record P(String name, BoundingBox box, boolean street, String path) {
	}

	private static P p(String name, String path, int x0, int z0, int x1, int z1) {
		return new P(name, new BoundingBox(x0, 60, z0, x1, 70, z1), false, path);
	}

	private static P street(String name, int x0, int z0, int x1, int z1) {
		return new P(name, new BoundingBox(x0, 60, z0, x1, 62, z1), true, "llanuras_castellana/streets/s0");
	}

	private static final BoundingBox SHED = new BoundingBox(0, 60, 0, 9, 68, 9);
	private static final BoundingBox PIER = new BoundingBox(2, 60, 10, 6, 63, 30);

	/** Open sea of the test pier (not in a static field: it would touch VillageStructure before the Bootstrap). */
	private static BoundingBox seaSide() {
		return VillageStructure.openSea(PIER, Direction.SOUTH);
	}

	private static List<P> run(List<P> village) {
		return VillageStructure.displaced(village, P::box, P::street, q -> VillageStructure.removable(q.path), SHED, PIER, seaSide());
	}

	@Test
	void removesBlockingHousesAndTheirContents() {
		P house = p("casa", "llanuras_castellana/houses/small_0", 5, 5, 14, 14);
		P villager = p("aldeano", "villagers/plains/librarian", 6, 6, 6, 6);          // inside the house (and in its box)
		P far = p("lejos", "llanuras_castellana/houses/small_1", 50, 50, 60, 60);
		P streetUnderShed = street("calle", 0, 0, 1, 9);                               // under the shed: valid
		List<P> out = run(List.of(house, villager, far, streetUnderShed));
		assertEquals(List.of(house, villager), out);
	}

	@Test
	void discardsShoreIfItHitsSomethingUnremovable() {
		P church = p("iglesia", "llanuras_castellana/specials/church", 3, 3, 12, 12);
		assertNull(run(List.of(church)));
		P plaza = p("plaza", "llanuras_castellana/plaza/std", 0, 20, 20, 40);
		assertNull(run(List.of(plaza)));
	}

	@Test
	void streetUnderPierDiscardsShore() {
		assertNull(run(List.of(street("calle", 4, 20, 5, 40))));
		assertEquals(List.of(), run(List.of(street("lejos", 40, 20, 41, 40))));
	}

	@Test
	void openSeaAroundPier() {
		assertEquals(new BoundingBox(-2, 60, 10, 10, 63, 36), seaSide());                      // 6 past the tip, 4 to the sides
		assertEquals(new BoundingBox(-8, 60, 2, 30, 63, 14),
				VillageStructure.openSea(new BoundingBox(-2, 60, 6, 30, 63, 10), Direction.WEST));
		// a special building in the water past the tip (its terrain adaptation would cover the tip) discards the shore
		assertNull(run(List.of(p("mercado", "costa_pescadores/specials/market_b", 0, 32, 12, 44))));
		// a house next to the pier is removed; a street beside it (planks over the water) does not get in the way
		P house = p("casa", "costa_pescadores/houses/small_0", 8, 14, 14, 20);
		assertEquals(List.of(house), run(List.of(house, street("calle", 8, 12, 9, 40))));
		assertEquals(List.of(), run(List.of(p("lejos", "costa_pescadores/houses/small_1", 12, 14, 20, 20))));
	}

	@Test
	void portFitsInTheEightStartChunks() {
		// start chunk from block 160, 320: blocks from 32 to 303 in x and from 192 to 463 in z are valid
		assertTrue(VillageStructure.inWindow(new BoundingBox(32, 60, 192, 303, 70, 463), 160, 320));
		assertFalse(VillageStructure.inWindow(new BoundingBox(31, 60, 200, 40, 70, 210), 160, 320));
		assertFalse(VillageStructure.inWindow(new BoundingBox(290, 60, 200, 304, 70, 210), 160, 320));
		assertFalse(VillageStructure.inWindow(new BoundingBox(100, 60, 191, 110, 70, 200), 160, 320));
		assertFalse(VillageStructure.inWindow(new BoundingBox(100, 60, 400, 110, 70, 464), 160, 320));
	}

	@Test
	void whatCanBeRemoved() {
		for (String ok : List.of("x/houses/a", "x/fillers/well", "x/decor/lamp", "x/terminators/tower", "villagers/plains/e_farmer", "golem")) {
			assertTrue(VillageStructure.removable(ok), ok);
		}
		for (String no : List.of("x/specials/church", "x/plaza/std", "x/streets/s0", "x/avenues/a", "x/tablon", "golems")) {
			assertFalse(VillageStructure.removable(no), no);
		}
		assertTrue(VillageStructure.isBoard("costa_puerto/tablon"));
		assertFalse(VillageStructure.isBoard("costa_puerto/tablon_b"));
	}

	@Test
	void tracesOfWorkInProgress() {
		// the traces sit on their plots (fillers): the port can displace them with the plot, and the option removes only them
		for (String t : List.of("llanuras_castellana/traces/laundry", "costa_pescadores/traces/fish_rack")) {
			assertTrue(VillageStructure.isTrace(t), t);
			assertTrue(VillageStructure.removable(t), t);
		}
		for (String no : List.of("llanuras_castellana/fillers/plot", "llanuras_castellana/houses/small_0", "llanuras_castellana/tablon",
				"villagers/plains/e_farmer", "golem")) {
			assertFalse(VillageStructure.isTrace(no), no);
		}
		assertTrue(VillageStructure.removable("llanuras_castellana/fillers/plot"));
	}

	@Test
	void rotationTowardsSea() {
		for (Direction d : Direction.Plane.HORIZONTAL) {
			Rotation r = VillageStructure.facing(d);
			BlockPos v = new BlockPos(0, 0, 1).rotate(r);
			assertEquals(d.getStepX(), v.getX(), d.toString());
			assertEquals(d.getStepZ(), v.getZ(), d.toString());
		}
		assertEquals(Rotation.NONE, VillageStructure.facing(Direction.SOUTH));
		assertEquals(Rotation.NONE, VillageStructure.facing(Direction.UP));      // no horizontal rotation possible
	}
}
