package io.github.albertosa23.heraldia.config;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
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
import java.util.Set;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * The light profile ("ligero"): it is applied whole like the others (the gameplay of estandar plus lighter generation), what
 * is written by hand overrides it and makes it custom, the other profiles do not touch generation (a generation option
 * written by hand with them is just an option), the in-game panel and the screen move the values when switching
 * ({@link Profiles#switchTo}), a version 2 file migrates without changing anything, and {@link ProfileAdvice} (suggestion
 * and seams).
 */
class LightProfileTest {
	@TempDir
	Path dir;

	@AfterEach
	void restore() {
		HeraldiaConfig.load(null);
	}

	private static Profiles profiles() {
		return HeraldiaConfig.profiles();
	}

	private Path file(String content) throws IOException {
		Path f = dir.resolve("heraldia.json");
		Files.writeString(f, content);
		return f;
	}

	private static JsonObject json(Path f) throws IOException {
		return JsonParser.parseString(Files.readString(f, StandardCharsets.UTF_8)).getAsJsonObject();
	}

	private static boolean has(JsonObject root, String key) {
		String[] p = key.split("\\.");
		JsonObject n = root;
		for (int i = 0; i < p.length - 1; i++) {
			if (!n.has(p[i]) || !n.get(p[i]).isJsonObject()) {
				return false;
			}
			n = n.getAsJsonObject(p[i]);
		}
		return n.has(p[p.length - 1]);
	}

	@Test
	void lightIsTheStandardGameWithLighterGeneration() {
		Map<String, JsonPrimitive> light = profiles().optionValues(Profiles.LIGHT), standard = profiles().optionValues(Profiles.STANDARD);
		for (String k : profiles().keysOf(Profiles.STANDARD)) {
			assertEquals(standard.get(k), light.get(k), k);
		}
		assertTrue(profiles().touchesGeneration(Profiles.LIGHT));
		assertFalse(light.get("aldeas.caminos.activado").getAsBoolean());
		assertFalse(light.get("caravanas.activado").getAsBoolean());
		assertEquals(50, light.get("medianas.frecuencia_porcentaje").getAsInt());
		assertEquals(1.0, light.get("minas.vanilla.multiplicador").getAsDouble());
		assertTrue(profiles().generationKeysOf(Profiles.LIGHT).contains("medianas.frecuencia_porcentaje"));
		assertFalse(profiles().generationKeysOf(Profiles.LIGHT).contains("caravanas.activado"), "caravans: gameplay");
		// it never moves the grids of villages or unique structures
		for (String k : profiles().keysOf(Profiles.LIGHT)) {
			assertFalse(k.startsWith("unicas.") || k.equals("aldeas.separacion_bloques") || k.equals("aldeas.maximo"), k);
		}
		// the other profiles give the default to the light profile's generation options
		for (String k : profiles().generationKeysOf(Profiles.LIGHT)) {
			assertEquals(HeraldiaConfig.defaults().get(k), profiles().optionValues("hardcore").get(k), k);
		}
	}

	@Test
	void chosenInTheFileItIsAppliedWholeAndNotWritten() throws IOException {
		Path f = file("{\"perfil\": \"ligero\"}");
		HeraldiaConfig c = HeraldiaConfig.load(f);
		assertEquals("ligero", c.profile().effective());
		assertFalse(c.getBool("aldeas.caminos.activado"));
		assertEquals(10, c.getInt("aldeas.porcentaje_grandes"));
		assertEquals("normal", c.getString("dificultad.nivel"));
		JsonObject root = json(f);
		for (String k : profiles().keys()) {
			assertFalse(has(root, k), "not set by hand: not written " + k);
		}
		assertTrue(c.profileInFile());
		// and back to estandar in the file: everything as always
		root.addProperty("perfil", "estandar");
		Files.writeString(f, root.toString());
		assertEquals(HeraldiaConfig.defaults(), HeraldiaConfig.load(f).values());
	}

	@Test
	void handWrittenOverridesLightAndMakesItCustom() throws IOException {
		HeraldiaConfig c = HeraldiaConfig.load(file("{\"perfil\": \"ligero\", \"aldeas\": {\"caminos\": {\"activado\": true}}}"));
		assertTrue(c.getBool("aldeas.caminos.activado"), "the file rules");
		assertEquals("personalizado", c.profile().effective());
		assertEquals(Set.of("aldeas.caminos.activado"), c.profile().differing().keySet());
		assertEquals(50, c.getInt("medianas.frecuencia_porcentaje"), "the rest, the profile's");
	}

	@Test
	void aGenerationOptionWithAGameplayProfileIsJustAnOption() throws IOException {
		Path f = file("{\"perfil\": \"casual\", \"aldeas\": {\"caminos\": {\"activado\": false}}, \"medianas\": {\"frecuencia_porcentaje\": 100}}");
		HeraldiaConfig c = HeraldiaConfig.load(f);
		assertFalse(c.getBool("aldeas.caminos.activado"));
		assertEquals("casual", c.profile().effective(), "casual does not set generation: it is not custom");
		assertTrue(c.profile().differing().isEmpty());
		JsonObject root = json(f);
		assertTrue(has(root, "aldeas.caminos.activado"), "set by hand: written");
		assertTrue(has(root, "medianas.frecuencia_porcentaje"), "written by hand, kept (even with the default value)");
		// switching that file to ligero keeps what was written by hand: it overrides the light profile
		root.addProperty("perfil", "ligero");
		Files.writeString(f, root.toString());
		HeraldiaConfig l = HeraldiaConfig.load(f);
		assertEquals(100, l.getInt("medianas.frecuencia_porcentaje"));
		assertEquals("personalizado", l.profile().effective());
	}

	@Test
	void switchingMovesTheProfileValuesAndKeepsWhatWasSetByHand() {
		Map<String, JsonPrimitive> v = new LinkedHashMap<>(profiles().switchTo(Profiles.STANDARD, "casual", HeraldiaConfig.defaults()));
		assertEquals("facil", v.get("dificultad.nivel").getAsString());
		v.put("jefes.barra.activado", new JsonPrimitive(false));                 // not a profile option: untouched
		v.put("dificultad.nivel", new JsonPrimitive("dificil"));                  // by hand: it stays
		v.put("medianas.frecuencia_porcentaje", new JsonPrimitive(150));          // by hand (generation): it stays
		Map<String, JsonPrimitive> l = profiles().switchTo("casual", Profiles.LIGHT, v);
		assertEquals("ligero", l.get(Profiles.KEY).getAsString());
		assertEquals("dificil", l.get("dificultad.nivel").getAsString());
		assertEquals(150, l.get("medianas.frecuencia_porcentaje").getAsInt());
		assertFalse(l.get("aldeas.caminos.activado").getAsBoolean());
		assertEquals(35, l.get("caravanas.prob_asalto").getAsInt(), "casual's 15 → light's (standard) 35");
		assertFalse(l.get("jefes.barra.activado").getAsBoolean());
		// what is saved as set by hand: only what differs from the light profile
		assertEquals(Set.of("dificultad.nivel", "medianas.frecuencia_porcentaje"), profiles().pinnedByDifference(Profiles.LIGHT, l));
		// back to estandar: the light profile's values go back to the defaults
		Map<String, JsonPrimitive> e = profiles().switchTo(Profiles.LIGHT, Profiles.STANDARD, l);
		assertTrue(e.get("aldeas.caminos.activado").getAsBoolean());
		assertEquals(150, e.get("medianas.frecuencia_porcentaje").getAsInt());
		// to custom: everything stays
		Map<String, JsonPrimitive> c = profiles().switchTo(Profiles.LIGHT, Profiles.CUSTOM, l);
		l.forEach((k, x) -> {
			if (!k.equals(Profiles.KEY)) {
				assertEquals(x, c.get(k), k);
			}
		});
	}

	@Test
	void savedAfterSwitchingItRereadsAsTheLightProfile() throws IOException {
		Path f = dir.resolve("heraldia.json");
		Map<String, JsonPrimitive> v = profiles().switchTo("hardcore", Profiles.LIGHT, profiles().switchTo(Profiles.STANDARD, "hardcore",
				HeraldiaConfig.defaults()));
		HeraldiaConfig.save(f, v);
		HeraldiaConfig.Reading r = HeraldiaConfig.readWithProfile(f);
		assertEquals("ligero", r.profile().effective(), "the panel's switch does not leave the previous profile's values pinned");
		assertTrue(r.profile().pinned().isEmpty());
		assertEquals(v, r.values());
	}

	@Test
	void versionTwoFileMigratesWithoutChangingAnything() throws IOException {
		// a version 2 file written by the mod: every generation option written (with the default), the profile ones only by hand
		Path f = file("{\"version\": 2, \"perfil\": \"casual\", \"aldeas\": {\"caminos\": {\"activado\": true}, \"porcentaje_grandes\": 40},"
				+ " \"medianas\": {\"frecuencia_porcentaje\": 100, \"activadas\": true}, \"minas\": {\"vanilla\": {\"multiplicador\": 2.0}},"
				+ " \"caravanas\": {\"activado\": true}, \"dificultad\": {\"nivel\": \"normal\"}}");
		HeraldiaConfig c = HeraldiaConfig.load(f);
		assertTrue(Files.isRegularFile(dir.resolve("heraldia.json.v2.bak")));
		JsonObject root = json(f);
		assertEquals(3, root.get("version").getAsInt());
		for (String k : List.of("aldeas.caminos.activado", "medianas.frecuencia_porcentaje", "minas.vanilla.multiplicador", "caravanas.activado")) {
			assertFalse(has(root, k), "the mod wrote it with the default: removed " + k);
		}
		assertEquals(40, root.getAsJsonObject("aldeas").get("porcentaje_grandes").getAsInt(), "another value: set by hand");
		assertTrue(has(root, "medianas.activadas"), "not a profile option: still written");
		assertEquals("normal", root.getAsJsonObject("dificultad").get("nivel").getAsString(), "a gameplay option set by hand in v2 stays");
		assertEquals("personalizado", c.profile().effective(), "difficulty normal by hand over casual, as before");
		assertEquals(Set.of("dificultad.nivel"), c.profile().differing().keySet(), "the large villages by hand do not make casual custom");
		assertTrue(c.getBool("aldeas.caminos.activado"));
		assertEquals(40, c.getInt("aldeas.porcentaje_grandes"));
	}

	@Test
	void theFileSaysWhetherAProfileWasChosen() throws IOException {
		assertFalse(HeraldiaConfig.load(dir.resolve("none.json")).profileInFile(), "first start: no file");
		assertFalse(HeraldiaConfig.load(file("{\"aldeas\": {\"maximo\": 50}}")).profileInFile());
		// the mod writes it at startup: on the next start it has been chosen (the suggestion stays quiet)
		assertTrue(HeraldiaConfig.load(dir.resolve("heraldia.json")).profileInFile());
		assertTrue(HeraldiaConfig.load(file("{\"perfil\": \"estandar\"}")).profileInFile());
	}

	@Test
	void helpOfTheFileShowsTheLightProfileValue() throws IOException {
		Path f = file("{}");
		HeraldiaConfig.load(f);
		JsonObject help = json(f).getAsJsonObject("_ayuda").getAsJsonObject("en_us");
		assertTrue(help.get("dificultad.nivel").getAsString().contains("casual facil, standard normal, hardcore heroica, light normal"),
				help.get("dificultad.nivel").getAsString());
		assertTrue(help.get("aldeas.caminos.activado").getAsString().contains("light false"), help.get("aldeas.caminos.activado").getAsString());
		assertFalse(help.get("aldeas.caminos.activado").getAsString().contains("hardcore"));
	}

	@Test
	void suggestionFromMemoryAndCores() {
		long gb = 1024L * 1024 * 1024;
		assertEquals(Optional.of("ligero"), ProfileAdvice.suggest(2 * gb, 8), "-Xmx2G");
		assertEquals(Optional.of("ligero"), ProfileAdvice.suggest(3 * gb - 100 * 1024 * 1024, 8), "-Xmx3G (the JVM reports a bit less)");
		assertEquals(Optional.of("ligero"), ProfileAdvice.suggest(16 * gb, 2), "two cores");
		assertEquals(Optional.empty(), ProfileAdvice.suggest(4 * gb - 150 * 1024 * 1024, 4), "-Xmx4G and 4 cores: fine");
		assertEquals(Optional.empty(), ProfileAdvice.suggest(8 * gb, 3));
		assertEquals("2.9", ProfileAdvice.gb(3 * gb - 100 * 1024 * 1024));
	}

	@Test
	void seamsOnlyWhenGenerationChangesInAWorldAlreadyPlayed() {
		Map<String, JsonPrimitive> values = new LinkedHashMap<>(HeraldiaConfig.defaults());
		Map<String, String> before = ProfileAdvice.fingerprint(values, profiles().generation());
		assertTrue(before.containsKey("medianas.frecuencia_porcentaje") && before.containsKey("aldeas.separacion_bloques"));
		assertFalse(before.containsKey("arena.generar_en_mundos_nuevos"), "the arena is not a seam");
		assertFalse(before.containsKey("dificultad.nivel"), "only generation");
		Map<String, JsonPrimitive> light = profiles().switchTo(Profiles.STANDARD, Profiles.LIGHT, values);
		Map<String, String> now = ProfileAdvice.fingerprint(light, profiles().generation());
		Map<String, String[]> changed = ProfileAdvice.changed(before, now);
		assertEquals(Set.copyOf(profiles().generationKeysOf(Profiles.LIGHT)), changed.keySet());
		assertTrue(ProfileAdvice.warnSeams(before, now, true, true));
		assertFalse(ProfileAdvice.warnSeams(before, now, false, true), "a new world: nothing generated to seam");
		assertFalse(ProfileAdvice.warnSeams(now, now, true, true), "nothing changed");
		// a world from before the record: only with a profile that changes generation
		assertTrue(ProfileAdvice.warnSeams(null, now, true, true));
		assertFalse(ProfileAdvice.warnSeams(null, before, true, false));
		// 2 and 2.0 are the same; an option of another version is not a change
		assertTrue(ProfileAdvice.changed(Map.of("minas.vanilla.multiplicador", "2"), Map.of("minas.vanilla.multiplicador", "2.0")).isEmpty());
		assertTrue(ProfileAdvice.changed(Map.of("vieja", "1"), Map.of("nueva", "2")).isEmpty());
	}
}
