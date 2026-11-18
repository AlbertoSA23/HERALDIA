package io.github.albertosa23.heraldia.dimensions;

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
class DimensionTerrainTest {
	private static final long[] SEEDS = {20261117L, 7L};
	private static final int CHUNKS = 120;
	private static HolderLookup.Provider vanilla;

	@BeforeAll
	static void bootstrap() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
		var data = new MultiPackResourceManager(PackType.SERVER_DATA, List.<PackResources>of(ServerPacksSource.createVanillaPackSource().fullResources()));
		TagLoader.loadTagsForExistingRegistries(data, RegistryAccess.fromRegistryOfRegistries(BuiltInRegistries.REGISTRY))
				.forEach(Registry.PendingTags::apply);
		vanilla = VanillaRegistries.createWorldLookup();
	}

	private record World(NoiseBasedChunkGenerator gen, RandomState rs, LevelHeightAccessor high) {
		NoiseColumn column(int x, int z) {
			return gen.getBaseColumn(x, z, high, rs);
		}

		int height(int x, int z) {
			return gen.getBaseHeight(x, z, Heightmap.Types.WORLD_SURFACE_WG, high, rs);
		}
	}

	private static World world(long seed, net.minecraft.resources.ResourceKey<NoiseGeneratorSettings> key, BiomeSource source, LevelHeightAccessor high) {
		Holder<NoiseGeneratorSettings> settings = vanilla.lookupOrThrow(Registries.NOISE_SETTINGS).getOrThrow(key);
		RandomState rs = RandomState.create(vanilla.lookupOrThrow(Registries.NOISE), seed, settings.value());
		return new World(new NoiseBasedChunkGenerator(source, settings), rs, high);
	}

	private static boolean solid(BlockState s) {
		return !s.isAir() && s.getFluidState().isEmpty();
	}

	@Test
	void netherFirmGroundWithAirBelowCeiling() {
		BiomeSource source = MultiNoiseBiomeSource.createFromPreset(vanilla.lookupOrThrow(Registries.MULTI_NOISE_BIOME_SOURCE_PARAMETER_LIST)
				.getOrThrow(MultiNoiseBiomeSourceParameterLists.NETHER));
		int radius = 8, free = 12, total = 0, exits = 0;
		for (long seed : SEEDS) {
			World m = world(seed, NoiseGeneratorSettings.NETHER, source, LevelHeightAccessor.create(0, 256));
			Random r = new Random(seed);
			for (int i = 0; i < CHUNKS; i++) {
				int cx = (r.nextInt(400) - 200) * 16 + 8, cz = (r.nextInt(400) - 200) * 16 + 8;
				DimensionStructure.Site st = DimensionStructure.site(m::column, null, cx, cz, radius, free);
				total++;
				if (st == null) {
					continue;
				}
				exits++;
				int x = st.x(), y = st.y(), z = st.z();
				assertTrue(Math.abs(x - cx) <= 8 && Math.abs(z - cz) <= 8, "dentro del chunk candidato");
				NoiseColumn c = m.column(x, z);
				assertTrue(y > Ground.NETHER_TO - 1 && y <= Ground.NETHER_FROM, "altura " + y + " en " + x + ", " + z);
				assertTrue(solid(c.getBlock(y - 1)), "suelo firme bajo " + x + ", " + y + ", " + z);
				for (int k = y; k < y + free; k++) {
					assertTrue(c.getBlock(k).isAir(), "aire en " + x + ", " + k + ", " + z + ": " + c.getBlock(k));
				}
				for (int dx = -radius; dx <= radius; dx += 2 * radius) {
					for (int dz = -radius; dz <= radius; dz += 2 * radius) {
						NoiseColumn e = m.column(x + dx, z + dz);
						boolean there = false;
						for (int k = y - Ground.DROP; k <= y + Ground.DROP && !there; k++) {
							there = solid(e.getBlock(k - 1)) && e.getBlock(k).isAir();
						}
						assertTrue(there, "esquina sin suelo a ±" + Ground.DROP + " en " + (x + dx) + ", " + (z + dz));
					}
				}
			}
		}
		// el Nether es abrupto: no todas las candidatas valen, pero una buena parte sí
		assertTrue(exits * 100 >= total * 25, "salen " + exits + " de " + total);
	}

	@Test
	void endOnlyOnOuterIslandsWithoutVoid() {
		BiomeSource source = TheEndBiomeSource.create(vanilla.lookupOrThrow(Registries.BIOME));
		int radius = 8, total = 0, exits = 0, center = 0;
		for (long seed : SEEDS) {
			World m = world(seed, NoiseGeneratorSettings.END, source, LevelHeightAccessor.create(0, 256));
			Random r = new Random(seed);
			for (int i = 0; i < CHUNKS; i++) {
				// la mitad cerca de la isla central (no debe salir nunca) y la mitad en las islas exteriores
				int side = i % 2 == 0 ? 60 : 600;
				int x = (r.nextInt(2 * side) - side) * 16 + 8, z = (r.nextInt(2 * side) - side) * 16 + 8;
				DimensionStructure.Site st = DimensionStructure.site(null, m::height, x, z, radius, 12);
				if ((long) x * x + (long) z * z < (long) (Ground.END_CENTRAL_RADIUS - 16) * (Ground.END_CENTRAL_RADIUS - 16)) {
					assertEquals(null, st, "cerca de la isla central: " + x + ", " + z);
					center++;
					continue;
				}
				total++;
				if (st == null) {
					continue;
				}
				exits++;
				x = st.x();
				z = st.z();
				assertTrue((long) x * x + (long) z * z >= (long) Ground.END_CENTRAL_RADIUS * Ground.END_CENTRAL_RADIUS);
				for (int[] d : new int[][] {{0, 0}, {-radius, -radius}, {-radius, radius}, {radius, -radius}, {radius, radius}}) {
					int h = m.height(x + d[0], z + d[1]);
					assertTrue(h >= Ground.END_MIN, "vacío bajo " + (x + d[0]) + ", " + (z + d[1]) + ": " + h);
				}
			}
		}
		assertTrue(center > 0, "ninguna candidata cerca del centro");
		// las islas exteriores dejan huecos de vacío: sale en algunas, no en todas
		assertTrue(exits > 0 && exits < total, "salen " + exits + " de " + total);
	}
}
