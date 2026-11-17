package io.github.albertosa23.heraldia.caravanas;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonPrimitive;
import io.github.albertosa23.heraldia.config.ConfigOption;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.config.Recarga;
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
class CaravanasOpcionesTest {
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

	static ConfigOption opcion(String k) {
		return HeraldiaConfig.options().stream().filter(o -> o.key().equals(k)).findFirst().orElseThrow();
	}

	@Test
	void porDefectoYRecargables() {
		HeraldiaConfig.load(null);
		HeraldiaConfig c = HeraldiaConfig.get();
		assertTrue(c.getBool(Caravanas.ACTIVADO));
		assertEquals(10, c.getInt(Caravanas.FRECUENCIA));
		assertEquals(35, c.getInt(Caravanas.PROB_ASALTO));
		assertEquals(1, c.getInt(Caravanas.MAX_ACTIVAS));
		for (String k : new String[]{Caravanas.ACTIVADO, Caravanas.FRECUENCIA, Caravanas.PROB_ASALTO, Caravanas.MAX_ACTIVAS}) {
			assertTrue(Recarga.recargable(k), k + " se aplica sin reiniciar");
			assertEquals("caravanas", opcion(k).section());
		}
		assertTrue(HeraldiaConfig.sections().containsKey("caravanas"));
	}

	@Test
	void desactivadasYRecargadas() throws IOException {
		Path file = dir.resolve("heraldia.json");
		Map<String, JsonPrimitive> v = new LinkedHashMap<>(HeraldiaConfig.defaults());
		v.put(Caravanas.ACTIVADO, new JsonPrimitive(false));
		v.put(Caravanas.MAX_ACTIVAS, new JsonPrimitive(3));
		HeraldiaConfig.save(file, v);
		HeraldiaConfig.load(file);
		HeraldiaConfig c = HeraldiaConfig.get();
		assertFalse(c.getBool(Caravanas.ACTIVADO));
		// desactivadas, el sorteo nunca saca una aunque todo lo demás lo permita
		assertFalse(Reglas.sale(c.getBool(Caravanas.ACTIVADO), 0, c.getInt(Caravanas.MAX_ACTIVAS), 1_000_000, 0, 100, 0));
		assertEquals(3, c.getInt(Caravanas.MAX_ACTIVAS));
		v.put(Caravanas.ACTIVADO, new JsonPrimitive(true));
		v.put(Caravanas.FRECUENCIA, new JsonPrimitive(0));
		HeraldiaConfig.save(file, v);
		Recarga.Resultado r = HeraldiaConfig.recargar(file);
		assertTrue(r.aplicadas().contains(Caravanas.ACTIVADO));
		assertTrue(r.pendientes().isEmpty(), "nada espera al reinicio");
		assertTrue(HeraldiaConfig.get().getBool(Caravanas.ACTIVADO));
		assertFalse(Reglas.sale(true, 0, 3, 1_000_000, 0, HeraldiaConfig.get().getInt(Caravanas.FRECUENCIA), 0), "frecuencia 0: solo el comando");
	}

	@Test
	void fueraDeRangoSeQuedaElDefecto() throws IOException {
		Path file = dir.resolve("heraldia.json");
		Files.writeString(file, "{\"caravanas\": {\"max_activas\": 9, \"prob_asalto\": -3}}");
		HeraldiaConfig.load(file);
		assertEquals(1, HeraldiaConfig.get().getInt(Caravanas.MAX_ACTIVAS), "de 1 a 3");
		assertEquals(35, HeraldiaConfig.get().getInt(Caravanas.PROB_ASALTO));
	}

	@Test
	void perfilCasualMenosAsaltosYHardcoreMas() throws IOException {
		Path file = dir.resolve("heraldia.json");
		Files.writeString(file, "{\"perfil\": \"casual\"}");
		int casual = HeraldiaConfig.load(file).getInt(Caravanas.PROB_ASALTO);
		Files.writeString(file, "{\"perfil\": \"hardcore\"}");
		int hardcore = HeraldiaConfig.load(file).getInt(Caravanas.PROB_ASALTO);
		Files.writeString(file, "{\"perfil\": \"estandar\"}");
		int estandar = HeraldiaConfig.load(file).getInt(Caravanas.PROB_ASALTO);
		assertTrue(casual < estandar && estandar < hardcore, casual + " < " + estandar + " < " + hardcore);
		// el perfil no toca si salen ni cuántas a la vez
		assertEquals(1, HeraldiaConfig.get().getInt(Caravanas.MAX_ACTIVAS));
	}

	@Test
	void queCuentaComoCamino() {
		for (var b : new net.minecraft.world.level.block.Block[]{Blocks.DIRT_PATH, Blocks.SMOOTH_SANDSTONE, Blocks.PACKED_MUD, Blocks.GRAVEL,
				Blocks.COBBLESTONE, Blocks.OAK_PLANKS, Blocks.SPRUCE_PLANKS, Blocks.SMOOTH_RED_SANDSTONE}) {
			assertTrue(Suelo.delCamino(b.defaultBlockState()), b.toString());
		}
		for (var b : new net.minecraft.world.level.block.Block[]{Blocks.GRASS_BLOCK, Blocks.SAND, Blocks.STONE, Blocks.WATER, Blocks.SNOW_BLOCK,
				Blocks.DIRT}) {
			assertFalse(Suelo.delCamino(b.defaultBlockState()), b.toString());
		}
		assertFalse(Suelo.hayCamino(3));
		assertTrue(Suelo.hayCamino(4));
		assertTrue(Suelo.hayCamino(9));
	}
}
