package io.github.albertosa23.heraldia.roads;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonParser;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
import java.util.Random;
import org.junit.jupiter.api.Test;

/**
 * The Herald's House roads (SpawnRoadLayout): the same numbers as tools/gen/spawn_roads.py (its tests check the same
 * cases, so the two cannot drift apart) and the owner's invariants on many seeds and arena sites.
 */
class SpawnRoadLayoutTest {
	private static final SpawnRoadLayout.Params P = params();
	private static final Map<String, int[]> GATES = Map.of("north", new int[] {64, 0}, "south", new int[] {64, 127},
			"west", new int[] {0, 60}, "east", new int[] {127, 60});
	private static final SpawnRoadLayout.Box TOWN = new SpawnRoadLayout.Box(0, 0, 127, 127);

	private static SpawnRoadLayout.Params params() {
		try (var in = SpawnRoadLayoutTest.class.getResourceAsStream("/heraldia/caminos_casa.json")) {
			return SpawnRoadLayout.Params.read(JsonParser.parseReader(new InputStreamReader(in, StandardCharsets.UTF_8)).getAsJsonObject());
		} catch (java.io.IOException e) {
			throw new IllegalStateException(e);
		}
	}

	private static void near(double expected, double actual) {
		assertEquals(expected, actual, 1e-6);
	}

	@Test
	void sameNumbersAsTheGenerator() {
		List<double[]> nr = SpawnRoadLayout.normal(new int[] {64, 0}, "north", 12345, P);
		assertEquals(6, nr.size());
		near(64.5, nr.get(0)[0]);
		near(-0.5, nr.get(0)[1]);
		near(64.5, nr.get(3)[0]);
		near(-43.5, nr.get(3)[1]);
		near(63.623404223, nr.get(4)[0]);
		near(-57.508814587, nr.get(4)[1]);
		near(62.5, nr.get(5)[0]);
		near(-71.5, nr.get(5)[1]);
		assertEquals(-7, SpawnRoadLayout.lateral(-7046029254386353131L, new int[] {1000, -37}, P));
		SpawnRoadLayout.Plan plan = SpawnRoadLayout.arenaPlan(GATES, new SpawnRoadLayout.Box(36, -290, 92, -234), 987654321L,
				SpawnRoadLayout.Structures.NONE, TOWN, P);
		assertEquals("north", plan.side());
		assertFalse(plan.fromHead());
		near(69.5, plan.start()[0]);
		near(-71.5, plan.start()[1]);
		assertNotNull(plan.arena());
		assertEquals(11, plan.arena().pts().size());
		assertEquals(3, plan.arena().knots().size());
		near(65.467164748, plan.arena().pts().get(8)[0]);
		near(-205.735851666, plan.arena().pts().get(8)[1]);
		near(-232.5, plan.arena().pts().get(10)[1]);
		near(167.23663, SpawnRoadLayout.length(plan.arena().pts()));
		List<int[]> lamps = SpawnRoadLayout.lamps(nr, P);
		assertEquals(11, lamps.size());
		assertArrayEquals(new int[] {68, -5}, lamps.get(0));
		assertArrayEquals(new int[] {61, -12}, lamps.get(1));
		assertArrayEquals(new int[] {68, -19}, lamps.get(2));
		assertArrayEquals(new int[] {61, -26}, lamps.get(3));
		List<int[]> arenaLamps = SpawnRoadLayout.lamps(plan.arena().pts(), SpawnRoadLayout.joined(plan.normal(), plan.fromHead(), P), P);
		assertEquals(25, arenaLamps.size());
		assertArrayEquals(new int[] {68, -224}, arenaLamps.get(22));
		assertArrayEquals(new int[] {61, -231}, arenaLamps.get(23));
		assertArrayEquals(new int[] {77, -157}, arenaLamps.get(24));
		// the huts: rotation and origin (spawn_roads.hut_frame)
		assertArrayEquals(new int[] {3, 67, -8}, SpawnRoadLayout.hutFrame(new int[] {64, 0}, "north", 1, 8, 7, 3));
		assertArrayEquals(new int[] {1, 61, -22}, SpawnRoadLayout.hutFrame(new int[] {64, 0}, "north", -1, 16, 7, 3));
		assertArrayEquals(new int[] {1, 61, 153}, SpawnRoadLayout.hutFrame(new int[] {64, 127}, "south", 1, 26, 7, 3));
		assertArrayEquals(new int[] {2, 149, 57}, SpawnRoadLayout.hutFrame(new int[] {127, 60}, "east", -1, 16, 7, 3));
	}

	@Test
	void roadsGoAwayFromSpawnForAtLeastTheMinimum() {
		Random r = new Random(7);
		for (int i = 0; i < 300; i++) {
			long seed = r.nextLong();
			for (String side : SpawnRoadLayout.SIDES) {
				int[] g = GATES.get(side);
				List<double[]> nr = SpawnRoadLayout.normal(g, side, seed, P);
				double[] end = nr.get(nr.size() - 1);
				assertTrue(Math.hypot(end[0] - g[0] - 0.5, end[1] - g[1] - 0.5) >= P.minimum());
				assertTrue(SpawnRoadLayout.awayShare(nr, 64.5, 60.5) >= 0.9, side + " " + seed);
			}
		}
	}

	@Test
	void theArenaRoadReachesItsEntranceWithoutCrossingIt() {
		Random r = new Random(11);
		for (int i = 0; i < 300; i++) {
			long seed = r.nextLong();
			int ox = r.nextInt(97) - 48, oz = r.nextInt(97) - 48;
			double a = Math.toRadians(15 * r.nextInt(24));
			int rad = 200 + 25 * r.nextInt(5);
			int ax = (int) Math.round(rad * Math.cos(a)), az = (int) Math.round(rad * Math.sin(a));
			SpawnRoadLayout.Box arena = new SpawnRoadLayout.Box(ax - 28, az - 28, ax + 28, az + 28);
			SpawnRoadLayout.Box town = new SpawnRoadLayout.Box(ox - 64, oz - 64, ox + 63, oz + 63);
			Map<String, int[]> gates = Map.of("north", new int[] {ox, oz - 64}, "south", new int[] {ox, oz + 63},
					"west", new int[] {ox - 64, oz - 4}, "east", new int[] {ox + 63, oz - 4});
			SpawnRoadLayout.Plan plan = SpawnRoadLayout.arenaPlan(gates, arena, seed, SpawnRoadLayout.Structures.NONE, town, P);
			assertNotNull(plan.arena(), "no arena road for " + ax + " " + az);
			List<double[]> pts = plan.arena().pts();
			double[] end = pts.get(pts.size() - 1), entrance = SpawnRoadLayout.arenaPoints(arena, P)[0];
			near(entrance[0], end[0]);
			near(entrance[1], end[1]);
			assertTrue(SpawnRoadLayout.clear(pts, arena, town, SpawnRoadLayout.Structures.NONE, P)[0]);
		}
	}

	@Test
	void aStructureInTheWayIsGoneRound() {
		SpawnRoadLayout.Box arena = new SpawnRoadLayout.Box(36, -290, 92, -234);
		SpawnRoadLayout.Plan straight = SpawnRoadLayout.arenaPlan(GATES, arena, 987654321L, SpawnRoadLayout.Structures.NONE, TOWN, P);
		double[] mid = straight.arena().pts().get(straight.arena().pts().size() / 2);
		int bx = (int) Math.floor(mid[0]) >> 4, bz = (int) Math.floor(mid[1]) >> 4;
		SpawnRoadLayout.Structures village = (cx, cz) -> Math.abs(cx - bx) <= 1 && Math.abs(cz - bz) <= 1;
		SpawnRoadLayout.Plan round = SpawnRoadLayout.arenaPlan(GATES, arena, 987654321L, village, TOWN, P);
		assertTrue(round.arena().clear());
		assertTrue(round.arena().knots().size() > 3);
		assertTrue(SpawnRoadLayout.clear(round.arena().pts(), arena, TOWN, village, P)[1]);
	}
}
