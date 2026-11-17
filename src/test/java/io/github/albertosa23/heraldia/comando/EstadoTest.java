package io.github.albertosa23.heraldia.comando;

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

/** /heraldia estado (lógica pura): logros de los ficheros de los jugadores, recuento por tipo y paginación. */
class EstadoTest {
	@TempDir
	Path dir;

	static final String FICHERO = """
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
	void leeElFicheroDeLogros() {
		Estado.Logros l = new Estado.Logros();
		l.sumarFichero(JsonParser.parseString(FICHERO).getAsJsonObject());
		assertEquals(1, l.jugadores());
		assertTrue(l.hecho("heraldia:unicas/castillo/descubrir"));
		assertFalse(l.hecho("heraldia:unicas/castillo/guardian"));
		assertTrue(l.hecho("heraldia:aldeas/llanuras"));
		assertFalse(l.hecho("minecraft:story/root"), "solo los de Heraldia");
		assertTrue(l.criterio("heraldia:medianas/todas", "posada"));
		assertTrue(l.criterio("heraldia:medianas/todas", "ermita"));
		assertFalse(l.criterio("heraldia:medianas/todas", "campamento"));
		assertFalse(l.criterio("heraldia:no/existe", "x"));
	}

	@Test
	void sumaVariosJugadores() {
		Estado.Logros l = new Estado.Logros();
		l.sumar("heraldia:minas/pequena", true, List.of("pequena"));
		l.jugador();
		l.sumar("heraldia:minas/grande", false, List.of());
		l.sumar("minecraft:x", true, List.of("y"));
		l.jugador();
		assertEquals(2, l.jugadores());
		assertTrue(l.hecho("heraldia:minas/pequena"));
		assertFalse(l.hecho("heraldia:minas/grande"));
		assertFalse(l.hecho("minecraft:x"));
	}

	@Test
	void leerFicherosSaltaLosConectadosYLosRotos() throws IOException {
		UUID conectado = UUID.randomUUID(), fuera = UUID.randomUUID();
		Files.writeString(dir.resolve(conectado + ".json"), FICHERO);
		Files.writeString(dir.resolve(fuera + ".json"), "{\"heraldia:minas/pequena\": {\"criteria\": {\"pequena\": \"x\"}, \"done\": true}}");
		Files.writeString(dir.resolve("otro.json"), FICHERO);            // no es un uuid
		Files.writeString(dir.resolve(UUID.randomUUID() + ".json"), "{roto");
		Files.writeString(dir.resolve("notas.txt"), FICHERO);
		Estado.Logros l = new Estado.Logros();
		EstadoCommand.leerFicheros(dir, Set.of(conectado), l);
		assertEquals(1, l.jugadores());
		assertTrue(l.hecho("heraldia:minas/pequena"));
		assertFalse(l.hecho("heraldia:unicas/castillo/descubrir"), "el conectado se cuenta de memoria, no de su fichero");
		Estado.Logros vacio = new Estado.Logros();
		EstadoCommand.leerFicheros(dir.resolve("no_existe"), Set.of(), vacio);
		assertEquals(0, vacio.jugadores());
	}

	@Test
	void cuentaPorTipo() {
		Estado.Cuenta c = Estado.contar(List.of("castillo", "faro", "mansion"), s -> !s.equals("faro"));
		assertEquals(new Estado.Cuenta(2, 3, List.of("faro")), c);
		assertEquals(new Estado.Cuenta(0, 0, List.of()), Estado.contar(List.of(), s -> true));
	}

	@Test
	void paginacion() {
		List<Integer> l = IntStream.rangeClosed(1, 19).boxed().toList();
		assertEquals(3, Estado.paginas(19, 8));
		assertEquals(1, Estado.paginas(0, 8));
		assertEquals(1, Estado.paginas(8, 8));
		assertEquals(List.of(1, 2, 3, 4, 5, 6, 7, 8), Estado.pagina(l, 1, 8));
		assertEquals(List.of(17, 18, 19), Estado.pagina(l, 3, 8));
		assertEquals(List.of(17, 18, 19), Estado.pagina(l, 99, 8), "se acota a la última");
		assertEquals(List.of(1, 2, 3, 4, 5, 6, 7, 8), Estado.pagina(l, -2, 8));
		assertEquals(List.of(), Estado.pagina(List.of(), 1, 8));
	}
}
