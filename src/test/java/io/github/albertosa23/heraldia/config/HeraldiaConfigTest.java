package io.github.albertosa23.heraldia.config;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.google.gson.JsonPrimitive;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * Reading, writing and validation of config/heraldia.json round trip, as the client's configuration screen uses them
 * ({@link HeraldiaConfig#readValues}, {@link HeraldiaConfig#save}, {@link ConfigOption#parse}), and that the schema
 * has everything the screen needs (section and texts in both languages).
 */
class HeraldiaConfigTest {
	@TempDir
	Path dir;

	private static JsonObject json(Path file) throws IOException {
		return JsonParser.parseString(Files.readString(file, StandardCharsets.UTF_8)).getAsJsonObject();
	}

	private static ConfigOption option(String key) {
		return HeraldiaConfig.options().stream().filter(o -> o.key().equals(key)).findFirst().orElseThrow();
	}

	@Test
	void noFileGivesDefaults() {
		Path file = dir.resolve("heraldia.json");
		assertEquals(HeraldiaConfig.defaults(), HeraldiaConfig.readValues(file));
		assertFalse(Files.exists(file), "readValues no debe crear el fichero");
	}

	@Test
	void saveAndReadRoundTrip() throws IOException {
		Path file = dir.resolve("config/heraldia.json");
		Map<String, JsonPrimitive> values = new LinkedHashMap<>(HeraldiaConfig.defaults());
		values.put("aldeas.separacion_bloques", new JsonPrimitive(2500));
		values.put("golems.limpieza", new JsonPrimitive(false));
		values.put("unicas.castillo.activada", new JsonPrimitive(false));
		values.put("unicas.castillo.separacion_bloques", new JsonPrimitive(7000));
		HeraldiaConfig.save(file, values);
		assertEquals(values, HeraldiaConfig.readValues(file));
		assertFalse(Files.exists(dir.resolve("config/heraldia.json.tmp")), "no debe quedar el temporal");

		JsonObject root = json(file);
		assertEquals(HeraldiaConfig.get().schema().get("version").getAsInt(), root.get("version").getAsInt());
		assertEquals(2500, root.getAsJsonObject("aldeas").get("separacion_bloques").getAsInt());
		assertFalse(root.getAsJsonObject("unicas").getAsJsonObject("castillo").get("activada").getAsBoolean());
		assertTrue(root.getAsJsonObject("_ayuda").has("es_es") && root.getAsJsonObject("_ayuda").has("en_us"));
	}

	@Test
	void sameFormatAsAtStartup() throws IOException {
		Path started = dir.resolve("arranque.json");
		Path saved = dir.resolve("pantalla.json");
		HeraldiaConfig.load(started);
		try {
			HeraldiaConfig.save(saved, HeraldiaConfig.defaults());
			assertEquals(Files.readString(started), Files.readString(saved));
		} finally {
			HeraldiaConfig.load(null);
		}
	}

	@Test
	void savingDoesNotChangeActiveConfig() throws IOException {
		HeraldiaConfig inUse = HeraldiaConfig.get();
		Map<String, JsonPrimitive> values = new LinkedHashMap<>(HeraldiaConfig.defaults());
		values.put("aldeas.maximo", new JsonPrimitive(3));
		HeraldiaConfig.save(dir.resolve("heraldia.json"), values);
		assertSame(inUse, HeraldiaConfig.get());
	}

	@Test
	void savingRejectsInvalidValues() {
		Path file = dir.resolve("heraldia.json");
		Map<String, JsonPrimitive> values = new LinkedHashMap<>(HeraldiaConfig.defaults());
		values.put("aldeas.separacion_bloques", new JsonPrimitive(999));
		assertThrows(IllegalArgumentException.class, () -> HeraldiaConfig.save(file, values));
		values.put("aldeas.separacion_bloques", new JsonPrimitive(true));
		assertThrows(IllegalArgumentException.class, () -> HeraldiaConfig.save(file, values));
		values.put("aldeas.separacion_bloques", new JsonPrimitive(1500));
		values.put("golems.limpieza", new JsonPrimitive(1));
		assertThrows(IllegalArgumentException.class, () -> HeraldiaConfig.save(file, values));
		values.remove("golems.limpieza");
		assertThrows(IllegalArgumentException.class, () -> HeraldiaConfig.save(file, values));
		assertFalse(Files.exists(file), "un guardado rechazado no escribe nada");
	}

	@Test
	void readingFixesAndMigrates() throws IOException {
		Path file = dir.resolve("heraldia.json");
		// Hand-written file (version 0, no field): out of range, of another type, decimal and unknown option.
		Files.writeString(file, """
				{"aldeas": {"separacion_bloques": 20000, "maximo": 50, "porcentaje_grandes": 12.5},
				 "golems": {"limpieza": "no", "limite_grande": 12.0},
				 "inventada": 3}
				""");
		Map<String, JsonPrimitive> v = HeraldiaConfig.readValues(file);
		assertEquals(1500, v.get("aldeas.separacion_bloques").getAsInt());
		assertEquals(50, v.get("aldeas.maximo").getAsInt());
		assertEquals(25, v.get("aldeas.porcentaje_grandes").getAsInt());
		assertTrue(v.get("golems.limpieza").getAsBoolean());
		assertEquals(12, v.get("golems.limite_grande").getAsInt());
		assertFalse(v.containsKey("inventada"));
		assertEquals(HeraldiaConfig.defaults().keySet(), v.keySet());

		Files.writeString(file, "[1, 2]");
		assertEquals(HeraldiaConfig.defaults(), HeraldiaConfig.readValues(file));
		Files.writeString(file, "{roto");
		assertEquals(HeraldiaConfig.defaults(), HeraldiaConfig.readValues(file));
	}

	@Test
	void screenValidation() {
		ConfigOption spacing = option("aldeas.separacion_bloques");
		assertEquals(Optional.of(new JsonPrimitive(1000)), spacing.parse("1000"));
		assertEquals(Optional.of(new JsonPrimitive(10000)), spacing.parse(" 10000 "));
		for (String bad : List.of("", "999", "10001", "-5", "abc", "1e3", "1500.0", "15 00", "99999999999", "+1500")) {
			assertTrue(spacing.parse(bad).isEmpty(), bad);
		}
		ConfigOption cleanup = option("golems.limpieza");
		assertEquals(Optional.of(new JsonPrimitive(false)), cleanup.parse("false"));
		assertTrue(cleanup.parse("1").isEmpty());
		assertTrue(cleanup.accept(new JsonPrimitive(true)).isPresent());
		assertTrue(spacing.accept(new JsonPrimitive(2000.0)).isPresent());
		assertTrue(spacing.accept(new JsonPrimitive(2000.5)).isEmpty());
	}

	@Test
	void schemaHasWhatTheScreenNeeds() throws IOException {
		Path lang = Path.of(System.getProperty("heraldia.generated"), "assets/heraldia/lang");
		JsonObject es = json(lang.resolve("es_es.json")), en = json(lang.resolve("en_us.json"));
		assertFalse(HeraldiaConfig.options().isEmpty());
		for (String key : HeraldiaConfig.sections().values()) {
			assertTrue(es.has(key) && en.has(key), key);
		}
		for (ConfigOption o : HeraldiaConfig.options()) {
			assertTrue(HeraldiaConfig.sections().containsKey(o.section()), o.key() + ": sección " + o.section());
			for (String key : List.of(o.name(), o.help())) {
				assertTrue(es.has(key) && en.has(key), o.key() + ": falta el texto " + key);
			}
			for (String key : o.argNames()) {
				assertTrue(key == null || es.has(key) && en.has(key), o.key() + ": falta el nombre " + key);
			}
			assertEquals(o.isBoolean() || o.isChoice(), o.min() == null, o.key());
			for (String key : o.valueNames()) {
				assertTrue(es.has(key) && en.has(key), o.key() + ": falta el nombre del valor " + key);
			}
			assertEquals(o.values().size(), o.valueNames().size(), o.key());
		}
		for (String key : List.of("titulo", "buscar", "guardar", "restaurar", "aviso", "aviso_mundo", "aviso_servidor", "invalido",
				"clave", "guardado", "error")) {
			assertTrue(es.has("heraldia.config.pantalla." + key) && en.has("heraldia.config.pantalla." + key), key);
		}
	}
}
