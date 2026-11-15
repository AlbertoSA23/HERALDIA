package io.github.albertosa23.heraldia.biomas;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;

import com.google.gson.JsonElement;
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
import java.util.Map;
import java.util.stream.Stream;
import org.junit.jupiter.api.Test;

/**
 * Las etiquetas de biomas de Heraldia citan etiquetas convencionales (#c:...) que define Fabric API. El generador las
 * resuelve con la copia tools/gen/etiquetas_c.json; esta prueba compara esa copia con las del jar de Fabric API del
 * classpath (la versión de gradle.properties) y comprueba que toda #c: citada existe ahí.
 */
class BiomasTest {
	private static final String DIR = "data/c/tags/worldgen/biome/";

	private static JsonElement fabricTag(String name) throws IOException {
		try (InputStream in = BiomasTest.class.getClassLoader().getResourceAsStream(DIR + name + ".json")) {
			if (in == null) {
				return null;
			}
			return JsonParser.parseReader(new InputStreamReader(in, StandardCharsets.UTF_8)).getAsJsonObject().get("values");
		}
	}

	@Test
	void copiaIgualQueFabricApi() throws IOException {
		JsonObject copy = JsonParser.parseString(Files.readString(Path.of("tools/gen/etiquetas_c.json"))).getAsJsonObject()
				.getAsJsonObject("etiquetas");
		assertFalse(copy.isEmpty());
		for (Map.Entry<String, JsonElement> e : copy.entrySet()) {
			assertEquals(fabricTag(e.getKey()), e.getValue(), "#c:" + e.getKey() + " distinta en Fabric API");
		}
	}

	@Test
	void etiquetasCitadasExisten() throws IOException {
		Path tags = Path.of(System.getProperty("heraldia.generated"), "data/heraldia/tags/worldgen/biome");
		List<Path> files = new ArrayList<>();
		try (Stream<Path> s = Files.walk(tags)) {
			s.filter(p -> p.toString().endsWith(".json")).forEach(files::add);
		}
		assertFalse(files.isEmpty());
		for (Path f : files) {
			for (JsonElement v : JsonParser.parseString(Files.readString(f)).getAsJsonObject().getAsJsonArray("values")) {
				String id = v.isJsonObject() ? v.getAsJsonObject().get("id").getAsString() : v.getAsString();
				if (id.startsWith("#c:")) {
					assertNotNull(fabricTag(id.substring(3)), f + ": " + id + " no existe en Fabric API");
				}
			}
		}
	}
}
