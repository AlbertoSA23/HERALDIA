package io.github.albertosa23.heraldia.quests;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonPrimitive;
import io.github.albertosa23.heraldia.roads.RoadLayout;
import io.github.albertosa23.heraldia.config.ConfigOption;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.config.Reload;
import java.io.IOException;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.Map;
import net.minecraft.SharedConstants;
import net.minecraft.server.Bootstrap;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/** Las opciones de los encargos y la reputación: sus valores por defecto, que se recargan y que se respetan apagadas. */
class QuestOptionsTest {
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
		assertTrue(HeraldiaConfig.get().getBool(Quests.ENABLED));
		assertEquals(3, HeraldiaConfig.get().getInt(Quests.ROTATION));
		assertTrue(HeraldiaConfig.get().getBool(Quests.REPUTATION));
		assertTrue(Quests.enabled());
		assertTrue(Quests.withReputation());
		for (String k : new String[]{Quests.ENABLED, Quests.ROTATION, Quests.REPUTATION}) {
			assertTrue(Reload.reloadable(k), k + " se aplica sin reiniciar");
		}
		assertEquals("encargos", option(Quests.ENABLED).section());
		assertEquals("encargos", option(Quests.REPUTATION).section());
		assertTrue(HeraldiaConfig.sections().containsKey("encargos"));
	}

	@Test
	void disabled() throws IOException {
		Path file = dir.resolve("heraldia.json");
		Map<String, JsonPrimitive> v = new LinkedHashMap<>(HeraldiaConfig.defaults());
		v.put(Quests.ENABLED, new JsonPrimitive(false));
		v.put(Quests.REPUTATION, new JsonPrimitive(false));
		v.put(Quests.ROTATION, new JsonPrimitive(7));
		HeraldiaConfig.save(file, v);
		HeraldiaConfig.load(file);
		assertFalse(Quests.enabled());
		assertFalse(Quests.withReputation());
		assertEquals(7, HeraldiaConfig.get().getInt(Quests.ROTATION));
		// sin reputación, ni descuento ni reputación al entregar
		assertEquals(0, Reputation.discountFor(Reputation.Tier.HERO, 30, Quests.withReputation(), false));
		Quest e = new Quest(0, 0, 0, 0, Type.BRING, "minecraft:bread", 16, 0, 0, 3, 20);
		assertEquals(0, Data.EMPTY.accept(e).deliver(e.id(), Quests.withReputation()).reputation(e.village()));
		// y se vuelven a encender con /heraldia reload
		v.put(Quests.ENABLED, new JsonPrimitive(true));
		v.put(Quests.REPUTATION, new JsonPrimitive(true));
		HeraldiaConfig.save(file, v);
		Reload.Result r = HeraldiaConfig.reload(file);
		assertTrue(r.applied().contains(Quests.ENABLED) && r.applied().contains(Quests.REPUTATION), r.applied().toString());
		assertTrue(Quests.enabled());
		assertTrue(Quests.withReputation());
	}

	@Test
	void rotationRange() {
		ConfigOption o = option(Quests.ROTATION);
		assertEquals(1, o.min());
		assertEquals(30, o.max());
	}

	@Test
	void neighborsOfALayoutVillage() {
		int cell = 1504;
		RoadLayout.Villages villages = (gx, gz) -> RoadLayout.pack(gx * cell + 300, gz * cell + 200);
		RoadLayout t = new RoadLayout(9, cell, 2000, villages, RoadLayout.Milestones.DRY);
		long[] v = t.neighborsOf(2 * cell + 300, -cell + 200);
		assertArrayEquals(t.neighbors(2, -1), v);
		assertTrue(v.length > 0);
		assertEquals(0, t.neighborsOf(2 * cell + 301, -cell + 200).length, "no es una aldea de la rejilla");
	}

	@Test
	void villageName() {
		String n = Quests.name(42, 10, -3);
		assertEquals(n, Quests.name(42, 10, -3));
		assertEquals(2, n.split(" ", 2).length);
	}
}
