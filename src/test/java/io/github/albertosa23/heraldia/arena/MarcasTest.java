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

/** Tiempos, logros de los modos, cómo se enseña cada marca y los ids de los modos (T41). */
class MarcasTest {
	private static final UUID A = UUID.randomUUID();

	@Test
	void tiempos() {
		assertEquals("0:00", Marcas.tiempo(0));
		assertEquals("0:00", Marcas.tiempo(19));
		assertEquals("0:01", Marcas.tiempo(20));
		assertEquals("4:32", Marcas.tiempo((4 * 60 + 32) * 20));
		assertEquals("59:59", Marcas.tiempo(3599 * 20));
		assertEquals("1:00:00", Marcas.tiempo(3600 * 20));
		assertEquals("2:03:04", Marcas.tiempo((2 * 3600 + 3 * 60 + 4) * 20L));
		assertEquals("-", Marcas.tiempo(-1));
	}

	@Test
	void logrosDelContrarreloj() {
		long rapido = Marcas.CONTRARRELOJ_RAPIDO_TICKS, lento = rapido + 1;
		assertEquals(List.of("arena/contrarreloj", "arena/contrarreloj_rapido"), Marcas.logros(Modo.CONTRARRELOJ, 10, rapido, 10));
		assertEquals(List.of("arena/contrarreloj"), Marcas.logros(Modo.CONTRARRELOJ, 10, lento, 10));
		assertEquals(List.of(), Marcas.logros(Modo.CONTRARRELOJ, 9, 100, 10), "sin acabar");
		assertEquals(List.of(), Marcas.logros(Modo.CONTRARRELOJ, 3, 100, 3), "con menos de 10 oleadas no cuenta");
		assertEquals(List.of("arena/contrarreloj", "arena/contrarreloj_rapido"), Marcas.logros(Modo.CONTRARRELOJ, 12, 100, 12));
		assertEquals(List.of(), Marcas.logros(Modo.COOPERATIVO, 30, 100, 0));
	}

	@Test
	void logrosDeLaSupervivencia() {
		assertEquals(List.of("arena/supervivencia_15"), Marcas.logros(Modo.SUPERVIVENCIA, 15, 1, 0));
		assertEquals(List.of(), Marcas.logros(Modo.SUPERVIVENCIA, 14, 1, 0));
		assertEquals("arena/campeon_survival", Marcas.logroCampeon(Modo.SUPERVIVENCIA));
		assertEquals("arena/campeon_coop", Marcas.logroCampeon(Modo.COOPERATIVO));
		assertEquals("arena/campeon_timeattack", Marcas.logroCampeon(Modo.CONTRARRELOJ));
	}

	@Test
	void comoSeEnsenaCadaMarca() {
		assertArrayEquals(new Object[] {"heraldia.arena.puntos.tiempo", "4:00", 10},
				Marcas.puntos(Modo.CONTRARRELOJ, new Temporada.Entrada(A, "a", 10, 4800, 0, 10)));
		assertArrayEquals(new Object[] {"heraldia.arena.puntos.parcial", 7, 10},
				Marcas.puntos(Modo.CONTRARRELOJ, new Temporada.Entrada(A, "a", 7, 4800, 0, 10)));
		assertArrayEquals(new Object[] {"heraldia.arena.puntos.oleadas", 12},
				Marcas.puntos(Modo.SUPERVIVENCIA, new Temporada.Entrada(A, "a", 12, 4800, 0, 0)));
		assertArrayEquals(new Object[] {"heraldia.arena.puntos.oleadas", 12},
				Marcas.puntos(Modo.COOPERATIVO, new Temporada.Entrada(A, "a", 12, -1, 0, 0)));
	}

	@Test
	void modos() {
		assertEquals(Optional.of(Modo.CONTRARRELOJ), Modo.deId("timeattack"));
		assertEquals(Optional.of(Modo.COOPERATIVO), Modo.deId("COOP"));
		assertEquals(Optional.empty(), Modo.deId("contrarreloj"), "el id es el del comando, en inglés");
		assertEquals(Optional.empty(), Modo.deId(null));
		for (Modo m : Modo.values()) {
			assertTrue(m.id().matches("[a-z]+"), m.id());
			assertEquals("arena.modos." + m.clave(), m.opcion());
			assertEquals("heraldia.arena.modo." + m.id(), m.texto());
		}
		assertEquals(Partida.PAUSA_TICKS, Modo.COOPERATIVO.pausa(), "el cooperativo, como siempre");
		assertEquals(0, Modo.SUPERVIVENCIA.pausa(), "sin pausa");
		assertTrue(Modo.CONTRARRELOJ.pausa() < Modo.COOPERATIVO.pausa());
	}

	@Test
	void lasOpcionesDeLosModosExisten() throws IOException {
		String py = Files.readString(Path.of("tools/gen/opciones.py"), StandardCharsets.UTF_8);
		for (Modo m : Modo.values()) {
			assertTrue(py.contains("(\"" + m.opcion() + "\", True"), m.opcion());
		}
		for (String k : List.of("arena.modos.oleadas_contrarreloj", "arena.temporada.dia_reinicio", "arena.temporada.hora_reinicio",
				"arena.temporada.historico")) {
			assertTrue(py.contains("(\"" + k + "\""), k);
		}
		for (String d : Semana.DIAS) {
			assertTrue(py.contains("\"" + d + "\""), d);
		}
	}
}
