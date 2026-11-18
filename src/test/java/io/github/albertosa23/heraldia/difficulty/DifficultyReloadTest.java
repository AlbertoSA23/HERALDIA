package io.github.albertosa23.heraldia.difficulty;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonPrimitive;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.config.Reload;
import java.io.IOException;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.Map;
import net.minecraft.SharedConstants;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.entity.ai.attributes.AttributeInstance;
import net.minecraft.world.entity.ai.attributes.AttributeModifier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * /heraldia reload y la dificultad: tras recargar, {@link MobDifficulty#adjust} (lo que se hace con cada mob de
 * Heraldia cargado) deja los modificadores del nivel nuevo, sin acumular los del anterior, y en normal los quita.
 */
class DifficultyReloadTest {
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

	private Path write(String tier, boolean perPlayers) throws IOException {
		Path file = dir.resolve("heraldia.json");
		Map<String, JsonPrimitive> v = new LinkedHashMap<>(HeraldiaConfig.defaults());
		v.put("dificultad.nivel", new JsonPrimitive(tier));
		v.put("dificultad.escalar_por_jugadores", new JsonPrimitive(perPlayers));
		HeraldiaConfig.save(file, v);
		return file;
	}

	private static AttributeInstance attribute(net.minecraft.core.Holder<net.minecraft.world.entity.ai.attributes.Attribute> a, double base) {
		AttributeInstance i = new AttributeInstance(a, x -> { });
		i.setBaseValue(base);
		return i;
	}

	@Test
	void reloadChangesModifiersOfAlreadyLoadedMobs() throws IOException {
		AttributeInstance health = attribute(Attributes.MAX_HEALTH, 20), damage = attribute(Attributes.ATTACK_DAMAGE, 4);
		HeraldiaConfig.load(write("heroica", true));
		MobDifficulty.adjust(health, damage, HeraldiaConfig.get());
		assertEquals(40, health.getValue(), 1e-9);
		assertEquals(6, damage.getValue(), 1e-9);
		// el extra por jugadores (lo pone el golpe) sigue mientras la opción esté activada
		MobDifficulty.put(health, MobDifficulty.PLAYERS, 0.5);
		assertEquals(60, health.getValue(), 1e-9);

		Reload.Result r = HeraldiaConfig.reload(write("facil", false));
		assertTrue(r.applied().contains("dificultad.nivel") && r.applied().contains("dificultad.escalar_por_jugadores"));
		MobDifficulty.adjust(health, damage, HeraldiaConfig.get());
		assertEquals(15, health.getValue(), 1e-9, "fácil x0,75 y sin el extra por jugadores");
		assertEquals(3, damage.getValue(), 1e-9);
		assertNull(health.getModifier(MobDifficulty.PLAYERS));
		AttributeModifier m = health.getModifier(MobDifficulty.HEALTH);
		assertEquals(-0.25, m.amount(), 1e-9);
		assertEquals(AttributeModifier.Operation.ADD_MULTIPLIED_TOTAL, m.operation());

		HeraldiaConfig.reload(write("normal", false));
		MobDifficulty.adjust(health, damage, HeraldiaConfig.get());
		assertNull(health.getModifier(MobDifficulty.HEALTH), "normal: sin modificadores, como siempre");
		assertNull(damage.getModifier(MobDifficulty.DAMAGE));
		assertEquals(20, health.getValue(), 1e-9);
		assertEquals(4, damage.getValue(), 1e-9);
	}

	@Test
	void currentHealthKeepsItsRatioOnReload() {
		// lo que hace ajustarVida con un mob a media vida al pasar de normal (20) a heroica (40) y luego a fácil (15)
		float v = ModDifficulty.readjustHealth(10, 20, 40);
		assertEquals(20, v, 1e-6);
		assertEquals(7.5f, ModDifficulty.readjustHealth(v, 40, 15), 1e-6);
	}
}
