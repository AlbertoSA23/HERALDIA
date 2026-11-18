package io.github.albertosa23.heraldia.villages;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;
import net.minecraft.SharedConstants;
import net.minecraft.core.Direction;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.level.levelgen.structure.BoundingBox;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/**
 * Choice of the port's shore ({@link Shoreline}) with synthetic height maps and the village's pieces as boxes
 * (with the same {@code VillageStructure.displaced} as in the game): shore next to the plaza, street under the tip,
 * inlet, no water, cliff, shallow water and preference for free shores.
 */
class ShorelineTest {
	private static final int SEA = 63, LENGTH = 18, REACH = 80;
	private static final int LAND = SEA + 1, DEPTH = SEA - 12;

	@BeforeAll
	static void bootstrap() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	/** Village piece: box, street (terrain_matching) and template path. */
	private record P(String name, BoundingBox box, boolean street, String path) {
	}

	private static P rigid(String name, String path, int x0, int z0, int x1, int z1) {
		return new P(name, new BoundingBox(x0, 60, z0, x1, 72, z1), false, path);
	}

	private static P street(int x0, int z0, int x1, int z1) {
		return new P("calle", new BoundingBox(x0, 60, z0, x1, 62, z1), true, "costa_pescadores/streets/s0");
	}

	/** Plan-view box (y from 60 to 72) from two corners in any order. */
	private static BoundingBox box(int ax, int az, int bx, int bz) {
		return new BoundingBox(Math.min(ax, bx), 60, Math.min(az, bz), Math.max(ax, bx), 72, Math.max(az, bz));
	}

	/** 9 x 9 shed on land with its joint (center of the sea face) on the shore; 9 x 18 pier from one block offshore. */
	private static BoundingBox[] boxes(Shoreline.Shore s) {
		Direction d = s.sea(), l = d.getClockWise();
		int x = s.x(), z = s.z();
		BoundingBox shed = box(x - l.getStepX() * 4 - d.getStepX() * 8, z - l.getStepZ() * 4 - d.getStepZ() * 8,
				x + l.getStepX() * 4, z + l.getStepZ() * 4);
		BoundingBox pier = box(x - l.getStepX() * 4 + d.getStepX(), z - l.getStepZ() * 4 + d.getStepZ(),
				x + l.getStepX() * 4 + d.getStepX() * LENGTH, z + l.getStepZ() * 4 + d.getStepZ() * LENGTH);
		return new BoundingBox[]{shed, pier};
	}

	private static Shoreline.Choice<List<P>> choose(Shoreline.Seabed depth, List<P> village) {
		return Shoreline.choose(depth, SEA, 0, 0, REACH, LENGTH, s -> {
			BoundingBox[] c = boxes(s);
			return VillageStructure.displaced(village, P::box, P::street, q -> VillageStructure.removable(q.path), c[0], c[1],
					VillageStructure.openSea(c[1], s.sea()));
		}, List::isEmpty);
	}

	/** Sea to the south from z = coast (bottom 12 below the sea), low beach to the north. */
	private static Shoreline.Seabed seaToTheSouth(int coast) {
		return (x, z) -> z >= coast ? DEPTH : LAND;
	}

	/** The chosen shore is on low land next to the water and its pier has sea below, at the tip and halfway. */
	private static void onTheShore(Shoreline.Seabed f, Shoreline.Shore s) {
		assertNotNull(s);
		assertTrue(f.en(s.x(), s.z()) >= SEA && f.en(s.x(), s.z()) <= SEA + Shoreline.SHALLOW, "la orilla es tierra baja: " + s);
		Direction d = s.sea();
		assertTrue(f.en(s.x() + d.getStepX() * LENGTH, s.z() + d.getStepZ() * LENGTH) <= SEA - 2, "agua en la punta: " + s);
		assertTrue(f.en(s.x() + d.getStepX() * LENGTH / 2, s.z() + d.getStepZ() * LENGTH / 2) < SEA, "agua a la mitad: " + s);
		assertTrue(Shoreline.seaSide(f, SEA, s, LENGTH));
	}

	@Test
	void nearestFreeShore() {
		Shoreline.Seabed f = seaToTheSouth(40);
		Shoreline.Choice<List<P>> e = choose(f, List.of());
		Shoreline.Shore s = e.shore();
		onTheShore(f, s);
		assertEquals(Direction.SOUTH, s.sea());
		assertEquals(0, s.x());
		assertEquals(38, s.z());              // last land with step 2 (39 is too)
		assertEquals(List.of(), e.gone());
	}

	@Test
	void shoreNextToPlaza() {
		// the plaza reaches the shore in front of the center: the port goes along the coast, not on top
		Shoreline.Seabed f = seaToTheSouth(40);
		P plaza = rigid("plaza", "costa_pescadores/plaza/std", -15, -15, 15, 38);
		Shoreline.Shore s = choose(f, List.of(plaza)).shore();
		onTheShore(f, s);
		assertEquals(Direction.SOUTH, s.sea());
		BoundingBox[] c = boxes(s);
		assertFalse(c[0].intersects(plaza.box()) || c[1].intersects(plaza.box()), "el puerto no pisa la plaza: " + s);
		assertEquals(24, Math.abs(s.x()));   // the line beside the node at 16 (at 16 the shed, 9 wide, still touches the plaza)
	}

	@Test
	void streetUnderTheTip() {
		// the avenue goes down to the south and into the sea (planks over the water): the pier cannot go on top
		Shoreline.Seabed f = seaToTheSouth(40);
		P avenue = street(-2, -80, 2, 80);
		Shoreline.Choice<List<P>> e = choose(f, List.of(avenue));
		Shoreline.Shore s = e.shore();
		onTheShore(f, s);
		assertFalse(boxes(s)[1].intersects(avenue.box().minX(), avenue.box().minZ(), avenue.box().maxX(), avenue.box().maxZ()));
		assertEquals(8, Math.abs(s.x()));    // the line beside the central one: the pier (9 wide) no longer steps on it
		assertTrue(e.blocked() + e.discarded() >= 1);
	}

	@Test
	void buildingsNotRemovedAlongTheCoast() {
		Shoreline.Seabed f = seaToTheSouth(40);
		P church = rigid("iglesia", "costa_pescadores/specials/church", -200, 20, 200, 39);
		Shoreline.Choice<List<P>> e = choose(f, List.of(church));
		assertNull(e.shore());
		assertEquals(e.candidates(), e.blocked());
		assertTrue(e.discarded() > 3, "se descartan por las piezas las direcciones hacia la costa: " + e.discarded());
	}

	@Test
	void pieceInWaterPastTheTip() {
		// the market is over the water in front of the nearest shore: its terrain would cover the tip
		Shoreline.Seabed f = seaToTheSouth(40);
		P market = rigid("mercado", "costa_pescadores/specials/market_b", -12, 58, 12, 70);
		Shoreline.Shore s = choose(f, List.of(market)).shore();
		onTheShore(f, s);
		assertFalse(VillageStructure.openSea(boxes(s)[1], s.sea()).intersects(market.box()), s.toString());
	}

	@Test
	void villageCenterSpendsNoQueries() {
		// the plaza and the special buildings cover the whole center: their nodes do not query the bottom
		Shoreline.Seabed f = seaToTheSouth(76);
		P center = rigid("centro", "costa_pescadores/specials/church", -50, -50, 50, 50);
		Shoreline.Choice<List<P>> free = choose(f, List.of());
		Shoreline.Choice<List<P>> covered = choose(f, List.of(center));
		assertNotNull(covered.shore());
		assertTrue(covered.discarded() > 0);
		int knotsInside = (int) Shoreline.knots(REACH / Shoreline.STEP).stream()
				.filter(n -> Math.abs(n[0] * Shoreline.STEP) <= 34 && Math.abs(n[1] * Shoreline.STEP) <= 34).count();
		assertTrue(knotsInside > 0);
		assertTrue(covered.queries() <= free.queries(), covered.queries() + " <= " + free.queries());
	}

	@Test
	void prefersFreeShoreOverDisplacingHouses() {
		Shoreline.Seabed f = seaToTheSouth(40);
		P house = rigid("casa", "costa_pescadores/houses/small_0", -10, 25, 10, 39);
		Shoreline.Choice<List<P>> e = choose(f, List.of(house));
		onTheShore(f, e.shore());
		assertEquals(List.of(), e.gone());
		assertTrue(Math.abs(e.shore().x()) >= 16);
		// houses along the whole coast: those of the nearest shore are removed
		P row = rigid("hilera", "costa_pescadores/houses/large_0", -200, 25, 200, 39);
		P tower = rigid("torre", "costa_pescadores/terminators/tower", -200, 41, 200, 45);    // in the water, under the pier
		Shoreline.Choice<List<P>> e2 = choose(f, List.of(row, tower));
		onTheShore(f, e2.shore());
		assertEquals(0, e2.shore().x());
		assertEquals(List.of(row, tower), e2.gone());
	}

	@Test
	void inletWithoutOpenSea() {
		// a narrow estuary (7 wide) that goes towards the center: the boats do not fit and the pier would end on land
		Shoreline.Seabed estuary = (x, z) -> z >= 20 && Math.abs(x) <= 3 ? DEPTH : LAND;
		Shoreline.Choice<List<P>> e = choose(estuary, List.of());
		assertNull(e.shore());
		assertTrue(e.noSeabed() > 0, "la ría da orillas, pero sin mar abierto");
		// the same estuary with open sea beyond: the port goes to the sea, not the estuary
		Shoreline.Seabed withSea = (x, z) -> z >= 72 || (z >= 20 && Math.abs(x) <= 3) ? DEPTH : LAND;
		Shoreline.Shore s = choose(withSea, List.of()).shore();
		onTheShore(withSea, s);
		assertEquals(Direction.SOUTH, s.sea());
		assertTrue(s.z() >= 64 && Math.abs(s.x()) > 3, "en la costa del mar abierto: " + s);
	}

	@Test
	void noWater() {
		java.util.Set<Long> columns = new java.util.HashSet<>();
		Shoreline.Choice<List<P>> e = choose((x, z) -> {
			columns.add(((long) x << 32) ^ (z & 0xFFFFFFFFL));
			return SEA + 8;
		}, List.of());
		assertNull(e.shore());
		assertEquals(0, e.candidates());
		// high land: one column per grid node and nothing more (in the game the Heights cache serves the repeated ones)
		assertEquals(Shoreline.knots(REACH / Shoreline.STEP).size(), columns.size());
	}

	@Test
	void cliffByWaterIsNotShore() {
		Shoreline.Seabed cliff = (x, z) -> z >= 40 ? DEPTH : SEA + 10;
		Shoreline.Choice<List<P>> e = choose(cliff, List.of());
		assertNull(e.shore());
		assertEquals(0, e.candidates());
		// low beach with a high step right before the water: the refined point is no longer low land
		Shoreline.Seabed ledge = (x, z) -> z >= 40 ? DEPTH : z >= 34 ? SEA + 9 : LAND;
		assertNull(choose(ledge, List.of()).shore());
	}

	@Test
	void shallowDoesNotWork() {
		Shoreline.Seabed shoal = (x, z) -> z >= 40 ? SEA - 1 : LAND;
		Shoreline.Choice<List<P>> e = choose(shoal, List.of());
		assertNull(e.shore());
		assertEquals(e.candidates(), e.noSeabed());
	}

	@Test
	void diagonalCoast() {
		Shoreline.Seabed f = (x, z) -> x + z >= 60 ? DEPTH : LAND;
		Shoreline.Shore s = choose(f, List.of()).shore();
		onTheShore(f, s);
		assertTrue(s.sea() == Direction.SOUTH || s.sea() == Direction.EAST, s.toString());
	}

	@Test
	void searchesInsideOutAndStopsWhenFound() {
		List<int[]> n = Shoreline.knots(5);
		assertEquals(81, n.size());
		assertEquals(0, n.get(0)[0]);
		assertEquals(0, n.get(0)[1]);
		for (int i = 1; i < n.size(); i++) {
			int a = n.get(i - 1)[0] * n.get(i - 1)[0] + n.get(i - 1)[1] * n.get(i - 1)[1];
			assertTrue(a <= n.get(i)[0] * n.get(i)[0] + n.get(i)[1] * n.get(i)[1]);
		}
		// with the shore close, the whole grid is not checked
		Shoreline.Choice<List<P>> near = choose(seaToTheSouth(24), List.of());
		Shoreline.Choice<List<P>> far = choose(seaToTheSouth(76), List.of());
		assertNotNull(near.shore());
		assertNotNull(far.shore());
		assertTrue(near.queries() < far.queries(), near.queries() + " < " + far.queries());
	}

	@Test
	void refineWithStep2() {
		Shoreline.Shore s = Shoreline.refine(seaToTheSouth(40), SEA, 0, 32, LAND, Direction.SOUTH);
		assertEquals(new Shoreline.Shore(0, 38, LAND, Direction.SOUTH), s);
		Shoreline.Shore n = Shoreline.refine((x, z) -> z <= -40 ? DEPTH : LAND, SEA, 16, -32, LAND, Direction.NORTH);
		assertEquals(new Shoreline.Shore(16, -38, LAND, Direction.NORTH), n);
	}
}
