package io.github.albertosa23.heraldia.huts;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import io.github.albertosa23.heraldia.config.ConfigOption;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.config.Reload;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import net.minecraft.SharedConstants;
import net.minecraft.server.Bootstrap;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/** Opciones de las chozas de mago y el botín del Mago Malvado tal como lo escribe el generador. */
class HutOptionsTest {
	private static Path data;

	@BeforeAll
	static void game() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
		data = Path.of(System.getProperty("heraldia.generated", "build/generated/heraldia"));
	}

	@AfterEach
	void restore() {
		HeraldiaConfig.load(null);
	}

	private static ConfigOption option(String k) {
		return HeraldiaConfig.options().stream().filter(o -> o.key().equals(k)).findFirst().orElseThrow();
	}

	@Test
	void defaultReloadableAndInTheirSection() {
		HeraldiaConfig.load(null);
		assertEquals(20, HeraldiaConfig.get().getInt(Wizards.EVIL_PROB));
		assertEquals(30, HeraldiaConfig.get().getInt(Wizards.PREMIUM_PROB));
		for (String k : List.of(Wizards.EVIL_PROB, Wizards.PREMIUM_PROB)) {
			assertTrue(Reload.reloadable(k), k);
			assertEquals("chozas_mago", option(k).section());
		}
		assertTrue(HeraldiaConfig.sections().containsKey("chozas_mago"));
	}

	private static JsonObject json(String route) throws IOException {
		return JsonParser.parseString(Files.readString(data.resolve(route))).getAsJsonObject();
	}

	private static List<String> items(JsonElement e) {
		List<String> out = new ArrayList<>();
		if (e.isJsonObject()) {
			JsonObject o = e.getAsJsonObject();
			if (o.has("type") && o.get("type").getAsString().equals("minecraft:item")) {
				out.add(o.get("name").getAsString());
			}
			o.entrySet().forEach(x -> out.addAll(items(x.getValue())));
		} else if (e.isJsonArray()) {
			for (JsonElement x : e.getAsJsonArray()) {
				out.addAll(items(x));
			}
		}
		return out;
	}

	@Test
	void lootWithoutBreakingProgression() throws IOException {
		JsonObject normal = json("data/heraldia/loot_table/chozas_mago/malvado.json");
		JsonObject premium = json("data/heraldia/loot_table/chozas_mago/malvado_premium.json");
		for (JsonObject t : List.of(normal, premium)) {
			for (String o : items(t)) {
				assertFalse(o.contains("netherite") || o.contains("elytra") || o.contains("enchanted_golden_apple"), o);
			}
			// solo si lo vence un jugador
			for (JsonElement p : t.getAsJsonArray("pools")) {
				assertEquals("minecraft:killed_by_player", p.getAsJsonObject().getAsJsonObject("condition").get("type").getAsString());
			}
		}
		JsonArray np = normal.getAsJsonArray("pools"), pp = premium.getAsJsonArray("pools");
		assertEquals(np.size() + 1, pp.size(), "premium = la normal más el grupo del premio");
		for (int i = 0; i < np.size(); i++) {
			assertEquals(np.get(i), pp.get(i));
		}
		// el tótem solo en el premio (el Mago Malvado no suelta el del evocador)
		assertFalse(items(normal).contains("minecraft:totem_of_undying"));
		List<String> prize = items(pp.get(pp.size() - 1));
		assertTrue(prize.contains("minecraft:totem_of_undying"));
		String txt = pp.get(pp.size() - 1).toString();
		assertTrue(txt.contains("minecraft:mending") && txt.contains("turtle_master") && txt.contains("long_slow_falling"), txt);
		// más que una mediana: algo que las medianas no pueden dar (diamantes, libros de nivel alto)
		assertTrue(items(normal).contains("minecraft:diamond"));
	}

	@Test
	void namesForJava() throws IOException {
		JsonObject o = json("heraldia/chozas_mago.json");
		assertEquals(16, o.getAsJsonArray("nombres").size());
		assertEquals(8, o.get("apodos").getAsInt());
	}
}
