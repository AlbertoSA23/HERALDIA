package io.github.albertosa23.heraldia.minas;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import io.github.albertosa23.heraldia.comun.Alturas;
import io.github.albertosa23.heraldia.comun.CacheAlturas;
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
 * La búsqueda de ladera de las entradas a mina de ahora (comprobaciones reordenadas, {@link Ladera}, con la caché
 * compartida de alturas, {@link CacheAlturas}) da exactamente lo mismo que la de la 0.1.0 ({@link LaderaAntigua}, con una
 * caché por búsqueda, {@link Alturas}): mismas minas en los mismos
 * sitios. Con el terreno real de 26.3 (VanillaRegistries, sin servidor) en varias semillas y muchos chunks, con las formas
 * de las tres bocas del datapack generado, en el orden de la generación (los diez estilos y variantes del set miran el
 * mismo chunk), con una caché diminuta que se vacía a mitad de búsqueda y desde varios hilos a la vez.
 */
class MinasDeterminismoTest {
	private static final long[] SEMILLAS = {20261116L, 1L, -4242L};
	private static final int CHUNKS_POR_SEMILLA = 40;
	private static HolderLookup.Provider vanilla;
	private static NoiseGeneratorSettings ajustes;
	private static Holder<NoiseGeneratorSettings> ajustesHolder;
	private static MultiNoiseBiomeSource biomas;
	private static final LevelHeightAccessor ALTO = LevelHeightAccessor.create(-64, 384);
	private static final Map<String, Ladera.Forma> FORMAS = new LinkedHashMap<>();

	@BeforeAll
	static void bootstrap() throws IOException {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
		// Las alturas del fondo (OCEAN_FLOOR_WG) miran la etiqueta de bloques minecraft:blocks_motion_in_heightmap: sin las
		// etiquetas de vanilla cargadas, todo da el fondo del mundo (como el servidor al cargar sus datos).
		var datos = new MultiPackResourceManager(PackType.SERVER_DATA, List.<PackResources>of(ServerPacksSource.createVanillaPackSource().fullResources()));
		TagLoader.loadTagsForExistingRegistries(datos, RegistryAccess.fromRegistryOfRegistries(BuiltInRegistries.REGISTRY))
				.forEach(Registry.PendingTags::apply);
		vanilla = VanillaRegistries.createWorldLookup();
		ajustesHolder = vanilla.lookupOrThrow(Registries.NOISE_SETTINGS).getOrThrow(NoiseGeneratorSettings.OVERWORLD);
		ajustes = ajustesHolder.value();
		biomas = MultiNoiseBiomeSource.createFromPreset(vanilla.lookupOrThrow(Registries.MULTI_NOISE_BIOME_SOURCE_PARAMETER_LIST)
				.getOrThrow(MultiNoiseBiomeSourceParameterLists.OVERWORLD));
		Path dir = Path.of(System.getProperty("heraldia.generated", "build/generated/heraldia"), "data", "heraldia", "worldgen", "structure", "minas");
		try (Stream<Path> files = Files.walk(dir)) {
			for (Path f : files.filter(p -> p.toString().endsWith(".json")).sorted().toList()) {
				JsonObject o = JsonParser.parseString(Files.readString(f)).getAsJsonObject();
				FORMAS.put(dir.relativize(f).toString(), forma(o));
			}
		}
		assertTrue(FORMAS.size() >= 30, "formas de las minas en el datapack: " + FORMAS.size());
	}

	private static Ladera.Forma forma(JsonObject o) {
		JsonArray e = o.getAsJsonArray("entrada"), p = o.getAsJsonArray("patio");
		List<int[]> techo = new ArrayList<>();
		for (JsonElement t : o.getAsJsonArray("techo")) {
			JsonArray a = t.getAsJsonArray();
			techo.add(new int[] {a.get(0).getAsInt(), a.get(1).getAsInt(), a.get(2).getAsInt()});
		}
		return new Ladera.Forma(new BlockPos(e.get(0).getAsInt(), e.get(1).getAsInt(), e.get(2).getAsInt()), p.get(0).getAsInt(),
				p.get(1).getAsInt(), p.get(2).getAsInt(), p.get(3).getAsInt(), techo);
	}

	/** Una forma de cada (las de los estilos y variantes de un tamaño coinciden). */
	private static List<Ladera.Forma> distintas() {
		Map<String, Ladera.Forma> out = new LinkedHashMap<>();
		FORMAS.values().forEach(f -> out.putIfAbsent(clave(f), f));
		return List.copyOf(out.values());
	}

	private static String clave(Ladera.Forma f) {
		return f.entrada() + " " + f.patioX0() + "," + f.patioZ0() + "," + f.patioX1() + "," + f.patioZ1() + " "
				+ java.util.Arrays.deepToString(f.techo().toArray());
	}

	/** Alturas de generación del mundo principal con esa semilla, contando cuántas columnas se evalúan. */
	private static CacheAlturas.Fuente fuente(long seed, AtomicInteger evaluadas) {
		RandomState rs = RandomState.create(vanilla.lookupOrThrow(Registries.NOISE), seed, ajustes);
		NoiseBasedChunkGenerator g = new NoiseBasedChunkGenerator(biomas, ajustesHolder);
		return (x, z, tipo) -> {
			evaluadas.incrementAndGet();
			return g.getBaseHeight(x, z, tipo, ALTO, rs);
		};
	}

	/**
	 * Chunks al azar (con la semilla del test) hasta 20.000 bloques del 0,0: una cuarta parte cualquiera (llanuras, mar...) y
	 * el resto con pendiente (el terreno sube al menos {@link Ladera#SUBIDA_MIN} hacia algún lado), donde la búsqueda llega
	 * hasta el final y salen laderas.
	 */
	private static List<int[]> chunks(long seed, int n, CacheAlturas.Fuente f) {
		Random r = new Random(seed * 31 + 7);
		List<int[]> out = new ArrayList<>();
		int cualquiera = n / 4;
		for (int intento = 0; out.size() < n && intento < n * 200; intento++) {
			int[] c = {r.nextInt(2500) - 1250, r.nextInt(2500) - 1250};
			if (out.size() < cualquiera || pendiente(f, c[0] * 16 + 8, c[1] * 16 + 8) >= Ladera.SUBIDA_MIN) {
				out.add(c);
			}
		}
		return out;
	}

	private static int pendiente(CacheAlturas.Fuente f, int x, int z) {
		Ladera.Terreno t = MinaEntradaStructure.terreno(new Alturas(f, 63));
		int r = Ladera.RADIO;
		return Math.max(Math.abs(t.suelo(x + r, z) - t.suelo(x - r, z)), Math.abs(t.suelo(x, z + r) - t.suelo(x, z - r)));
	}

	private static Ladera.Sitio buscar(Ladera.Terreno t, int[] c, Ladera.Forma f, boolean forzada) {
		return Ladera.buscar(t, c[0] * 16 + 8, c[1] * 16 + 8, f, ALTO.getMinY(), forzada);
	}

	/** La ruta antigua entera: la búsqueda de la 0.1.0 ({@link LaderaAntigua}) con una caché nueva por búsqueda. */
	private static Ladera.Sitio antigua(CacheAlturas.Fuente f, int[] c, Ladera.Forma forma, boolean forzada) {
		return LaderaAntigua.buscar(MinaEntradaStructure.terreno(new Alturas(f, 63)), c[0] * 16 + 8, c[1] * 16 + 8, forma, ALTO.getMinY(), forzada);
	}

	@Test
	void laCacheCompartidaDaLasMismasMinasQueLaRutaAntigua() {
		int encontradas = 0, comparadas = 0;
		long antes = 0, despues = 0;
		for (long seed : SEMILLAS) {
			AtomicInteger viejas = new AtomicInteger(), nuevas = new AtomicInteger();
			CacheAlturas.Fuente fv = fuente(seed, viejas), fn = fuente(seed, nuevas);
			CacheAlturas compartida = new CacheAlturas(fn, 63, CacheAlturas.CAPACIDAD);
			for (int[] c : chunks(seed, CHUNKS_POR_SEMILLA, fuente(seed, new AtomicInteger()))) {
				// antes: cada estructura del set (diez por tamaño) con su propia caché, nueva en cada findGenerationPoint; las
				// de formas iguales dan lo mismo, así que la ruta antigua se calcula una vez por forma distinta y se cuenta
				// como si se hubiera repetido
				Map<String, Ladera.Sitio> antiguas = new java.util.HashMap<>();
				Map<String, Integer> coste = new java.util.HashMap<>();
				for (Map.Entry<String, Ladera.Forma> e : FORMAS.entrySet()) {
					Ladera.Forma forma = e.getValue();
					String k = clave(forma);
					if (!antiguas.containsKey(k)) {
						int n0 = viejas.get();
						antiguas.put(k, antigua(fv, c, forma, false));
						coste.put(k, viejas.get() - n0);
					} else {
						viejas.addAndGet(coste.get(k));
					}
					Ladera.Sitio viejo = antiguas.get(k);
					Ladera.Sitio nuevo = buscar(MinaEntradaStructure.terreno(compartida), c, forma, false);
					assertEquals(viejo, nuevo, () -> "semilla " + seed + ", chunk " + c[0] + "," + c[1] + ", " + e.getKey());
					comparadas++;
					if (nuevo != null) {
						encontradas++;
					}
				}
			}
			antes += viejas.get();
			despues += nuevas.get();
		}
		assertTrue(comparadas >= SEMILLAS.length * CHUNKS_POR_SEMILLA * 30, "comparadas " + comparadas);
		assertTrue(encontradas >= 20, "pocas laderas encontradas para que la comparación valga: " + encontradas);
		// la mejora: los estilos y variantes del set (y luego /locate) ya no repiten columnas
		assertTrue(despues * 5 < antes, "columnas evaluadas: " + antes + " antes, " + despues + " con la caché compartida");
		System.out.printf("MinasDeterminismo: %d búsquedas, %d laderas; columnas evaluadas %d -> %d%n", comparadas, encontradas, antes, despues);
	}

	@Test
	void conLaCacheDiminutaQueSeVaciaAMitadTambienDaLoMismo() {
		long seed = SEMILLAS[0];
		AtomicInteger n = new AtomicInteger();
		CacheAlturas.Fuente f = fuente(seed, n);
		CacheAlturas diminuta = new CacheAlturas(f, 63, 64);    // una columna por franja: se vacía sin parar
		int encontradas = 0;
		for (int[] c : chunks(seed + 1, 40, f)) {
			for (Ladera.Forma forma : distintas()) {
			Ladera.Sitio viejo = antigua(f, c, forma, false);
			assertEquals(viejo, buscar(MinaEntradaStructure.terreno(diminuta), c, forma, false), () -> "chunk " + c[0] + "," + c[1]);
			assertEquals(antigua(f, c, forma, true),
					buscar(MinaEntradaStructure.terreno(diminuta), c, forma, true), () -> "forzada, chunk " + c[0] + "," + c[1]);
			encontradas += viejo != null ? 1 : 0;
			assertTrue(diminuta.tamano() <= diminuta.capacidad());
			}
		}
		assertTrue(encontradas > 0, "ninguna ladera: la comparación no vale");
		assertEquals(64, diminuta.capacidad());
	}

	@Test
	void desdeVariosHilosALaVezDaLoMismo() throws Exception {
		long seed = SEMILLAS[1];
		AtomicInteger n = new AtomicInteger();
		CacheAlturas.Fuente f = fuente(seed, n);
		CacheAlturas compartida = new CacheAlturas(f, 63, 4096);
		List<int[]> cs = chunks(seed + 2, 40, f);
		List<Ladera.Forma> formas = distintas();
		List<Ladera.Sitio> esperado = new ArrayList<>();
		for (int[] c : cs) {
			for (Ladera.Forma forma : formas) {
				esperado.add(antigua(f, c, forma, false));
			}
		}
		ExecutorService pool = Executors.newFixedThreadPool(4);
		try {
			List<Future<List<Ladera.Sitio>>> hilos = new ArrayList<>();
			for (int h = 0; h < 4; h++) {
				hilos.add(pool.submit(() -> {
					List<Ladera.Sitio> out = new ArrayList<>();
					for (int[] c : cs) {
						for (Ladera.Forma forma : formas) {
							out.add(buscar(MinaEntradaStructure.terreno(compartida), c, forma, false));
						}
					}
					return out;
				}));
			}
			for (Future<List<Ladera.Sitio>> h : hilos) {
				List<Ladera.Sitio> got = h.get();
				for (int i = 0; i < esperado.size(); i++) {
					assertTrue(Objects.equals(esperado.get(i), got.get(i)), "búsqueda " + i);
				}
			}
		} finally {
			pool.shutdownNow();
		}
		assertTrue(compartida.tamano() <= compartida.capacidad());
	}
}
