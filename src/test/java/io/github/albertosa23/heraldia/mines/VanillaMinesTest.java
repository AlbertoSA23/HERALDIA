package io.github.albertosa23.heraldia.mines;

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
 * Multiplied vanilla abandoned mineshafts ({@link VanillaMinesPlacement}, minas.vanilla.multiplicador): the structure_set
 * minecraft:mineshafts the generator writes has the same values as 26.3's (read from the game's own .jar),
 * with 1 the placement is exactly vanilla's (same float, same grid and same roll in each chunk), with more it is a
 * superset (no earlier mineshaft is lost or changes place) with about k times more, and the value is read from the
 * configuration. With the 0.004 roll per chunk, 200 x 200 chunks give about 160 mineshafts.
 */
class VanillaMinesTest {
	private static final String ROUTE = "data/minecraft/worldgen/structure_set/mineshafts.json";
	private static final long SEED = 4242L;

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
		for (URL u : Collections.list(VanillaMinesTest.class.getClassLoader().getResources(ROUTE))) {
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

	private static VanillaMinesPlacement with(double m) {
		return new VanillaMinesPlacement(Vec3i.ZERO, AbstractSpreadingStructurePlacement.FrequencyReductionMethod.LEGACY_TYPE_3, 0.004F, 0,
				1, 0, RandomSpreadType.LINEAR, m);
	}

	/** Does a mineshaft spawn in the chunk? isStructureChunk without the generator's state: the cell and the frequency roll. */
	private static boolean outcome(RandomSpreadStructurePlacement p, float rate, int x, int z) {
		ChunkPos c = p.getPotentialStructureChunk(SEED, x, z);
		return c.x() == x && c.z() == z && AbstractSpreadingStructurePlacement.FrequencyReductionMethod.LEGACY_TYPE_3
				.shouldGenerate(SEED, 0, x, z, rate);
	}

	@Test
	void setIsVanillaWithOwnType() throws IOException {
		JsonObject v = vanilla(), h = heraldia();
		assertNotNull(v, "el .jar del juego trae su mineshafts.json");
		assertEquals(v.get("structures"), h.get("structures"), "mismas estructuras (mineshaft y mineshaft_mesa) y pesos");
		JsonObject pv = v.getAsJsonObject("placement").deepCopy(), ph = h.getAsJsonObject("placement").deepCopy();
		pv.remove("type");
		ph.remove("type");
		assertEquals(pv, ph, "frecuencia, método, sal, separación y espaciado de 26.3");
	}

	@Test
	void withOneIsExactVanilla() throws IOException {
		RandomSpreadStructurePlacement v = RandomSpreadStructurePlacement.CODEC.codec()
				.parse(JsonOps.INSTANCE, vanilla().getAsJsonObject("placement")).getOrThrow();
		VanillaMinesPlacement h = with(1.0);
		assertEquals(0.004F, h.rate());
		assertEquals(Float.floatToIntBits(0.004F), Float.floatToIntBits(VanillaMinesPlacement.rate(0.004F, 1.0)));
		for (int x = -100; x < 100; x++) {
			for (int z = -100; z < 100; z++) {
				assertEquals(v.getPotentialStructureChunk(SEED, x, z), h.getPotentialStructureChunk(SEED, x, z));
				assertEquals(outcome(v, 0.004F, x, z), outcome(h, h.rate(), x, z));
			}
		}
	}

	@Test
	void withMoreIsSupersetWithKTimesMore() {
		VanillaMinesPlacement one = with(1.0);
		for (double m : new double[] {1.5, 2.0, 5.0}) {
			VanillaMinesPlacement k = with(m);
			assertEquals((float) (0.004 * m), k.rate(), 1e-7);
			int before = 0, now = 0;
			for (int x = -100; x < 100; x++) {
				for (int z = -100; z < 100; z++) {
					boolean a = outcome(one, one.rate(), x, z), b = outcome(k, k.rate(), x, z);
					assertTrue(!a || b, "con x" + m + " se pierde la mina del chunk " + x + ", " + z);
					before += a ? 1 : 0;
					now += b ? 1 : 0;
				}
			}
			double r = now / (double) before;
			assertTrue(r > m * 0.8 && r < m * 1.2, "x" + m + ": " + before + " -> " + now);
		}
		assertEquals(1.0F, VanillaMinesPlacement.rate(0.5F, 5), "como mucho 1");
	}

	@Test
	void readsMultiplierFromConfig() throws IOException {
		JsonObject p = heraldia().getAsJsonObject("placement");
		HeraldiaConfig.load(null);
		assertEquals(0.008F, VanillaMinesPlacement.CODEC.codec().parse(JsonOps.INSTANCE, p).getOrThrow().rate(), 1e-7,
				"por defecto x2");
		Path f = dir.resolve("heraldia.json");
		Files.writeString(f, "{\"minas\": {\"vanilla\": {\"multiplicador\": 3.5}}}");
		HeraldiaConfig.load(f);
		assertEquals(0.014F, VanillaMinesPlacement.CODEC.codec().parse(JsonOps.INSTANCE, p).getOrThrow().rate(), 1e-7);
		Files.writeString(f, "{\"minas\": {\"vanilla\": {\"multiplicador\": 1}}}");
		HeraldiaConfig.load(f);
		assertEquals(0.004F, VanillaMinesPlacement.CODEC.codec().parse(JsonOps.INSTANCE, p).getOrThrow().rate());
		Files.writeString(f, "{\"minas\": {\"vanilla\": {\"multiplicador\": 9}}}");
		HeraldiaConfig.load(f);
		assertEquals(2.0, HeraldiaConfig.get().getDouble(Mines.MULTIPLIER), "fuera de 1-5: el valor por defecto");
	}
}
