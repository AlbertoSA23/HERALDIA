package io.github.albertosa23.heraldia.config;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import net.minecraft.resources.Identifier;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/** Qué aldeas puede generar una casilla (VillageRules) según la configuración: estilos, familias y tamaño. */
class VillageRulesTest {
	@TempDir
	Path dir;

	@AfterEach
	void restore() {
		HeraldiaConfig.load(null);
	}

	private VillageRules rules(String json) throws IOException {
		Path file = dir.resolve("heraldia.json");
		Files.writeString(file, json);
		return HeraldiaConfig.load(file).villages();
	}

	private static Identifier id(String path) {
		return Identifier.fromNamespaceAndPath("heraldia", path);
	}

	private static String anyStyle(String family) {
		var styles = HeraldiaConfig.get().schema().getAsJsonObject("aldeas").getAsJsonObject("estilos");
		return styles.entrySet().stream().filter(e -> e.getValue().getAsString().equals(family)).findFirst().orElseThrow().getKey();
	}

	@Test
	void lasAjenasSiempreValen() throws IOException {
		VillageRules r = rules("{}");
		assertTrue(r.allows(Identifier.fromNamespaceAndPath("minecraft", "village_plains"), 1, 0, 0));
		assertTrue(r.allows(id("unicas/castillo"), 1, 0, 0));
	}

	@Test
	void porcentajeDeGrandesExtremos() throws IOException {
		String style = anyStyle("llanuras");
		VillageRules none = rules("{\"aldeas\": {\"porcentaje_grandes\": 0}}");
		VillageRules all = rules("{\"aldeas\": {\"porcentaje_grandes\": 100}}");
		for (int k = 0; k < 200; k++) {
			assertTrue(none.allows(id(style), k, k, -k) && !none.allows(id(style + "_grande"), k, k, -k));
			assertTrue(all.allows(id(style + "_grande"), k, k, -k) && !all.allows(id(style), k, k, -k));
		}
	}

	@Test
	void unaSolaVarianteDeTamanoPorCasillaYDeterminista() throws IOException {
		String style = anyStyle("llanuras");
		VillageRules r = rules("{\"aldeas\": {\"porcentaje_grandes\": 25}}");
		int large = 0;
		for (int k = 0; k < 2000; k++) {
			boolean std = r.allows(id(style), 42, k, 3 * k), big = r.allows(id(style + "_grande"), 42, k, 3 * k);
			assertTrue(std != big, "en cada casilla vale exactamente un tamaño");
			assertEquals(big, r.allows(id(style + "_grande"), 42, k, 3 * k));
			large += big ? 1 : 0;
		}
		assertTrue(large > 400 && large < 600, "grandes: " + large + " de 2000 (25 %)");
	}

	@Test
	void familiasYEstilosDesactivados() throws IOException {
		String plains = anyStyle("llanuras"), swamp = anyStyle("pantano");
		VillageRules r = rules("{\"aldeas\": {\"familias\": {\"pantano\": false}, \"estilos\": {\"" + plains + "\": false}}}");
		for (String s : new String[]{plains, swamp}) {
			assertFalse(r.allows(id(s), 1, 0, 0) || r.allows(id(s + "_grande"), 1, 0, 0), s);
		}
		int total = HeraldiaConfig.get().schema().getAsJsonObject("aldeas").getAsJsonObject("estilos").size();
		long swampStyles = HeraldiaConfig.get().schema().getAsJsonObject("aldeas").getAsJsonObject("estilos").entrySet().stream()
				.filter(e -> e.getValue().getAsString().equals("pantano")).count();
		assertEquals(total - swampStyles - 1, r.enabledStyles());
		assertEquals(total, rules("{}").enabledStyles());
	}
}
