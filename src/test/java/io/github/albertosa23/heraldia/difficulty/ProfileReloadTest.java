package io.github.albertosa23.heraldia.difficulty;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.config.Reload;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import net.minecraft.SharedConstants;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.entity.ai.attributes.AttributeInstance;
import net.minecraft.world.entity.ai.attributes.Attributes;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * /heraldia reload with the gameplay profile (T36): changing "perfil" in the file and reloading applies all its options without
 * restarting (they are reloadable), recomputes the difficulty of the already loaded mobs and leaves nothing pending; an option
 * set by hand still overrides after reloading.
 */
class ProfileReloadTest {
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

	private Path file(String json) throws IOException {
		Path f = dir.resolve("heraldia.json");
		Files.writeString(f, json);
		return f;
	}

	@Test
	void allProfileOptionsAreReloadable() {
		assertTrue(Reload.reloadable("perfil"));
		for (String k : HeraldiaConfig.profiles().keys()) {
			assertTrue(Reload.reloadable(k), k);
		}
	}

	@Test
	void reloadingProfileRecomputesDifficulty() throws IOException {
		AttributeInstance health = new AttributeInstance(Attributes.MAX_HEALTH, x -> { });
		health.setBaseValue(20);
		AttributeInstance damage = new AttributeInstance(Attributes.ATTACK_DAMAGE, x -> { });
		damage.setBaseValue(4);
		HeraldiaConfig.load(file("{\"perfil\": \"estandar\"}"));
		MobDifficulty.adjust(health, damage, HeraldiaConfig.get());
		assertEquals(20, health.getValue(), 1e-9);

		Reload.Result r = HeraldiaConfig.reload(file("{\"version\": 2, \"perfil\": \"hardcore\"}"));
		assertTrue(r.pending().isEmpty(), "nada espera al reinicio: " + r.pending());
		assertTrue(r.applied().contains("perfil") && r.applied().contains("dificultad.nivel"), r.applied().toString());
		assertEquals("hardcore", HeraldiaConfig.get().profile().effective());
		assertEquals(6, HeraldiaConfig.get().getInt("jefes.refuerzos.maximo_vivos"));
		MobDifficulty.adjust(health, damage, HeraldiaConfig.get());
		assertEquals(40, health.getValue(), 1e-9, "heroica x2");

		r = HeraldiaConfig.reload(file("{\"version\": 2, \"perfil\": \"casual\", \"dificultad\": {\"nivel\": \"dificil\"}}"));
		assertTrue(r.pending().isEmpty());
		assertEquals("personalizado", HeraldiaConfig.get().profile().effective());
		assertEquals(12, HeraldiaConfig.get().getInt("arena.max_mobs_vivos"), "lo demás, del perfil casual");
		MobDifficulty.adjust(health, damage, HeraldiaConfig.get());
		assertEquals(30, health.getValue(), 1e-9, "manda lo fijado a mano: difícil x1,5");
	}
}
