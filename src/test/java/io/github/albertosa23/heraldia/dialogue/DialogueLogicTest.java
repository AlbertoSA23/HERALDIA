package io.github.albertosa23.heraldia.dialogue;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonParser;
import com.mojang.serialization.JsonOps;
import io.github.albertosa23.heraldia.quests.Reputation;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.Set;
import java.util.UUID;
import org.junit.jupiter.api.Test;

/** The villager conversations' pure logic (P9a): lines and their fallback, the choice, the context, the wayfarers and the memory. */
class DialogueLogicTest {
	private static Map<String, Map<String, String>> file(String... poolIdText) {
		Map<String, Map<String, String>> out = new LinkedHashMap<>();
		for (int i = 0; i < poolIdText.length; i += 3) {
			out.computeIfAbsent(poolIdText[i], k -> new LinkedHashMap<>()).put(poolIdText[i + 1], poolIdText[i + 2]);
		}
		return out;
	}

	private static Lines lines(String pool, int n) {
		String[] a = new String[n * 3];
		for (int i = 0; i < n; i++) {
			a[i * 3] = pool;
			a[i * 3 + 1] = String.valueOf(i + 1);
			a[i * 3 + 2] = "line " + (i + 1);
		}
		return Lines.resolve(file(a), Map.of(), Map.of());
	}

	// --- Lines ---

	@Test
	void missingLinesFallBackToEnglishThenSpanish() {
		var es = file("general", "1", "hola", "general", "2", "adiós", "farewell", "1", "vale");
		var en = file("general", "1", "hello", "general", "2", "bye");
		var fr = file("general", "1", "bonjour", "extra", "9", "jamais");
		Lines l = Lines.resolve(es, en, fr);
		assertEquals(List.of("bonjour", "bye"), l.pool("general").stream().map(Lines.Line::text).toList());
		assertEquals("vale", l.pool("farewell").getFirst().text(), "neither English nor French: the Spanish");
		assertTrue(l.pool("extra").isEmpty(), "a pool the Spanish does not have does not exist");
		assertEquals(3, l.size());
		assertEquals("general.2", l.pool("general").get(1).key());
	}

	@Test
	void blankTextIsMissing() {
		Lines l = Lines.resolve(file("general", "1", "hola"), file("general", "1", "  "), Map.of());
		assertEquals("hola", l.pool("general").getFirst().text());
	}

	@Test
	void parseIgnoresWhatIsNotALine() {
		var o = JsonParser.parseString("{\"general\": {\"1\": \"a\", \"2\": {\"x\": 1}}, \"raro\": 5}").getAsJsonObject();
		assertEquals(Map.of("general", Map.of("1", "a")), Lines.parse(o));
	}

	// --- Selector ---

	@Test
	void neverRepeatsARecentLineWhileThereAreOthers() {
		Lines l = lines("general", 4);
		List<String> recent = List.of("general.1", "general.2", "general.3");
		for (int seed = 0; seed < 50; seed++) {
			assertEquals("general.4", Selector.one(l, "general", recent, new Random(seed)).key());
		}
	}

	@Test
	void allHeardGivesTheOldest() {
		Lines l = lines("general", 3);
		assertEquals("general.2", Selector.one(l, "general", List.of("general.2", "general.3", "general.1"), new Random(1)).key());
	}

	@Test
	void emptyPoolGivesNothing() {
		assertNull(Selector.one(lines("general", 2), "farewell", List.of(), new Random(1)));
	}

	@Test
	void weightsAndEmptyPools() {
		var es = new LinkedHashMap<String, Map<String, String>>();
		for (int i = 1; i <= 30; i++) {
			es.computeIfAbsent("profession.farmer", k -> new LinkedHashMap<>()).put(String.valueOf(i), "f" + i);
			es.computeIfAbsent("general", k -> new LinkedHashMap<>()).put(String.valueOf(i), "g" + i);
		}
		Lines l = Lines.resolve(es, Map.of(), Map.of());
		Context c = new Context("farmer", "taiga", "night", "clear", Reputation.Tier.UNKNOWN);   // family, time... have no lines
		Map<String, Integer> n = new HashMap<>();
		Random r = new Random(7);
		for (int i = 0; i < 5200; i++) {
			n.merge(Selector.body(l, c.pools(), List.of(), r).pool(), 1, Integer::sum);
		}
		assertEquals(Set.of("profession.farmer", "general"), n.keySet(), "only pools with lines");
		double share = n.get("profession.farmer") / 5200.0;     // 40 / (40 + 12)
		assertTrue(Math.abs(share - 40.0 / 52) < 0.03, "profession share " + share);
	}

	@Test
	void aConversationVaries() {
		Lines l = lines("general", 30);
		List<String> heard = new ArrayList<>();
		Memory.Player m = Memory.Player.EMPTY;
		Random r = new Random(3);
		for (int i = 0; i < 24; i++) {
			Lines.Line x = Selector.one(l, "general", m.recent(), r);
			heard.add(x.key());
			m = m.heard(x.key());
		}
		assertEquals(24, new HashSet<>(heard).size(), "24 lines in a row, none repeated");
	}

	// --- Context ---

	@Test
	void momentsOfTheDay() {
		assertEquals("morning", Context.moment(0));
		assertEquals("morning", Context.moment(5999));
		assertEquals("afternoon", Context.moment(6000));
		assertEquals("evening", Context.moment(12000));
		assertEquals("night", Context.moment(14000));
		assertEquals("night", Context.moment(23999));
		assertEquals("morning", Context.moment(24000 * 5 + 10));
		assertEquals("night", Context.moment(-1), "a clock moved back with /time");
	}

	@Test
	void weather() {
		assertEquals("clear", Context.weather(false, false, false));
		assertEquals("clear", Context.weather(false, true, false), "thunder without rain here (a desert) is no storm");
		assertEquals("rain", Context.weather(true, false, false));
		assertEquals("snow", Context.weather(true, false, true));
		assertEquals("thunder", Context.weather(true, true, true));
	}

	@Test
	void poolsOfAContext() {
		Context c = new Context("librarian", "desierto", "evening", "rain", Reputation.Tier.FRIEND);
		assertEquals(List.of("profession.librarian", "family.desierto", "time.evening", "weather.rain", "reputation.amigo", "general"),
				c.pools().stream().map(Context.Weighted::pool).toList());
		assertEquals("greeting.amigo", c.greeting());
		int clear = new Context("librarian", "desierto", "evening", "clear", Reputation.Tier.FRIEND).pools().get(3).weight();
		assertTrue(c.pools().get(3).weight() > clear, "bad weather is talked about more");
	}

	// --- Hints ---

	@Test
	void aboutOneInTenIsAWayfarer() {
		Random r = new Random(11);
		int n = 0, total = 20000;
		for (int i = 0; i < total; i++) {
			if (Hints.wayfarer(new UUID(r.nextLong(), r.nextLong()), 10)) {
				n++;
			}
		}
		assertTrue(Math.abs(n / (double) total - 0.10) < 0.01, "share " + n / (double) total);
		UUID u = new UUID(1, 2);
		assertFalse(Hints.wayfarer(u, 0));
		assertTrue(Hints.wayfarer(u, 100));
		assertEquals(Hints.wayfarer(u, 10), Hints.wayfarer(new UUID(1, 2), 10), "the same villager, always the same");
	}

	@Test
	void trust() {
		assertFalse(Hints.trusts(true, 19, 20));
		assertTrue(Hints.trusts(true, 20, 20));
		assertTrue(Hints.trusts(false, -100, 20), "without reputation, anyone");
	}

	@Test
	void aWayfarerKnowsOneOfTheNearest() {
		List<Hints.Place> places = new ArrayList<>();
		for (int i = 0; i < 20; i++) {
			places.add(new Hints.Place(i % 2 == 0 ? "medium" : "mine", "p" + i, i * 100, 0, 2000 - i * 100));
		}
		assertNull(Hints.choose(new UUID(3, 4), List.of()));
		Set<String> known = new HashSet<>();
		Random r = new Random(5);
		for (int i = 0; i < 500; i++) {
			UUID u = new UUID(r.nextLong(), r.nextLong());
			Hints.Place p = Hints.choose(u, places);
			assertTrue(p.distance() <= 2000 - 14 * 100, "one of the 6 nearest: " + p);
			assertEquals(p, Hints.choose(u, new ArrayList<>(places.reversed())), "the order of the search does not matter");
			known.add(p.id());
		}
		assertEquals(Hints.NEAREST, known.size(), "different wayfarers know different places");
	}

	// --- Memory ---

	@Test
	void villagerRests() {
		Memory.Villager m = Memory.Villager.EMPTY;
		assertFalse(m.resting(100, 1200), "never talked");
		m = m.talks(1000);
		assertTrue(m.resting(1000, 1200));
		assertTrue(m.resting(2199, 1200));
		assertEquals(1, m.left(2199, 1200));
		assertFalse(m.resting(2200, 1200));
		assertFalse(m.resting(1500, 0), "no wait");
		assertFalse(m.resting(500, 1200), "a clock behind the last talk (another world) does not lock it");
		assertTrue(m.tellsHint().hintTold());
		assertTrue(m.tellsHint().talks(5000).hintTold(), "the hint, once in its life");
	}

	@Test
	void playerRemembersTheLast() {
		Memory.Player m = Memory.Player.EMPTY;
		for (int i = 0; i < 30; i++) {
			m = m.heard("general." + i);
		}
		assertEquals(Memory.Player.RECENT, m.recent().size());
		assertEquals("general.6", m.recent().getFirst());
		m = m.heard("general.10");
		assertEquals("general.10", m.recent().getLast(), "heard again: the newest");
		assertEquals(Memory.Player.RECENT, m.recent().size());
	}

	@Test
	void memoryCodecs() {
		Memory.Villager v = new Memory.Villager(1234, true);
		var json = Memory.Villager.CODEC.encodeStart(JsonOps.INSTANCE, v).getOrThrow();
		assertEquals("{\"ultima_charla\":1234,\"pista_contada\":true}", json.toString());
		assertEquals(v, Memory.Villager.CODEC.parse(JsonOps.INSTANCE, json).getOrThrow());
		assertEquals(Memory.Villager.EMPTY, Memory.Villager.CODEC.parse(JsonOps.INSTANCE, JsonParser.parseString("{}")).getOrThrow());
		Memory.Player p = Memory.Player.EMPTY.heard("a.1").heard("b.2");
		assertEquals(p, Memory.Player.CODEC.parse(JsonOps.INSTANCE, Memory.Player.CODEC.encodeStart(JsonOps.INSTANCE, p).getOrThrow()).getOrThrow());
	}

	// --- Gesture ---

	@Test
	void whenAClickTalks() {
		Gesture.Click yes = new Gesture.Click(true, true, false, false, true, false, false, false, false, false);
		assertTrue(Gesture.mayTalk(yes));
		assertFalse(Gesture.mayTalk(new Gesture.Click(false, true, false, false, true, false, false, false, false, false)), "system off");
		assertFalse(Gesture.mayTalk(new Gesture.Click(true, false, false, false, true, false, false, false, false, false)), "off hand");
		assertFalse(Gesture.mayTalk(new Gesture.Click(true, true, true, false, true, false, false, false, false, false)), "sneaking: trades");
		assertFalse(Gesture.mayTalk(new Gesture.Click(true, true, false, true, true, false, false, false, false, false)), "spectator");
		assertFalse(Gesture.mayTalk(new Gesture.Click(true, true, false, false, false, false, false, false, false, false)), "vanilla villager");
		assertFalse(Gesture.mayTalk(new Gesture.Click(true, true, false, false, true, true, false, false, false, false)), "the bailiff");
		assertFalse(Gesture.mayTalk(new Gesture.Click(true, true, false, false, true, false, true, false, false, false)), "a baby");
		assertFalse(Gesture.mayTalk(new Gesture.Click(true, true, false, false, true, false, false, true, false, false)), "asleep");
		assertFalse(Gesture.mayTalk(new Gesture.Click(true, true, false, false, true, false, false, false, true, false)), "trading");
		assertFalse(Gesture.mayTalk(new Gesture.Click(true, true, false, false, true, false, false, false, false, true)), "a name tag");
	}

	// --- the generated files ---

	@Test
	void generatedLinesAreReadable() throws IOException {
		Path dir = Path.of(System.getProperty("heraldia.generated"), "heraldia/dialogos");
		var es = Lines.parse(JsonParser.parseString(Files.readString(dir.resolve("es_es.json"), StandardCharsets.UTF_8)).getAsJsonObject());
		var en = Lines.parse(JsonParser.parseString(Files.readString(dir.resolve("en_us.json"), StandardCharsets.UTF_8)).getAsJsonObject());
		Lines l = Lines.resolve(es, en, en);
		for (String pool : List.of("general", "rumor", "busy", "farewell", "hint.unique", "hint.medium", "hint.mine", "hint.withheld",
				"hint.told", "hint.nothing", "greeting.desconocido", "greeting.conocido", "greeting.amigo", "greeting.heroe")) {
			assertTrue(l.has(pool), "always something to say in " + pool);
		}
		for (Lines.Line x : l.pool("hint.unique")) {
			assertTrue(x.text().contains("%1$s") && x.text().contains("%2$s") && x.text().contains("%3$s"), x.key());
		}
		assertNotEquals(es.get("general").get("1"), l.pool("general").getFirst().text(), "English text, not the Spanish");
		assertNotNull(Lines.of("es_es"));
	}
}
