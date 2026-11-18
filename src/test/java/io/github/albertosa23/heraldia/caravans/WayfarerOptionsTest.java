package io.github.albertosa23.heraldia.caravans;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonPrimitive;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.config.Reload;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import net.minecraft.SharedConstants;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.Identifier;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.item.DyeColor;
import net.minecraft.world.item.Items;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/** The wayfarer options (defaults, reloadable, their section, each kind off on its own) and that what they carry exists in 26.3. */
class WayfarerOptionsTest {
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

	@Test
	void defaultsReloadableAndTheirSection() {
		HeraldiaConfig.load(null);
		HeraldiaConfig c = HeraldiaConfig.get();
		assertTrue(c.getBool(Wayfarers.ENABLED));
		assertEquals(30, c.getInt(Wayfarers.FREQUENCY));
		assertEquals(1, c.getInt(Wayfarers.MAX_ACTIVE));
		List<String> keys = new java.util.ArrayList<>(List.of(Wayfarers.ENABLED, Wayfarers.FREQUENCY, Wayfarers.MAX_ACTIVE));
		for (Wayfarers.Kind k : Wayfarers.Kind.values()) {
			assertTrue(c.getBool(k.option()), k.option());
			keys.add(k.option());
		}
		for (String k : keys) {
			assertTrue(Reload.reloadable(k), k + " applies without restarting");
			assertEquals("viajeros", CaravanOptionsTest.option(k).section(), k);
		}
		assertTrue(HeraldiaConfig.sections().containsKey("viajeros"));
	}

	@Test
	void eachKindOffOnItsOwnAndOutOfRange() throws IOException {
		Path file = dir.resolve("heraldia.json");
		Map<String, JsonPrimitive> v = new LinkedHashMap<>(HeraldiaConfig.defaults());
		v.put(Wayfarers.Kind.SHEPHERD.option(), new JsonPrimitive(false));
		v.put(Wayfarers.MAX_ACTIVE, new JsonPrimitive(3));
		HeraldiaConfig.save(file, v);
		HeraldiaConfig.load(file);
		assertFalse(HeraldiaConfig.get().getBool(Wayfarers.Kind.SHEPHERD.option()));
		assertTrue(HeraldiaConfig.get().getBool(Wayfarers.Kind.HUNTER.option()), "the others stay");
		assertTrue(HeraldiaConfig.get().getBool(Wayfarers.ENABLED));
		assertEquals(3, HeraldiaConfig.get().getInt(Wayfarers.MAX_ACTIVE));
		Files.writeString(file, "{\"viajeros\": {\"max_activos\": 9, \"frecuencia\": 140}}");
		HeraldiaConfig.load(file);
		assertEquals(1, HeraldiaConfig.get().getInt(Wayfarers.MAX_ACTIVE), "from 1 to 3");
		assertEquals(30, HeraldiaConfig.get().getInt(Wayfarers.FREQUENCY), "from 0 to 100");
		// independent of the caravans
		Files.writeString(file, "{\"caravanas\": {\"activado\": false}}");
		HeraldiaConfig.load(file);
		assertTrue(HeraldiaConfig.get().getBool(Wayfarers.ENABLED));
	}

	@Test
	void theLightProfileLeavesThemAsTheyAre() throws IOException {
		// a profile option changes the file format (LESSONS): the wayfarers are not one; the administrator turns them off by hand
		Path file = dir.resolve("heraldia.json");
		Files.writeString(file, "{\"perfil\": \"ligero\"}");
		HeraldiaConfig.load(file);
		assertTrue(HeraldiaConfig.get().getBool(Wayfarers.ENABLED));
		assertFalse(HeraldiaConfig.get().getBool(Caravans.ENABLED));
	}

	@Test
	void whatTheyCarryAndSellExists() {
		for (Wayfarers.Kind k : Wayfarers.Kind.values()) {
			for (String z : Wayfarers.FAMILIES) {
				String held = Wayfarers.held(k, z);
				if (held != null) {
					assertNotEquals(Items.AIR, Wayfaring.item(held), held);
				}
				for (Wayfarers.Trade t : Wayfarers.trades(k, z, List.of("white", "light_gray", "gray", "black", "brown", "pink"))) {
					for (String id : List.of(t.cost(), t.result())) {
						assertTrue(BuiltInRegistries.ITEM.containsKey(Identifier.parse(id)), id);
					}
				}
				for (int i = 0; i < 20; i++) {
					String c = Wayfarers.woolColor(z, i / 20.0);
					assertNotNull(DyeColor.byName(c, null), c);
				}
			}
		}
		for (Wayfarers.Prey p : Wayfarers.Prey.values()) {
			for (String id : List.of(p.raw, p.cooked, p.byproduct)) {
				assertTrue(BuiltInRegistries.ITEM.containsKey(Identifier.parse(id)), id);
			}
		}
	}
}
