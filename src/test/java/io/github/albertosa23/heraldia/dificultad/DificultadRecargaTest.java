package io.github.albertosa23.heraldia.dificultad;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonPrimitive;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.config.Recarga;
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
 * /heraldia recargar y la dificultad: tras recargar, {@link DificultadMobs#ajustar} (lo que se hace con cada mob de
 * Heraldia cargado) deja los modificadores del nivel nuevo, sin acumular los del anterior, y en normal los quita.
 */
class DificultadRecargaTest {
	@TempDir
	Path dir;

	@BeforeAll
	static void juego() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	@AfterEach
	void restaurar() {
		HeraldiaConfig.load(null);
	}

	private Path escribir(String nivel, boolean porJugadores) throws IOException {
		Path file = dir.resolve("heraldia.json");
		Map<String, JsonPrimitive> v = new LinkedHashMap<>(HeraldiaConfig.defaults());
		v.put("dificultad.nivel", new JsonPrimitive(nivel));
		v.put("dificultad.escalar_por_jugadores", new JsonPrimitive(porJugadores));
		HeraldiaConfig.save(file, v);
		return file;
	}

	private static AttributeInstance atributo(net.minecraft.core.Holder<net.minecraft.world.entity.ai.attributes.Attribute> a, double base) {
		AttributeInstance i = new AttributeInstance(a, x -> { });
		i.setBaseValue(base);
		return i;
	}

	@Test
	void recargarCambiaLosModificadoresDeLosMobsYaCargados() throws IOException {
		AttributeInstance vida = atributo(Attributes.MAX_HEALTH, 20), dano = atributo(Attributes.ATTACK_DAMAGE, 4);
		HeraldiaConfig.load(escribir("heroica", true));
		DificultadMobs.ajustar(vida, dano, HeraldiaConfig.get());
		assertEquals(40, vida.getValue(), 1e-9);
		assertEquals(6, dano.getValue(), 1e-9);
		// el extra por jugadores (lo pone el golpe) sigue mientras la opción esté activada
		DificultadMobs.poner(vida, DificultadMobs.JUGADORES, 0.5);
		assertEquals(60, vida.getValue(), 1e-9);

		Recarga.Resultado r = HeraldiaConfig.recargar(escribir("facil", false));
		assertTrue(r.aplicadas().contains("dificultad.nivel") && r.aplicadas().contains("dificultad.escalar_por_jugadores"));
		DificultadMobs.ajustar(vida, dano, HeraldiaConfig.get());
		assertEquals(15, vida.getValue(), 1e-9, "fácil x0,75 y sin el extra por jugadores");
		assertEquals(3, dano.getValue(), 1e-9);
		assertNull(vida.getModifier(DificultadMobs.JUGADORES));
		AttributeModifier m = vida.getModifier(DificultadMobs.VIDA);
		assertEquals(-0.25, m.amount(), 1e-9);
		assertEquals(AttributeModifier.Operation.ADD_MULTIPLIED_TOTAL, m.operation());

		HeraldiaConfig.recargar(escribir("normal", false));
		DificultadMobs.ajustar(vida, dano, HeraldiaConfig.get());
		assertNull(vida.getModifier(DificultadMobs.VIDA), "normal: sin modificadores, como siempre");
		assertNull(dano.getModifier(DificultadMobs.DANO));
		assertEquals(20, vida.getValue(), 1e-9);
		assertEquals(4, dano.getValue(), 1e-9);
	}

	@Test
	void laVidaActualConservaLaProporcionAlRecargar() {
		// lo que hace ajustarVida con un mob a media vida al pasar de normal (20) a heroica (40) y luego a fácil (15)
		float v = Dificultad.reajustarVida(10, 20, 40);
		assertEquals(20, v, 1e-6);
		assertEquals(7.5f, Dificultad.reajustarVida(v, 40, 15), 1e-6);
	}
}
