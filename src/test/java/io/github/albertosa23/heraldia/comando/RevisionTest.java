package io.github.albertosa23.heraldia.comando;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import io.github.albertosa23.heraldia.comando.Revision.Marca;
import io.github.albertosa23.heraldia.comando.Revision.Parada;
import io.github.albertosa23.heraldia.comando.Revision.Tipo;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/** Ruta de /heraldia revisar (lógica pura): orden de las paradas, navegación, marcas, fichero y resumen en Markdown. */
class RevisionTest {
	@TempDir
	Path dir;

	static final UUID ALBERTO = UUID.fromString("00000000-0000-0000-0000-00000000a1b0"), OTRO = UUID.randomUUID();

	static final List<String> ESTRUCTURAS = List.of("unicas/torre_mago", "unicas/atlantida", "unicas/castillo",
			"medianas/posada/llanura", "medianas/ermita/bosque", "medianas/ermita/taiga",
			"minas/grande/roca/a", "minas/pequena/roca/a", "minas/mediana/arena/b",
			"bosque_lenadores", "llanuras_castellana_grande", "taiga_pinar", "aldeas_sin_estilo");

	static Map<String, String> estilos() {
		Map<String, String> m = new LinkedHashMap<>();      // en el orden del esquema: llanuras, bosque, taiga
		m.put("llanuras_castellana", "llanuras");
		m.put("llanuras_gallega", "llanuras");
		m.put("bosque_lenadores", "bosque");
		m.put("taiga_pinar", "taiga");
		m.put("pantano_palafitos", "pantano");             // sin estructura registrada: no hay parada
		return m;
	}

	static List<Parada> ruta() {
		return Revision.ruta(ESTRUCTURAS, estilos(), p -> true, true, true);
	}

	@Test
	void ordenDeLaRuta() {
		assertEquals(List.of("aldea/llanuras", "aldea/bosque", "aldea/taiga",
						"unica/atlantida", "unica/castillo", "unica/torre_mago",
						"mediana/ermita", "mediana/posada",
						"mina/pequena", "mina/mediana", "mina/grande",
						"arena", "camino"),
				ruta().stream().map(Parada::id).toList());
		Parada a = ruta().getFirst();
		assertEquals(Tipo.ALDEA, a.tipo());
		assertEquals("llanuras", a.sub());
		assertEquals(Tipo.CAMINO, ruta().getLast().tipo());
		assertEquals("", ruta().getLast().sub());
		// determinista: el orden de entrada no cambia nada
		List<String> al = new java.util.ArrayList<>(ESTRUCTURAS);
		java.util.Collections.reverse(al);
		assertEquals(ruta(), Revision.ruta(al, estilos(), p -> true, true, true));
	}

	@Test
	void sinArenaNiCaminosYLoDesactivadoFuera() {
		List<Parada> r = Revision.ruta(ESTRUCTURAS, estilos(), p -> !p.id().equals("unica/castillo") && p.tipo() != Tipo.MINA, false, false);
		assertEquals(List.of("aldea/llanuras", "aldea/bosque", "aldea/taiga", "unica/atlantida", "unica/torre_mago",
				"mediana/ermita", "mediana/posada"), r.stream().map(Parada::id).toList());
		assertTrue(Revision.ruta(List.of(), Map.of(), p -> true, false, false).isEmpty());
	}

	@Test
	void navegacion() {
		List<Parada> r = ruta();
		assertEquals(1, Revision.siguiente(r, 0));
		assertEquals(r.size(), Revision.siguiente(r, r.size() - 1), "tras la última: terminada");
		assertEquals(r.size(), Revision.siguiente(r, r.size()));
		assertEquals(0, Revision.anterior(r, 0));
		assertEquals(r.size() - 1, Revision.anterior(r, r.size()), "desde el final vuelve a la última");
		assertEquals(r.size() - 1, Revision.anterior(r, r.size() + 5), "fuera de rango: como desde el final");
		assertEquals(4, Revision.indice(r, "unica/castillo"));
		assertEquals(-1, Revision.indice(r, "unica/no_existe"));
	}

	@Test
	void marcasYCuenta() {
		List<Parada> r = ruta();
		Revision.Registro reg = new Revision.Registro();
		reg.marcar(ALBERTO, "Alberto", "aldea/llanuras", Marca.REVISADA, "", 1000);
		reg.marcar(ALBERTO, "Alberto", "unica/castillo", Marca.PROBLEMA, "  escalera  sin\nterminar ", 2000);
		reg.marcar(ALBERTO, "Alberto", "mina/grande", Marca.SALTADA, "", 3000);
		reg.marcar(ALBERTO, "Alberto", "aldea/llanuras", Marca.PROBLEMA, "farol flotando", 4000);   // sustituye
		Revision.Progreso p = reg.jugadores().get(ALBERTO);
		assertEquals("escalera  sin terminar", p.nota("unica/castillo").nota(), "sin saltos de línea ni espacios al borde");
		assertEquals(Marca.PROBLEMA, p.nota("aldea/llanuras").marca());
		assertEquals(new Revision.Cuenta(0, 2, 1, r.size() - 3), Revision.cuenta(r, p));
		assertEquals(new Revision.Cuenta(0, 0, 0, r.size()), Revision.cuenta(r, null));
		assertEquals(256, Revision.limpiar("x".repeat(1000)).length());
		assertEquals("", Revision.limpiar(null));
		reg.reiniciar(ALBERTO);
		assertNull(reg.jugadores().get(ALBERTO));
	}

	@Test
	void ficheroIdaYVuelta() throws IOException {
		Revision.Registro reg = new Revision.Registro();
		reg.marcar(ALBERTO, "Alberto", "unica/castillo", Marca.PROBLEMA, "puerta | sin salida", 1_700_000_000_000L);
		reg.de(ALBERTO, "Alberto").actual = 5;
		reg.marcar(OTRO, "Vecino", "arena", Marca.REVISADA, "", 5);
		Path f = dir.resolve(Revision.FICHERO);
		Revision.escribir(f, Revision.json(reg));
		assertFalse(Files.exists(dir.resolve(Revision.FICHERO + ".tmp")));
		Revision.Registro leido = Revision.leer(f);
		assertEquals(reg.json(), leido.json());
		assertEquals(5, leido.jugadores().get(ALBERTO).actual());
		assertEquals("Vecino", leido.jugadores().get(OTRO).nombre());
		assertEquals(reg.json(), reg.copia().json());
		// el orden de los jugadores y de sus marcas se conserva
		assertEquals(List.of(ALBERTO, OTRO), List.copyOf(leido.jugadores().keySet()));
	}

	@Test
	void ficheroAusenteOMalEscritoNoFalla() throws IOException {
		assertTrue(Revision.leer(dir.resolve("no_existe.json")).jugadores().isEmpty());
		Path roto = dir.resolve("roto.json");
		Files.writeString(roto, "{ esto no es json");
		assertTrue(Revision.leer(roto).jugadores().isEmpty());
		Files.writeString(roto, "[1, 2]");
		assertTrue(Revision.leer(roto).jugadores().isEmpty());
		// un jugador mal escrito se ignora y el resto se conserva
		JsonObject o = JsonParser.parseString("{\"jugadores\": {\"no-es-uuid\": {}, \"" + ALBERTO + "\": {\"nombre\": \"Alberto\", "
				+ "\"actual\": -3, \"paradas\": {\"arena\": {\"marca\": \"revisada\"}, \"camino\": {\"marca\": \"rara\"}}}}}").getAsJsonObject();
		Files.writeString(roto, o.toString());
		Revision.Registro r = Revision.leer(roto);
		assertEquals(1, r.jugadores().size());
		Revision.Progreso p = r.jugadores().get(ALBERTO);
		assertEquals(0, p.actual(), "nunca negativa");
	}

	@Test
	void resumenEnMarkdown() {
		List<Parada> r = ruta();
		Revision.Registro reg = new Revision.Registro();
		reg.marcar(ALBERTO, "Alberto", "aldea/bosque", Marca.REVISADA, "bonita", 1_700_000_000_000L);
		reg.marcar(ALBERTO, "Alberto", "unica/castillo", Marca.PROBLEMA, "puerta | sin <salida>", 1_700_000_000_000L);
		reg.marcar(ALBERTO, "Alberto", "unica/borrada", Marca.SALTADA, "", 0);          // ya no está en la ruta
		String md = Revision.markdown(r, reg, p -> "Nombre de " + p.id(), 1_700_000_000_000L);
		assertTrue(md.startsWith("# Revisión de Heraldia\n"));
		assertTrue(md.contains("2023-11-14 22:13 (UTC)"));
		assertTrue(md.contains("## Alberto"));
		assertTrue(md.contains("1 revisadas, 1 con problema, 0 saltadas, " + (r.size() - 2) + " pendientes."));
		int problema = md.indexOf("`unica/castillo`"), revisada = md.indexOf("`aldea/bosque`"), pendiente = md.indexOf("`aldea/llanuras`");
		assertTrue(problema > 0 && problema < revisada && problema < pendiente, "primero los problemas");
		assertTrue(md.contains("puerta \\| sin &lt;salida>"), "la tabla no se rompe");
		assertTrue(md.contains("**problema**"));
		assertTrue(md.contains("(fuera de la ruta) | `unica/borrada`"));
		assertEquals(r.size() + 1, md.lines().filter(l -> l.startsWith("| ") && l.contains("`")).count());
		assertTrue(Revision.markdown(r, new Revision.Registro(), Parada::id, 0).contains("Nadie ha marcado"));
	}
}
