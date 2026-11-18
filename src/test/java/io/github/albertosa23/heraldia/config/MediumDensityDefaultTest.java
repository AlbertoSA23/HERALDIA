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
import java.util.Map;
import java.util.Set;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * The lower default density of the medium structures (medianas.frecuencia_porcentaje) and the existing worlds: the old
 * density (100) is still an option; a value written by hand in the file never changes with the update (whatever the file
 * format); what the mod wrote on its own with the old default (formats 1 and 2) is not "by hand"; and the seam warning fires
 * in a world already played that now gets the new default, with or without the record of its generation options.
 */
class MediumDensityDefaultTest {
	private static final String KEY = "medianas.frecuencia_porcentaje";
	private static final int OLD = 100;

	@TempDir
	Path dir;

	@AfterEach
	void restore() {
		HeraldiaConfig.load(null);
	}

	private static int newDefault() {
		return HeraldiaConfig.defaults().get(KEY).getAsInt();
	}

	private Path file(String content) throws IOException {
		Path f = dir.resolve("heraldia.json");
		Files.writeString(f, content);
		return f;
	}

	private static JsonObject json(Path f) throws IOException {
		return JsonParser.parseString(Files.readString(f, StandardCharsets.UTF_8)).getAsJsonObject();
	}

	private static JsonPrimitive written(Path f) throws IOException {
		JsonObject m = json(f).getAsJsonObject("medianas");
		return m != null && m.has("frecuencia_porcentaje") ? m.getAsJsonPrimitive("frecuencia_porcentaje") : null;
	}

	@Test
	void theDefaultIsLowerAndTheOldDensityIsStillAnOption() {
		int now = newDefault();
		assertTrue(now < OLD, "fewer medium structures by default: " + now);
		assertEquals(Integer.parseInt(ProfileAdvice.PREVIOUS_DEFAULTS.get(KEY)), OLD);
		ConfigOption o = HeraldiaConfig.options().stream().filter(x -> x.key().equals(KEY)).findFirst().orElseThrow();
		assertTrue(o.accept(new JsonPrimitive(OLD)).isPresent(), "100 (the density before) is still accepted");
		Profiles ps = HeraldiaConfig.profiles();
		assertEquals(now, ps.optionValues(Profiles.STANDARD).get(KEY).getAsInt(), "the standard profile is the default");
		assertTrue(ps.optionValues(Profiles.LIGHT).get(KEY).getAsInt() <= now, "the light profile is never denser than the default");
		assertEquals(now, HeraldiaConfig.get().getInt(KEY));
	}

	@Test
	void writtenByHandInTheCurrentFormatItStays() throws IOException {
		Path f = file("{\"version\": 3, \"perfil\": \"estandar\", \"medianas\": {\"frecuencia_porcentaje\": 100}}");
		HeraldiaConfig c = HeraldiaConfig.load(f);
		assertEquals(OLD, c.getInt(KEY), "the old density, kept");
		assertTrue(c.profile().pinned().containsKey(KEY));
		assertEquals(OLD, written(f).getAsInt(), "rewritten at startup with the value by hand");
		assertEquals(OLD, HeraldiaConfig.load(f).getInt(KEY), "and on every later start");
	}

	@Test
	void writtenByHandWithoutVersionItStays() throws IOException {
		// format 0: a file written by hand (the mod always writes "version")
		Path f = file("{\"medianas\": {\"frecuencia_porcentaje\": 100}}");
		assertEquals(OLD, HeraldiaConfig.load(f).getInt(KEY));
		assertEquals(OLD, written(f).getAsInt());
	}

	@Test
	void writtenByTheModWithTheOldDefaultIsNotByHand() throws IOException {
		// formats 1 and 2: the mod wrote every option, frecuencia_porcentaje too, with the default of then (100)
		for (int version : new int[] {1, 2}) {
			Path f = file("{\"version\": " + version + ", \"medianas\": {\"frecuencia_porcentaje\": 100, \"activadas\": true}}");
			HeraldiaConfig c = HeraldiaConfig.load(f);
			assertEquals(newDefault(), c.getInt(KEY), "format " + version + ": the mod's own value is not by hand");
			assertFalse(c.profile().pinned().containsKey(KEY));
			assertEquals(null, written(f), "removed from the file, as with the other profile options");
		}
		// another value in those formats was set by hand: it stays
		Path f = file("{\"version\": 2, \"medianas\": {\"frecuencia_porcentaje\": 150}}");
		assertEquals(150, HeraldiaConfig.load(f).getInt(KEY));
		assertEquals(150, written(f).getAsInt());
	}

	@Test
	void writtenByDefaultOnlyForTheOldDefault() {
		assertTrue(HeraldiaConfig.writtenByDefault(KEY, new JsonPrimitive(100)));
		assertTrue(HeraldiaConfig.writtenByDefault(KEY, new JsonPrimitive(100.0)));
		assertFalse(HeraldiaConfig.writtenByDefault(KEY, new JsonPrimitive(150)));
		assertFalse(HeraldiaConfig.writtenByDefault("medianas.distancia_minima.bloques", new JsonPrimitive(192)));
	}

	@Test
	void previousDefaultsAreProfileOptions() {
		// only profile options: for those the file says whether they are set by hand
		assertTrue(HeraldiaConfig.profiles().keys().containsAll(ProfileAdvice.PREVIOUS_DEFAULTS.keySet()));
		assertTrue(HeraldiaConfig.profiles().generation().containsAll(ProfileAdvice.PREVIOUS_DEFAULTS.keySet()));
	}

	private static Map<String, String> fingerprint(HeraldiaConfig c) {
		return ProfileAdvice.fingerprint(c.values(), HeraldiaConfig.profiles().generation());
	}

	@Test
	void seamsInAWorldWithTheRecord() throws IOException {
		// the record of the last start says 100; now it starts with the new default
		Map<String, String> stored = new LinkedHashMap<>(fingerprint(HeraldiaConfig.load(null)));
		stored.put(KEY, String.valueOf(OLD));
		Map<String, String> now = fingerprint(HeraldiaConfig.load(null));
		Map<String, String[]> changed = ProfileAdvice.changed(stored, now);
		assertEquals(Set.of(KEY), changed.keySet());
		assertEquals("100", changed.get(KEY)[0]);
		assertEquals(String.valueOf(newDefault()), changed.get(KEY)[1]);
		assertTrue(ProfileAdvice.warnSeams(stored, now, true, false, Map.of()));
		assertFalse(ProfileAdvice.warnSeams(stored, now, false, false, Map.of()), "a new world: nothing to seam");
		// with 100 by hand, nothing changed: no warning
		Map<String, String> kept = fingerprint(HeraldiaConfig.load(file("{\"version\": 3, \"medianas\": {\"frecuencia_porcentaje\": 100}}")));
		assertFalse(ProfileAdvice.warnSeams(stored, kept, true, false, Map.of()));
	}

	@Test
	void seamsInAWorldFromBeforeTheRecord() throws IOException {
		HeraldiaConfig c = HeraldiaConfig.load(null);
		Map<String, String> now = fingerprint(c);
		Map<String, String[]> fromDefaults = ProfileAdvice.defaultChanges(now, c.profile().pinned().keySet());
		assertEquals(Set.of(KEY), fromDefaults.keySet(), "the default changed: this world had 100");
		assertEquals("100", fromDefaults.get(KEY)[0]);
		assertEquals(String.valueOf(newDefault()), fromDefaults.get(KEY)[1]);
		assertTrue(ProfileAdvice.warnSeams(null, now, true, false, fromDefaults), "warned with the standard profile too");
		assertFalse(ProfileAdvice.warnSeams(null, now, false, false, fromDefaults), "a new world: nothing to seam");
		assertNotEquals(String.valueOf(OLD), now.get(KEY));
		// with the value by hand (100 or another one), the update changes nothing in that world: no warning
		for (String v : new String[] {"100", "150"}) {
			HeraldiaConfig h = HeraldiaConfig.load(file("{\"version\": 3, \"medianas\": {\"frecuencia_porcentaje\": " + v + "}}"));
			Map<String, String> hn = fingerprint(h);
			Map<String, String[]> d = ProfileAdvice.defaultChanges(hn, h.profile().pinned().keySet());
			assertTrue(d.isEmpty(), v + " by hand");
			assertFalse(ProfileAdvice.warnSeams(null, hn, true, false, d), v + " by hand");
		}
		// the light profile: warned for the profile, and the frequency it gives is listed too
		HeraldiaConfig l = HeraldiaConfig.load(file("{\"perfil\": \"ligero\"}"));
		Map<String, String> ln = fingerprint(l);
		Map<String, String[]> ld = ProfileAdvice.defaultChanges(ln, l.profile().pinned().keySet());
		assertEquals(String.valueOf(HeraldiaConfig.profiles().optionValues(Profiles.LIGHT).get(KEY).getAsInt()), ld.get(KEY)[1]);
		assertTrue(ProfileAdvice.warnSeams(null, ln, true, true, ld));
	}
}
