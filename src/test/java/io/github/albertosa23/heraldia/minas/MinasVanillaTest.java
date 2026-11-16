package io.github.albertosa23.heraldia.minas;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.mojang.serialization.JsonOps;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import net.minecraft.SharedConstants;
import net.minecraft.core.Vec3i;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.levelgen.structure.placement.AbstractSpreadingStructurePlacement;
import net.minecraft.world.level.levelgen.structure.placement.RandomSpreadStructurePlacement;
import net.minecraft.world.level.levelgen.structure.placement.RandomSpreadType;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * Minas abandonadas vanilla multiplicadas ({@link MinasVanillaPlacement}, minas.vanilla.multiplicador): el structure_set
 * minecraft:mineshafts que escribe el generador tiene los mismos valores que el de 26.3 (leído del propio .jar del juego),
 * con 1 la colocación es la vanilla exacta (mismo float, misma rejilla y mismo sorteo en cada chunk), con más es un
 * superconjunto (no se pierde ninguna mina de antes ni cambia de sitio) con unas k veces más, y el valor se lee de la
 * configuración. Con el sorteo de 0,004 por chunk, 200 x 200 chunks dan unas 160 minas.
 */
class MinasVanillaTest {
	private static final String RUTA = "data/minecraft/worldgen/structure_set/mineshafts.json";
	private static final long SEMILLA = 4242L;

	@TempDir
	Path dir;

	@BeforeAll
	static void bootstrap() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	@AfterEach
	void restore() {
		HeraldiaConfig.load(null);
	}

	private static List<JsonObject> sets() throws IOException {
		List<JsonObject> out = new ArrayList<>();
		for (URL u : Collections.list(MinasVanillaTest.class.getClassLoader().getResources(RUTA))) {
			try (InputStream in = u.openStream()) {
				out.add(JsonParser.parseReader(new InputStreamReader(in, StandardCharsets.UTF_8)).getAsJsonObject());
			}
		}
		return out;
	}

	private static JsonObject vanilla() throws IOException {
		return sets().stream().filter(s -> s.getAsJsonObject("placement").get("type").getAsString().equals("minecraft:random_spread"))
				.findFirst().orElseThrow();
	}

	private static JsonObject heraldia() throws IOException {
		return sets().stream().filter(s -> s.getAsJsonObject("placement").get("type").getAsString().equals("heraldia:minas_vanilla"))
				.findFirst().orElseThrow();
	}

	private static MinasVanillaPlacement con(double m) {
		return new MinasVanillaPlacement(Vec3i.ZERO, AbstractSpreadingStructurePlacement.FrequencyReductionMethod.LEGACY_TYPE_3, 0.004F, 0,
				1, 0, RandomSpreadType.LINEAR, m);
	}

	/** ¿Sale una mina en el chunk? isStructureChunk sin el estado del generador: la casilla y el sorteo de frecuencia. */
	private static boolean sale(RandomSpreadStructurePlacement p, float frecuencia, int x, int z) {
		ChunkPos c = p.getPotentialStructureChunk(SEMILLA, x, z);
		return c.x() == x && c.z() == z && AbstractSpreadingStructurePlacement.FrequencyReductionMethod.LEGACY_TYPE_3
				.shouldGenerate(SEMILLA, 0, x, z, frecuencia);
	}

	@Test
	void elSetEsElDeVanillaConElTipoPropio() throws IOException {
		JsonObject v = vanilla(), h = heraldia();
		assertNotNull(v, "el .jar del juego trae su mineshafts.json");
		assertEquals(v.get("structures"), h.get("structures"), "mismas estructuras (mineshaft y mineshaft_mesa) y pesos");
		JsonObject pv = v.getAsJsonObject("placement").deepCopy(), ph = h.getAsJsonObject("placement").deepCopy();
		pv.remove("type");
		ph.remove("type");
		assertEquals(pv, ph, "frecuencia, método, sal, separación y espaciado de 26.3");
	}

	@Test
	void conUnoEsLaVanillaExacta() throws IOException {
		RandomSpreadStructurePlacement v = RandomSpreadStructurePlacement.CODEC.codec()
				.parse(JsonOps.INSTANCE, vanilla().getAsJsonObject("placement")).getOrThrow();
		MinasVanillaPlacement h = con(1.0);
		assertEquals(0.004F, h.frecuencia());
		assertEquals(Float.floatToIntBits(0.004F), Float.floatToIntBits(MinasVanillaPlacement.frecuencia(0.004F, 1.0)));
		for (int x = -100; x < 100; x++) {
			for (int z = -100; z < 100; z++) {
				assertEquals(v.getPotentialStructureChunk(SEMILLA, x, z), h.getPotentialStructureChunk(SEMILLA, x, z));
				assertEquals(sale(v, 0.004F, x, z), sale(h, h.frecuencia(), x, z));
			}
		}
	}

	@Test
	void conMasEsUnSuperconjuntoConKVecesMas() {
		MinasVanillaPlacement uno = con(1.0);
		for (double m : new double[] {1.5, 2.0, 5.0}) {
			MinasVanillaPlacement k = con(m);
			assertEquals((float) (0.004 * m), k.frecuencia(), 1e-7);
			int antes = 0, ahora = 0;
			for (int x = -100; x < 100; x++) {
				for (int z = -100; z < 100; z++) {
					boolean a = sale(uno, uno.frecuencia(), x, z), b = sale(k, k.frecuencia(), x, z);
					assertTrue(!a || b, "con x" + m + " se pierde la mina del chunk " + x + ", " + z);
					antes += a ? 1 : 0;
					ahora += b ? 1 : 0;
				}
			}
			double r = ahora / (double) antes;
			assertTrue(r > m * 0.8 && r < m * 1.2, "x" + m + ": " + antes + " -> " + ahora);
		}
		assertEquals(1.0F, MinasVanillaPlacement.frecuencia(0.5F, 5), "como mucho 1");
	}

	@Test
	void leeElMultiplicadorDeLaConfiguracion() throws IOException {
		JsonObject p = heraldia().getAsJsonObject("placement");
		HeraldiaConfig.load(null);
		assertEquals(0.008F, MinasVanillaPlacement.CODEC.codec().parse(JsonOps.INSTANCE, p).getOrThrow().frecuencia(), 1e-7,
				"por defecto x2");
		Path f = dir.resolve("heraldia.json");
		Files.writeString(f, "{\"minas\": {\"vanilla\": {\"multiplicador\": 3.5}}}");
		HeraldiaConfig.load(f);
		assertEquals(0.014F, MinasVanillaPlacement.CODEC.codec().parse(JsonOps.INSTANCE, p).getOrThrow().frecuencia(), 1e-7);
		Files.writeString(f, "{\"minas\": {\"vanilla\": {\"multiplicador\": 1}}}");
		HeraldiaConfig.load(f);
		assertEquals(0.004F, MinasVanillaPlacement.CODEC.codec().parse(JsonOps.INSTANCE, p).getOrThrow().frecuencia());
		Files.writeString(f, "{\"minas\": {\"vanilla\": {\"multiplicador\": 9}}}");
		HeraldiaConfig.load(f);
		assertEquals(2.0, HeraldiaConfig.get().getDouble(Minas.MULTIPLICADOR), "fuera de 1-5: el valor por defecto");
	}
}
