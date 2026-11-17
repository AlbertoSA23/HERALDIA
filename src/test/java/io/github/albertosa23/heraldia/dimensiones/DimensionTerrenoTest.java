package io.github.albertosa23.heraldia.dimensiones;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;
import java.util.Random;
import net.minecraft.SharedConstants;
import net.minecraft.core.Holder;
import net.minecraft.core.HolderLookup;
import net.minecraft.core.Registry;
import net.minecraft.core.RegistryAccess;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.data.registries.VanillaRegistries;
import net.minecraft.server.Bootstrap;
import net.minecraft.server.packs.PackResources;
import net.minecraft.server.packs.PackType;
import net.minecraft.server.packs.repository.ServerPacksSource;
import net.minecraft.server.packs.resources.MultiPackResourceManager;
import net.minecraft.tags.TagLoader;
import net.minecraft.world.level.LevelHeightAccessor;
import net.minecraft.world.level.NoiseColumn;
import net.minecraft.world.level.biome.BiomeSource;
import net.minecraft.world.level.biome.MultiNoiseBiomeSource;
import net.minecraft.world.level.biome.MultiNoiseBiomeSourceParameterLists;
import net.minecraft.world.level.biome.TheEndBiomeSource;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.level.levelgen.NoiseBasedChunkGenerator;
import net.minecraft.world.level.levelgen.NoiseGeneratorSettings;
import net.minecraft.world.level.levelgen.RandomState;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/**
 * Alturas de {@link DimensionStructure} con el terreno real de 26.3 del Nether y del End (VanillaRegistries, sin
 * servidor): en el Nether, el suelo que elige es firme, con aire para toda la plantilla y por debajo del techo de bedrock,
 * nunca sobre el mar de lava, y sus esquinas a ±DESNIVEL; en el End, nunca sobre el vacío ni cerca de la isla central. Y
 * con chunks al azar sale en una parte razonable de las candidatas (si no, casi ninguna rejilla daría estructura).
 */
class DimensionTerrenoTest {
	private static final long[] SEMILLAS = {20261117L, 7L};
	private static final int CHUNKS = 120;
	private static HolderLookup.Provider vanilla;

	@BeforeAll
	static void bootstrap() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
		var datos = new MultiPackResourceManager(PackType.SERVER_DATA, List.<PackResources>of(ServerPacksSource.createVanillaPackSource().fullResources()));
		TagLoader.loadTagsForExistingRegistries(datos, RegistryAccess.fromRegistryOfRegistries(BuiltInRegistries.REGISTRY))
				.forEach(Registry.PendingTags::apply);
		vanilla = VanillaRegistries.createWorldLookup();
	}

	private record Mundo(NoiseBasedChunkGenerator gen, RandomState rs, LevelHeightAccessor alto) {
		NoiseColumn columna(int x, int z) {
			return gen.getBaseColumn(x, z, alto, rs);
		}

		int altura(int x, int z) {
			return gen.getBaseHeight(x, z, Heightmap.Types.WORLD_SURFACE_WG, alto, rs);
		}
	}

	private static Mundo mundo(long seed, net.minecraft.resources.ResourceKey<NoiseGeneratorSettings> clave, BiomeSource fuente, LevelHeightAccessor alto) {
		Holder<NoiseGeneratorSettings> ajustes = vanilla.lookupOrThrow(Registries.NOISE_SETTINGS).getOrThrow(clave);
		RandomState rs = RandomState.create(vanilla.lookupOrThrow(Registries.NOISE), seed, ajustes.value());
		return new Mundo(new NoiseBasedChunkGenerator(fuente, ajustes), rs, alto);
	}

	private static boolean solido(BlockState s) {
		return !s.isAir() && s.getFluidState().isEmpty();
	}

	@Test
	void netherSueloFirmeConAireBajoElTecho() {
		BiomeSource fuente = MultiNoiseBiomeSource.createFromPreset(vanilla.lookupOrThrow(Registries.MULTI_NOISE_BIOME_SOURCE_PARAMETER_LIST)
				.getOrThrow(MultiNoiseBiomeSourceParameterLists.NETHER));
		int radio = 8, libre = 12, total = 0, salen = 0;
		for (long seed : SEMILLAS) {
			Mundo m = mundo(seed, NoiseGeneratorSettings.NETHER, fuente, LevelHeightAccessor.create(0, 256));
			Random r = new Random(seed);
			for (int i = 0; i < CHUNKS; i++) {
				int cx = (r.nextInt(400) - 200) * 16 + 8, cz = (r.nextInt(400) - 200) * 16 + 8;
				DimensionStructure.Sitio st = DimensionStructure.sitio(m::columna, null, cx, cz, radio, libre);
				total++;
				if (st == null) {
					continue;
				}
				salen++;
				int x = st.x(), y = st.y(), z = st.z();
				assertTrue(Math.abs(x - cx) <= 8 && Math.abs(z - cz) <= 8, "dentro del chunk candidato");
				NoiseColumn c = m.columna(x, z);
				assertTrue(y > Suelo.NETHER_HASTA - 1 && y <= Suelo.NETHER_DESDE, "altura " + y + " en " + x + ", " + z);
				assertTrue(solido(c.getBlock(y - 1)), "suelo firme bajo " + x + ", " + y + ", " + z);
				for (int k = y; k < y + libre; k++) {
					assertTrue(c.getBlock(k).isAir(), "aire en " + x + ", " + k + ", " + z + ": " + c.getBlock(k));
				}
				for (int dx = -radio; dx <= radio; dx += 2 * radio) {
					for (int dz = -radio; dz <= radio; dz += 2 * radio) {
						NoiseColumn e = m.columna(x + dx, z + dz);
						boolean hay = false;
						for (int k = y - Suelo.DESNIVEL; k <= y + Suelo.DESNIVEL && !hay; k++) {
							hay = solido(e.getBlock(k - 1)) && e.getBlock(k).isAir();
						}
						assertTrue(hay, "esquina sin suelo a ±" + Suelo.DESNIVEL + " en " + (x + dx) + ", " + (z + dz));
					}
				}
			}
		}
		// el Nether es abrupto: no todas las candidatas valen, pero una buena parte sí
		assertTrue(salen * 100 >= total * 25, "salen " + salen + " de " + total);
	}

	@Test
	void endSoloEnIslasExterioresSinVacio() {
		BiomeSource fuente = TheEndBiomeSource.create(vanilla.lookupOrThrow(Registries.BIOME));
		int radio = 8, total = 0, salen = 0, centro = 0;
		for (long seed : SEMILLAS) {
			Mundo m = mundo(seed, NoiseGeneratorSettings.END, fuente, LevelHeightAccessor.create(0, 256));
			Random r = new Random(seed);
			for (int i = 0; i < CHUNKS; i++) {
				// la mitad cerca de la isla central (no debe salir nunca) y la mitad en las islas exteriores
				int lado = i % 2 == 0 ? 60 : 600;
				int x = (r.nextInt(2 * lado) - lado) * 16 + 8, z = (r.nextInt(2 * lado) - lado) * 16 + 8;
				DimensionStructure.Sitio st = DimensionStructure.sitio(null, m::altura, x, z, radio, 12);
				if ((long) x * x + (long) z * z < (long) (Suelo.END_RADIO_CENTRAL - 16) * (Suelo.END_RADIO_CENTRAL - 16)) {
					assertEquals(null, st, "cerca de la isla central: " + x + ", " + z);
					centro++;
					continue;
				}
				total++;
				if (st == null) {
					continue;
				}
				salen++;
				x = st.x();
				z = st.z();
				assertTrue((long) x * x + (long) z * z >= (long) Suelo.END_RADIO_CENTRAL * Suelo.END_RADIO_CENTRAL);
				for (int[] d : new int[][] {{0, 0}, {-radio, -radio}, {-radio, radio}, {radio, -radio}, {radio, radio}}) {
					int h = m.altura(x + d[0], z + d[1]);
					assertTrue(h >= Suelo.END_MINIMO, "vacío bajo " + (x + d[0]) + ", " + (z + d[1]) + ": " + h);
				}
			}
		}
		assertTrue(centro > 0, "ninguna candidata cerca del centro");
		// las islas exteriores dejan huecos de vacío: sale en algunas, no en todas
		assertTrue(salen > 0 && salen < total, "salen " + salen + " de " + total);
	}
}
