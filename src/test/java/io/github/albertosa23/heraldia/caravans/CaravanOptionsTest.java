package io.github.albertosa23.heraldia.caravans;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonPrimitive;
import io.github.albertosa23.heraldia.config.ConfigOption;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.config.Reload;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.Map;
import net.minecraft.SharedConstants;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.level.block.Blocks;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/** Las opciones de las caravanas (por defecto, recargables, desactivadas, el perfil) y qué cuenta como camino. */
class CaravanOptionsTest {
	@TempDir
	Path dir;

	@BeforeAll
	static void game() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	@AfterEach
	void restore() {
		HeraldiaConfig.load(null);
	}

	static ConfigOption option(String k) {
		return HeraldiaConfig.options().stream().filter(o -> o.key().equals(k)).findFirst().orElseThrow();
	}

	@Test
	void defaultAndReloadable() {
		HeraldiaConfig.load(null);
		HeraldiaConfig c = HeraldiaConfig.get();
		assertTrue(c.getBool(Caravans.ENABLED));
		assertEquals(10, c.getInt(Caravans.FREQUENCY));
		assertEquals(35, c.getInt(Caravans.AMBUSH_PROB));
		assertEquals(1, c.getInt(Caravans.MAX_ACTIVE));
		for (String k : new String[]{Caravans.ENABLED, Caravans.FREQUENCY, Caravans.AMBUSH_PROB, Caravans.MAX_ACTIVE}) {
			assertTrue(Reload.reloadable(k), k + " se aplica sin reiniciar");
			assertEquals("caravanas", option(k).section());
		}
		assertTrue(HeraldiaConfig.sections().containsKey("caravanas"));
	}

	@Test
	void disabledAndReloaded() throws IOException {
		Path file = dir.resolve("heraldia.json");
		Map<String, JsonPrimitive> v = new LinkedHashMap<>(HeraldiaConfig.defaults());
		v.put(Caravans.ENABLED, new JsonPrimitive(false));
		v.put(Caravans.MAX_ACTIVE, new JsonPrimitive(3));
		HeraldiaConfig.save(file, v);
		HeraldiaConfig.load(file);
		HeraldiaConfig c = HeraldiaConfig.get();
		assertFalse(c.getBool(Caravans.ENABLED));
		// desactivadas, el sorteo nunca saca una aunque todo lo demás lo permita
		assertFalse(Rules.outcome(c.getBool(Caravans.ENABLED), 0, c.getInt(Caravans.MAX_ACTIVE), 1_000_000, 0, 100, 0));
		assertEquals(3, c.getInt(Caravans.MAX_ACTIVE));
		v.put(Caravans.ENABLED, new JsonPrimitive(true));
		v.put(Caravans.FREQUENCY, new JsonPrimitive(0));
		HeraldiaConfig.save(file, v);
		Reload.Result r = HeraldiaConfig.reload(file);
		assertTrue(r.applied().contains(Caravans.ENABLED));
		assertTrue(r.pending().isEmpty(), "nada espera al reinicio");
		assertTrue(HeraldiaConfig.get().getBool(Caravans.ENABLED));
		assertFalse(Rules.outcome(true, 0, 3, 1_000_000, 0, HeraldiaConfig.get().getInt(Caravans.FREQUENCY), 0), "frecuencia 0: solo el comando");
	}

	@Test
	void outOfRangeKeepsDefault() throws IOException {
		Path file = dir.resolve("heraldia.json");
		Files.writeString(file, "{\"caravanas\": {\"max_activas\": 9, \"prob_asalto\": -3}}");
		HeraldiaConfig.load(file);
		assertEquals(1, HeraldiaConfig.get().getInt(Caravans.MAX_ACTIVE), "de 1 a 3");
		assertEquals(35, HeraldiaConfig.get().getInt(Caravans.AMBUSH_PROB));
	}

	@Test
	void casualProfileFewerAmbushesHardcoreMore() throws IOException {
		Path file = dir.resolve("heraldia.json");
		Files.writeString(file, "{\"perfil\": \"casual\"}");
		int casual = HeraldiaConfig.load(file).getInt(Caravans.AMBUSH_PROB);
		Files.writeString(file, "{\"perfil\": \"hardcore\"}");
		int hardcore = HeraldiaConfig.load(file).getInt(Caravans.AMBUSH_PROB);
		Files.writeString(file, "{\"perfil\": \"estandar\"}");
		int standard = HeraldiaConfig.load(file).getInt(Caravans.AMBUSH_PROB);
		assertTrue(casual < standard && standard < hardcore, casual + " < " + standard + " < " + hardcore);
		// el perfil no toca si salen ni cuántas a la vez
		assertEquals(1, HeraldiaConfig.get().getInt(Caravans.MAX_ACTIVE));
	}

	@Test
	void whatCountsAsRoad() {
		for (var b : new net.minecraft.world.level.block.Block[]{Blocks.DIRT_PATH, Blocks.SMOOTH_SANDSTONE, Blocks.PACKED_MUD, Blocks.GRAVEL,
				Blocks.COBBLESTONE, Blocks.OAK_PLANKS, Blocks.SPRUCE_PLANKS, Blocks.SMOOTH_RED_SANDSTONE}) {
			assertTrue(Ground.ofRoad(b.defaultBlockState()), b.toString());
		}
		for (var b : new net.minecraft.world.level.block.Block[]{Blocks.GRASS_BLOCK, Blocks.SAND, Blocks.STONE, Blocks.WATER, Blocks.SNOW_BLOCK,
				Blocks.DIRT}) {
			assertFalse(Ground.ofRoad(b.defaultBlockState()), b.toString());
		}
		assertFalse(Ground.hasRoad(3));
		assertTrue(Ground.hasRoad(4));
		assertTrue(Ground.hasRoad(9));
	}
}
