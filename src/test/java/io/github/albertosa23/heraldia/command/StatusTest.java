package io.github.albertosa23.heraldia.command;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonParser;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Set;
import java.util.UUID;
import java.util.stream.IntStream;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/** /heraldia status (lógica pura): logros de los ficheros de los jugadores, recuento por tipo y paginación. */
class StatusTest {
	@TempDir
	Path dir;

	static final String FILE = """
			{
			  "heraldia:unicas/castillo/descubrir": {"criteria": {"descubrir": "2026-11-10 10:00:00 +0000"}, "done": true},
			  "heraldia:unicas/castillo/guardian": {"criteria": {}, "done": false},
			  "heraldia:medianas/todas": {"criteria": {"posada": "2026-11-10 10:00:00 +0000", "ermita": "x"}, "done": false},
			  "heraldia:aldeas/llanuras": {"criteria": {"llanuras": "x"}, "done": true},
			  "minecraft:story/root": {"criteria": {"crafting_table": "x"}, "done": true},
			  "heraldia:raro": 7,
			  "DataVersion": 5023
			}""";

	@Test
	void readsAdvancementsFile() {
		State.Achievements l = new State.Achievements();
		l.addFile(JsonParser.parseString(FILE).getAsJsonObject());
		assertEquals(1, l.players());
		assertTrue(l.done("heraldia:unicas/castillo/descubrir"));
		assertFalse(l.done("heraldia:unicas/castillo/guardian"));
		assertTrue(l.done("heraldia:aldeas/llanuras"));
		assertFalse(l.done("minecraft:story/root"), "solo los de Heraldia");
		assertTrue(l.criterion("heraldia:medianas/todas", "posada"));
		assertTrue(l.criterion("heraldia:medianas/todas", "ermita"));
		assertFalse(l.criterion("heraldia:medianas/todas", "campamento"));
		assertFalse(l.criterion("heraldia:no/existe", "x"));
	}

	@Test
	void sumsSeveralPlayers() {
		State.Achievements l = new State.Achievements();
		l.add("heraldia:minas/pequena", true, List.of("pequena"));
		l.player();
		l.add("heraldia:minas/grande", false, List.of());
		l.add("minecraft:x", true, List.of("y"));
		l.player();
		assertEquals(2, l.players());
		assertTrue(l.done("heraldia:minas/pequena"));
		assertFalse(l.done("heraldia:minas/grande"));
		assertFalse(l.done("minecraft:x"));
	}

	@Test
	void readingFilesSkipsOnlineAndBroken() throws IOException {
		UUID online = UUID.randomUUID(), outside = UUID.randomUUID();
		Files.writeString(dir.resolve(online + ".json"), FILE);
		Files.writeString(dir.resolve(outside + ".json"), "{\"heraldia:minas/pequena\": {\"criteria\": {\"pequena\": \"x\"}, \"done\": true}}");
		Files.writeString(dir.resolve("otro.json"), FILE);            // no es un uuid
		Files.writeString(dir.resolve(UUID.randomUUID() + ".json"), "{roto");
		Files.writeString(dir.resolve("notas.txt"), FILE);
		State.Achievements l = new State.Achievements();
		StatusCommand.readFiles(dir, Set.of(online), l);
		assertEquals(1, l.players());
		assertTrue(l.done("heraldia:minas/pequena"));
		assertFalse(l.done("heraldia:unicas/castillo/descubrir"), "el conectado se cuenta de memoria, no de su fichero");
		State.Achievements empty = new State.Achievements();
		StatusCommand.readFiles(dir.resolve("no_existe"), Set.of(), empty);
		assertEquals(0, empty.players());
	}

	@Test
	void countByType() {
		State.Tally c = State.count(List.of("castillo", "faro", "mansion"), s -> !s.equals("faro"));
		assertEquals(new State.Tally(2, 3, List.of("faro")), c);
		assertEquals(new State.Tally(0, 0, List.of()), State.count(List.of(), s -> true));
	}

	@Test
	void pagination() {
		List<Integer> l = IntStream.rangeClosed(1, 19).boxed().toList();
		assertEquals(3, State.pages(19, 8));
		assertEquals(1, State.pages(0, 8));
		assertEquals(1, State.pages(8, 8));
		assertEquals(List.of(1, 2, 3, 4, 5, 6, 7, 8), State.pagina(l, 1, 8));
		assertEquals(List.of(17, 18, 19), State.pagina(l, 3, 8));
		assertEquals(List.of(17, 18, 19), State.pagina(l, 99, 8), "se acota a la última");
		assertEquals(List.of(1, 2, 3, 4, 5, 6, 7, 8), State.pagina(l, -2, 8));
		assertEquals(List.of(), State.pagina(List.of(), 1, 8));
	}
}
