package io.github.albertosa23.heraldia.chronicle;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonElement;
import com.mojang.serialization.JsonOps;
import io.github.albertosa23.heraldia.chronicle.Ending.Guardian;
import io.github.albertosa23.heraldia.chronicle.Ending.Progress;
import io.github.albertosa23.heraldia.chronicle.Ending.Step;
import io.github.albertosa23.heraldia.command.Texts;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

/** The end of the Chronicle: which guardians count, when one is defeated, what is owed and the pages of the last leaf. */
class EndingTest {
	static Guardian main(String sid, boolean enabled, boolean defeated) {
		return new Guardian(sid, false, enabled, defeated);
	}

	static Guardian beyond(String sid, boolean defeated) {
		return new Guardian(sid, true, true, defeated);
	}

	@Test
	void countsTheEnabledAndTheDefeatedOnes() {
		Progress p = Progress.of(List.of(main("castillo", true, true), main("palacio", true, false),
				main("catedral", false, false), main("cripta", false, true), beyond("ciudadela_ceniza", false)));
		assertEquals(List.of("castillo", "palacio", "cripta"), p.main().stream().map(Guardian::sid).toList(),
				"a disabled unique not defeated is not owed; one defeated and disabled later still counts");
		assertEquals(2, p.defeated());
		assertFalse(p.complete());
		assertEquals(1, p.beyond().size());
		assertFalse(Progress.of(List.of()).complete(), "nothing to defeat is not an end");
		assertFalse(Progress.of(List.of(beyond("sagrario_vacio", true))).complete(), "the Nether and End alone never close it");
	}

	@Test
	void mainWorldOnlyCloseIt() {
		Progress p = Progress.of(List.of(main("castillo", true, true), main("atlantida", true, true),
				beyond("ciudadela_ceniza", false), beyond("sagrario_vacio", false)));
		assertTrue(p.complete(), "the player who never leaves the main world can close the Chronicle");
		assertFalse(p.beyondComplete());
		Progress all = Progress.of(List.of(main("castillo", true, true), beyond("ciudadela_ceniza", true), beyond("sagrario_vacio", true)));
		assertTrue(all.beyondComplete());
		assertFalse(Progress.of(List.of(main("castillo", true, false), beyond("ciudadela_ceniza", true))).beyondComplete(),
				"beyond only counts once the main world is closed");
		assertFalse(Progress.of(List.of(main("castillo", true, true))).beyondComplete(), "with nothing beyond, no beyond");
	}

	@Test
	void stepsAreGivenOnce() {
		Progress open = Progress.of(List.of(main("castillo", true, false)));
		Progress closed = Progress.of(List.of(main("castillo", true, true), beyond("ciudadela_ceniza", false)));
		Progress further = Progress.of(List.of(main("castillo", true, true), beyond("ciudadela_ceniza", true)));
		assertEquals(Step.NONE, Ending.step(true, open, false, false));
		assertEquals(Step.FINAL, Ending.step(true, closed, false, false));
		assertEquals(Step.NONE, Ending.step(true, closed, true, false), "already a Herald: nothing again");
		assertEquals(Step.BOTH, Ending.step(true, further, false, false));
		assertEquals(Step.BEYOND, Ending.step(true, further, true, false));
		assertEquals(Step.NONE, Ending.step(true, further, true, true));
		assertEquals(Step.NONE, Ending.step(false, further, false, false), "option off: nothing");
	}

	@Test
	void defeatedByAdvancementTakingPartOrOncePerWorld() {
		assertTrue(Ending.defeated(true, false, false, false), "the guardian advancement: also kills from before this version");
		assertTrue(Ending.defeated(false, true, false, false), "took part: was nearby when it fell");
		assertTrue(Ending.defeated(false, false, true, true), "Atlantis fallen to anyone counts for everybody");
		assertFalse(Ending.defeated(false, false, false, true), "a guardian with many copies in the world: each player beats one");
		assertFalse(Ending.defeated(false, false, true, false));
	}

	@Test
	void fallenRecordIsIdempotentAndSaved() {
		Ending.Fallen f = Ending.Fallen.EMPTY.with("castillo");
		assertSame(f, f.with("castillo"));
		assertEquals(List.of("castillo", "palacio"), f.with("palacio").sids());
		JsonElement json = Ending.Fallen.CODEC.encodeStart(JsonOps.INSTANCE, f.with("palacio")).getOrThrow();
		assertEquals("{\"guardianes\":[\"castillo\",\"palacio\"]}", json.toString());
		assertEquals(f.with("palacio"), Ending.Fallen.CODEC.parse(JsonOps.INSTANCE, json).getOrThrow());
		assertEquals(Ending.Fallen.EMPTY, Ending.Fallen.CODEC.parse(JsonOps.INSTANCE, com.google.gson.JsonParser.parseString("{}")).getOrThrow());
	}

	@Test
	void lastLeafPagesFromTheGenerator() {
		Ending.Data d = Ending.Data.read();
		assertEquals(List.of("juramento", "dignos", "camino", "estandarte"), d.pages());
		assertEquals("cronica/final", d.finalAdvancement());
		assertEquals("cronica/mas_alla", d.beyondAdvancement());
		Progress noBeyond = Progress.of(List.of(main("castillo", true, true)));
		assertEquals(d.pages(), Ending.pages(d, noBeyond), "nothing beyond in this world: no beyond page");
		Progress pending = Progress.of(List.of(main("castillo", true, true), beyond("ciudadela_ceniza", true), beyond("sagrario_vacio", false)));
		assertEquals("coda.pendiente", Ending.pages(d, pending).getLast());
		Progress done = Progress.of(List.of(main("castillo", true, true), beyond("ciudadela_ceniza", true)));
		assertEquals("coda.hecho", Ending.pages(d, done).getLast());
		assertTrue(d.titled().contains("juramento") && d.titled().contains("coda.hecho"));
		for (String code : Texts.languages()) {
			Map<String, String> l = Texts.texts(code);
			for (String id : Ending.pages(d, done)) {
				assertNotNull(l.get(ChronicleEnding.KEY + "pagina." + id), code + " " + id);
			}
			assertNotNull(l.get(ChronicleEnding.KEY + "pagina.coda.pendiente"), code);
			for (String k : List.of("libro", "titulo", "estandarte", "estandarte.alzado", "diario.linea", "diario.cerrada")) {
				assertNotNull(l.get(ChronicleEnding.KEY + k), code + " " + k);
			}
		}
	}
}
