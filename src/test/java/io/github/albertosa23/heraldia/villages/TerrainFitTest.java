package io.github.albertosa23.heraldia.villages;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import io.github.albertosa23.heraldia.villages.TerrainFit.Kind;
import io.github.albertosa23.heraldia.villages.TerrainFit.Part;
import io.github.albertosa23.heraldia.villages.TerrainFit.Reason;
import java.util.ArrayList;
import java.util.List;
import java.util.function.IntBinaryOperator;
import net.minecraft.SharedConstants;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.level.levelgen.structure.BoundingBox;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/**
 * Which village pieces a villager can walk to ({@link TerrainFit}), on made-up terrain: a plaza, a street running east
 * from it and a house on the street's north side, as the jigsaw lays them out.
 */
class TerrainFitTest {
	@BeforeAll
	static void bootstrap() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	private static TerrainFit.Ground land(IntBinaryOperator h) {
		return h::applyAsInt;
	}

	// plaza 0..9 x 0..9 (floor row at y 64), street 10..25 x 2..8 running east (joint at the plaza's edge, x 9),
	// house 14..20 x -7..-1 on the street's north side (its door at z -1, joint on the street's edge row z 2... the street's
	// jigsaw block one column outside the house: z 0 here, inside the street box), villager inside the house.
	private static final BoundingBox PLAZA = new BoundingBox(0, 64, 0, 9, 70, 9);
	private static final BoundingBox STREET = new BoundingBox(10, 63, 2, 25, 68, 8);
	private static final BoundingBox HOUSE = new BoundingBox(14, 65, -6, 20, 75, 1);
	private static final BoundingBox VILLAGER = new BoundingBox(16, 66, -3, 16, 67, -3);

	private static List<Part> village() {
		List<Part> parts = new ArrayList<>();
		parts.add(Part.of(PLAZA, Kind.ROOT, -1, 0, 0));
		parts.add(Part.of(STREET, Kind.STREET, 0, 9, 5));
		parts.add(Part.of(HOUSE, Kind.BUILDING, 1, 17, 2));
		parts.add(Part.of(VILLAGER, Kind.CONTENT, 2, 16, -2));
		return parts;
	}

	private static Reason[] reasons(TerrainFit.Ground g) {
		return TerrainFit.fit(village(), g).reasons();
	}

	@Test
	void flatLandKeepsEverything() {
		// the plaza floor row is at 64 (standing at 65) and the land's first free height is 65
		assertArrayEquals(new Reason[] {Reason.KEPT, Reason.KEPT, Reason.KEPT, Reason.KEPT}, reasons(land((x, z) -> 65)));
	}

	@Test
	void aGentleSlopeIsWalkable() {
		// one block up every two columns eastwards (and the house's joint column on the slope like the street)
		TerrainFit.Ground slope = land((x, z) -> x < 10 ? 65 : 65 + (x - 10) / 2);
		assertEquals(Reason.KEPT, reasons(slope)[1]);
		// one block a column is still walkable
		assertEquals(Reason.KEPT, reasons(land((x, z) -> x < 10 ? 65 : 65 + (x - 9)))[1]);
	}

	@Test
	void aStepOfTwoIsGradedIntoARamp() {
		TerrainFit.Ground step = land((x, z) -> x < 18 ? 65 : 67);
		TerrainFit.Result r = TerrainFit.fit(village(), step);
		assertArrayEquals(new Reason[] {Reason.KEPT, Reason.KEPT, Reason.KEPT, Reason.KEPT}, r.reasons());
		// grading points along the centre line (z 5), one every two columns, climbing one block at a time
		List<int[]> points = r.grades().get(1);
		assertTrue(!points.isEmpty());
		int prevX = Integer.MIN_VALUE, prevY = 0;
		for (int[] q : points) {
			assertEquals(5, q[2]);
			assertTrue(q[0] >= STREET.minX() && q[0] <= STREET.maxX());
			assertTrue(q[1] >= 65 && q[1] <= 67);
			if (prevX != Integer.MIN_VALUE) {
				assertTrue(Math.abs(q[1] - prevY) <= q[0] - prevX);
			}
			prevX = q[0];
			prevY = q[1];
		}
		assertTrue(r.grades().get(0).isEmpty() && r.grades().get(2).isEmpty());
		assertTrue(r.summary().contains("1 streets and doors graded"), r.summary());
	}

	@Test
	void aCliffTooHighToGradeIsLeftAsItIs() {
		TerrainFit.Result r = TerrainFit.fit(village(), land((x, z) -> x < 18 ? 65 : 65 + 2 * TerrainFit.MAX_GRADE + 2));
		// the street stays (what hangs from it works on its own), ungraded
		assertArrayEquals(new Reason[] {Reason.KEPT, Reason.STEEP_STREET, Reason.KEPT, Reason.KEPT}, r.reasons());
		assertTrue(r.kept(1) && r.grades().get(1).isEmpty());
	}

	@Test
	void oneWalkableLaneIsEnough() {
		// the cliff cuts the north lanes but the southern one (z 7) climbs it as a ramp: nothing to grade
		TerrainFit.Ground partly = land((x, z) -> z >= 7 ? 65 + Math.max(0, Math.min(2, x - 17)) : (x < 18 ? 65 : 67));
		TerrainFit.Result r = TerrainFit.fit(village(), partly);
		assertEquals(Reason.KEPT, r.reasons()[1]);
		assertTrue(r.grades().get(1).isEmpty());
	}

	@Test
	void aStreetBelowThePlazaRampsUpToItsFloor() {
		// the street's ground two blocks below the plaza's standing height (65): graded from the plaza down
		TerrainFit.Result r = TerrainFit.fit(village(), land((x, z) -> x < 10 ? 65 : 63));
		assertEquals(Reason.KEPT, r.reasons()[1]);
		assertEquals(64, r.grades().get(1).get(0)[1]);
		// one block below is a step: nothing to grade
		assertTrue(TerrainFit.fit(village(), land((x, z) -> x < 10 ? 65 : 64)).grades().get(1).isEmpty());
	}

	@Test
	void gradeKeepsTheEndsAndClimbsAStepAColumn() {
		int[] r = {65, 65, 65, 68, 68, 68, 68, 66};
		int[] t = TerrainFit.grade(r);
		assertEquals(65, t[0]);
		assertEquals(66, t[t.length - 1]);
		for (int k = 1; k < t.length; k++) {
			assertTrue(Math.abs(t[k] - t[k - 1]) <= 1, java.util.Arrays.toString(t));
		}
		assertTrue(TerrainFit.deviation(r, t) <= 2, java.util.Arrays.toString(t));
		// already walkable: unchanged
		int[] flat = {64, 65, 65, 66, 65};
		assertArrayEquals(flat, TerrainFit.grade(flat));
		// ends further apart in height than in columns: impossible
		assertNull(TerrainFit.grade(new int[] {60, 61, 70}));
	}

	@Test
	void aDoorTwoStepsAboveTheStreetGetsARamp() {
		// the house stands on its joint column (z 2); the street column next to it (z 3) is two blocks lower
		TerrainFit.Result r = TerrainFit.fit(village(), land((x, z) -> z <= 2 && x >= 14 && x <= 20 ? 67 : 65));
		assertArrayEquals(new Reason[] {Reason.KEPT, Reason.KEPT, Reason.KEPT, Reason.KEPT}, r.reasons());
		// the joint column at the door's height (67), then one block lower into the street; z 4 is already at 65
		List<int[]> ramp = r.grades().get(2);
		assertEquals(2, ramp.size());
		assertArrayEquals(new int[] {17, 67, 2}, ramp.get(0));
		assertArrayEquals(new int[] {17, 66, 3}, ramp.get(1));
	}

	@Test
	void aDoorTooFarAboveTheStreetDropsTheHouseAndItsVillager() {
		TerrainFit.Ground cliff = land((x, z) -> z <= 2 && x >= 14 && x <= 20 ? 65 + TerrainFit.MAX_DOOR + 1 : 65);
		assertArrayEquals(new Reason[] {Reason.KEPT, Reason.KEPT, Reason.DOOR_STEP, Reason.PARENT}, reasons(cliff));
	}

	@Test
	void aLowPieceSunkInAPitIsDropped() {
		BoundingBox garden = new BoundingBox(14, 65, -6, 20, 67, 1);
		List<Part> parts = village();
		parts.set(2, Part.of(garden, Kind.BUILDING, 1, 17, 2));
		// the ground rises behind the garden to three blocks over its floor row
		TerrainFit.Ground hill = land((x, z) -> z < -2 ? 68 : 65);
		assertEquals(Reason.PIT, TerrainFit.fit(parts, hill).reasons()[2]);
		// a tall house in the same spot is dug into the hill, not a pit
		assertEquals(Reason.KEPT, reasons(hill)[2]);
	}

	@Test
	void sideFindsTheFaceTheJointIsBeside() {
		BoundingBox b = new BoundingBox(0, 0, 0, 6, 5, 6);
		assertArrayEquals(new int[] {-1, 0}, TerrainFit.side(-1, 3, b));
		assertArrayEquals(new int[] {1, 0}, TerrainFit.side(7, 3, b));
		assertArrayEquals(new int[] {0, -1}, TerrainFit.side(3, -1, b));
		assertArrayEquals(new int[] {0, 1}, TerrainFit.side(3, 7, b));
		assertNull(TerrainFit.side(3, 3, b));
		assertNull(TerrainFit.side(-1, -1, b));
		assertArrayEquals(new int[] {3, 8}, TerrainFit.outward(3, 7, b));
		assertArrayEquals(new int[] {3, 6}, TerrainFit.inward(3, 7, b));
	}

	@Test
	void parentsComeFromTheJunctions() {
		// plaza, street, house and villager, each with the junctions the jigsaw gives them (at the other's jigsaw block)
		List<BoundingBox> boxes = List.of(PLAZA, STREET, HOUSE, VILLAGER);
		List<List<int[]>> junctions = List.of(
				List.of(new int[] {10, 5}),                          // plaza: at the street's first column
				List.of(new int[] {9, 5}, new int[] {17, 1}),        // street: plaza's jigsaw, house's door
				List.of(new int[] {17, 2}, new int[] {16, -3}),      // house: street's edge, villager's slot
				List.of(new int[] {16, -2}));                        // villager: the house's slot
		assertNull(VillageStructure.parent(boxes, junctions, 0));
		assertArrayEquals(new int[] {0, 9, 5}, VillageStructure.parent(boxes, junctions, 1));
		assertArrayEquals(new int[] {1, 17, 2}, VillageStructure.parent(boxes, junctions, 2));
		assertArrayEquals(new int[] {2, 16, -2}, VillageStructure.parent(boxes, junctions, 3));
	}

	@Test
	void kindsByTemplatePath() {
		assertEquals(Kind.BUILDING, VillageStructure.kind("llanuras_castellana/houses/small_0"));
		assertEquals(Kind.BUILDING, VillageStructure.kind("llanuras_castellana/specials/tavern_b"));
		assertEquals(Kind.BUILDING, VillageStructure.kind("llanuras_castellana/fillers/well"));
		assertEquals(Kind.BUILDING, VillageStructure.kind("llanuras_castellana/terminators/tower"));
		assertEquals(Kind.CONTENT, VillageStructure.kind("villagers/plains/e_farmer"));
		assertEquals(Kind.CONTENT, VillageStructure.kind("golem"));
		assertEquals(Kind.CONTENT, VillageStructure.kind("llanuras_castellana/decor/lamp"));
		assertEquals(Kind.CONTENT, VillageStructure.kind("llanuras_castellana/tablon"));
	}

	@Test
	void summaryCountsEveryReason() {
		// a door too far above the street: the house and its villager go
		TerrainFit.Result r = TerrainFit.fit(village(), land((x, z) -> z <= 2 && x >= 14 && x <= 20 ? 70 : 65));
		assertEquals(2, r.count(Reason.KEPT));
		assertEquals(1, r.count(Reason.DOOR_STEP));
		assertEquals(1, r.count(Reason.PARENT));
		assertTrue(r.summary().startsWith("2 of 4 pieces kept, 0 streets and doors graded"), r.summary());
	}
}
