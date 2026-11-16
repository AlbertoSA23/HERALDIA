package io.github.albertosa23.heraldia.comando;

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
class IdiomasTest {
	private static final Path LANG = Path.of(System.getProperty("heraldia.generated", "build/generated/heraldia"))
			.resolve("assets/heraldia/lang");
	private static final Set<String> ESPERADOS = Set.of("es_es", "en_us", "fr_fr", "de_de", "it_it", "pt_br", "ca_es", "gl_es");
	private static final Pattern MARCA = Pattern.compile("%(?:(\\d+)\\$)?([a-zA-Z%])");
	private static Map<String, Map<String, String>> generados;

	@BeforeAll
	static void leer() throws IOException {
		generados = new HashMap<>();
		try (Stream<Path> s = Files.list(LANG)) {
			for (Path p : s.toList()) {
				Map<String, String> m = new HashMap<>();
				JsonParser.parseString(Files.readString(p, StandardCharsets.UTF_8)).getAsJsonObject().entrySet()
						.forEach(e -> m.put(e.getKey(), e.getValue().getAsString()));
				generados.put(p.getFileName().toString().replace(".json", ""), m);
			}
		}
	}

	/** Argumentos que usa un texto de formato: índices 1..n ordenados y, al final, -1 por cada %% (como idiomas.marcadores). */
	static List<Integer> huecos(String texto) {
		List<Integer> out = new ArrayList<>();
		int siguiente = 1, literales = 0;
		Matcher m = MARCA.matcher(texto);
		while (m.find()) {
			if (m.group(2).equals("%")) {
				literales++;
			} else {
				assertEquals("s", m.group(2), "marcador desconocido en «" + texto + "»");
				out.add(m.group(1) != null ? Integer.parseInt(m.group(1)) : siguiente++);
			}
		}
		out.sort(null);
		for (int i = 0; i < literales; i++) {
			out.add(-1);
		}
		return out;
	}

	@Test
	void elJarTraeTodosLosIdiomas() {
		assertEquals(ESPERADOS, generados.keySet());
		assertEquals(new TreeSet<>(ESPERADOS), new TreeSet<>(Textos.idiomas()));
	}

	@Test
	void mismasClavesYHuecosEnTodosLosIdiomas() {
		Map<String, String> es = generados.get("es_es"), en = generados.get("en_us");
		assertTrue(es.size() > 1000, "claves: " + es.size());
		for (Map.Entry<String, Map<String, String>> idioma : generados.entrySet()) {
			Map<String, String> t = idioma.getValue();
			Set<String> faltan = new TreeSet<>(es.keySet()), sobran = new TreeSet<>(t.keySet());
			faltan.removeAll(t.keySet());
			sobran.removeAll(es.keySet());
			assertEquals(Set.of(), faltan, idioma.getKey() + ": faltan");
			assertEquals(Set.of(), sobran, idioma.getKey() + ": sobran");
			for (Map.Entry<String, String> e : t.entrySet()) {
				assertFalse(e.getValue().isBlank(), idioma.getKey() + " " + e.getKey() + " vacía");
				assertEquals(huecos(en.get(e.getKey())), huecos(e.getValue()), idioma.getKey() + " " + e.getKey());
			}
		}
	}

	@Test
	void lasTraduccionesNoSonCopiasDelEspanolNiDelIngles() {
		Map<String, String> es = generados.get("es_es"), en = generados.get("en_us");
		for (String idioma : ESPERADOS) {
			if (!idioma.equals("es_es") && !idioma.equals("en_us")) {
				Map<String, String> t = generados.get(idioma);
				long iguales = t.entrySet().stream()
						.filter(e -> e.getValue().equals(es.get(e.getKey())) || e.getValue().equals(en.get(e.getKey()))).count();
				// nombres propios, inscripciones y formatos («%s», «%s/%s  %s») se repiten; el resto no
				assertTrue(iguales < t.size() / 5, idioma + ": " + iguales + " textos iguales al español o al inglés");
			}
		}
	}

	@ParameterizedTest
	@CsvSource({"fr_fr, fr_fr", "fr_ca, fr_fr", "FR_CA, fr_fr", "de_de, de_de", "de_at, de_de", "de_ch, de_de",
			"it_it, it_it", "pt_br, pt_br", "pt_pt, pt_br", "ca_es, ca_es", "val_es, ca_es", "gl_es, gl_es",
			"es_es, es_es", "es_mx, es_es", "es_ar, es_es", "es_cl, es_es", "es_ec, es_es", "es_uy, es_es", "es_ve, es_es",
			"esan, es_es", "en_us, en_us", "en_gb, en_us", "en_au, en_us", "ja_jp, en_us", "nl_nl, en_us", "ast_es, en_us",
			"eu_es, en_us", "'', en_us"})
	void idiomaPorLengua(String cliente, String esperado) {
		assertEquals(esperado, Textos.codigo(cliente, Textos.lenguas()));
		assertEquals(esperado, Textos.codigoDe(Textos.idioma(cliente)));
	}

	@Test
	void sinIdiomaElIngles() {
		assertEquals("en_us", Textos.codigo(null, Textos.lenguas()));
	}

	@Test
	void traduccionesCargadasDelJar() {
		for (String idioma : ESPERADOS) {
			Map<String, String> jar = Textos.idioma(idioma);
			assertEquals(generados.get(idioma), jar, idioma);
		}
		assertNotEquals(Textos.idioma("fr_fr").get("heraldia.guia.nombre"), Textos.idioma("en_us").get("heraldia.guia.nombre"));
		assertEquals(Textos.idioma("pt_br"), Textos.idioma("pt_pt"));
		// el respaldo de un texto lleva el idioma pedido; si le faltara la clave, el español
		assertEquals(generados.get("de_de").get("heraldia.guia.copia"),
				Textos.t(Textos.idioma("de_at"), "heraldia.guia.copia").getString());
	}
}
