package io.github.albertosa23.heraldia.mixin;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.TreeSet;
import java.util.stream.Stream;
import org.junit.jupiter.api.Test;

/**
 * The mixin configuration names real classes (T45, final audit): T47b renamed seven mixins without updating
 * heraldia.mixins.json, which is "required", so the mod did not start; no other JUnit test reads the file. Every class
 * listed exists in the package and every *Mixin.java of the package is listed (none is forgotten).
 */
class MixinConfigTest {
	private static final String PACKAGE = "io.github.albertosa23.heraldia.mixin";

	@Test
	void everyListedMixinExistsAndEveryMixinIsListed() throws IOException {
		JsonObject cfg;
		try (InputStream in = MixinConfigTest.class.getClassLoader().getResourceAsStream("heraldia.mixins.json")) {
			assertNotNull(in, "heraldia.mixins.json is not on the classpath");
			cfg = JsonParser.parseReader(new InputStreamReader(in, StandardCharsets.UTF_8)).getAsJsonObject();
		}
		assertEquals(PACKAGE, cfg.get("package").getAsString());
		List<String> listed = new ArrayList<>();
		for (String section : List.of("mixins", "client", "server")) {
			if (cfg.has(section)) {
				cfg.getAsJsonArray(section).forEach(e -> listed.add(e.getAsString()));
			}
		}
		for (String name : listed) {
			String resource = PACKAGE.replace('.', '/') + "/" + name.replace('.', '/') + ".class";
			assertNotNull(MixinConfigTest.class.getClassLoader().getResource(resource), "mixin listed but missing: " + name);
		}
		Path dir = Path.of("src/main/java", PACKAGE.replace('.', '/'));
		assertTrue(Files.isDirectory(dir), "run from the project folder: " + dir.toAbsolutePath());
		TreeSet<String> sources = new TreeSet<>();
		try (Stream<Path> files = Files.list(dir)) {
			files.map(p -> p.getFileName().toString()).filter(f -> f.endsWith("Mixin.java"))
					.forEach(f -> sources.add(f.substring(0, f.length() - ".java".length())));
		}
		assertEquals(sources, new TreeSet<>(listed), "the mixins of the package and those of heraldia.mixins.json differ");
	}
}
