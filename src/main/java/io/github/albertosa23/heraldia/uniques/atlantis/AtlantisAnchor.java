package io.github.albertosa23.heraldia.uniques.atlantis;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;
import net.fabricmc.fabric.api.tag.convention.v2.ConventionalBiomeTags;
import net.minecraft.core.Holder;
import net.minecraft.core.QuartPos;
import net.minecraft.resources.Identifier;
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.tags.BiomeTags;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.biome.Biome;
import net.minecraft.world.level.biome.BiomeResolver;
import net.minecraft.world.level.dimension.DimensionType;
import net.minecraft.world.level.levelgen.densityfunction.SamplerContext;
import net.minecraft.world.level.storage.LevelResource;
import org.jspecify.annotations.Nullable;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Atlantis anchor: the start chunk of the central district. It is computed once per world when the Overworld loads,
 * off the server thread, and saved in data/heraldia/atlantida.json so it does not change even if the
 * biomes or the explored area change. The generation threads wait for the result.
 */
public final class AtlantisAnchor {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	/** Districts: 3 x 3, each of 16 x 16 chunks with the start at chunk 8 (covers -8 to +7, within the ±8 limit). */
	public static final int DISTRICT_CHUNKS = 16, DISTRICTS_PER_SIDE = 3;
	private static final int STEP = 64, SEARCH_RADIUS = 12288, MIN_DISTANCE = 1500, SAMPLE_Y = 40;
	private static final int HALF_CELLS = 7, DEEP_HALF_CELLS = 4; // 448 blocks of ocean from the center (384 of city + margin)
	private static final int EXCLUSION_RADIUS = 372 + 72; // wall + half an ocean monument and slack
	private static final Identifier STRUCTURE_ID = Identifier.fromNamespaceAndPath("heraldia", "unicas/atlantida");
	/** Structures the game needs (the stronghold has the End portal and its ring has no other place): never excluded. */
	private static final Set<Identifier> REQUIRED = Set.of(Identifier.fromNamespaceAndPath("minecraft", "stronghold"));
	private static final Map<Long, CompletableFuture<ChunkPos>> BY_SEED = new ConcurrentHashMap<>();

	private AtlantisAnchor() {
	}

	static void onLevelLoad(MinecraftServer server, ServerLevel level) {
		if (level.dimension() != Level.OVERWORLD) {
			return;
		}
		Path root = server.getWorldPath(LevelResource.DATA).getParent();
		Path file = root.resolve("data").resolve("heraldia").resolve("atlantida.json");
		Path regions = DimensionType.getStorageFolder(Level.OVERWORLD, root).resolve("region");
		long seed = level.getSeed();
		var generator = level.getChunkSource().getGenerator();
		var randomState = level.getChunkSource().getGeneratorState().randomState();
		CompletableFuture<ChunkPos> future = new CompletableFuture<>();
		BY_SEED.put(seed, future);
		Thread thread = new Thread(() -> {
			try {
				ChunkPos saved = read(file, seed);
				if (saved == null) {
					BiomeResolver resolver = generator.getBiomeSource().createResolver(randomState.createClimateSampler(SamplerContext.EMPTY_UNCACHED));
					long t = System.nanoTime();
					saved = search(resolver, regions);
					write(file, seed, saved);
					LOGGER.info("Heraldia: Atlántida situada en el bloque {}, {} (búsqueda de {} ms)", saved.getMinBlockX(), saved.getMinBlockZ(),
							(System.nanoTime() - t) / 1_000_000);
				} else {
					LOGGER.info("Heraldia: Atlántida en el bloque {}, {} (posición guardada)", saved.getMinBlockX(), saved.getMinBlockZ());
				}
				future.complete(saved);
			} catch (Throwable e) {
				LOGGER.error("Heraldia: no se pudo situar la Atlántida; no se generará en esta sesión", e);
				future.complete(null);
			}
		}, "heraldia-atlantida");
		thread.setDaemon(true);
		thread.start();
	}

	static void clear() {
		BY_SEED.clear();
	}

	/** Start chunk of the central district, or null if this world has no anchor (yet). */
	public static @Nullable ChunkPos get(long seed) {
		CompletableFuture<ChunkPos> future = BY_SEED.get(seed);
		return future == null ? null : future.join();
	}

	public static boolean isDistrictStart(long seed, int chunkX, int chunkZ) {
		ChunkPos anchor = get(seed);
		if (anchor == null) {
			return false;
		}
		int dx = chunkX - anchor.x(), dz = chunkZ - anchor.z(), reach = DISTRICT_CHUNKS * (DISTRICTS_PER_SIDE / 2);
		return Math.floorMod(dx, DISTRICT_CHUNKS) == 0 && Math.floorMod(dz, DISTRICT_CHUNKS) == 0 && Math.abs(dx) <= reach && Math.abs(dz) <= reach;
	}

	/**
	 * No other structure can be born inside the city or right next to it (monuments, shipwrecks, ocean ruins):
	 * its start chunk is excluded within the wall's radius plus a margin. Strongholds (REQUIRED) are not excluded.
	 */
	public static boolean excludes(Identifier structure, ResourceKey<Level> dimension, long seed, int chunkX, int chunkZ) {
		if (dimension != Level.OVERWORLD || STRUCTURE_ID.equals(structure) || REQUIRED.contains(structure)) {
			return false;
		}
		ChunkPos anchor = get(seed);
		if (anchor == null) {
			return false;
		}
		long dx = (chunkX - anchor.x()) * 16L + 8, dz = (chunkZ - anchor.z()) * 16L + 8;
		return dx * dx + dz * dz <= (long) EXCLUSION_RADIUS * EXCLUSION_RADIUS;
	}

	private static @Nullable ChunkPos read(Path file, long seed) throws IOException {
		if (!Files.isRegularFile(file)) {
			return null;
		}
		JsonObject o = JsonParser.parseString(Files.readString(file, StandardCharsets.UTF_8)).getAsJsonObject();
		return o.get("semilla").getAsLong() == seed ? new ChunkPos(o.get("chunk_x").getAsInt(), o.get("chunk_z").getAsInt()) : null;
	}

	private static void write(Path file, long seed, ChunkPos pos) throws IOException {
		JsonObject o = new JsonObject();
		o.addProperty("semilla", seed);
		o.addProperty("chunk_x", pos.x());
		o.addProperty("chunk_z", pos.z());
		Files.createDirectories(file.getParent());
		Files.writeString(file, o + "\n", StandardCharsets.UTF_8);
	}

	/**
	 * Samples the biomes every 64 blocks and chooses, by decreasing levels of strictness, the center closest to 0,0:
	 * 0) all ocean within ±448, deep at the center, unexplored; 1) all ocean, unexplored; 2) almost all ocean,
	 * unexplored; 3) almost all ocean; 4) the one with the most ocean. It always returns one.
	 */
	private static ChunkPos search(BiomeResolver resolver, Path regions) {
		int n = 2 * SEARCH_RADIUS / STEP;
		int[][] land = new int[n + 1][n + 1], deep = new int[n + 1][n + 1]; // cumulative sums
		for (int i = 0; i < n; i++) {
			for (int j = 0; j < n; j++) {
				Holder<Biome> biome = resolver.getNoiseBiome(QuartPos.fromBlock(i * STEP - SEARCH_RADIUS + STEP / 2), QuartPos.fromBlock(SAMPLE_Y),
						QuartPos.fromBlock(j * STEP - SEARCH_RADIUS + STEP / 2));
				// vanilla and conventional tags (other mods' oceans); in vanilla #c:is_ocean = #minecraft:is_ocean
				int l = biome.is(BiomeTags.IS_OCEAN) || biome.is(ConventionalBiomeTags.IS_OCEAN) ? 0 : 1;
				int d = biome.is(BiomeTags.IS_DEEP_OCEAN) || biome.is(ConventionalBiomeTags.IS_DEEP_OCEAN) ? 1 : 0;
				land[i + 1][j + 1] = l + land[i][j + 1] + land[i + 1][j] - land[i][j];
				deep[i + 1][j + 1] = d + deep[i][j + 1] + deep[i + 1][j] - deep[i][j];
			}
		}
		Map<Long, Boolean> explored = new HashMap<>();
		int window = 4 * HALF_CELLS * HALF_CELLS, inner = 4 * DEEP_HALF_CELLS * DEEP_HALF_CELLS;
		int[] best = new int[5 * 2];
		long[] bestKey = new long[5];
		java.util.Arrays.fill(bestKey, Long.MAX_VALUE);
		for (int i = HALF_CELLS; i <= n - HALF_CELLS; i++) {
			for (int j = HALF_CELLS; j <= n - HALF_CELLS; j++) {
				long x = (long) i * STEP - SEARCH_RADIUS, z = (long) j * STEP - SEARCH_RADIUS, dist = x * x + z * z;
				if (dist < (long) MIN_DISTANCE * MIN_DISTANCE) {
					continue;
				}
				int landCount = sum(land, i, j, HALF_CELLS), deepCount = sum(deep, i, j, DEEP_HALF_CELLS);
				int tier = landCount == 0 ? (deepCount * 5 >= inner * 4 ? 0 : 1) : landCount * 20 <= window ? 2 : 4;
				long key = tier == 4 ? (long) landCount << 40 | dist : dist;
				if (tier < 4 && key < bestKey[tier] && explored((int) x, (int) z, regions, explored)) {
					tier = 3; // explored: only valid if there is nothing unexplored
				}
				if (key < bestKey[tier]) {
					bestKey[tier] = key;
					best[tier * 2] = (int) x;
					best[tier * 2 + 1] = (int) z;
				}
			}
		}
		for (int tier = 0; tier < 5; tier++) {
			if (bestKey[tier] != Long.MAX_VALUE) {
				if (tier > 0) {
					LOGGER.warn("Heraldia: no hay una cuenca de océano profundo ideal para la Atlántida; se usa la mejor disponible (nivel {})", tier);
				}
				return new ChunkPos(best[tier * 2] >> 4, best[tier * 2 + 1] >> 4);
			}
		}
		throw new IllegalStateException("sin candidatos");
	}

	private static int sum(int[][] acc, int i, int j, int half) {
		return acc[i + half][j + half] - acc[i - half][j + half] - acc[i + half][j - half] + acc[i - half][j - half];
	}

	/** Is there already some region file under the city's footprint (some chunk generated in that region)? */
	private static boolean explored(int x, int z, Path regions, Map<Long, Boolean> cache) {
		int reach = HALF_CELLS * STEP;
		for (int rx = Math.floorDiv(x - reach, 512); rx <= Math.floorDiv(x + reach, 512); rx++) {
			for (int rz = Math.floorDiv(z - reach, 512); rz <= Math.floorDiv(z + reach, 512); rz++) {
				int fx = rx, fz = rz;
				if (cache.computeIfAbsent(ChunkPos.pack(rx, rz), k -> Files.exists(regions.resolve("r." + fx + "." + fz + ".mca")))) {
					return true;
				}
			}
		}
		return false;
	}
}
