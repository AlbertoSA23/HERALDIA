package io.github.albertosa23.heraldia.dificultad;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.config.Recarga;
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
 * /heraldia reload con el perfil de juego (T36): cambiar «perfil» en el fichero y recargar aplica todas sus opciones sin
 * reiniciar (son recargables), recalcula la dificultad de los mobs ya cargados y no deja nada pendiente; una opción
 * fijada a mano sigue mandando tras recargar.
 */
class PerfilRecargaTest {
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

	private Path fichero(String json) throws IOException {
		Path f = dir.resolve("heraldia.json");
		Files.writeString(f, json);
		return f;
	}

	@Test
	void todasLasOpcionesDelPerfilSonRecargables() {
		assertTrue(Recarga.recargable("perfil"));
		for (String k : HeraldiaConfig.profiles().claves()) {
			assertTrue(Recarga.recargable(k), k);
		}
	}

	@Test
	void recargarElPerfilRecalculaLaDificultad() throws IOException {
		AttributeInstance vida = new AttributeInstance(Attributes.MAX_HEALTH, x -> { });
		vida.setBaseValue(20);
		AttributeInstance dano = new AttributeInstance(Attributes.ATTACK_DAMAGE, x -> { });
		dano.setBaseValue(4);
		HeraldiaConfig.load(fichero("{\"perfil\": \"estandar\"}"));
		DificultadMobs.ajustar(vida, dano, HeraldiaConfig.get());
		assertEquals(20, vida.getValue(), 1e-9);

		Recarga.Resultado r = HeraldiaConfig.recargar(fichero("{\"version\": 2, \"perfil\": \"hardcore\"}"));
		assertTrue(r.pendientes().isEmpty(), "nada espera al reinicio: " + r.pendientes());
		assertTrue(r.aplicadas().contains("perfil") && r.aplicadas().contains("dificultad.nivel"), r.aplicadas().toString());
		assertEquals("hardcore", HeraldiaConfig.get().profile().efectivo());
		assertEquals(6, HeraldiaConfig.get().getInt("jefes.refuerzos.maximo_vivos"));
		DificultadMobs.ajustar(vida, dano, HeraldiaConfig.get());
		assertEquals(40, vida.getValue(), 1e-9, "heroica x2");

		r = HeraldiaConfig.recargar(fichero("{\"version\": 2, \"perfil\": \"casual\", \"dificultad\": {\"nivel\": \"dificil\"}}"));
		assertTrue(r.pendientes().isEmpty());
		assertEquals("personalizado", HeraldiaConfig.get().profile().efectivo());
		assertEquals(12, HeraldiaConfig.get().getInt("arena.max_mobs_vivos"), "lo demás, del perfil casual");
		DificultadMobs.ajustar(vida, dano, HeraldiaConfig.get());
		assertEquals(30, vida.getValue(), 1e-9, "manda lo fijado a mano: difícil x1,5");
	}
}
