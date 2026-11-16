package io.github.albertosa23.heraldia.comando;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonElement;
import com.google.gson.JsonParser;
import com.mojang.serialization.JsonOps;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Stream;
import net.minecraft.SharedConstants;
import net.minecraft.core.RegistryAccess;
import net.minecraft.core.component.DataComponents;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.ComponentSerialization;
import net.minecraft.network.chat.contents.PlainTextContents;
import net.minecraft.network.chat.contents.TranslatableContents;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.component.WrittenBookContent;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

/**
 * Guía del Heraldo con los datos generados (heraldia/guia.json y los idiomas del .jar) y las únicas reales: paginación,
 * límites del libro vanilla, que un cliente sin el mod lo lee (todo traducible lleva respaldo y el texto que ve es el
 * del idioma pedido), el diario con 0, algunas y todas las únicas descubiertas y la regla de «ya entregada».
 * Que cada página cabe en 14 líneas lo comprueba el generador (tools/gen/tests/test_guia.py) con nombresPorPagina y
 * pistasPorPagina; aquí, que el Java respeta esas cuentas.
 */
class GuiaTest {
	private static final Path GEN = Path.of(System.getProperty("heraldia.generated", "build/generated/heraldia"));
	private static List<String> ids;
	private static Map<String, String> es, en;

	@BeforeAll
	static void bootstrap() throws IOException {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
		if (!Items.WRITTEN_BOOK.builtInRegistryHolder().areComponentsBound()) {
			Items.WRITTEN_BOOK.builtInRegistryHolder().bindComponents(DataComponents.COMMON_ITEM_COMPONENTS);
		}
		try (Stream<Path> s = Files.list(GEN.resolve("data/heraldia/worldgen/structure/unicas"))) {
			ids = s.map(p -> p.getFileName().toString().replace(".json", "")).sorted().toList();
		}
		es = Textos.idioma("es_es");
		en = Textos.idioma("en_us");
	}

	private static List<Guia.Unica> unicas(int descubiertas) {
		List<Guia.Unica> out = new ArrayList<>();
		for (int i = 0; i < ids.size(); i++) {
			out.add(new Guia.Unica(ids.get(i), i < descubiertas));
		}
		return out;
	}

	private static int paginasEsperadas(int hechas, int faltan) {
		Guia.Datos d = Guia.DATOS;
		return d.paginas().size() + 1 + Math.ceilDiv(hechas, d.nombresPorPagina()) + Math.ceilDiv(faltan, d.pistasPorPagina());
	}

	/** Lo que ve un cliente vanilla: sin las claves del mod, cada traducible se pinta con su respaldo. */
	private static String vista(Component c) {
		return c.getString();
	}

	@Test
	void datosDelGenerador() {
		Guia.Datos d = Guia.DATOS;
		assertTrue(d.paginas().contains("bienvenida") && d.paginas().contains("atlantida") && d.paginas().contains("diario"));
		assertTrue(d.nombresPorPagina() >= 1 && d.pistasPorPagina() >= 1);
		assertEquals("heraldia_guia_libro", d.marca());
		assertTrue(ids.size() >= 20 && ids.contains("atlantida") && ids.contains("isla_corsario"), ids.toString());
	}

	@Test
	void traduccionesCompletasEnTodosLosIdiomas() throws IOException {
		List<String> claves = new ArrayList<>();
		for (String p : Guia.DATOS.paginas()) {
			claves.add("heraldia.guia.pagina." + p);
			claves.add("heraldia.guia.pagina." + p + ".titulo");
		}
		for (String k : List.of("nombre", "lore", "resumen.titulo", "resumen", "resumen.ninguna", "resumen.faltan",
				"resumen.todas", "descubiertas", "descubierta", "pistas", "pista", "entregada", "copia")) {
			claves.add("heraldia.guia." + k);
		}
		for (String sid : ids) {
			claves.add("heraldia.unicas." + sid + ".nombre");
			claves.add("heraldia.historia." + sid + ".pista");
		}
		List<Path> idiomas;
		try (Stream<Path> s = Files.list(GEN.resolve("assets/heraldia/lang"))) {
			idiomas = s.sorted().toList();
		}
		assertTrue(idiomas.size() >= 2, idiomas.toString());
		Set<String> todas = null;
		for (Path p : idiomas) {
			Map<String, String> m = new HashMap<>();
			JsonParser.parseString(Files.readString(p, StandardCharsets.UTF_8)).getAsJsonObject().entrySet()
					.forEach(e -> m.put(e.getKey(), e.getValue().getAsString()));
			for (String k : claves) {
				assertFalse(m.getOrDefault(k, "").isBlank(), p.getFileName() + " sin " + k);
			}
			Set<String> guia = Set.copyOf(m.keySet().stream().filter(k -> k.startsWith("heraldia.guia.")).toList());
			if (todas != null) {
				assertEquals(todas, guia, "claves de la guía distintas en " + p.getFileName());
			}
			todas = guia;
		}
	}

	@ParameterizedTest
	@ValueSource(ints = {0, 1, 7, -1})
	void paginacionDelDiario(int descubiertas) {
		int n = descubiertas < 0 ? ids.size() : descubiertas;
		List<Component> paginas = Guia.paginas(Guia.DATOS, es, unicas(n));
		assertEquals(paginasEsperadas(n, ids.size() - n), paginas.size());
		assertTrue(paginas.size() <= 100, "más de 100 páginas");
		int fijas = Guia.DATOS.paginas().size();
		String resumen = vista(paginas.get(fijas));
		assertTrue(resumen.startsWith("Tu diario\n\nHas descubierto " + n + " de las " + ids.size() + " "), resumen);
		// cada página de la lista lleva su título y como mucho las entradas que caben
		int nombres = 0, pistas = 0;
		for (Component c : paginas.subList(fijas + 1, paginas.size())) {
			String[] lineas = vista(c).split("\n");
			int entradas = lineas.length - 2;
			assertEquals("", lineas[1]);
			if (lineas[0].equals(es.get("heraldia.guia.descubiertas"))) {
				assertTrue(entradas >= 1 && entradas <= Guia.DATOS.nombresPorPagina(), vista(c));
				assertEquals(0, pistas, "las descubiertas van antes que las pistas");
				nombres += entradas;
			} else {
				assertEquals(es.get("heraldia.guia.pistas"), lineas[0]);
				assertTrue(entradas >= 1 && entradas <= Guia.DATOS.pistasPorPagina(), vista(c));
				pistas += entradas;
			}
		}
		assertEquals(n, nombres);
		assertEquals(ids.size() - n, pistas);
	}

	@Test
	void ningunaDescubierta() {
		List<Component> paginas = Guia.paginas(Guia.DATOS, es, unicas(0));
		String todo = String.join("\n", paginas.stream().map(GuiaTest::vista).toList());
		assertTrue(todo.contains(es.get("heraldia.guia.resumen.ninguna")));
		assertFalse(todo.contains(es.get("heraldia.guia.descubiertas") + "\n"));
		for (String sid : ids) {
			assertTrue(todo.contains(es.get("heraldia.historia." + sid + ".pista")), sid);
		}
	}

	@Test
	void algunasDescubiertas() {
		List<Guia.Unica> u = unicas(3);
		List<Component> paginas = Guia.paginas(Guia.DATOS, es, u);
		int fijas = Guia.DATOS.paginas().size();
		String resumen = vista(paginas.get(fijas));
		assertTrue(resumen.contains(String.format(es.get("heraldia.guia.resumen.faltan"), ids.size() - 3)), resumen);
		String diario = String.join("\n", paginas.subList(fijas + 1, paginas.size()).stream().map(GuiaTest::vista).toList());
		for (Guia.Unica x : u) {
			String nombre = "• " + es.get("heraldia.unicas." + x.id() + ".nombre");
			String pista = es.get("heraldia.historia." + x.id() + ".pista");
			// de las descubiertas, el nombre y no la pista; de las que faltan, la pista y nunca el nombre
			assertEquals(x.descubierta(), diario.contains(nombre + "\n") || diario.endsWith(nombre), x.id());
			assertEquals(!x.descubierta(), diario.contains(pista), x.id());
		}
		// pistas suaves: sin coordenadas (ningún número en las páginas de pistas)
		for (Component c : paginas.subList(fijas + 2, paginas.size())) {
			if (vista(c).startsWith(es.get("heraldia.guia.pistas"))) {
				assertFalse(vista(c).matches("(?s).*\\d.*"), vista(c));
			}
		}
	}

	@Test
	void todasDescubiertas() {
		List<Component> paginas = Guia.paginas(Guia.DATOS, es, unicas(ids.size()));
		String todo = String.join("\n", paginas.stream().map(GuiaTest::vista).toList());
		assertTrue(todo.contains(es.get("heraldia.guia.resumen.todas")));
		assertFalse(todo.contains(es.get("heraldia.guia.pistas") + "\n\n"));
	}

	@Test
	void descubiertasEnOrdenAlfabetico() {
		List<Component> paginas = Guia.paginas(Guia.DATOS, es, unicas(ids.size()));
		List<String> nombres = new ArrayList<>();
		for (Component c : paginas) {
			String[] l = vista(c).split("\n");
			if (l[0].equals(es.get("heraldia.guia.descubiertas"))) {
				for (int i = 2; i < l.length; i++) {
					nombres.add(l[i].substring(2));
				}
			}
		}
		assertEquals(ids.size(), nombres.size());
		java.text.Collator c = java.text.Collator.getInstance(java.util.Locale.forLanguageTag("es"));
		c.setStrength(java.text.Collator.PRIMARY);
		List<String> ordenados = new ArrayList<>(nombres);
		ordenados.sort(c);
		assertEquals(ordenados, nombres);
	}

	@Test
	void enInglesElRespaldoEsElIngles() {
		List<Component> paginas = Guia.paginas(Guia.DATOS, en, unicas(2));
		assertEquals(en.get("heraldia.guia.pagina.bienvenida.titulo") + "\n\n" + en.get("heraldia.guia.pagina.bienvenida"),
				vista(paginas.get(0)));
		String resumen = vista(paginas.get(Guia.DATOS.paginas().size()));
		assertTrue(resumen.startsWith("Your diary\n\nYou have discovered 2 of the " + ids.size()), resumen);
	}

	@Test
	void todoTraducibleLlevaRespaldoYSoloTextoVanilla() {
		for (List<Component> paginas : List.of(Guia.paginas(Guia.DATOS, es, unicas(5)), Guia.paginas(Guia.DATOS, en, unicas(0)))) {
			for (Component p : paginas) {
				revisar(p);
			}
		}
	}

	private static void revisar(Component c) {
		if (c.getContents() instanceof TranslatableContents t) {
			assertNotNull(t.getFallback(), t.getKey());
			assertFalse(t.getFallback().equals(t.getKey()), "sin texto para " + t.getKey());
			for (Object a : t.getArgs()) {
				if (a instanceof Component ac) {
					revisar(ac);
				}
			}
		} else {
			assertTrue(c.getContents() instanceof PlainTextContents, c.getContents().toString());
		}
		c.getSiblings().forEach(GuiaTest::revisar);
	}

	@Test
	void libroValidoParaUnClienteVanilla() {
		ItemStack libro = Guia.libro(Guia.DATOS, en, unicas(4), "9.9.9");
		assertTrue(libro.is(Items.WRITTEN_BOOK));
		assertTrue(Guia.esGuia(libro));
		assertFalse(Guia.esGuia(new ItemStack(Items.WRITTEN_BOOK)));
		WrittenBookContent w = libro.get(DataComponents.WRITTEN_BOOK_CONTENT);
		assertEquals("The Herald's Guide", w.title().raw());
		assertTrue(w.title().raw().length() <= WrittenBookContent.TITLE_MAX_LENGTH);
		assertEquals("Heraldia", w.author());
		assertEquals(paginasEsperadas(4, ids.size() - 4), w.pages().size());
		assertEquals("The Herald's Guide", libro.getHoverName().getString());
		assertEquals("Heraldia edition 9.9.9", libro.get(DataComponents.LORE).lines().get(0).getString());
		assertEquals("9.9.9", libro.get(DataComponents.CUSTOM_DATA).copyTag().getStringOr("heraldia_guia_libro", ""));
		// el componente del libro se codifica y se lee igual (lo que viaja al cliente y se guarda), y cada página cabe
		JsonElement json = WrittenBookContent.CODEC.encodeStart(JsonOps.INSTANCE, w).getOrThrow();
		WrittenBookContent leido = WrittenBookContent.CODEC.parse(JsonOps.INSTANCE, json).getOrThrow();
		assertEquals(json, WrittenBookContent.CODEC.encodeStart(JsonOps.INSTANCE, leido).getOrThrow());
		assertEquals(w.pages().size(), leido.pages().size());
		for (int i = 0; i < w.pages().size(); i++) {
			assertEquals(vista(w.pages().get(i).raw()), vista(leido.pages().get(i).raw()));
		}
		for (var p : w.pages()) {
			String s = ComponentSerialization.CODEC.encodeStart(JsonOps.INSTANCE, p.raw()).getOrThrow().toString();
			assertTrue(s.length() < WrittenBookContent.PAGE_LENGTH, s.length() + " caracteres");
		}
		// el objeto entero, con los registros del juego (como al guardar el inventario)
		var ops = RegistryAccess.fromRegistryOfRegistries(BuiltInRegistries.REGISTRY).createSerializationContext(JsonOps.INSTANCE);
		JsonElement item = ItemStack.CODEC.encodeStart(ops, libro).getOrThrow();
		ItemStack copia = ItemStack.CODEC.parse(ops, item).getOrThrow();
		assertEquals(item, ItemStack.CODEC.encodeStart(ops, copia).getOrThrow());
		assertTrue(Guia.esGuia(copia));
	}

	@Test
	void entregaUnaVezPorVersion() {
		assertTrue(Guia.debeEntregar(true, null, "0.2.0"), "nunca la tuvo");
		assertTrue(Guia.debeEntregar(true, "0.1.0", "0.2.0"), "actualización del mod");
		assertFalse(Guia.debeEntregar(true, "0.2.0", "0.2.0"), "ya tiene la de esta versión");
		assertFalse(Guia.debeEntregar(false, null, "0.2.0"), "opción desactivada");
		assertFalse(Guia.debeEntregar(false, "0.1.0", "0.2.0"), "opción desactivada");
	}

	@Test
	void comandoSinPermisos() {
		var guia = Guia.comando().build().getChild("guia");
		assertNotNull(guia);
		assertNotNull(guia.getCommand());
		// sin .requires: el requisito por defecto acepta cualquier fuente, también la de un jugador sin permisos
		assertTrue(guia.getRequirement().test(null));
	}

	@Test
	void idiomaDelCliente() {
		Set<String> hay = Set.of("es_es", "en_us");
		assertEquals("es_es", Textos.codigo("es_es", hay::contains));
		assertEquals("es_es", Textos.codigo("es_MX", hay::contains));
		assertEquals("es_es", Textos.codigo("es_ar", hay::contains));
		assertEquals("en_us", Textos.codigo("en_gb", hay::contains));
		assertEquals("en_us", Textos.codigo("fr_fr", hay::contains));
		assertEquals("en_us", Textos.codigo(null, hay::contains));
		assertEquals("en_us", Textos.codigo("", hay::contains));
		assertEquals("Guía del Heraldo", Textos.idioma("es_mx").get("heraldia.guia.nombre"));
		assertEquals("The Herald's Guide", Textos.idioma("de_de").get("heraldia.guia.nombre"));
		assertEquals("The Herald's Guide", Textos.idioma("../../x").get("heraldia.guia.nombre"));
	}
}
