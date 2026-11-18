package io.github.albertosa23.heraldia.command;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import io.github.albertosa23.heraldia.command.Revision.Mark;
import io.github.albertosa23.heraldia.command.Revision.Stop;
import io.github.albertosa23.heraldia.command.Revision.Type;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/** Ruta de /heraldia review (lógica pura): orden de las paradas, navegación, marcas, fichero y resumen en Markdown. */
class RevisionTest {
	@TempDir
	Path dir;

	static final UUID OWNER = UUID.fromString("00000000-0000-0000-0000-00000000a1b0"), OTHER_PLAYER = UUID.randomUUID();

	static final List<String> STRUCTURES = List.of("unicas/torre_mago", "unicas/atlantida", "unicas/castillo",
			"medianas/posada/llanura", "medianas/ermita/bosque", "medianas/ermita/taiga",
			"minas/grande/roca/a", "minas/pequena/roca/a", "minas/mediana/arena/b",
			"costa/naufragio/fria/b", "costa/faro/templada/a", "costa/faro/nevada/b",
			"bosque_lenadores", "llanuras_castellana_grande", "taiga_pinar", "aldeas_sin_estilo");

	static Map<String, String> styles() {
		Map<String, String> m = new LinkedHashMap<>();      // en el orden del esquema: llanuras, bosque, taiga
		m.put("llanuras_castellana", "llanuras");
		m.put("llanuras_gallega", "llanuras");
		m.put("bosque_lenadores", "bosque");
		m.put("taiga_pinar", "taiga");
		m.put("pantano_palafitos", "pantano");             // sin estructura registrada: no hay parada
		return m;
	}

	static List<Stop> route() {
		return Revision.route(STRUCTURES, styles(), p -> true, true, true);
	}

	@Test
	void routeOrder() {
		assertEquals(List.of("aldea/llanuras", "aldea/bosque", "aldea/taiga",
						"unica/atlantida", "unica/castillo", "unica/torre_mago",
						"mediana/ermita", "mediana/posada",
						"mina/pequena", "mina/mediana", "mina/grande",
						"costa/faro", "costa/naufragio",
						"arena", "camino"),
				route().stream().map(Stop::id).toList());
		Stop a = route().getFirst();
		assertEquals(Type.VILLAGE, a.type());
		assertEquals("llanuras", a.sub());
		assertEquals(Type.ROAD, route().getLast().type());
		assertEquals("", route().getLast().sub());
		// determinista: el orden de entrada no cambia nada
		List<String> al = new java.util.ArrayList<>(STRUCTURES);
		java.util.Collections.reverse(al);
		assertEquals(route(), Revision.route(al, styles(), p -> true, true, true));
	}

	@Test
	void noArenaNoRoadsAndDisabledOut() {
		List<Stop> r = Revision.route(STRUCTURES, styles(), p -> !p.id().equals("unica/castillo") && p.type() != Type.MINE
				&& !p.id().equals("costa/faro"), false, false);
		assertEquals(List.of("aldea/llanuras", "aldea/bosque", "aldea/taiga", "unica/atlantida", "unica/torre_mago",
				"mediana/ermita", "mediana/posada", "costa/naufragio"), r.stream().map(Stop::id).toList());
		assertTrue(Revision.route(List.of(), Map.of(), p -> true, false, false).isEmpty());
	}

	@Test
	void navigation() {
		List<Stop> r = route();
		assertEquals(1, Revision.next(r, 0));
		assertEquals(r.size(), Revision.next(r, r.size() - 1), "tras la última: terminada");
		assertEquals(r.size(), Revision.next(r, r.size()));
		assertEquals(0, Revision.previous(r, 0));
		assertEquals(r.size() - 1, Revision.previous(r, r.size()), "desde el final vuelve a la última");
		assertEquals(r.size() - 1, Revision.previous(r, r.size() + 5), "fuera de rango: como desde el final");
		assertEquals(4, Revision.index(r, "unica/castillo"));
		assertEquals(-1, Revision.index(r, "unica/no_existe"));
	}

	@Test
	void marksAndTally() {
		List<Stop> r = route();
		Revision.Ledger reg = new Revision.Ledger();
		reg.markStop(OWNER, "Steve", "aldea/llanuras", Mark.REVIEWED, "", 1000);
		reg.markStop(OWNER, "Steve", "unica/castillo", Mark.PROBLEM, "  escalera  sin\nterminar ", 2000);
		reg.markStop(OWNER, "Steve", "mina/grande", Mark.SKIPPED, "", 3000);
		reg.markStop(OWNER, "Steve", "aldea/llanuras", Mark.PROBLEM, "farol flotando", 4000);   // sustituye
		Revision.Progress p = reg.players().get(OWNER);
		assertEquals("escalera  sin terminar", p.note("unica/castillo").note(), "sin saltos de línea ni espacios al borde");
		assertEquals(Mark.PROBLEM, p.note("aldea/llanuras").mark());
		assertEquals(new Revision.Tally(0, 2, 1, r.size() - 3), Revision.tally(r, p));
		assertEquals(new Revision.Tally(0, 0, 0, r.size()), Revision.tally(r, null));
		assertEquals(256, Revision.clean("x".repeat(1000)).length());
		assertEquals("", Revision.clean(null));
		reg.reset(OWNER);
		assertNull(reg.players().get(OWNER));
	}

	@Test
	void fileRoundTrip() throws IOException {
		Revision.Ledger reg = new Revision.Ledger();
		reg.markStop(OWNER, "Steve", "unica/castillo", Mark.PROBLEM, "puerta | sin salida", 1_700_000_000_000L);
		reg.of(OWNER, "Steve").actual = 5;
		reg.markStop(OTHER_PLAYER, "Vecino", "arena", Mark.REVIEWED, "", 5);
		Path f = dir.resolve(Revision.FILE);
		Revision.write(f, Revision.json(reg));
		assertFalse(Files.exists(dir.resolve(Revision.FILE + ".tmp")));
		Revision.Ledger read = Revision.read(f);
		assertEquals(reg.json(), read.json());
		assertEquals(5, read.players().get(OWNER).actual());
		assertEquals("Vecino", read.players().get(OTHER_PLAYER).name());
		assertEquals(reg.json(), reg.backup().json());
		// el orden de los jugadores y de sus marcas se conserva
		assertEquals(List.of(OWNER, OTHER_PLAYER), List.copyOf(read.players().keySet()));
	}

	@Test
	void missingOrMalformedFileDoesNotFail() throws IOException {
		assertTrue(Revision.read(dir.resolve("no_existe.json")).players().isEmpty());
		Path broken = dir.resolve("roto.json");
		Files.writeString(broken, "{ esto no es json");
		assertTrue(Revision.read(broken).players().isEmpty());
		Files.writeString(broken, "[1, 2]");
		assertTrue(Revision.read(broken).players().isEmpty());
		// un jugador mal escrito se ignora y el resto se conserva
		JsonObject o = JsonParser.parseString("{\"jugadores\": {\"no-es-uuid\": {}, \"" + OWNER + "\": {\"nombre\": \"Steve\", "
				+ "\"actual\": -3, \"paradas\": {\"arena\": {\"marca\": \"revisada\"}, \"camino\": {\"marca\": \"rara\"}}}}}").getAsJsonObject();
		Files.writeString(broken, o.toString());
		Revision.Ledger r = Revision.read(broken);
		assertEquals(1, r.players().size());
		Revision.Progress p = r.players().get(OWNER);
		assertEquals(0, p.actual(), "nunca negativa");
	}

	@Test
	void markdownSummary() {
		List<Stop> r = route();
		Revision.Ledger reg = new Revision.Ledger();
		reg.markStop(OWNER, "Steve", "aldea/bosque", Mark.REVIEWED, "bonita", 1_700_000_000_000L);
		reg.markStop(OWNER, "Steve", "unica/castillo", Mark.PROBLEM, "puerta | sin <salida>", 1_700_000_000_000L);
		reg.markStop(OWNER, "Steve", "unica/borrada", Mark.SKIPPED, "", 0);          // ya no está en la ruta
		String md = Revision.markdown(r, reg, p -> "Nombre de " + p.id(), 1_700_000_000_000L);
		assertTrue(md.startsWith("# Revisión de Heraldia\n"));
		assertTrue(md.contains("2023-11-14 22:13 (UTC)"));
		assertTrue(md.contains("## Steve"));
		assertTrue(md.contains("1 revisadas, 1 con problema, 0 saltadas, " + (r.size() - 2) + " pendientes."));
		int problem = md.indexOf("`unica/castillo`"), reviewed = md.indexOf("`aldea/bosque`"), pending = md.indexOf("`aldea/llanuras`");
		assertTrue(problem > 0 && problem < reviewed && problem < pending, "primero los problemas");
		assertTrue(md.contains("puerta \\| sin &lt;salida>"), "la tabla no se rompe");
		assertTrue(md.contains("**problema**"));
		assertTrue(md.contains("(fuera de la ruta) | `unica/borrada`"));
		assertEquals(r.size() + 1, md.lines().filter(l -> l.startsWith("| ") && l.contains("`")).count());
		assertTrue(Revision.markdown(r, new Revision.Ledger(), Stop::id, 0).contains("Nadie ha marcado"));
	}
}
