package io.github.albertosa23.heraldia.config;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/** Migración generalizada del fichero de configuración (T46): pasos en orden, versión, la 1 → 2 y la copia de seguridad. */
class ConfigMigrationTest {
	@TempDir
	Path dir;

	@AfterEach
	void restore() {
		HeraldiaConfig.load(null);
	}

	@Test
	void stepsInOrderAndVersion() {
		List<String> finished = new ArrayList<>();
		ConfigMigration m = new ConfigMigration(Map.of(0, (r, d) -> finished.add("0:" + d), 2, (r, d) -> finished.add("2:" + d)));
		JsonObject root = new JsonObject();
		ConfigMigration.Result r = m.migrate(root, 0, 4);
		assertEquals(List.of("0:0", "2:0"), finished);
		assertEquals(List.of(1, 3), r.noStep());
		assertEquals(4, root.get("version").getAsInt());
		assertTrue(r.migrated());
		JsonObject upToDate = new JsonObject();
		assertFalse(m.migrate(upToDate, 4, 4).migrated());
		assertFalse(upToDate.has("version"));                     // ya al día: no se toca
	}

	@Test
	void fromOneToTwoWithBackup() throws IOException {
		Path f = dir.resolve("heraldia.json");
		// un fichero de la versión 1 lo escribía el mod con todas las opciones: las que tenían el valor por defecto se quitan
		String v1 = "{\"version\": 1, \"dificultad\": {\"nivel\": \"normal\"}, \"jefes\": {\"refuerzos\": {\"porcentaje\": 150}},"
				+ " \"aldeas\": {\"porcentaje_grandes\": 40}}";
		Files.writeString(f, v1);
		HeraldiaConfig c = HeraldiaConfig.load(f);
		Path backup = dir.resolve("heraldia.json.v1.bak");
		assertTrue(Files.isRegularFile(backup));
		assertEquals(v1, Files.readString(backup));          // la copia es el fichero tal cual estaba
		JsonObject newValue = JsonParser.parseString(Files.readString(f)).getAsJsonObject();
		assertEquals(2, newValue.get("version").getAsInt());
		assertFalse(newValue.has("dificultad") && newValue.getAsJsonObject("dificultad").has("nivel"));
		assertEquals(150, newValue.getAsJsonObject("jefes").getAsJsonObject("refuerzos").get("porcentaje").getAsInt());
		assertEquals(40, c.getInt("aldeas.porcentaje_grandes"));
		assertEquals(150, c.getInt("jefes.refuerzos.porcentaje"));
		// al volver a arrancar ya está en la 2: ni otra copia ni cambios
		String after = Files.readString(f);
		HeraldiaConfig.load(f);
		assertEquals(after, Files.readString(f));
		try (var s = Files.list(dir)) {
			assertEquals(1, s.filter(p -> p.getFileName().toString().endsWith(".bak")).count());
		}
	}

	@Test
	void aBackupDoesNotOverwriteAnother() throws IOException {
		Path f = dir.resolve("heraldia.json");
		Files.writeString(f, "{}");
		Files.writeString(dir.resolve("heraldia.json.v0.bak"), "vieja");
		Path p = ConfigMigration.copy(f, 0);
		assertEquals("heraldia.json.v0.2.bak", p.getFileName().toString());
		assertEquals("vieja", Files.readString(dir.resolve("heraldia.json.v0.bak")));
	}

	@Test
	void reloadMakesNoBackup() throws IOException {
		Path f = dir.resolve("heraldia.json");
		Files.writeString(f, "{\"version\": 1}");
		HeraldiaConfig.readValues(f);                       // la pantalla y /heraldia reload leen sin reescribir
		assertFalse(Files.exists(dir.resolve("heraldia.json.v1.bak")));
	}
}
