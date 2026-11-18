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
import java.util.Map;
import java.util.Set;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * The default density of the medium structures (medianas.frecuencia_porcentaje) and the existing worlds. The default is 100
 * (each type at its own spacing); the medium-density session lowered it to 60 for a few hours and it went back to 100. Checked:
 * the default is 100 and the light profile stays lower; a value written by hand in the file never changes with the update
 * (whatever the file format, 60 included); what the mod wrote on its own with 100 (formats 1 and 2) is not "by hand"; a world
 * started with the 60 of those hours (it has the record of its generation options) is warned about the seam of going back to
 * 100; and a world from before the record (generated with 100) is not, unless a profile changes its generation.
 */
class MediumDensityDefaultTest {
	private static final String KEY = "medianas.frecuencia_porcentaje";
	/** The default, before the medium-density session and again now; the value a world without the record was generated with. */
	private static final int DEFAULT = 100;
	/** The default of those few hours. */
	private static final int INTERIM = 60;

	@TempDir
	Path dir;

	@AfterEach
	void restore() {
		HeraldiaConfig.load(null);
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

	private static int light() {
		return HeraldiaConfig.profiles().optionValues(Profiles.LIGHT).get(KEY).getAsInt();
	}

	@Test
	void theDefaultIs100AndTheLightProfileStaysLower() {
		assertEquals(DEFAULT, HeraldiaConfig.defaults().get(KEY).getAsInt(), "a world full of structures");
		assertEquals(String.valueOf(DEFAULT), ProfileAdvice.PREVIOUS_DEFAULTS.get(KEY), "a world without the record had 100");
		ConfigOption o = HeraldiaConfig.options().stream().filter(x -> x.key().equals(KEY)).findFirst().orElseThrow();
		assertTrue(o.accept(new JsonPrimitive(INTERIM)).isPresent(), "60 (the default of those hours) is still accepted");
		Profiles ps = HeraldiaConfig.profiles();
		assertEquals(DEFAULT, ps.optionValues(Profiles.STANDARD).get(KEY).getAsInt(), "the standard profile is the default");
		assertTrue(light() < DEFAULT, "the light profile has fewer medium structures than the default: " + light());
		assertTrue(o.accept(new JsonPrimitive(light())).isPresent());
		assertEquals(DEFAULT, HeraldiaConfig.get().getInt(KEY));
	}

	@Test
	void writtenByHandInTheCurrentFormatItStays() throws IOException {
		for (int v : new int[] {INTERIM, 150}) {
			Path f = file("{\"version\": 3, \"perfil\": \"estandar\", \"medianas\": {\"frecuencia_porcentaje\": " + v + "}}");
			HeraldiaConfig c = HeraldiaConfig.load(f);
			assertEquals(v, c.getInt(KEY), v + " by hand, kept");
			assertTrue(c.profile().pinned().containsKey(KEY));
			assertEquals(v, written(f).getAsInt(), "rewritten at startup with the value by hand");
			assertEquals(v, HeraldiaConfig.load(f).getInt(KEY), "and on every later start");
		}
	}

	@Test
	void writtenByHandWithoutVersionItStays() throws IOException {
		// format 0: a file written by hand (the mod always writes "version")
		Path f = file("{\"medianas\": {\"frecuencia_porcentaje\": 60}}");
		assertEquals(INTERIM, HeraldiaConfig.load(f).getInt(KEY));
		assertEquals(INTERIM, written(f).getAsInt());
	}

	@Test
	void writtenByTheModWith100IsNotByHand() throws IOException {
		// formats 1 and 2: the mod wrote every option, frecuencia_porcentaje too, with the default of then (100)
		for (int version : new int[] {1, 2}) {
			Path f = file("{\"version\": " + version + ", \"medianas\": {\"frecuencia_porcentaje\": 100, \"activadas\": true}}");
			HeraldiaConfig c = HeraldiaConfig.load(f);
			assertEquals(DEFAULT, c.getInt(KEY), "format " + version);
			assertFalse(c.profile().pinned().containsKey(KEY), "format " + version + ": the mod's own value is not by hand");
			assertEquals(null, written(f), "removed from the file, as with the other profile options");
		}
		// another value in those formats was set by hand: it stays
		Path f = file("{\"version\": 2, \"medianas\": {\"frecuencia_porcentaje\": 150}}");
		assertEquals(150, HeraldiaConfig.load(f).getInt(KEY));
		assertEquals(150, written(f).getAsInt());
	}

	@Test
	void writtenByDefaultOnlyFor100() {
		assertTrue(HeraldiaConfig.writtenByDefault(KEY, new JsonPrimitive(100)));
		assertTrue(HeraldiaConfig.writtenByDefault(KEY, new JsonPrimitive(100.0)));
		assertFalse(HeraldiaConfig.writtenByDefault(KEY, new JsonPrimitive(60)), "the mod never wrote 60 on its own (format 3)");
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
	void aWorldStartedWithThe60IsWarnedWhenItGoesBackTo100() throws IOException {
		// the record of the last start says 60 (a world started during those hours); now it starts with the default
		Map<String, String> stored = new LinkedHashMap<>(fingerprint(HeraldiaConfig.load(null)));
		stored.put(KEY, String.valueOf(INTERIM));
		Map<String, String> now = fingerprint(HeraldiaConfig.load(null));
		Map<String, String[]> changed = ProfileAdvice.changed(stored, now);
		assertEquals(Set.of(KEY), changed.keySet());
		assertEquals("60", changed.get(KEY)[0]);
		assertEquals("100", changed.get(KEY)[1]);
		assertTrue(ProfileAdvice.warnSeams(stored, now, true, false, Map.of()), "already generated at 60, new land at 100: a seam");
		assertFalse(ProfileAdvice.warnSeams(stored, now, false, false, Map.of()), "a new world: nothing to seam");
		// with 60 by hand, nothing changed: no warning
		Map<String, String> kept = fingerprint(HeraldiaConfig.load(file("{\"version\": 3, \"medianas\": {\"frecuencia_porcentaje\": 60}}")));
		assertFalse(ProfileAdvice.warnSeams(stored, kept, true, false, Map.of()));
		// a world recorded with 100 (before those hours, or after) starting with the default: no warning
		Map<String, String> at100 = new LinkedHashMap<>(stored);
		at100.put(KEY, "100");
		assertFalse(ProfileAdvice.warnSeams(at100, now, true, false, Map.of()));
	}

	@Test
	void aWorldFromBeforeTheRecordHasNoSeamWithTheDefault() throws IOException {
		HeraldiaConfig c = HeraldiaConfig.load(null);
		Map<String, String> now = fingerprint(c);
		Map<String, String[]> fromDefaults = ProfileAdvice.defaultChanges(now, c.profile().pinned().keySet());
		assertTrue(fromDefaults.isEmpty(), "generated with 100, and 100 it is");
		assertFalse(ProfileAdvice.warnSeams(null, now, true, false, fromDefaults));
		// by hand, the update changes nothing in that world: no warning
		for (String v : new String[] {"60", "100", "150"}) {
			HeraldiaConfig h = HeraldiaConfig.load(file("{\"version\": 3, \"medianas\": {\"frecuencia_porcentaje\": " + v + "}}"));
			Map<String, String> hn = fingerprint(h);
			Map<String, String[]> d = ProfileAdvice.defaultChanges(hn, h.profile().pinned().keySet());
			assertTrue(d.isEmpty(), v + " by hand");
			assertFalse(ProfileAdvice.warnSeams(null, hn, true, false, d), v + " by hand");
		}
		// the light profile: warned for the profile, and the frequency it gives is listed too (100 → 50)
		HeraldiaConfig l = HeraldiaConfig.load(file("{\"perfil\": \"ligero\"}"));
		Map<String, String> ln = fingerprint(l);
		Map<String, String[]> ld = ProfileAdvice.defaultChanges(ln, l.profile().pinned().keySet());
		assertEquals("100", ld.get(KEY)[0]);
		assertEquals(String.valueOf(light()), ld.get(KEY)[1]);
		assertTrue(ProfileAdvice.warnSeams(null, ln, true, true, ld));
	}
}
