package io.github.albertosa23.heraldia.mines;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import io.github.albertosa23.heraldia.common.Heights;
import io.github.albertosa23.heraldia.common.HeightCache;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Random;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.stream.Stream;
import net.minecraft.SharedConstants;
import net.minecraft.core.BlockPos;
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
import net.minecraft.world.level.biome.MultiNoiseBiomeSource;
import net.minecraft.world.level.biome.MultiNoiseBiomeSourceParameterLists;
import net.minecraft.world.level.levelgen.NoiseBasedChunkGenerator;
import net.minecraft.world.level.levelgen.NoiseGeneratorSettings;
import net.minecraft.world.level.levelgen.RandomState;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/**
 * La búsqueda de ladera de las entradas a mina de ahora (comprobaciones reordenadas, {@link Hillside}, con la caché
 * compartida de alturas, {@link HeightCache}) da exactamente lo mismo que la de la 0.1.0 ({@link OldHillside}, con una
 * caché por búsqueda, {@link Heights}): mismas minas en los mismos
 * sitios. Con el terreno real de 26.3 (VanillaRegistries, sin servidor) en varias semillas y muchos chunks, con las formas
 * de las tres bocas del datapack generado, en el orden de la generación (los diez estilos y variantes del set miran el
 * mismo chunk), con una caché diminuta que se vacía a mitad de búsqueda y desde varios hilos a la vez.
 */
class MinesDeterminismTest {
	private static final long[] SEEDS = {20261116L, 1L, -4242L};
	private static final int CHUNKS_PER_SEED = 40;
	private static HolderLookup.Provider vanilla;
	private static NoiseGeneratorSettings settings;
	private static Holder<NoiseGeneratorSettings> settingsHolder;
	private static MultiNoiseBiomeSource biomes;
	private static final LevelHeightAccessor HIGH = LevelHeightAccessor.create(-64, 384);
	private static final Map<String, Hillside.Shape> SHAPES = new LinkedHashMap<>();

	@BeforeAll
	static void bootstrap() throws IOException {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
		// Las alturas del fondo (OCEAN_FLOOR_WG) miran la etiqueta de bloques minecraft:blocks_motion_in_heightmap: sin las
		// etiquetas de vanilla cargadas, todo da el fondo del mundo (como el servidor al cargar sus datos).
		var data = new MultiPackResourceManager(PackType.SERVER_DATA, List.<PackResources>of(ServerPacksSource.createVanillaPackSource().fullResources()));
		TagLoader.loadTagsForExistingRegistries(data, RegistryAccess.fromRegistryOfRegistries(BuiltInRegistries.REGISTRY))
				.forEach(Registry.PendingTags::apply);
		vanilla = VanillaRegistries.createWorldLookup();
		settingsHolder = vanilla.lookupOrThrow(Registries.NOISE_SETTINGS).getOrThrow(NoiseGeneratorSettings.OVERWORLD);
		settings = settingsHolder.value();
		biomes = MultiNoiseBiomeSource.createFromPreset(vanilla.lookupOrThrow(Registries.MULTI_NOISE_BIOME_SOURCE_PARAMETER_LIST)
				.getOrThrow(MultiNoiseBiomeSourceParameterLists.OVERWORLD));
		Path dir = Path.of(System.getProperty("heraldia.generated", "build/generated/heraldia"), "data", "heraldia", "worldgen", "structure", "minas");
		try (Stream<Path> files = Files.walk(dir)) {
			for (Path f : files.filter(p -> p.toString().endsWith(".json")).sorted().toList()) {
				JsonObject o = JsonParser.parseString(Files.readString(f)).getAsJsonObject();
				SHAPES.put(dir.relativize(f).toString(), shape(o));
			}
		}
		assertTrue(SHAPES.size() >= 30, "formas de las minas en el datapack: " + SHAPES.size());
	}

	private static Hillside.Shape shape(JsonObject o) {
		JsonArray e = o.getAsJsonArray("entrada"), p = o.getAsJsonArray("patio");
		List<int[]> ceiling = new ArrayList<>();
		for (JsonElement t : o.getAsJsonArray("techo")) {
			JsonArray a = t.getAsJsonArray();
			ceiling.add(new int[] {a.get(0).getAsInt(), a.get(1).getAsInt(), a.get(2).getAsInt()});
		}
		return new Hillside.Shape(new BlockPos(e.get(0).getAsInt(), e.get(1).getAsInt(), e.get(2).getAsInt()), p.get(0).getAsInt(),
				p.get(1).getAsInt(), p.get(2).getAsInt(), p.get(3).getAsInt(), ceiling);
	}

	/** Una forma de cada (las de los estilos y variantes de un tamaño coinciden). */
	private static List<Hillside.Shape> distinct() {
		Map<String, Hillside.Shape> out = new LinkedHashMap<>();
		SHAPES.values().forEach(f -> out.putIfAbsent(key(f), f));
		return List.copyOf(out.values());
	}

	private static String key(Hillside.Shape f) {
		return f.entry() + " " + f.yardX0() + "," + f.yardZ0() + "," + f.yardX1() + "," + f.yardZ1() + " "
				+ java.util.Arrays.deepToString(f.ceiling().toArray());
	}

	/** Alturas de generación del mundo principal con esa semilla, contando cuántas columnas se evalúan. */
	private static HeightCache.Source source(long seed, AtomicInteger evaluated) {
		RandomState rs = RandomState.create(vanilla.lookupOrThrow(Registries.NOISE), seed, settings);
		NoiseBasedChunkGenerator g = new NoiseBasedChunkGenerator(biomes, settingsHolder);
		return (x, z, type) -> {
			evaluated.incrementAndGet();
			return g.getBaseHeight(x, z, type, HIGH, rs);
		};
	}

	/**
	 * Chunks al azar (con la semilla del test) hasta 20.000 bloques del 0,0: una cuarta parte cualquiera (llanuras, mar...) y
	 * el resto con pendiente (el terreno sube al menos {@link Hillside#RISE_MIN} hacia algún lado), donde la búsqueda llega
	 * hasta el final y salen laderas.
	 */
	private static List<int[]> chunks(long seed, int n, HeightCache.Source f) {
		Random r = new Random(seed * 31 + 7);
		List<int[]> out = new ArrayList<>();
		int any = n / 4;
		for (int attempt = 0; out.size() < n && attempt < n * 200; attempt++) {
			int[] c = {r.nextInt(2500) - 1250, r.nextInt(2500) - 1250};
			if (out.size() < any || pending(f, c[0] * 16 + 8, c[1] * 16 + 8) >= Hillside.RISE_MIN) {
				out.add(c);
			}
		}
		return out;
	}

	private static int pending(HeightCache.Source f, int x, int z) {
		Hillside.Terrain t = MineEntranceStructure.terrain(new Heights(f, 63));
		int r = Hillside.RADIUS;
		return Math.max(Math.abs(t.ground(x + r, z) - t.ground(x - r, z)), Math.abs(t.ground(x, z + r) - t.ground(x, z - r)));
	}

	private static Hillside.Site search(Hillside.Terrain t, int[] c, Hillside.Shape f, boolean forced) {
		return Hillside.search(t, c[0] * 16 + 8, c[1] * 16 + 8, f, HIGH.getMinY(), forced);
	}

	/** La ruta antigua entera: la búsqueda de la 0.1.0 ({@link OldHillside}) con una caché nueva por búsqueda. */
	private static Hillside.Site old(HeightCache.Source f, int[] c, Hillside.Shape shape, boolean forced) {
		return OldHillside.search(MineEntranceStructure.terrain(new Heights(f, 63)), c[0] * 16 + 8, c[1] * 16 + 8, shape, HIGH.getMinY(), forced);
	}

	@Test
	void sharedCacheGivesSameMinesAsOldPath() {
		int found = 0, compared = 0;
		long before = 0, after = 0;
		for (long seed : SEEDS) {
			AtomicInteger olds = new AtomicInteger(), news = new AtomicInteger();
			HeightCache.Source fv = source(seed, olds), fn = source(seed, news);
			HeightCache shared = new HeightCache(fn, 63, HeightCache.CAPACITY);
			for (int[] c : chunks(seed, CHUNKS_PER_SEED, source(seed, new AtomicInteger()))) {
				// antes: cada estructura del set (diez por tamaño) con su propia caché, nueva en cada findGenerationPoint; las
				// de formas iguales dan lo mismo, así que la ruta antigua se calcula una vez por forma distinta y se cuenta
				// como si se hubiera repetido
				Map<String, Hillside.Site> legacyOnes = new java.util.HashMap<>();
				Map<String, Integer> cost = new java.util.HashMap<>();
				for (Map.Entry<String, Hillside.Shape> e : SHAPES.entrySet()) {
					Hillside.Shape shape = e.getValue();
					String k = key(shape);
					if (!legacyOnes.containsKey(k)) {
						int n0 = olds.get();
						legacyOnes.put(k, old(fv, c, shape, false));
						cost.put(k, olds.get() - n0);
					} else {
						olds.addAndGet(cost.get(k));
					}
					Hillside.Site oldValue = legacyOnes.get(k);
					Hillside.Site newValue = search(MineEntranceStructure.terrain(shared), c, shape, false);
					assertEquals(oldValue, newValue, () -> "semilla " + seed + ", chunk " + c[0] + "," + c[1] + ", " + e.getKey());
					compared++;
					if (newValue != null) {
						found++;
					}
				}
			}
			before += olds.get();
			after += news.get();
		}
		assertTrue(compared >= SEEDS.length * CHUNKS_PER_SEED * 30, "comparadas " + compared);
		assertTrue(found >= 20, "pocas laderas encontradas para que la comparación valga: " + found);
		// la mejora: los estilos y variantes del set (y luego /locate) ya no repiten columnas
		assertTrue(after * 5 < before, "columnas evaluadas: " + before + " antes, " + after + " con la caché compartida");
		System.out.printf("MinasDeterminismo: %d búsquedas, %d laderas; columnas evaluadas %d -> %d%n", compared, found, before, after);
	}

	@Test
	void tinyCacheEmptiedHalfwayGivesTheSame() {
		long seed = SEEDS[0];
		AtomicInteger n = new AtomicInteger();
		HeightCache.Source f = source(seed, n);
		HeightCache tiny = new HeightCache(f, 63, 64);    // una columna por franja: se vacía sin parar
		int found = 0;
		for (int[] c : chunks(seed + 1, 40, f)) {
			for (Hillside.Shape shape : distinct()) {
			Hillside.Site oldValue = old(f, c, shape, false);
			assertEquals(oldValue, search(MineEntranceStructure.terrain(tiny), c, shape, false), () -> "chunk " + c[0] + "," + c[1]);
			assertEquals(old(f, c, shape, true),
					search(MineEntranceStructure.terrain(tiny), c, shape, true), () -> "forzada, chunk " + c[0] + "," + c[1]);
			found += oldValue != null ? 1 : 0;
			assertTrue(tiny.size() <= tiny.capacity());
			}
		}
		assertTrue(found > 0, "ninguna ladera: la comparación no vale");
		assertEquals(64, tiny.capacity());
	}

	@Test
	void fromSeveralThreadsAtOnceGivesTheSame() throws Exception {
		long seed = SEEDS[1];
		AtomicInteger n = new AtomicInteger();
		HeightCache.Source f = source(seed, n);
		HeightCache shared = new HeightCache(f, 63, 4096);
		List<int[]> cs = chunks(seed + 2, 40, f);
		List<Hillside.Shape> shapes = distinct();
		List<Hillside.Site> expected = new ArrayList<>();
		for (int[] c : cs) {
			for (Hillside.Shape shape : shapes) {
				expected.add(old(f, c, shape, false));
			}
		}
		ExecutorService pool = Executors.newFixedThreadPool(4);
		try {
			List<Future<List<Hillside.Site>>> threads = new ArrayList<>();
			for (int h = 0; h < 4; h++) {
				threads.add(pool.submit(() -> {
					List<Hillside.Site> out = new ArrayList<>();
					for (int[] c : cs) {
						for (Hillside.Shape shape : shapes) {
							out.add(search(MineEntranceStructure.terrain(shared), c, shape, false));
						}
					}
					return out;
				}));
			}
			for (Future<List<Hillside.Site>> h : threads) {
				List<Hillside.Site> got = h.get();
				for (int i = 0; i < expected.size(); i++) {
					assertTrue(Objects.equals(expected.get(i), got.get(i)), "búsqueda " + i);
				}
			}
		} finally {
			pool.shutdownNow();
		}
		assertTrue(shared.size() <= shared.capacity());
	}
}
