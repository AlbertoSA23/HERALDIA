package io.github.albertosa23.heraldia.command;

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
class GuideTest {
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
		es = Texts.language("es_es");
		en = Texts.language("en_us");
	}

	private static List<Guide.Unique> uniques(int discovered) {
		List<Guide.Unique> out = new ArrayList<>();
		for (int i = 0; i < ids.size(); i++) {
			out.add(new Guide.Unique(ids.get(i), i < discovered));
		}
		return out;
	}

	private static int expectedPages(int done, int missing) {
		Guide.Data d = Guide.DATA;
		return d.pages().size() + 1 + Math.ceilDiv(done, d.namesPerPage()) + Math.ceilDiv(missing, d.cluesPerPage());
	}

	/** Lo que ve un cliente vanilla: sin las claves del mod, cada traducible se pinta con su respaldo. */
	private static String view(Component c) {
		return c.getString();
	}

	@Test
	void generatorData() {
		Guide.Data d = Guide.DATA;
		assertTrue(d.pages().contains("bienvenida") && d.pages().contains("atlantida") && d.pages().contains("diario"));
		assertTrue(d.namesPerPage() >= 1 && d.cluesPerPage() >= 1);
		assertEquals("heraldia_guia_libro", d.mark());
		assertTrue(ids.size() >= 20 && ids.contains("atlantida") && ids.contains("isla_corsario"), ids.toString());
	}

	@Test
	void completeTranslationsInAllLanguages() throws IOException {
		List<String> keys = new ArrayList<>();
		for (String p : Guide.DATA.pages()) {
			keys.add("heraldia.guia.pagina." + p);
			keys.add("heraldia.guia.pagina." + p + ".titulo");
		}
		for (String k : List.of("nombre", "lore", "resumen.titulo", "resumen", "resumen.ninguna", "resumen.faltan",
				"resumen.todas", "descubiertas", "descubierta", "pistas", "pista", "entregada", "copia")) {
			keys.add("heraldia.guia." + k);
		}
		for (String sid : ids) {
			keys.add("heraldia.unicas." + sid + ".nombre");
			keys.add("heraldia.historia." + sid + ".pista");
		}
		List<Path> languages;
		try (Stream<Path> s = Files.list(GEN.resolve("assets/heraldia/lang"))) {
			languages = s.sorted().toList();
		}
		assertTrue(languages.size() >= 2, languages.toString());
		Set<String> all = null;
		for (Path p : languages) {
			Map<String, String> m = new HashMap<>();
			JsonParser.parseString(Files.readString(p, StandardCharsets.UTF_8)).getAsJsonObject().entrySet()
					.forEach(e -> m.put(e.getKey(), e.getValue().getAsString()));
			for (String k : keys) {
				assertFalse(m.getOrDefault(k, "").isBlank(), p.getFileName() + " sin " + k);
			}
			Set<String> guide = Set.copyOf(m.keySet().stream().filter(k -> k.startsWith("heraldia.guia.")).toList());
			if (all != null) {
				assertEquals(all, guide, "claves de la guía distintas en " + p.getFileName());
			}
			all = guide;
		}
	}

	@ParameterizedTest
	@ValueSource(ints = {0, 1, 7, -1})
	void journalPagination(int discovered) {
		int n = discovered < 0 ? ids.size() : discovered;
		List<Component> pages = Guide.pages(Guide.DATA, es, uniques(n));
		assertEquals(expectedPages(n, ids.size() - n), pages.size());
		assertTrue(pages.size() <= 100, "más de 100 páginas");
		int fixed = Guide.DATA.pages().size();
		String summary = view(pages.get(fixed));
		assertTrue(summary.startsWith("Tu diario\n\nHas descubierto " + n + " de las " + ids.size() + " "), summary);
		// cada página de la lista lleva su título y como mucho las entradas que caben
		int names = 0, clues = 0;
		for (Component c : pages.subList(fixed + 1, pages.size())) {
			String[] lines = view(c).split("\n");
			int entries = lines.length - 2;
			assertEquals("", lines[1]);
			if (lines[0].equals(es.get("heraldia.guia.descubiertas"))) {
				assertTrue(entries >= 1 && entries <= Guide.DATA.namesPerPage(), view(c));
				assertEquals(0, clues, "las descubiertas van antes que las pistas");
				names += entries;
			} else {
				assertEquals(es.get("heraldia.guia.pistas"), lines[0]);
				assertTrue(entries >= 1 && entries <= Guide.DATA.cluesPerPage(), view(c));
				clues += entries;
			}
		}
		assertEquals(n, names);
		assertEquals(ids.size() - n, clues);
	}

	@Test
	void noneDiscovered() {
		List<Component> pages = Guide.pages(Guide.DATA, es, uniques(0));
		String everything = String.join("\n", pages.stream().map(GuideTest::view).toList());
		assertTrue(everything.contains(es.get("heraldia.guia.resumen.ninguna")));
		assertFalse(everything.contains(es.get("heraldia.guia.descubiertas") + "\n"));
		for (String sid : ids) {
			assertTrue(everything.contains(es.get("heraldia.historia." + sid + ".pista")), sid);
		}
	}

	@Test
	void someDiscovered() {
		List<Guide.Unique> u = uniques(3);
		List<Component> pages = Guide.pages(Guide.DATA, es, u);
		int fixed = Guide.DATA.pages().size();
		String summary = view(pages.get(fixed));
		assertTrue(summary.contains(String.format(es.get("heraldia.guia.resumen.faltan"), ids.size() - 3)), summary);
		String journal = String.join("\n", pages.subList(fixed + 1, pages.size()).stream().map(GuideTest::view).toList());
		for (Guide.Unique x : u) {
			String name = "• " + es.get("heraldia.unicas." + x.id() + ".nombre");
			String clue = es.get("heraldia.historia." + x.id() + ".pista");
			// de las descubiertas, el nombre y no la pista; de las que faltan, la pista y nunca el nombre
			assertEquals(x.discovered(), journal.contains(name + "\n") || journal.endsWith(name), x.id());
			assertEquals(!x.discovered(), journal.contains(clue), x.id());
		}
		// pistas suaves: sin coordenadas (ningún número en las páginas de pistas)
		for (Component c : pages.subList(fixed + 2, pages.size())) {
			if (view(c).startsWith(es.get("heraldia.guia.pistas"))) {
				assertFalse(view(c).matches("(?s).*\\d.*"), view(c));
			}
		}
	}

	@Test
	void allDiscovered() {
		List<Component> pages = Guide.pages(Guide.DATA, es, uniques(ids.size()));
		String everything = String.join("\n", pages.stream().map(GuideTest::view).toList());
		assertTrue(everything.contains(es.get("heraldia.guia.resumen.todas")));
		assertFalse(everything.contains(es.get("heraldia.guia.pistas") + "\n\n"));
	}

	@Test
	void discoveredInAlphabeticalOrder() {
		List<Component> pages = Guide.pages(Guide.DATA, es, uniques(ids.size()));
		List<String> names = new ArrayList<>();
		for (Component c : pages) {
			String[] l = view(c).split("\n");
			if (l[0].equals(es.get("heraldia.guia.descubiertas"))) {
				for (int i = 2; i < l.length; i++) {
					names.add(l[i].substring(2));
				}
			}
		}
		assertEquals(ids.size(), names.size());
		java.text.Collator c = java.text.Collator.getInstance(java.util.Locale.forLanguageTag("es"));
		c.setStrength(java.text.Collator.PRIMARY);
		List<String> sorted = new ArrayList<>(names);
		sorted.sort(c);
		assertEquals(sorted, names);
	}

	@Test
	void inEnglishFallbackIsEnglish() {
		List<Component> pages = Guide.pages(Guide.DATA, en, uniques(2));
		assertEquals(en.get("heraldia.guia.pagina.bienvenida.titulo") + "\n\n" + en.get("heraldia.guia.pagina.bienvenida"),
				view(pages.get(0)));
		String summary = view(pages.get(Guide.DATA.pages().size()));
		assertTrue(summary.startsWith("Your diary\n\nYou have discovered 2 of the " + ids.size()), summary);
	}

	@Test
	void everythingTranslatableHasFallbackAndOnlyVanillaText() {
		for (List<Component> pages : List.of(Guide.pages(Guide.DATA, es, uniques(5)), Guide.pages(Guide.DATA, en, uniques(0)))) {
			for (Component p : pages) {
				review(p);
			}
		}
	}

	private static void review(Component c) {
		if (c.getContents() instanceof TranslatableContents t) {
			assertNotNull(t.getFallback(), t.getKey());
			assertFalse(t.getFallback().equals(t.getKey()), "sin texto para " + t.getKey());
			for (Object a : t.getArgs()) {
				if (a instanceof Component ac) {
					review(ac);
				}
			}
		} else {
			assertTrue(c.getContents() instanceof PlainTextContents, c.getContents().toString());
		}
		c.getSiblings().forEach(GuideTest::review);
	}

	@Test
	void bookValidForVanillaClient() {
		ItemStack book = Guide.book(Guide.DATA, en, uniques(4), "9.9.9");
		assertTrue(book.is(Items.WRITTEN_BOOK));
		assertTrue(Guide.isGuide(book));
		assertFalse(Guide.isGuide(new ItemStack(Items.WRITTEN_BOOK)));
		WrittenBookContent w = book.get(DataComponents.WRITTEN_BOOK_CONTENT);
		assertEquals("The Herald's Guide", w.title().raw());
		assertTrue(w.title().raw().length() <= WrittenBookContent.TITLE_MAX_LENGTH);
		assertEquals("Heraldia", w.author());
		assertEquals(expectedPages(4, ids.size() - 4), w.pages().size());
		assertEquals("The Herald's Guide", book.getHoverName().getString());
		assertEquals("Heraldia edition 9.9.9", book.get(DataComponents.LORE).lines().get(0).getString());
		assertEquals("9.9.9", book.get(DataComponents.CUSTOM_DATA).copyTag().getStringOr("heraldia_guia_libro", ""));
		// el componente del libro se codifica y se lee igual (lo que viaja al cliente y se guarda), y cada página cabe
		JsonElement json = WrittenBookContent.CODEC.encodeStart(JsonOps.INSTANCE, w).getOrThrow();
		WrittenBookContent read = WrittenBookContent.CODEC.parse(JsonOps.INSTANCE, json).getOrThrow();
		assertEquals(json, WrittenBookContent.CODEC.encodeStart(JsonOps.INSTANCE, read).getOrThrow());
		assertEquals(w.pages().size(), read.pages().size());
		for (int i = 0; i < w.pages().size(); i++) {
			assertEquals(view(w.pages().get(i).raw()), view(read.pages().get(i).raw()));
		}
		for (var p : w.pages()) {
			String s = ComponentSerialization.CODEC.encodeStart(JsonOps.INSTANCE, p.raw()).getOrThrow().toString();
			assertTrue(s.length() < WrittenBookContent.PAGE_LENGTH, s.length() + " caracteres");
		}
		// el objeto entero, con los registros del juego (como al guardar el inventario)
		var ops = RegistryAccess.fromRegistryOfRegistries(BuiltInRegistries.REGISTRY).createSerializationContext(JsonOps.INSTANCE);
		JsonElement item = ItemStack.CODEC.encodeStart(ops, book).getOrThrow();
		ItemStack backup = ItemStack.CODEC.parse(ops, item).getOrThrow();
		assertEquals(item, ItemStack.CODEC.encodeStart(ops, backup).getOrThrow());
		assertTrue(Guide.isGuide(backup));
	}

	@Test
	void givesOncePerVersion() {
		assertTrue(Guide.shouldDeliver(true, null, "0.2.0"), "nunca la tuvo");
		assertTrue(Guide.shouldDeliver(true, "0.1.0", "0.2.0"), "actualización del mod");
		assertFalse(Guide.shouldDeliver(true, "0.2.0", "0.2.0"), "ya tiene la de esta versión");
		assertFalse(Guide.shouldDeliver(false, null, "0.2.0"), "opción desactivada");
		assertFalse(Guide.shouldDeliver(false, "0.1.0", "0.2.0"), "opción desactivada");
	}

	@Test
	void commandWithoutPermissions() {
		var guide = Guide.node().build();
		assertEquals("guide", guide.getName());
		assertNotNull(guide);
		assertNotNull(guide.getCommand());
		// sin .requires: el requisito por defecto acepta cualquier fuente, también la de un jugador sin permisos
		assertTrue(guide.getRequirement().test(null));
	}

	@Test
	void clientLanguage() {
		Map<String, String> there = Map.of("es", "es_es", "en", "en_us");
		assertEquals("es_es", Texts.code("es_es", there));
		assertEquals("es_es", Texts.code("es_MX", there));
		assertEquals("es_es", Texts.code("es_ar", there));
		assertEquals("en_us", Texts.code("en_gb", there));
		assertEquals("en_us", Texts.code("fr_fr", there));
		assertEquals("en_us", Texts.code(null, there));
		assertEquals("en_us", Texts.code("", there));
		assertEquals("Guía del Heraldo", Texts.language("es_mx").get("heraldia.guia.nombre"));
		assertEquals("The Herald's Guide", Texts.language("ja_jp").get("heraldia.guia.nombre"));
		assertEquals("The Herald's Guide", Texts.language("../../x").get("heraldia.guia.nombre"));
	}

	/** En cada idioma del .jar: el libro vanilla es válido, sus páginas salen en ese idioma y las descubiertas, en su orden. */
	@ParameterizedTest
	@ValueSource(strings = {"es_es", "en_us", "fr_fr", "de_de", "it_it", "pt_br", "ca_es", "gl_es"})
	void bookInEachLanguage(String language) {
		Map<String, String> texts = Texts.language(language);
		assertEquals(language, Texts.codeOf(texts));
		String title = texts.get("heraldia.guia.nombre");
		assertTrue(title != null && !title.isBlank() && title.length() <= WrittenBookContent.TITLE_MAX_LENGTH, title);
		ItemStack book = Guide.book(Guide.DATA, texts, uniques(ids.size() / 2), "1.0");
		WrittenBookContent content = book.get(DataComponents.WRITTEN_BOOK_CONTENT);
		assertEquals(title, content.title().raw());
		assertEquals(expectedPages(ids.size() / 2, ids.size() - ids.size() / 2), content.pages().size());
		assertTrue(content.pages().size() <= 100);   // máximo de páginas de un libro vanilla
		List<Component> pages = Guide.pages(Guide.DATA, texts, uniques(ids.size()));
		assertEquals(texts.get("heraldia.guia.pagina.bienvenida.titulo") + "\n\n" + texts.get("heraldia.guia.pagina.bienvenida"),
				view(pages.get(0)));
		List<String> names = new ArrayList<>();
		for (Component c : pages) {
			String[] l = view(c).split("\n");
			if (l[0].equals(texts.get("heraldia.guia.descubiertas"))) {
				for (int i = 2; i < l.length; i++) {
					names.add(l[i]);
				}
			}
		}
		assertEquals(ids.size(), names.size());
		java.text.Collator c = java.text.Collator.getInstance(java.util.Locale.forLanguageTag(language.replace('_', '-')));
		c.setStrength(java.text.Collator.PRIMARY);
		List<String> sorted = new ArrayList<>(names);
		sorted.sort(c);
		assertEquals(sorted, names);
	}
}
