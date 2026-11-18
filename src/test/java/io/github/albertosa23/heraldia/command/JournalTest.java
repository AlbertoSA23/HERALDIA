package io.github.albertosa23.heraldia.command;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonParser;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Pattern;
import net.minecraft.SharedConstants;
import net.minecraft.network.chat.ClickEvent;
import net.minecraft.network.chat.Component;
import net.minecraft.server.Bootstrap;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/** /heraldia journal: what counts as found or missing, the bars, the order and what the chat shows (vanilla client). */
class JournalTest {
	@BeforeAll
	static void game() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	/** A player who entered a plains village, the castle, an inn, a Nether lookout and a small mine. */
	static State.Achievements player() {
		State.Achievements a = new State.Achievements();
		a.addFile(JsonParser.parseString("""
				{
				  "heraldia:aldeas/llanuras": {"criteria": {"llanuras": "x"}, "done": true},
				  "heraldia:aldeas/todas": {"criteria": {"llanuras": "x"}, "done": false},
				  "heraldia:unicas/castillo/descubrir": {"criteria": {"descubrir": "x"}, "done": true},
				  "heraldia:unicas/cripta/descubrir": {"criteria": {"descubrir": "x"}, "done": true},
				  "heraldia:medianas/todas": {"criteria": {"posada": "x"}, "done": false},
				  "heraldia:medianas/nether": {"criteria": {"mirador_basalto": "x"}, "done": false},
				  "heraldia:minas/pequena": {"criteria": {"pequena": "x"}, "done": true},
				  "heraldia:costa/faro": {"criteria": {}, "done": false}
				}""").getAsJsonObject());
		return a;
	}

	static Journal.Candidate adv(String id, String key, String advancement, boolean enabled) {
		return new Journal.Candidate(id, key, advancement, null, enabled);
	}

	static Map<String, List<Journal.Candidate>> catalog() {
		Map<String, List<Journal.Candidate>> c = new LinkedHashMap<>();
		Journal.SECTIONS.forEach(s -> c.put(s, new ArrayList<>()));
		for (String f : List.of("llanuras", "desierto", "taiga")) {
			c.get("villages").add(adv(f, "heraldia.familia." + f, "heraldia:aldeas/" + f, !f.equals("taiga")));
		}
		// cripta: found and disabled later (still counts); catedral: disabled and not found (left out)
		for (String[] u : new String[][] {{"castillo", "1"}, {"cripta", "0"}, {"catedral", "0"}, {"palacio", "1"}}) {
			c.get("uniques").add(adv(u[0], "heraldia.unicas." + u[0] + ".nombre", "heraldia:unicas/" + u[0] + "/descubrir", u[1].equals("1")));
		}
		for (String m : List.of("posada", "ermita")) {
			c.get("mediums").add(new Journal.Candidate(m, "heraldia.medianas." + m + ".nombre", "heraldia:medianas/todas", m, true));
		}
		c.get("nether").add(new Journal.Candidate("mirador_basalto", "x", "heraldia:medianas/nether", "mirador_basalto", true));
		c.get("nether").add(adv("ciudadela_ceniza", "y", "heraldia:unicas/ciudadela_ceniza/descubrir", true));
		for (String s : Revision.SIZES) {
			c.get("mines").add(adv(s, "heraldia.minas." + s + ".nombre", "heraldia:minas/" + s, true));
		}
		c.get("coast").add(adv("faro", "heraldia.costa.faro.nombre", "heraldia:costa/faro", false));   // disabled, not found
		return c;
	}

	static Journal.Section section(List<Journal.Section> all, String id) {
		return all.stream().filter(s -> s.id().equals(id)).findFirst().orElse(null);
	}

	@Test
	void countsFoundAndMissingFromTheAdvancements() {
		List<Journal.Section> s = Journal.sections(catalog(), player());
		Journal.Section villages = section(s, "villages");
		assertEquals(1, villages.found());
		assertEquals(2, villages.total(), "a disabled family that was not found is not missing");
		Journal.Section uniques = section(s, "uniques");
		assertEquals(List.of("castillo", "cripta", "palacio"), uniques.items().stream().map(Journal.Item::id).toList());
		assertEquals(2, uniques.found(), "found and then disabled still counts");
		assertEquals(List.of("palacio"), uniques.missing().stream().map(Journal.Item::id).toList());
		assertEquals(1, section(s, "mediums").found(), "a criterion of medianas/todas");
		assertEquals(1, section(s, "nether").found(), "a criterion of medianas/nether");
		assertEquals(2, section(s, "nether").total());
		assertEquals(1, section(s, "mines").found());
		assertEquals(List.of("pequena", "mediana", "grande"), section(s, "mines").items().stream().map(Journal.Item::id).toList());
		assertNull(section(s, "coast"), "a section with nothing to find is left out");
		assertNull(section(s, "end"));
		assertEquals(List.of("villages", "uniques", "mediums", "mines", "nether"), s.stream().map(Journal.Section::id).toList());
	}

	@Test
	void barFillsOnlyWhenComplete() {
		assertEquals(0, Journal.filled(0, 21, 10));
		assertEquals(1, Journal.filled(1, 21, 10), "something found shows at least one cell");
		assertEquals(9, Journal.filled(20, 21, 10), "almost everything is not a full bar");
		assertEquals(10, Journal.filled(21, 21, 10));
		assertEquals(5, Journal.filled(6, 12, 10));
		assertEquals(0, Journal.filled(0, 0, 10));
		String bar = Journal.bar(3, 12).getString();
		assertEquals(Journal.BAR, bar.length());
		assertEquals("■■□□□□□□□□", bar);
	}

	@Test
	void sortsByNameInThePlayersLanguageExceptMines() {
		Map<String, String> l = Map.of("a", "Zeta", "b", "alfa", "c", "Ábaco");
		List<Journal.Section> in = List.of(
				new Journal.Section("uniques", List.of(new Journal.Item("1", "a", false), new Journal.Item("2", "b", true),
						new Journal.Item("3", "c", false))),
				new Journal.Section("mines", List.of(new Journal.Item("pequena", "a", true), new Journal.Item("grande", "c", false))));
		List<Journal.Section> out = Journal.sort(in, l);
		assertEquals(List.of("3", "2", "1"), out.get(0).items().stream().map(Journal.Item::id).toList(), "collator: accents ignored");
		assertEquals(List.of("pequena", "grande"), out.get(1).items().stream().map(Journal.Item::id).toList());
	}

	@Test
	void overviewInChatWithTotalAndClickableSections() {
		Map<String, String> en = Texts.language("en_us");
		List<Journal.Section> s = Journal.sort(Journal.sections(catalog(), player()), en);
		List<Component> out = Journal.overview(en, "Steve", s);
		String text = String.join("\n", out.stream().map(Component::getString).toList());
		assertTrue(text.startsWith("Steve's journal"), text);
		assertTrue(text.contains("6 of 12 discoveries in total"), text);
		assertTrue(text.contains("1/2 Village families"), text);
		assertTrue(text.contains("2/3 Unique structures"), text);
		assertTrue(text.contains("1/3 Mine entrances (by size)"), text);
		assertTrue(text.contains("/heraldia guide"), "unique structures missing: points to the Guide's clues");
		for (Journal.Section x : s) {
			Component line = out.stream().filter(c -> c.getString().contains(en.get(Journal.KEY + "seccion." + x.id()))).findFirst().orElseThrow();
			ClickEvent click = line.getStyle().getClickEvent();
			assertNotNull(click, x.id());
			assertEquals("/heraldia journal " + x.id(), ((ClickEvent.RunCommand) click).command());
			assertNotNull(line.getStyle().getHoverEvent(), x.id());
		}
		assertFalse(Pattern.compile("-?\\d{3,}").matcher(text).find(), "no coordinates: " + text);
	}

	@Test
	void detailListsFoundAndMissingByName() {
		Map<String, String> en = Texts.language("en_us");
		List<Journal.Section> s = Journal.sort(Journal.sections(catalog(), player()), en);
		String mines = String.join("\n", Journal.detail(en, s, "mines").stream().map(Component::getString).toList());
		assertTrue(mines.contains("Found (1): " + en.get("heraldia.minas.pequena.nombre")), mines);
		assertTrue(mines.contains("Still to find (2): " + en.get("heraldia.minas.mediana.nombre") + ", "
				+ en.get("heraldia.minas.grande.nombre")), mines);
		assertTrue(mines.contains("[« Journal]"), mines);
		String coast = String.join("\n", Journal.detail(en, s, "coast").stream().map(Component::getString).toList());
		assertTrue(coast.contains(en.get(Journal.KEY + "vacio")), coast);
		Journal.Section done = new Journal.Section("mines", List.of(new Journal.Item("pequena", "heraldia.minas.pequena.nombre", true)));
		String all = String.join("\n", Journal.detail(en, List.of(done), "mines").stream().map(Component::getString).toList());
		assertTrue(all.contains(en.get(Journal.KEY + "todas")), all);
		String complete = String.join("\n", Journal.overview(en, "Alex", List.of(done)).stream().map(Component::getString).toList());
		assertTrue(complete.contains(en.get(Journal.KEY + "completo")), complete);
		assertTrue(complete.contains("✔"), complete);
	}

	static Journal.Chronicle chronicle(boolean lastOneToo, boolean herald) {
		var p = io.github.albertosa23.heraldia.chronicle.Ending.Progress.of(List.of(
				new io.github.albertosa23.heraldia.chronicle.Ending.Guardian("castillo", false, true, true),
				new io.github.albertosa23.heraldia.chronicle.Ending.Guardian("palacio", false, true, lastOneToo),
				new io.github.albertosa23.heraldia.chronicle.Ending.Guardian("ciudadela_ceniza", true, true, false)));
		return Journal.Chronicle.of(p, herald);
	}

	@Test
	void chronicleLineBeforeTheFooterAndTitleForAHerald() {
		Map<String, String> en = Texts.language("en_us");
		List<Journal.Section> s = Journal.sort(Journal.sections(catalog(), player()), en);
		List<Component> out = Journal.overview(en, "Steve", s, chronicle(false, false));
		String text = String.join("\n", out.stream().map(Component::getString).toList());
		assertTrue(text.contains("6 of 12 discoveries in total"), "the Chronicle is not one more kind in the total: " + text);
		Component line = out.stream().filter(c -> c.getString().contains("Chronicle: guardians defeated")).findFirst().orElseThrow();
		assertTrue(line.getString().contains("1/2"), line.getString());
		assertEquals("/heraldia journal chronicle", ((ClickEvent.RunCommand) line.getStyle().getClickEvent()).command());
		assertTrue(out.indexOf(line) < out.size() - 2, "before the footer and the Guide's line");
		assertFalse(text.contains("Herald of Atlantis"), text);
		String herald = String.join("\n", Journal.overview(en, "Alex", s, chronicle(true, true)).stream().map(Component::getString).toList());
		assertTrue(herald.contains("Alex, Herald of Atlantis"), herald);
		assertTrue(herald.contains("2/2 Chronicle: guardians defeated ✔"), herald);
		assertEquals(Journal.overview(en, "Steve", s).size() + 1, out.size(), "without the Chronicle, the summary as before");
	}

	@Test
	void chronicleDetailNamesDefeatedAndWatchingWithoutPlaces() {
		Map<String, String> en = Texts.language("en_us");
		String open = String.join("\n", Journal.chronicleDetail(en, chronicle(false, false).sorted(en)).stream().map(Component::getString).toList());
		assertTrue(open.contains("Defeated (1): " + en.get("heraldia.unicas.castillo.nombre")), open);
		assertTrue(open.contains("Still keeping watch (1): " + en.get("heraldia.unicas.palacio.nombre")), open);
		assertTrue(open.contains("Beyond the map (optional): 0/1"), open);
		assertTrue(open.contains(en.get("heraldia.cronica.diario.abierta")), open);
		assertFalse(open.contains("[Read the last leaf]"), "no copy before the end");
		List<Component> closed = Journal.chronicleDetail(en, chronicle(true, true).sorted(en));
		String text = String.join("\n", closed.stream().map(Component::getString).toList());
		assertTrue(text.contains(en.get("heraldia.cronica.diario.cerrada")), text);
		assertTrue(text.contains("[Read the last leaf]") && text.contains("[« Journal]"), text);
		assertFalse(Pattern.compile("-?\\d{3,}").matcher(text).find(), "no coordinates: " + text);
	}

	@Test
	void everyLanguageHasTheJournalTexts() {
		for (String code : Texts.languages()) {
			Map<String, String> l = Texts.texts(code);
			for (String k : List.of("titulo", "total", "cuenta", "ver", "faltan", "encontradas", "ninguna", "todas", "pie", "completo",
					"guia", "vacio", "volver", "en_estado")) {
				assertNotNull(l.get(Journal.KEY + k), code + " " + k);
			}
			for (String s : Journal.SECTIONS) {
				assertNotNull(l.get(Journal.KEY + "seccion." + s), code + " " + s);
			}
		}
	}
}
