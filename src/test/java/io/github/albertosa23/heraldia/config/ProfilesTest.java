package io.github.albertosa23.heraldia.config;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
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
import java.util.Set;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * Gameplay profiles (option "perfil", {@link Profiles}): estandar is exactly the usual, an option written in the
 * file overrides the profile (and the profile becomes personalizado if it differs), the profile never touches generation, the
 * migration of 0.1.0 files changes nothing, the screen saves what differs from the profile and rereading the
 * file (the hot-reload path) applies the new profile.
 */
class ProfilesTest {
	@TempDir
	Path dir;

	@AfterEach
	void restore() {
		HeraldiaConfig.load(null);
	}

	private static Profiles profiles() {
		return HeraldiaConfig.profiles();
	}

	private static JsonObject json(Path file) throws IOException {
		return JsonParser.parseString(Files.readString(file, StandardCharsets.UTF_8)).getAsJsonObject();
	}

	private Path file(String content) throws IOException {
		Path f = dir.resolve("heraldia.json");
		Files.writeString(f, content);
		return f;
	}

	private static boolean has(JsonObject root, String key) {
		String[] p = key.split("\\.");
		JsonObject n = root;
		for (int i = 0; i < p.length - 1; i++) {
			if (!n.has(p[i])) {
				return false;
			}
			n = n.getAsJsonObject(p[i]);
		}
		return n.has(p[p.length - 1]);
	}

	@Test
	void thereAreThreeProfilesAndTheySetGameplayOptions() {
		assertEquals(Set.of("casual", "estandar", "hardcore"), profiles().names());
		List<String> keys = profiles().keys();
		for (String k : List.of("dificultad.nivel", "dificultad.escalar_por_jugadores", "botin.reponer.activado", "botin.reponer.dias",
				"jefes.refuerzos.activado", "jefes.fases.activado", "arena.experiencia_porcentaje", "arena.oleada.mobs_incremento",
				"arena.oleada.stats_incremento", "jefes.refuerzos.porcentaje", "jefes.refuerzos.maximo_vivos")) {
			assertTrue(keys.contains(k), k);
		}
		ConfigOption profile = HeraldiaConfig.options().stream().filter(o -> o.key().equals(Profiles.KEY)).findFirst().orElseThrow();
		assertEquals(List.of("casual", "estandar", "hardcore", "personalizado"), profile.values());
		assertEquals("estandar", profile.defaultValue().getAsString());
	}

	@Test
	void standardIsExactlyTheUsualBehavior() {
		Map<String, JsonPrimitive> defaults = HeraldiaConfig.defaults();
		assertEquals("estandar", defaults.get(Profiles.KEY).getAsString());
		profiles().optionValues(Profiles.STANDARD).forEach((k, v) -> assertEquals(defaults.get(k), v, k));
		// without a file and with a file that only says "estandar", the defaults
		assertEquals(defaults, HeraldiaConfig.readValues(dir.resolve("no.json")));
		// the new reinforcements, by default, give the old ones (100 % and cap 4)
		assertEquals(100, defaults.get("jefes.refuerzos.porcentaje").getAsInt());
		assertEquals(4, defaults.get("jefes.refuerzos.maximo_vivos").getAsInt());
		assertEquals("normal", defaults.get("dificultad.nivel").getAsString());
	}

	@Test
	void standardInTheFileToo() throws IOException {
		Path f = file("{\"version\": 2, \"perfil\": \"estandar\"}");
		HeraldiaConfig.Reading l = HeraldiaConfig.readWithProfile(f);
		assertEquals(HeraldiaConfig.defaults(), l.values());
		assertEquals("estandar", l.profile().effective());
		assertTrue(l.profile().pinned().isEmpty());
	}

	@Test
	void aProfileSetsItsOptionsAndNothingElse() throws IOException {
		for (String name : List.of("casual", "hardcore")) {
			Map<String, JsonPrimitive> v = HeraldiaConfig.readValues(file("{\"perfil\": \"" + name + "\"}"));
			Map<String, JsonPrimitive> profile = profiles().optionValues(name);
			Map<String, JsonPrimitive> defaults = HeraldiaConfig.defaults();
			for (String k : defaults.keySet()) {
				if (profile.containsKey(k)) {
					assertEquals(profile.get(k), v.get(k), name + ": " + k);
				} else if (!k.equals(Profiles.KEY)) {
					assertEquals(defaults.get(k), v.get(k), name + " no debe tocar " + k);
				}
			}
		}
		Map<String, JsonPrimitive> h = HeraldiaConfig.readValues(file("{\"perfil\": \"hardcore\"}"));
		assertEquals("heroica", h.get("dificultad.nivel").getAsString());
		assertTrue(h.get("jefes.refuerzos.porcentaje").getAsInt() > 100 && h.get("jefes.refuerzos.maximo_vivos").getAsInt() > 4, "más refuerzos");
		assertTrue(h.get("arena.experiencia_porcentaje").getAsInt() < 15, "menos experiencia");
		Map<String, JsonPrimitive> c = HeraldiaConfig.readValues(file("{\"perfil\": \"casual\"}"));
		assertEquals("facil", c.get("dificultad.nivel").getAsString());
		assertTrue(c.get("botin.reponer.activado").getAsBoolean(), "casual: con el botín que se repone");
	}

	@Test
	void profileNeverTouchesGeneration() {
		Set<String> gen = profiles().generation();
		for (String k : profiles().keys()) {
			assertFalse(gen.contains(k), k);
			for (String prefix : List.of("aldeas.", "unicas.", "medianas.", "minas.", "compatibilidad.")) {
				assertFalse(k.startsWith(prefix), k);
			}
		}
		assertFalse(profiles().keys().contains("arena.generar_en_mundos_nuevos"));
		// the generation options are marked in the schema
		for (ConfigOption o : HeraldiaConfig.options()) {
			if (o.key().startsWith("aldeas.separacion") || o.key().startsWith("unicas.") || o.key().startsWith("medianas.")
					|| o.key().startsWith("minas.") || o.key().equals("arena.generar_en_mundos_nuevos")) {
				assertTrue(gen.contains(o.key()), o.key());
			}
		}
		assertTrue(gen.size() > 100, "opciones de la generación: " + gen.size());
	}

	@Test
	void fileOptionOverridesProfile() throws IOException {
		Path f = file("{\"perfil\": \"hardcore\", \"dificultad\": {\"nivel\": \"normal\"}, \"arena\": {\"experiencia_porcentaje\": 5}}");
		HeraldiaConfig c = HeraldiaConfig.load(f);
		assertEquals("normal", c.getString("dificultad.nivel"), "lo del fichero manda");
		assertEquals("hardcore", c.profile().chosen());
		assertEquals("personalizado", c.profile().effective(), "una opción distinta del perfil: personalizado");
		assertEquals(Set.of("dificultad.nivel"), c.profile().differing().keySet(), "solo difiere la que no es la del perfil");
		assertEquals("heroica", c.profile().differing().get("dificultad.nivel")[1].getAsString());
		assertEquals(Set.of("dificultad.nivel", "arena.experiencia_porcentaje"), c.profile().pinned().keySet());
		assertEquals(profiles().optionValues("hardcore").get("jefes.refuerzos.maximo_vivos"), c.values().get("jefes.refuerzos.maximo_vivos"));
		// when rewritten, what was set by hand stays in the file (and the rest of the profile does not)
		JsonObject root = json(f);
		assertTrue(has(root, "dificultad.nivel") && has(root, "arena.experiencia_porcentaje"));
		assertFalse(has(root, "jefes.refuerzos.maximo_vivos"));
		assertEquals("personalizado", root.getAsJsonObject("_perfil").get("efectivo").getAsString());
		assertTrue(root.getAsJsonObject("_perfil").getAsJsonObject("difieren").has("dificultad.nivel"));
		// and when read again, the same
		assertEquals(c.values(), HeraldiaConfig.readValues(f));
	}

	@Test
	void pinnedWithProfileValueDoesNotChangeIt() throws IOException {
		HeraldiaConfig c = HeraldiaConfig.load(file("{\"perfil\": \"casual\", \"dificultad\": {\"nivel\": \"facil\"}}"));
		assertEquals("casual", c.profile().effective());
		assertTrue(c.profile().differing().isEmpty());
		assertEquals(Set.of("dificultad.nivel"), c.profile().pinned().keySet());
	}

	@Test
	void customPinsNothing() throws IOException {
		HeraldiaConfig c = HeraldiaConfig.load(file("{\"perfil\": \"personalizado\", \"botin\": {\"reponer\": {\"activado\": true}}}"));
		assertEquals("personalizado", c.profile().effective());
		assertTrue(c.profile().differing().isEmpty());
		assertTrue(c.getBool("botin.reponer.activado"));
		Map<String, JsonPrimitive> defaults = HeraldiaConfig.defaults();
		for (String k : profiles().keys()) {
			if (!k.equals("botin.reponer.activado")) {
				assertEquals(defaults.get(k), c.values().get(k), k);
			}
		}
	}

	@Test
	void invalidValues() throws IOException {
		// a profile that does not exist: the default one; a profile option out of range: the profile's, without pinning it
		HeraldiaConfig c = HeraldiaConfig.load(file("{\"perfil\": \"imposible\"}"));
		assertEquals("estandar", c.profile().chosen());
		c = HeraldiaConfig.load(file("{\"perfil\": \"hardcore\", \"arena\": {\"max_mobs_vivos\": 999}, \"jefes\": {\"refuerzos\": {\"porcentaje\": \"x\"}}}"));
		assertEquals(profiles().optionValues("hardcore").get("arena.max_mobs_vivos"), c.values().get("arena.max_mobs_vivos"));
		assertEquals(profiles().optionValues("hardcore").get("jefes.refuerzos.porcentaje"), c.values().get("jefes.refuerzos.porcentaje"));
		assertTrue(c.profile().pinned().isEmpty());
		assertEquals("hardcore", c.profile().effective());
	}

	/** 0.1.0 file (version 1): the mod wrote all the options with their value. */
	private Path fileV1(Map<String, JsonPrimitive> optionValues) throws IOException {
		JsonObject root = new JsonObject();
		root.addProperty("version", 1);
		optionValues.forEach((k, v) -> {
			if (k.equals(Profiles.KEY) || k.startsWith("jefes.refuerzos.porcentaje") || k.startsWith("jefes.refuerzos.maximo_vivos")) {
				return;                      // they did not exist
			}
			String[] p = k.split("\\.");
			JsonObject n = root;
			for (int i = 0; i < p.length - 1; i++) {
				if (!n.has(p[i])) {
					n.add(p[i], new JsonObject());
				}
				n = n.getAsJsonObject(p[i]);
			}
			n.add(p[p.length - 1], v);
		});
		return file(root.toString());
	}

	@Test
	void migratingA010FileChangesNothing() throws IOException {
		Path f = fileV1(HeraldiaConfig.defaults());
		HeraldiaConfig c = HeraldiaConfig.load(f);
		assertEquals(HeraldiaConfig.defaults(), c.values());
		assertEquals("estandar", c.profile().effective());
		assertTrue(c.profile().pinned().isEmpty(), "lo que escribía el mod no cuenta como fijado a mano");
		JsonObject root = json(f);
		assertEquals(2, root.get("version").getAsInt());
		for (String k : profiles().keys()) {
			assertFalse(has(root, k), "tras migrar no se escribe " + k);
		}
		// and now changing the profile in the file does do something
		root.addProperty("perfil", "hardcore");
		Files.writeString(f, root.toString());
		assertEquals("heroica", HeraldiaConfig.load(f).getString("dificultad.nivel"));
	}

	@Test
	void migrationKeepsManualChanges() throws IOException {
		Map<String, JsonPrimitive> v = new LinkedHashMap<>(HeraldiaConfig.defaults());
		v.put("dificultad.nivel", new JsonPrimitive("dificil"));
		v.put("botin.reponer.activado", new JsonPrimitive(true));
		v.put("aldeas.separacion_bloques", new JsonPrimitive(2500));
		HeraldiaConfig c = HeraldiaConfig.load(fileV1(v));
		assertEquals("dificil", c.getString("dificultad.nivel"));
		assertTrue(c.getBool("botin.reponer.activado"));
		assertEquals(2500, c.getInt("aldeas.separacion_bloques"));
		assertEquals(Set.of("dificultad.nivel", "botin.reponer.activado"), c.profile().pinned().keySet());
		assertEquals("personalizado", c.profile().effective());
		Map<String, JsonPrimitive> expected = new LinkedHashMap<>(v);
		assertEquals(expected, c.values(), "los mismos valores que en la 0.1.0");
	}

	@Test
	void screenSavesWhatDiffersFromProfile() throws IOException {
		Path f = dir.resolve("pantalla.json");
		Map<String, JsonPrimitive> v = new LinkedHashMap<>(HeraldiaConfig.defaults());
		v.put(Profiles.KEY, new JsonPrimitive("hardcore"));
		v.putAll(profiles().optionValues("hardcore"));
		v.put("arena.max_mobs_vivos", new JsonPrimitive(40));
		HeraldiaConfig.save(f, v);
		JsonObject root = json(f);
		assertTrue(has(root, "arena.max_mobs_vivos"));
		assertFalse(has(root, "dificultad.nivel"), "lo que da el perfil no se escribe");
		HeraldiaConfig.Reading l = HeraldiaConfig.readWithProfile(f);
		assertEquals(v, l.values());
		assertEquals(Set.of("arena.max_mobs_vivos"), l.profile().pinned().keySet());
		assertEquals(Set.of("arena.max_mobs_vivos"), profiles().pinnedByDifference("hardcore", v));
	}

	@Test
	void rereadingFileAppliesNewProfile() throws IOException {
		// the hot-reload path: HeraldiaConfig.load again with the changed file
		Path f = file("{\"perfil\": \"casual\"}");
		assertEquals("facil", HeraldiaConfig.load(f).getString("dificultad.nivel"));
		assertEquals("facil", HeraldiaConfig.get().getString("dificultad.nivel"));
		JsonObject root = json(f);
		root.addProperty("perfil", "hardcore");
		Files.writeString(f, root.toString());
		HeraldiaConfig.load(f);
		assertEquals("heroica", HeraldiaConfig.get().getString("dificultad.nivel"));
		assertEquals("hardcore", HeraldiaConfig.get().profile().effective());
		root = json(f);
		root.addProperty("perfil", "estandar");
		Files.writeString(f, root.toString());
		assertEquals(HeraldiaConfig.defaults(), HeraldiaConfig.load(f).values());
	}

	@Test
	void fileHelpListsEachProfileValues() throws IOException {
		Path f = dir.resolve("ayuda.json");
		HeraldiaConfig.load(f);
		JsonObject root = json(f);
		String es = root.getAsJsonObject("_ayuda").getAsJsonObject("es_es").get("dificultad.nivel").getAsString();
		assertTrue(es.contains("casual facil") && es.contains("hardcore heroica"), es);
		assertTrue(root.getAsJsonObject("_ayuda").getAsJsonObject("en_us").has("perfil"));
		assertEquals("estandar", root.get("perfil").getAsString());
		assertNotEquals(null, root.getAsJsonObject("_perfil"));
	}

	@Test
	void applyIsPureLogic() {
		Profiles p = profiles();
		Profiles.Applied a = p.apply("hardcore", Map.of());
		assertEquals(p.optionValues("hardcore"), a.optionValues());
		assertEquals("hardcore", a.effective());
		a = p.apply("hardcore", Map.of("dificultad.nivel", new JsonPrimitive("heroica")));
		assertEquals("hardcore", a.effective());
		a = p.apply("hardcore", Map.of("dificultad.nivel", new JsonPrimitive("facil")));
		assertEquals("personalizado", a.effective());
		assertEquals("facil", a.optionValues().get("dificultad.nivel").getAsString());
		assertEquals(p.optionValues(Profiles.STANDARD), p.optionValues(Profiles.CUSTOM), "personalizado parte de los de por defecto");
	}
}
