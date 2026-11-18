package io.github.albertosa23.heraldia.treasure;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Optional;
import java.util.Random;
import java.util.Set;
import java.util.UUID;
import org.junit.jupiter.api.Test;

/** La elección de la cadena: determinista, con tipos válidos, dentro del radio, sin repetir y prefiriendo lo generado. */
class PlannerTest {
	static final Planner.Biomes BIOMES = (x, z) -> x < 0 ? "minecraft:desert" : "minecraft:plains";

	/** Un mundo de mentira: medianas y minas repartidas al azar (con su semilla) en ±5000 bloques. */
	record World(List<Planner.Candidate> all) implements Planner.Finder {
		static World rng(long seed, int n) {
			Random r = new Random(seed);
			List<Planner.Candidate> l = new ArrayList<>();
			for (int i = 0; i < n; i++) {
				Destination.Type t = r.nextBoolean() ? Destination.Type.MEDIUM : Destination.Type.MINE;
				l.add(new Planner.Candidate(t, "heraldia:" + t.id() + "/" + i, r.nextInt(10000) - 5000, r.nextInt(10000) - 5000,
						r.nextInt(3) > 0));
			}
			return new World(l);
		}

		@Override
		public List<Planner.Candidate> search(Destination.Type type, int x, int z, int radius) {
			List<Planner.Candidate> out = new ArrayList<>();
			for (Planner.Candidate c : all) {   // devuelve de más (otro tipo, fuera del radio): el planificador filtra
				if (Planner.dist(c.x() - x, c.z() - z) <= 4L * radius * radius) {
					out.add(c);
				}
			}
			return out;
		}
	}

	@Test
	void sameSeedSameChain() {
		World m = World.rng(7, 400);
		for (long s = 0; s < 50; s++) {
			assertEquals(Planner.plan(s, 100, 200, 1500, m, BIOMES), Planner.plan(s, 100, 200, 1500, m, BIOMES));
		}
	}

	@Test
	void candidateOrderDoesNotMatter() {
		World m = World.rng(11, 300);
		List<Planner.Candidate> reversed = new ArrayList<>(m.all());
		java.util.Collections.reverse(reversed);
		World inverse = new World(reversed);
		for (long s = 0; s < 30; s++) {
			assertEquals(Planner.plan(s, 0, 0, 1500, m, BIOMES), Planner.plan(s, 0, 0, 1500, inverse, BIOMES));
		}
	}

	@Test
	void differentSeedsGiveDifferentChains() {
		World m = World.rng(3, 600);
		Set<List<Destination>> distinct = new HashSet<>();
		for (long s = 0; s < 40; s++) {
			Planner.plan(s, 0, 0, 1500, m, BIOMES).ifPresent(distinct::add);
		}
		assertTrue(distinct.size() > 20, "casi todas distintas: " + distinct.size());
	}

	@Test
	void typesRadiusAndNoRepeats() {
		for (long world = 0; world < 20; world++) {
			World m = World.rng(world, 500);
			for (long s = 0; s < 20; s++) {
				int radius = 600 + (int) (s * 50);
				Optional<List<Destination>> o = Planner.plan(s, 0, 0, radius, m, BIOMES);
				if (o.isEmpty()) {
					continue;
				}
				List<Destination> d = o.get();
				assertTrue(d.size() == 2 || d.size() == 3, d.toString());
				assertEquals(Destination.Type.TREASURE, d.getLast().type());
				assertTrue(d.subList(0, d.size() - 1).stream().allMatch(x -> x.type() != Destination.Type.TREASURE));
				int px = 0, pz = 0;
				for (int i = 0; i < d.size() - 1; i++) {
					Destination x = d.get(i);
					long dist = x.distanceSq(px, pz);
					assertTrue(dist <= (long) radius * radius && dist >= (long) Planner.MIN_DISTANCE * Planner.MIN_DISTANCE,
							"marca " + i + " a " + Math.sqrt(dist) + " de la anterior (radio " + radius + ")");
					assertTrue(m.all().stream().anyMatch(c -> c.x() == x.x() && c.z() == x.z() && c.type() == x.type()
							&& c.structure().equals(x.structure())), "estructura real: " + x);
					px = x.x();
					pz = x.z();
				}
				for (int i = 0; i < d.size(); i++) {
					for (int j = i + 1; j < d.size() - 1; j++) {
						assertTrue(d.get(i).distanceSq(d.get(j).x(), d.get(j).z()) >= (long) Planner.MIN_DISTANCE * Planner.MIN_DISTANCE);
					}
				}
				long t = d.getLast().distanceSq(px, pz);
				assertTrue(t >= (long) (Planner.TREASURE_MIN - 1) * (Planner.TREASURE_MIN - 1)
						&& t <= (long) (Planner.TREASURE_MAX + 1) * (Planner.TREASURE_MAX + 1), "tesoro a " + Math.sqrt(t));
			}
		}
	}

	@Test
	void mediumThenMineThenTreasure() {
		World m = new World(List.of(
				new Planner.Candidate(Destination.Type.MEDIUM, "heraldia:medianas/posada/a", 500, 0, true),
				new Planner.Candidate(Destination.Type.MINE, "heraldia:minas/pequena/a/a", 900, 0, true)));
		List<Destination> d = Planner.plan(1, 0, 0, 1500, m, BIOMES).orElseThrow();
		assertEquals(List.of(Destination.Type.MEDIUM, Destination.Type.MINE, Destination.Type.TREASURE), d.stream().map(Destination::type).toList());
		assertEquals("minecraft:plains", d.getFirst().biome());
	}

	@Test
	void noMineAnotherMediumAndNoMediumAMine() {
		World onlyMediums = new World(List.of(
				new Planner.Candidate(Destination.Type.MEDIUM, "heraldia:medianas/posada/a", 500, 0, true),
				new Planner.Candidate(Destination.Type.MEDIUM, "heraldia:medianas/ermita/a", 900, 0, false)));
		assertEquals(List.of(Destination.Type.MEDIUM, Destination.Type.MEDIUM, Destination.Type.TREASURE),
				Planner.plan(1, 0, 0, 1500, onlyMediums, BIOMES).orElseThrow().stream().map(Destination::type).toList());
		World onlyOneMine = new World(List.of(new Planner.Candidate(Destination.Type.MINE, "heraldia:minas/grande/a/a", -400, 0, true)));
		List<Destination> d = Planner.plan(1, 0, 0, 1500, onlyOneMine, BIOMES).orElseThrow();
		assertEquals(List.of(Destination.Type.MINE, Destination.Type.TREASURE), d.stream().map(Destination::type).toList());
		assertEquals("minecraft:desert", d.getFirst().biome());
	}

	@Test
	void noStructuresNoChain() {
		assertTrue(Planner.plan(1, 0, 0, 1500, new World(List.of()), BIOMES).isEmpty());
		World far = new World(List.of(new Planner.Candidate(Destination.Type.MEDIUM, "heraldia:medianas/a", 3000, 0, true)));
		assertTrue(Planner.plan(1, 0, 0, 1500, far, BIOMES).isEmpty(), "fuera del radio");
		World near = new World(List.of(new Planner.Candidate(Destination.Type.MEDIUM, "heraldia:medianas/a", 50, 0, true)));
		assertTrue(Planner.plan(1, 0, 0, 1500, near, BIOMES).isEmpty(), "demasiado cerca del origen");
	}

	@Test
	void prefersGenerated() {
		List<Planner.Candidate> l = new ArrayList<>();
		for (int i = 0; i < 6; i++) {   // previstas más cerca, generadas más lejos
			l.add(new Planner.Candidate(Destination.Type.MEDIUM, "heraldia:medianas/prevista" + i, 150 + i * 20, 0, false));
		}
		for (int i = 0; i < 3; i++) {
			l.add(new Planner.Candidate(Destination.Type.MEDIUM, "heraldia:medianas/generada" + i, -800 - i * 20, 0, true));
		}
		World m = new World(l);
		for (long s = 0; s < 30; s++) {
			assertTrue(Planner.plan(s, 0, 0, 1500, m, BIOMES).orElseThrow().getFirst().generated());
		}
	}

	@Test
	void drawsAmongTheNearest() {
		List<Planner.Candidate> l = new ArrayList<>();
		for (int i = 0; i < 10; i++) {
			l.add(new Planner.Candidate(Destination.Type.MEDIUM, "heraldia:medianas/" + i, 200 + i * 100, 0, true));
		}
		World m = new World(l);
		Set<Integer> firsts = new HashSet<>();
		for (long s = 0; s < 60; s++) {
			firsts.add(Planner.plan(s, 0, 0, 1500, m, BIOMES).orElseThrow().getFirst().x());
		}
		assertEquals(Set.of(200, 300, 400), firsts, "solo las " + Planner.ELIGIBLE + " más cercanas, y todas salen");
	}

	@Test
	void seedPerWorldPlayerAndNumber() {
		UUID a = UUID.fromString("00000000-0000-0000-0000-000000000001"), b = UUID.fromString("00000000-0000-0000-0000-000000000002");
		assertEquals(Planner.seed(5, a, 0), Planner.seed(5, a, 0));
		assertNotEquals(Planner.seed(5, a, 0), Planner.seed(5, a, 1));
		assertNotEquals(Planner.seed(5, a, 0), Planner.seed(5, b, 0));
		assertNotEquals(Planner.seed(5, a, 0), Planner.seed(6, a, 0));
		Set<Long> s = new HashSet<>();
		for (int n = 0; n < 1000; n++) {
			s.add(Planner.seed(42, a, n));
		}
		assertEquals(1000, s.size());
	}

	@Test
	void movingTreasureIsDeterministicAndNear() {
		Chain c = ChainTest.chain().advance().advance();
		Destination t1 = Planner.moveTreasure(c, BIOMES);
		assertEquals(t1, Planner.moveTreasure(c, BIOMES));
		long d = t1.distanceSq(ChainTest.TREASURE.x(), ChainTest.TREASURE.z());
		assertTrue(d >= 31 * 31 && d <= 65 * 65, "a " + Math.sqrt(d));
		Chain moved = c.withTreasure(t1);
		assertNotEquals(t1, Planner.moveTreasure(moved, BIOMES), "el segundo intento va a otro sitio");
		assertFalse(moved.completed());
	}
}
