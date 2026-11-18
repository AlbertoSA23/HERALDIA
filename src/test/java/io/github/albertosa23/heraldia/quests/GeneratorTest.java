package io.github.albertosa23.heraldia.quests;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonObject;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.TreeSet;
import net.minecraft.SharedConstants;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.Identifier;
import net.minecraft.server.Bootstrap;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/** El tablón de cada aldea: determinista por aldea y periodo, con 2-4 encargos de los tipos que haya alrededor. */
class GeneratorTest {
	static final long SEED = 123456789L;
	static final List<Generator.Objective> GUARDIANS = List.of(new Generator.Objective("castillo", 900, -300, 950),
			new Generator.Objective("catedral", -1800, 400, 1850), new Generator.Objective("piramide", 3000, 2000, 3600));
	static final List<Generator.Objective> PLACES = List.of(new Generator.Objective("heraldia:medianas/posada/llanuras", 300, 200, 360),
			new Generator.Objective("heraldia:minas/pequena/montes", -700, 900, 1140));
	static final List<Generator.Objective> NEIGHBORS = List.of(new Generator.Objective("Torre del Roble", 1500, 0, 1500));
	static final Generator.Candidates ALL = new Generator.Candidates("llanuras", GUARDIANS, PLACES, NEIGHBORS, true);

	@BeforeAll
	static void game() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	@Test
	void sameBoardWithSameData() {
		for (long p = 0; p < 20; p++) {
			assertEquals(Generator.board(SEED, 10, -20, p, ALL), Generator.board(SEED, 10, -20, p, ALL));
		}
	}

	@Test
	void changesWithPeriodVillageAndSeed() {
		Set<List<Quest>> distinct = new HashSet<>();
		for (long p = 0; p < 20; p++) {
			distinct.add(strip(Generator.board(SEED, 10, -20, p, ALL)));
		}
		assertTrue(distinct.size() > 10, "el tablón casi no rota: " + distinct.size());
		assertNotEquals(strip(Generator.board(SEED, 10, -20, 3, ALL)), strip(Generator.board(SEED, 11, -20, 3, ALL)));
		assertNotEquals(strip(Generator.board(SEED, 10, -20, 3, ALL)), strip(Generator.board(SEED + 1, 10, -20, 3, ALL)));
	}

	/** Sin aldea ni periodo (para comparar el contenido). */
	private static List<Quest> strip(List<Quest> t) {
		return t.stream().map(e -> new Quest(0, 0, 0, e.gap(), e.type(), e.target(), e.amount(), e.x(), e.z(), e.emeralds(),
				e.experience())).toList();
	}

	@Test
	void twoToFourWithFirstOfBring() {
		int[] sizes = new int[Generator.MAX + 1];
		for (long p = 0; p < 300; p++) {
			List<Quest> t = Generator.board(SEED, 3, 4, p, ALL);
			assertTrue(t.size() >= Generator.MIN && t.size() <= Generator.MAX, "tamaño " + t.size());
			sizes[t.size()]++;
			assertEquals(Type.BRING, t.get(0).type());
			assertEquals(Type.GUARDIAN, t.get(1).type(), "con guardianes cerca, el segundo es de guardián");
			for (int i = 0; i < t.size(); i++) {
				Quest e = t.get(i);
				assertEquals(i, e.gap());
				assertEquals(3, e.villageX());
				assertEquals(4, e.villageZ());
				assertEquals(p, e.period());
				assertEquals("3.4." + p + "." + i, e.id());
				assertEquals("3,4", e.village());
			}
			assertEquals(t.size(), t.stream().map(Quest::id).distinct().count());
		}
		for (int n = Generator.MIN; n <= Generator.MAX; n++) {
			assertTrue(sizes[n] > 30, "casi nunca salen " + n + " encargos");
		}
	}

	@Test
	void allNearbyTypesAppear() {
		Set<Type> seen = new TreeSet<>();
		for (long p = 0; p < 200; p++) {
			Generator.board(SEED, 0, 0, p, ALL).forEach(e -> seen.add(e.type()));
		}
		assertEquals(Set.of(Type.values()), seen);
	}

	@Test
	void onlyWhatExists() {
		Generator.Candidates alone = Generator.Candidates.alone("desierto");
		Generator.Candidates places = new Generator.Candidates("desierto", List.of(), PLACES, List.of(), false);
		for (long p = 0; p < 200; p++) {
			List<Quest> t = Generator.board(SEED, 7, 7, p, alone);
			assertTrue(t.stream().allMatch(e -> e.type() == Type.BRING), "sin nada alrededor, solo traer: " + t);
			List<Quest> l = Generator.board(SEED, 7, 7, p, places);
			assertEquals(Type.EXPLORE, l.get(1).type(), "sin guardianes, el segundo es explorar");
			assertTrue(l.stream().noneMatch(e -> e.type() == Type.GUARDIAN || e.type() == Type.ARENA || e.type() == Type.JOURNEY));
		}
	}

	@Test
	void objectivesWithoutRepeatsAndWithTheirSite() {
		for (long p = 0; p < 300; p++) {
			List<Quest> t = Generator.board(SEED, -5, 9, p, ALL);
			List<String> items = t.stream().filter(e -> e.type() == Type.BRING).map(Quest::target).toList();
			assertEquals(items.size(), new HashSet<>(items).size(), "objeto repetido: " + t);
			List<String> guardians = t.stream().filter(e -> e.type() == Type.GUARDIAN).map(Quest::target).toList();
			assertEquals(guardians.size(), new HashSet<>(guardians).size(), "guardián repetido: " + t);
			for (Quest e : t) {
				switch (e.type()) {
					case GUARDIAN -> assertTrue(GUARDIANS.stream().anyMatch(o -> o.id().equals(e.target()) && o.x() == e.x() && o.z() == e.z()));
					case EXPLORE -> assertTrue(PLACES.stream().anyMatch(o -> o.id().equals(e.target()) && o.x() == e.x() && o.z() == e.z()));
					case JOURNEY -> assertEquals("Torre del Roble", e.target());
					case ARENA -> assertTrue(List.of(3, 5, 8).contains(e.amount()));
					case BRING -> assertTrue(Generator.items("llanuras").stream().anyMatch(o -> o.id().equals(e.target())
							&& e.amount() >= o.min() && e.amount() <= o.max()));
				}
				assertEquals(e.withPlace(), e.type() == Type.GUARDIAN || e.type() == Type.EXPLORE || e.type() == Type.JOURNEY);
			}
		}
	}

	@Test
	void farGuardianIsTheFarthest() {
		boolean seen = false;
		for (long p = 0; p < 200; p++) {
			List<Quest> t = Generator.board(SEED, 1, 1, p, ALL);
			Quest first = t.get(1);
			assertTrue(List.of("castillo", "catedral").contains(first.target()), "el primero, de los dos más cercanos");
			List<Quest> others = t.subList(2, t.size()).stream().filter(e -> e.type() == Type.GUARDIAN).toList();
			for (Quest e : others) {
				seen = true;
				assertEquals("piramide", e.target());
				assertEquals(Generator.EM_FAR_GUARDIAN, e.emeralds(), "lejos paga más");
			}
		}
		assertTrue(seen);
	}

	@Test
	void modestRewards() {
		for (String fam : families()) {
			Generator.Candidates c = new Generator.Candidates(fam, GUARDIANS, PLACES, NEIGHBORS, true);
			for (long p = 0; p < 100; p++) {
				for (Quest e : Generator.board(SEED, 2, 2, p, c)) {
					assertTrue(e.emeralds() >= 1 && e.emeralds() <= 12, e.toString());
					assertTrue(e.experience() > 0 && e.experience() <= 120, e.toString());
					assertTrue(e.reputation() > 0 && e.reputation() <= 30, e.toString());
				}
			}
		}
	}

	/** Las familias de aldeas del esquema (themes.FAMILIES): cada una con sus materiales del bioma. */
	static Set<String> families() {
		JsonObject styles = HeraldiaConfig.get().schema().getAsJsonObject("aldeas").getAsJsonObject("estilos");
		Set<String> out = new TreeSet<>();
		styles.entrySet().forEach(e -> out.add(e.getValue().getAsString()));
		return out;
	}

	@Test
	void eachFamilyHasItsMaterialsAndAllExist() {
		assertEquals(families(), new TreeSet<>(Generator.BIOME.keySet()));
		List<Generator.Item> all = new ArrayList<>(Generator.FOOD);
		all.addAll(Generator.ORES);
		Generator.BIOME.values().forEach(all::addAll);
		for (Generator.Item o : all) {
			assertTrue(BuiltInRegistries.ITEM.containsKey(Identifier.parse(o.id())), "no existe " + o.id());
			assertTrue(o.min() > 0 && o.min() <= o.max() && o.max() <= 64, o.toString());
			assertFalse(o.id().contains("diamond") || o.id().contains("netherite") || o.id().contains("emerald"), o.id());
		}
		for (String fam : families()) {
			List<Generator.Item> l = Generator.items(fam);
			assertTrue(l.containsAll(Generator.BIOME.get(fam)) && l.containsAll(Generator.FOOD) && l.containsAll(Generator.ORES));
		}
	}

	@Test
	void periodAndRemaining() {
		assertEquals(0, Generator.period(0, 3));
		assertEquals(0, Generator.period(3 * Generator.DAY - 1, 3));
		assertEquals(1, Generator.period(3 * Generator.DAY, 3));
		assertEquals(10, Generator.period(10 * Generator.DAY + 5, 1));
		assertEquals(0, Generator.period(5, 0), "días < 1 cuenta como 1");
		assertEquals(3 * Generator.DAY, Generator.remaining(0, 3));
		assertEquals(1, Generator.remaining(3 * Generator.DAY - 1, 3));
		assertEquals(Generator.DAY - 5, Generator.remaining(Generator.DAY + 5, 1));
		for (long t : new long[]{0, 5, 3 * Generator.DAY, 7 * Generator.DAY + 123}) {
			long p = Generator.period(t, 3);
			assertTrue(Generator.start(p, 3) <= t && t < Generator.start(p + 1, 3));
		}
	}
}
