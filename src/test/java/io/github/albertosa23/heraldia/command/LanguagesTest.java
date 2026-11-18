package io.github.albertosa23.heraldia.command;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonParser;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Stream;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

/**
 * Idiomas del .jar (tools/gen/idiomas.py): todos con las mismas claves y los mismos huecos de formato que el español y
 * el inglés, y el idioma que Textos elige para el respaldo de un cliente sin el mod según su lengua (fr_ca -> fr_fr,
 * pt_pt -> pt_br...; una lengua sin idioma propio, inglés). Los textos se leen del classpath, como del .jar.
 */
class LanguagesTest {
	private static final Path LANG = Path.of(System.getProperty("heraldia.generated", "build/generated/heraldia"))
			.resolve("assets/heraldia/lang");
	private static final Set<String> EXPECTED = Set.of("es_es", "en_us", "fr_fr", "de_de", "it_it", "pt_br", "ca_es", "gl_es");
	private static final Pattern MARK = Pattern.compile("%(?:(\\d+)\\$)?([a-zA-Z%])");
	private static Map<String, Map<String, String>> generated;

	@BeforeAll
	static void read() throws IOException {
		generated = new HashMap<>();
		try (Stream<Path> s = Files.list(LANG)) {
			for (Path p : s.toList()) {
				Map<String, String> m = new HashMap<>();
				JsonParser.parseString(Files.readString(p, StandardCharsets.UTF_8)).getAsJsonObject().entrySet()
						.forEach(e -> m.put(e.getKey(), e.getValue().getAsString()));
				generated.put(p.getFileName().toString().replace(".json", ""), m);
			}
		}
	}

	/** Argumentos que usa un texto de formato: índices 1..n ordenados y, al final, -1 por cada %% (como idiomas.marcadores). */
	static List<Integer> placeholders(String text) {
		List<Integer> out = new ArrayList<>();
		int next = 1, literals = 0;
		Matcher m = MARK.matcher(text);
		while (m.find()) {
			if (m.group(2).equals("%")) {
				literals++;
			} else {
				assertEquals("s", m.group(2), "marcador desconocido en «" + text + "»");
				out.add(m.group(1) != null ? Integer.parseInt(m.group(1)) : next++);
			}
		}
		out.sort(null);
		for (int i = 0; i < literals; i++) {
			out.add(-1);
		}
		return out;
	}

	@Test
	void jarHasAllLanguages() {
		assertEquals(EXPECTED, generated.keySet());
		assertEquals(new TreeSet<>(EXPECTED), new TreeSet<>(Texts.languages()));
	}

	@Test
	void sameKeysAndPlaceholdersInAllLanguages() {
		Map<String, String> es = generated.get("es_es"), en = generated.get("en_us");
		assertTrue(es.size() > 1000, "claves: " + es.size());
		for (Map.Entry<String, Map<String, String>> language : generated.entrySet()) {
			Map<String, String> t = language.getValue();
			Set<String> missing = new TreeSet<>(es.keySet()), extra = new TreeSet<>(t.keySet());
			missing.removeAll(t.keySet());
			extra.removeAll(es.keySet());
			assertEquals(Set.of(), missing, language.getKey() + ": faltan");
			assertEquals(Set.of(), extra, language.getKey() + ": sobran");
			for (Map.Entry<String, String> e : t.entrySet()) {
				assertFalse(e.getValue().isBlank(), language.getKey() + " " + e.getKey() + " vacía");
				assertEquals(placeholders(en.get(e.getKey())), placeholders(e.getValue()), language.getKey() + " " + e.getKey());
			}
		}
	}

	@Test
	void translationsAreNotCopiesOfSpanishOrEnglish() {
		Map<String, String> es = generated.get("es_es"), en = generated.get("en_us");
		for (String language : EXPECTED) {
			if (!language.equals("es_es") && !language.equals("en_us")) {
				Map<String, String> t = generated.get(language);
				long equal = t.entrySet().stream()
						.filter(e -> e.getValue().equals(es.get(e.getKey())) || e.getValue().equals(en.get(e.getKey()))).count();
				// nombres propios, inscripciones y formatos («%s», «%s/%s  %s») se repiten; el resto no
				assertTrue(equal < t.size() / 5, language + ": " + equal + " textos iguales al español o al inglés");
			}
		}
	}

	@ParameterizedTest
	@CsvSource({"fr_fr, fr_fr", "fr_ca, fr_fr", "FR_CA, fr_fr", "de_de, de_de", "de_at, de_de", "de_ch, de_de",
			"it_it, it_it", "pt_br, pt_br", "pt_pt, pt_br", "ca_es, ca_es", "val_es, ca_es", "gl_es, gl_es",
			"es_es, es_es", "es_mx, es_es", "es_ar, es_es", "es_cl, es_es", "es_ec, es_es", "es_uy, es_es", "es_ve, es_es",
			"esan, es_es", "en_us, en_us", "en_gb, en_us", "en_au, en_us", "ja_jp, en_us", "nl_nl, en_us", "ast_es, en_us",
			"eu_es, en_us", "'', en_us"})
	void languageByLocale(String client, String expected) {
		assertEquals(expected, Texts.code(client, Texts.locales()));
		assertEquals(expected, Texts.codeOf(Texts.language(client)));
	}

	@Test
	void noLanguageMeansEnglish() {
		assertEquals("en_us", Texts.code(null, Texts.locales()));
	}

	@Test
	void translationsLoadedFromJar() {
		for (String language : EXPECTED) {
			Map<String, String> jar = Texts.language(language);
			assertEquals(generated.get(language), jar, language);
		}
		assertNotEquals(Texts.language("fr_fr").get("heraldia.guia.nombre"), Texts.language("en_us").get("heraldia.guia.nombre"));
		assertEquals(Texts.language("pt_br"), Texts.language("pt_pt"));
		// el respaldo de un texto lleva el idioma pedido; si le faltara la clave, el español
		assertEquals(generated.get("de_de").get("heraldia.guia.copia"),
				Texts.t(Texts.language("de_at"), "heraldia.guia.copia").getString());
	}
}
