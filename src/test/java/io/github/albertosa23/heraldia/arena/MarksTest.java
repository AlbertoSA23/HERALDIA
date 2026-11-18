package io.github.albertosa23.heraldia.arena;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.Test;

/** Times, mode advancements, how each mark is shown and the mode ids (T41). */
class MarksTest {
	private static final UUID A = UUID.randomUUID();

	@Test
	void times() {
		assertEquals("0:00", Marks.time(0));
		assertEquals("0:00", Marks.time(19));
		assertEquals("0:01", Marks.time(20));
		assertEquals("4:32", Marks.time((4 * 60 + 32) * 20));
		assertEquals("59:59", Marks.time(3599 * 20));
		assertEquals("1:00:00", Marks.time(3600 * 20));
		assertEquals("2:03:04", Marks.time((2 * 3600 + 3 * 60 + 4) * 20L));
		assertEquals("-", Marks.time(-1));
	}

	@Test
	void timeTrialAdvancements() {
		long fast = Marks.TIME_TRIAL_FAST_TICKS, slow = fast + 1;
		assertEquals(List.of("arena/contrarreloj", "arena/contrarreloj_rapido"), Marks.advancements(Mode.TIME_TRIAL, 10, fast, 10));
		assertEquals(List.of("arena/contrarreloj"), Marks.advancements(Mode.TIME_TRIAL, 10, slow, 10));
		assertEquals(List.of(), Marks.advancements(Mode.TIME_TRIAL, 9, 100, 10), "sin acabar");
		assertEquals(List.of(), Marks.advancements(Mode.TIME_TRIAL, 3, 100, 3), "con menos de 10 oleadas no cuenta");
		assertEquals(List.of("arena/contrarreloj", "arena/contrarreloj_rapido"), Marks.advancements(Mode.TIME_TRIAL, 12, 100, 12));
		assertEquals(List.of(), Marks.advancements(Mode.COOP, 30, 100, 0));
	}

	@Test
	void survivalAdvancements() {
		assertEquals(List.of("arena/supervivencia_15"), Marks.advancements(Mode.SURVIVAL, 15, 1, 0));
		assertEquals(List.of(), Marks.advancements(Mode.SURVIVAL, 14, 1, 0));
		assertEquals("arena/campeon_survival", Marks.championAdvancement(Mode.SURVIVAL));
		assertEquals("arena/campeon_coop", Marks.championAdvancement(Mode.COOP));
		assertEquals("arena/campeon_timeattack", Marks.championAdvancement(Mode.TIME_TRIAL));
	}

	@Test
	void howEachMarkIsShown() {
		assertArrayEquals(new Object[] {"heraldia.arena.puntos.tiempo", "4:00", 10},
				Marks.points(Mode.TIME_TRIAL, new Season.Entry(A, "a", 10, 4800, 0, 10)));
		assertArrayEquals(new Object[] {"heraldia.arena.puntos.parcial", 7, 10},
				Marks.points(Mode.TIME_TRIAL, new Season.Entry(A, "a", 7, 4800, 0, 10)));
		assertArrayEquals(new Object[] {"heraldia.arena.puntos.oleadas", 12},
				Marks.points(Mode.SURVIVAL, new Season.Entry(A, "a", 12, 4800, 0, 0)));
		assertArrayEquals(new Object[] {"heraldia.arena.puntos.oleadas", 12},
				Marks.points(Mode.COOP, new Season.Entry(A, "a", 12, -1, 0, 0)));
	}

	@Test
	void modes() {
		assertEquals(Optional.of(Mode.TIME_TRIAL), Mode.fromId("timeattack"));
		assertEquals(Optional.of(Mode.COOP), Mode.fromId("COOP"));
		assertEquals(Optional.empty(), Mode.fromId("contrarreloj"), "el id es el del comando, en inglés");
		assertEquals(Optional.empty(), Mode.fromId(null));
		for (Mode m : Mode.values()) {
			assertTrue(m.id().matches("[a-z]+"), m.id());
			assertEquals("arena.modos." + m.key(), m.option());
			assertEquals("heraldia.arena.modo." + m.id(), m.text());
		}
		assertEquals(Match.PAUSE_TICKS, Mode.COOP.pause(), "el cooperativo, como siempre");
		assertEquals(0, Mode.SURVIVAL.pause(), "sin pausa");
		assertTrue(Mode.TIME_TRIAL.pause() < Mode.COOP.pause());
	}

	@Test
	void modeOptionsExist() throws IOException {
		String py = Files.readString(Path.of("tools/gen/opciones.py"), StandardCharsets.UTF_8);
		for (Mode m : Mode.values()) {
			assertTrue(py.contains("(\"" + m.option() + "\", True"), m.option());
		}
		for (String k : List.of("arena.modos.oleadas_contrarreloj", "arena.temporada.dia_reinicio", "arena.temporada.hora_reinicio",
				"arena.temporada.historico")) {
			assertTrue(py.contains("(\"" + k + "\""), k);
		}
		for (String d : Week.DAYS) {
			assertTrue(py.contains("\"" + d + "\""), d);
		}
	}
}
