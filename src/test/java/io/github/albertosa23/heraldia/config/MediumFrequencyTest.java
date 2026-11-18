package io.github.albertosa23.heraldia.config;

import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.mojang.serialization.JsonOps;
import io.github.albertosa23.heraldia.common.MediumStructures;
import io.github.albertosa23.heraldia.common.ForeignZone;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Stream;
import net.minecraft.SharedConstants;
import net.minecraft.core.HolderLookup;
import net.minecraft.core.QuartPos;
import net.minecraft.core.registries.Registries;
import net.minecraft.data.registries.VanillaRegistries;
import net.minecraft.resources.Identifier;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.biome.BiomeResolver;
import net.minecraft.world.level.biome.MultiNoiseBiomeSource;
import net.minecraft.world.level.biome.MultiNoiseBiomeSourceParameterLists;
import net.minecraft.world.level.levelgen.NoiseGeneratorSettings;
import net.minecraft.world.level.levelgen.RandomState;
import net.minecraft.world.level.levelgen.densityfunction.SamplerContext;
import net.minecraft.world.level.levelgen.structure.Structure;
import net.minecraft.world.level.levelgen.structure.placement.RandomSpreadStructurePlacement;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/**
 * Frecuencia real de las estructuras medianas con la configuración por defecto: simula la rejilla (las mismas
 * GridPlacement del datapack generado, con la búsqueda de la candidata en su bioma) sobre el ruido de biomas real del
 * mundo principal de 26.3 (VanillaRegistries, sin servidor), con las aldeas y las únicas a su alrededor (su rejilla, sus
 * biomas y la distancia mínima entre únicas), las rejillas vanilla de estructuras que asoman (a las que ceden el sitio) y la
 * regla de {@link MediumStructures}. Mide cuántas salen en un cuadrado de LADO bloques por semilla y la separación media que
 * resulta (raíz del área por estructura), y comprueba que ninguna queda en la zona de una aldea o una única que sale.
 * Aproximaciones: el bioma de la candidata se mira en la esquina del chunk a y = 96 (el de aldeas y únicas, a 64) y no se
 * mira el terreno (findValidGenerationPoint
 * también descarta algo por altura), ni la zona de exclusión frente a las aldeas vanilla, ni la Atlántida.
 */
class MediumFrequencyTest {
	private static final int SIDE = 16000;
	private static final long[] SEEDS = {1L, 20261116L, -4242L};
	/** Owner's target (T24): overall, one every ~400-800 blocks. */
	private static final double MIN_SEP = 400, MAX_SEP = 800;
	private static HolderLookup.Provider vanilla;
	private static Path data;

	@BeforeAll
	static void bootstrap() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
		vanilla = VanillaRegistries.createWorldLookup();
		data = Path.of(System.getProperty("heraldia.generated", "build/generated/heraldia"), "data", "heraldia");
		HeraldiaConfig.load(null);
	}

	private static JsonObject json(Path p) {
		try {
			return JsonParser.parseString(Files.readString(p)).getAsJsonObject();
		} catch (IOException e) {
			throw new IllegalStateException("falta " + p + " (¿se ha generado el datapack?)", e);
		}
	}

	/** Biomas vanilla de una etiqueta de Heraldia (#heraldia:x, con las etiquetas de Heraldia anidadas). */
	private static Set<String> biomes(String tag) {
		Set<String> out = new HashSet<>();
		for (JsonElement e : json(data.resolve("tags/worldgen/biome/" + tag.substring("#heraldia:".length()) + ".json")).getAsJsonArray("values")) {
			if (e.isJsonPrimitive()) {
				String v = e.getAsString();
				if (v.startsWith("#heraldia:")) {
					out.addAll(biomes(v));
				} else if (!v.startsWith("#")) {
					out.add(v);
				}
			}
		}
		return out;
	}

	private static Set<String> biomesOf(String structure) {
		return biomes(json(data.resolve("worldgen/structure/" + structure.substring("heraldia:".length()) + ".json")).get("biomes").getAsString());
	}

	@AfterAll
	static void restore() {
		GridPlacement.testContext(0, null);
		HeraldiaConfig.load(null);
	}

	private static final Map<Structure, Set<String>> VANILLA = new HashMap<>();
	private static JsonObject VANILLA_TAGS_FIELD;

	/** Biomas de una estructura vanilla: su lista o su etiqueta (#minecraft:has_structure/...) resuelta con mcmeta. */
	private static Set<String> vanillaBiomes(Structure st) {
		return VANILLA.computeIfAbsent(st, k -> {
			Set<String> out = new HashSet<>();
			var tag = st.biomes().unwrapKey();
			if (tag.isEmpty()) {
				st.biomes().forEach(h -> out.add(h.unwrapKey().orElseThrow().identifier().toString()));
			} else {
				resolver(tag.get().location().getPath(), out);
			}
			return out;
		});
	}

	private static void resolver(String tag, Set<String> out) {
		if (VANILLA_TAGS_FIELD == null) {
			String dir = System.getProperty("heraldia.mcmeta", "build/mcmeta-summary");
			VANILLA_TAGS_FIELD = json(Path.of(dir, "data", "tag", "worldgen", "biome", "data.json"));
		}
		for (JsonElement e : VANILLA_TAGS_FIELD.getAsJsonObject(tag).getAsJsonArray("values")) {
			String v = e.isJsonPrimitive() ? e.getAsString() : e.getAsJsonObject().get("id").getAsString();
			if (v.startsWith("#")) {
				resolver(v.substring(v.indexOf(':') + 1), out);
			} else {
				out.add(v.contains(":") ? v : "minecraft:" + v);
			}
		}
	}

	/** heraldia:rejilla del structure_set, sin la zona de exclusión (necesita el registro). */
	private static GridPlacement mediumGrid(JsonObject set) {
		JsonObject p = set.getAsJsonObject("placement").deepCopy();
		p.remove("type");
		p.remove("exclusion_zone");
		return GridPlacement.CODEC.codec().parse(JsonOps.INSTANCE, p).getOrThrow();
	}

	private record Type(Identifier id, GridPlacement grid, Set<String> biomes) {
	}

	private static List<Type> types(String dir) throws IOException {
		List<Type> out = new ArrayList<>();
		try (Stream<Path> files = Files.list(data.resolve("worldgen/structure_set/" + dir))) {
			for (Path f : files.sorted().toList()) {
				JsonObject set = json(f);
				if (!set.getAsJsonObject("placement").get("type").getAsString().equals("heraldia:rejilla")) {
					continue; // la Atlántida (colocación propia)
				}
				Set<String> b = new HashSet<>();
				JsonArray structures = set.getAsJsonArray("structures");
				String first = structures.get(0).getAsJsonObject().get("structure").getAsString();
				if (json(data.resolve("worldgen/structure/" + first.substring("heraldia:".length()) + ".json")).get("type")
						.getAsString().equals("heraldia:dimension")) {
					continue; // del Nether o el End: ni en el mundo principal ni en su frecuencia
				}
				structures.forEach(e -> b.addAll(biomesOf(e.getAsJsonObject().get("structure").getAsString())));
				String name = f.getFileName().toString().replace(".json", "");
				out.add(new Type(Identifier.fromNamespaceAndPath("heraldia", dir + "/" + name), mediumGrid(set), b));
			}
		}
		return out;
	}

	@Test
	void frequencyWithRealBiomes() throws IOException {
		List<Type> uniques = types("unicas"), mediums = types("medianas");
		GridPlacement villages = mediumGrid(json(data.resolve("worldgen/structure_set/aldeas.json")));
		Set<String> villageBiomes = new HashSet<>();
		try (Stream<Path> files = Files.list(data.resolve("tags/worldgen/biome"))) {
			files.filter(Files::isRegularFile).forEach(f -> villageBiomes.addAll(biomes("#heraldia:" + f.getFileName().toString().replace(".json", ""))));
		}
		HeraldiaConfig cfg = HeraldiaConfig.get();
		int zoneBlocks = cfg.getInt(MediumStructures.ZONE), distance = cfg.getInt(MediumStructures.DISTANCE);
		Object src = new Object();
		UniqueSeparation sep = new UniqueSeparation(src, uniques.stream().map(Type::id).toList(),
				Collections.nCopies(uniques.size(), (Structure) null), uniques.stream().map(t -> (RandomSpreadStructurePlacement) t.grid).toList(),
				Collections.nCopies(uniques.size(), false), cfg.getBool("unicas.distancia_minima.activada"), cfg.getInt("unicas.distancia_minima.bloques"));
		NoiseGeneratorSettings settings = vanilla.lookupOrThrow(Registries.NOISE_SETTINGS).getOrThrow(NoiseGeneratorSettings.OVERWORLD).value();
		MultiNoiseBiomeSource source = MultiNoiseBiomeSource.createFromPreset(vanilla.lookupOrThrow(Registries.MULTI_NOISE_BIOME_SOURCE_PARAMETER_LIST)
				.getOrThrow(MultiNoiseBiomeSourceParameterLists.OVERWORLD));
		List<MediumStructures.Foreign> foreign = new ArrayList<>();   // las rejillas vanilla de estructuras que asoman
		vanilla.lookupOrThrow(Registries.STRUCTURE_SET).listElements().forEach(set -> {
			MediumStructures.Foreign a = MediumStructures.foreignAt(set.key().identifier(), set.value());
			if (a != null) {
				foreign.add(a);
			}
		});
		assertTrue(foreign.size() >= 8, "rejillas vanilla de estructuras que asoman: " + foreign.size());
		int total = 0;
		StringBuilder report = new StringBuilder();
		for (long seed : SEEDS) {
			RandomState rs = RandomState.create(vanilla.lookupOrThrow(Registries.NOISE), seed, settings);
			BiomeResolver resolver = source.createResolver(rs.createClimateSampler(SamplerContext.EMPTY_UNCACHED));
			Map<Long, String> cache = new HashMap<>(), highCache = new HashMap<>();
			java.util.function.BiFunction<Integer, Integer, String> biome = (x, z) -> cache.computeIfAbsent(ChunkPos.pack(x, z),
					k -> resolver.getNoiseBiome(QuartPos.fromBlock(x * 16), QuartPos.fromBlock(64), QuartPos.fromBlock(z * 16))
							.unwrapKey().orElseThrow().identifier().toString());
			java.util.function.BiFunction<Integer, Integer, String> highBiome = (x, z) -> highCache.computeIfAbsent(ChunkPos.pack(x, z),
					k -> resolver.getNoiseBiome(QuartPos.fromBlock(x * 16), QuartPos.fromBlock(96), QuartPos.fromBlock(z * 16))
							.unwrapKey().orElseThrow().identifier().toString());
			// la búsqueda de la candidata en el bioma de GridPlacement, con el ruido real (como registerBiomeSearch)
			Map<String, Set<String>> tags = new HashMap<>();
			GridPlacement.testContext(seed, (tag, qx, qy, qz) -> tags.computeIfAbsent(tag.location().toString(), t -> biomes("#" + t))
					.contains(resolver.getNoiseBiome(qx, qy, qz).unwrapKey().orElseThrow().identifier().toString()));
			UniqueSeparation.Viability unique = (j, x, z) -> uniques.get(j).biomes.contains(biome.apply(x, z));
			ForeignZone.Village village = (x, z) -> villageBiomes.contains(biome.apply(x, z));
			ForeignZone zone = new ForeignZone(src, zoneBlocks, villages, List.of(), List.of());
			MediumStructures m = new MediumStructures(src, mediums.stream().map(Type::id).toList(),
					mediums.stream().map(t -> List.of(t.id)).toList(), mediums.stream().map(t -> List.<Structure>of()).toList(),
					mediums.stream().map(t -> (RandomSpreadStructurePlacement) t.grid).toList(), null, distance, foreign);
			// una estructura vanilla «sale» si su candidata cae en uno de sus biomas (sin terreno); las etiquetas de biomas
			// no están ligadas en VanillaRegistries: se resuelven con el resumen de mcmeta de la compilación
			MediumStructures.Outcome foreignWins = (st, x, z) -> vanillaBiomes(st).contains(resolver.getNoiseBiome(QuartPos.fromBlock(x * 16),
					QuartPos.fromBlock(64), QuartPos.fromBlock(z * 16)).unwrapKey().orElseThrow().identifier().toString());
			MediumStructures.Zone inZone = (x, z) -> {
				long[] c = zone.nearby(sep, seed, x, z);
				return c != null && zone.occupied(c, sep, seed, unique, village) || m.yieldsToForeign(x, z, seed, foreignWins);
			};
			MediumStructures.Styles styles = (j, x, z) -> mediums.get(j).biomes.contains(highBiome.apply(x, z));
			// aldeas y únicas que salen en el cuadrado (y un margen): ninguna mediana a menos de la zona
			List<int[]> larges = new ArrayList<>();
			int r = SIDE / 32 + zoneBlocks / 16 + 1;
			for (int[] c : cells(villages, seed, r)) {
				if (villages.applyAdditionalChunkRestrictions(c[0], c[1], seed) && village.outcome(c[0], c[1])) {
					larges.add(c);
				}
			}
			for (int j = 0; j < uniques.size(); j++) {
				for (int[] c : cells(uniques.get(j).grid, seed, r)) {
					if (unique.valid(j, c[0], c[1]) && !sep.blocked(j, c[0], c[1], seed, unique)) {
						larges.add(c);
					}
				}
			}
			int n = 0, byZone = 0, byOther = 0, noBiome = 0;
			List<int[]> alive = new ArrayList<>();
			for (int i = 0; i < mediums.size(); i++) {
				int ofType = 0;
				GridPlacement g = mediums.get(i).grid;
				for (int[] c : cells(g, seed, SIDE / 32)) {
					if (Math.abs(c[0]) * 16 > SIDE / 2 || Math.abs(c[1]) * 16 > SIDE / 2 || !g.applyAdditionalChunkRestrictions(c[0], c[1], seed)) {
						continue;
					}
					if (!styles.outcome(i, c[0], c[1])) {
						noBiome++;
					} else if (inZone.occupied(c[0], c[1])) {
						byZone++;
					} else if (m.rejects(i, c[0], c[1], seed, inZone, styles, (x, z) -> false)) {
						byOther++;
					} else {
						ofType++;
						alive.add(c);
					}
				}
				n += ofType;
				report.append(String.format("  semilla %d %s: %d (una cada %.0f bloques)%n", seed, mediums.get(i).id.getPath(), ofType,
						ofType == 0 ? Double.POSITIVE_INFINITY : Math.sqrt((double) SIDE * SIDE / ofType)));
			}
			for (int[] v : alive) {
				for (int[] g : larges) {
					double d = Math.hypot((v[0] - g[0]) * 16.0, (v[1] - g[1]) * 16.0);
					assertTrue(d >= zoneBlocks, "mediana en " + v[0] * 16 + ", " + v[1] * 16 + " a " + Math.round(d) + " bloques de una aldea o única");
				}
			}
			double each = Math.sqrt((double) SIDE * SIDE / n);
			report.append(String.format("semilla %d: %d medianas en %d x %d bloques: una cada %.0f bloques (descartadas: %d sin bioma, %d por aldeas, únicas o estructuras vanilla, %d por otra mediana)%n",
					seed, n, SIDE, SIDE, each, noBiome, byZone, byOther));
			total += n;
		}
		double each = Math.sqrt((double) SIDE * SIDE * SEEDS.length / total);
		report.append(String.format("media: una cada %.0f bloques%n", each));
		System.out.print(report);
		assertTrue(each >= MIN_SEP && each <= MAX_SEP, "separación media " + Math.round(each) + " fuera de " + MIN_SEP + "-" + MAX_SEP + "\n" + report);
	}

	/** Candidatas de la rejilla en las casillas que cubren ±r chunks. */
	private static List<int[]> cells(RandomSpreadStructurePlacement p, long seed, int r) {
		List<int[]> out = new ArrayList<>();
		int s = p.spacing(), ox = UniqueSeparation.offsetX(p), oz = UniqueSeparation.offsetZ(p);
		for (int gx = Math.floorDiv(-r - ox, s); gx <= Math.floorDiv(r - ox, s); gx++) {
			for (int gz = Math.floorDiv(-r - oz, s); gz <= Math.floorDiv(r - oz, s); gz++) {
				ChunkPos c = p.getPotentialStructureChunk(seed, gx * s + ox, gz * s + oz);
				out.add(new int[]{c.x(), c.z()});
			}
		}
		return out;
	}
}
