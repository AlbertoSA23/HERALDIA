package io.github.albertosa23.heraldia.config;

import com.mojang.serialization.Codec;
import com.mojang.serialization.MapCodec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashSet;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLevelEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.minecraft.core.Holder;
import net.minecraft.core.QuartPos;
import net.minecraft.core.Vec3i;
import net.minecraft.core.registries.Registries;
import net.minecraft.tags.TagKey;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.biome.Biome;
import net.minecraft.world.level.biome.BiomeResolver;
import net.minecraft.world.level.chunk.ChunkGeneratorStructureState;
import net.minecraft.world.level.levelgen.densityfunction.SamplerContext;
import net.minecraft.world.level.levelgen.structure.placement.AbstractSpreadingStructurePlacement;
import net.minecraft.world.level.levelgen.structure.placement.RandomSpreadStructurePlacement;
import net.minecraft.world.level.levelgen.structure.placement.RandomSpreadType;
import org.jspecify.annotations.Nullable;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * heraldia:rejilla: un random_spread cuya separación, activación, máximo de casillas y zona de exclusión salen de
 * config/heraldia.json. Los valores del JSON del datapack (spacing, separation, exclusion_zone) son los de por defecto
 * y marcan la proporción; el grupo ("aldeas" o "unicas/&lt;id&gt;") dice qué opciones se aplican. Todo se calcula al
 * leer el datapack y queda inmutable. Hereda de random_spread para que /locate la recorra como a las vanilla.
 * <p>En las únicas la separación del datapack no se usa: la mínima es la distancia mínima entre únicas (así dos del
 * mismo tipo tampoco quedan más cerca) y el origen de la rejilla se desplaza por tipo (según la sal). Con la proporción
 * 190/250 y origen común, las candidatas de todos los tipos caían en la misma esquina de 960 bloques de cada casilla.
 * <p>Con «bioma» (una etiqueta de biomas, opcional) la candidata de cada casilla deja de ser un chunk al azar: es el
 * punto de una malla de 128 bloques, dentro de la misma ventana que el random_spread (así se conserva la separación
 * mínima), que cae en ese bioma y tiene más vecinos a 64 bloques también en él (el más metido en el bioma). Sirve para
 * biomas tan raros que una candidata al azar casi nunca acierta (los campos de champiñones). La búsqueda solo lee el
 * ruido de biomas del mundo principal (sin cargar chunks), se hace una vez por casilla y queda en memoria.
 * «bioma_y» (opcional, por defecto 64) es la altura a la que se mira el bioma: para los de cueva (la Mina perdida),
 * la del centro de la estructura.
 * <p>«rejilla_antigua» marca las únicas que ya estaban en la 0.1.0. Con la opción unicas.rejilla_compatible (mundos
 * creados con esa versión) usan la rejilla de entonces: separación interna con la proporción del datapack (190/250),
 * origen común y sin búsqueda de bioma; isPlacementChunk y getPotentialStructureChunk acaban en el random_spread de
 * vanilla con desfase 0, el mismo coste que entonces. Así /locate, los mapas y la distancia mínima vuelven a dar con las
 * ya generadas. Las demás siguen con la rejilla nueva (y {@link UniqueSeparation} da prioridad a las antiguas).
 */
@SuppressWarnings("deprecation") // ExclusionZone está marcada obsoleta en vanilla, pero es la que usan sus aldeas
public final class GridPlacement extends RandomSpreadStructurePlacement {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	public static final MapCodec<GridPlacement> CODEC = RecordCodecBuilder.mapCodec(i -> i.group(
			Codec.STRING.fieldOf("grupo").forGetter(p -> p.group),
			Codec.intRange(1, 4096).fieldOf("spacing").forGetter(p -> p.baseSpacing),
			Codec.intRange(0, 4095).fieldOf("separation").forGetter(p -> p.baseSeparation),
			Codec.INT.fieldOf("salt").forGetter(p -> p.baseSalt),
			AbstractSpreadingStructurePlacement.ExclusionZone.CODEC.optionalFieldOf("exclusion_zone").forGetter(p -> p.baseExclusion),
			TagKey.codec(Registries.BIOME).optionalFieldOf("bioma").forGetter(p -> p.biome),
			Codec.intRange(-64, 320).optionalFieldOf("bioma_y", 64).forGetter(p -> p.sampleY),
			Codec.BOOL.optionalFieldOf("rejilla_antigua", false).forGetter(p -> p.oldGrid)
	).apply(i, GridPlacement::create));
	/** Malla de la búsqueda de bioma (chunks), vecinos a medio paso y vecinos mínimos (de 9) para aceptar un punto. */
	private static final int STEP = 8, HALF = STEP / 2, MIN_SCORE = 6, SAMPLE_Y = 64, CACHE_MAX = 1 << 14;
	private static final long NONE = Long.MIN_VALUE;
	private record BiomeContext(long seed, BiomeResolver resolver) {
	}
	private static volatile @Nullable BiomeContext context;
	private static volatile int searchesLogged;

	private final String group;
	private final boolean oldGrid; // marcada en el datapack (existía en la 0.1.0)
	private final boolean legacy;  // y la opción unicas.rejilla_compatible está activada: rejilla de la 0.1.0
	private final int baseSpacing, baseSeparation, baseSalt;
	private final Optional<AbstractSpreadingStructurePlacement.ExclusionZone> baseExclusion;
	private final boolean enabled;
	private final Set<Long> cells; // null = sin límite
	private final int offsetX, offsetZ; // desfase del origen de la rejilla, en chunks (0 en las aldeas)
	private final Optional<TagKey<Biome>> biome;
	private final int sampleY; // altura a la que se mira el bioma (la del mar; más abajo, para biomas de cueva)
	private final ConcurrentHashMap<Long, Long> candidates = new ConcurrentHashMap<>(); // casilla -> chunk (o NONE)
	private volatile @Nullable BiomeContext cachedFor;

	private GridPlacement(String group, int baseSpacing, int baseSeparation, int salt,
						  Optional<AbstractSpreadingStructurePlacement.ExclusionZone> baseExclusion, Optional<TagKey<Biome>> biome, int sampleY,
						  boolean oldGrid, Settings s) {
		super(Vec3i.ZERO, AbstractSpreadingStructurePlacement.FrequencyReductionMethod.DEFAULT, 1.0F, salt, s.exclusion,
				s.spacing, s.separation, RandomSpreadType.LINEAR);
		this.group = group;
		this.oldGrid = oldGrid;
		this.legacy = s.legacy;
		this.baseSpacing = baseSpacing;
		this.baseSeparation = baseSeparation;
		this.baseSalt = salt;
		this.baseExclusion = baseExclusion;
		this.biome = s.legacy ? Optional.empty() : biome;
		this.sampleY = sampleY;
		this.enabled = s.enabled;
		this.cells = s.maxCells < 0 ? null : Set.copyOf(nearestCells(s.maxCells));
		this.offsetX = s.shifted ? (int) Math.floorMod(UniqueSeparation.mix(salt * 0x9E3779B97F4A7C15L), (long) s.spacing) : 0;
		this.offsetZ = s.shifted ? (int) Math.floorMod(UniqueSeparation.mix(salt * 0xC2B2AE3D27D4EB4FL + 1), (long) s.spacing) : 0;
	}

	private record Settings(boolean enabled, int spacing, int separation, int maxCells,
							Optional<AbstractSpreadingStructurePlacement.ExclusionZone> exclusion, boolean shifted, boolean legacy) {
	}

	private static GridPlacement create(String group, int spacing, int separation, int salt,
										Optional<AbstractSpreadingStructurePlacement.ExclusionZone> exclusion, Optional<TagKey<Biome>> biome,
										int sampleY, boolean oldGrid) {
		HeraldiaConfig cfg = HeraldiaConfig.get();
		Settings s;
		if (group.equals("aldeas")) {
			int sp = chunks(cfg.getInt("aldeas.separacion_bloques"));
			int distance = cfg.getInt("aldeas.distancia_aldeas_vanilla_bloques");
			Optional<AbstractSpreadingStructurePlacement.ExclusionZone> ex = distance == 0 ? Optional.empty()
					: exclusion.map(z -> new AbstractSpreadingStructurePlacement.ExclusionZone(z.otherSet(), Math.clamp((distance + 15) / 16, 1, 16)));
			s = new Settings(true, sp, scaled(sp, spacing, separation), cfg.getInt("aldeas.maximo"), ex, false, false);
		} else if (group.startsWith("unicas/") && cfg.has(group.replace('/', '.') + ".separacion_bloques")) {
			String key = group.replace('/', '.');
			int sp = chunks(cfg.getInt(key + ".separacion_bloques"));
			if (oldGrid && cfg.getBool(LEGACY_OPTION)) { // la de la 0.1.0, tal cual: proporción del datapack y origen común
				s = new Settings(cfg.getBool(key + ".activada"), sp, scaled(sp, spacing, separation), -1, exclusion, false, true);
			} else {
				int sep = Math.clamp((cfg.getInt("unicas.distancia_minima.bloques") + 15) / 16, 0, sp - 1);
				s = new Settings(cfg.getBool(key + ".activada"), sp, sep, -1, exclusion, true, false);
			}
		} else {
			LOGGER.warn("Heraldia: grupo de colocación sin opciones {}; se usan los valores del datapack", group);
			s = new Settings(true, spacing, Math.min(separation, spacing - 1), -1, exclusion, false, false);
		}
		LOGGER.info("Heraldia: rejilla {}: {}, cada {} chunks (separación mínima {}{}), {}, exclusión {}{}", group,
				s.enabled ? "activada" : "desactivada", s.spacing, s.separation,
				s.shifted ? ", origen desplazado" : s.legacy ? ", rejilla antigua" : "",
				s.maxCells < 0 ? "sin máximo" : "máximo " + s.maxCells + " casillas",
				s.exclusion.map(z -> z.chunkCount() + " chunks").orElse("ninguna"),
				biome.filter(b -> !s.legacy).map(b -> ", candidata en el bioma #" + b.location() + (sampleY != SAMPLE_Y ? " a y = " + sampleY : "")).orElse(""));
		return new GridPlacement(group, spacing, separation, salt, exclusion, biome, sampleY, oldGrid, s);
	}

	/** Opción de los mundos creados con la 0.1.0: las únicas de entonces vuelven a su rejilla. */
	public static final String LEGACY_OPTION = "unicas.rejilla_compatible";

	/** Usa la rejilla de la 0.1.0 (marcada en el datapack y con unicas.rejilla_compatible activada). */
	public boolean legacy() {
		return legacy;
	}

	private static int chunks(int blocks) {
		return Math.clamp(Math.round(blocks / 16.0F), 2, 4096);
	}

	/** Separación mínima con la misma proporción que la del datapack (62/94 en las aldeas). */
	private static int scaled(int spacing, int baseSpacing, int baseSeparation) {
		return Math.clamp(Math.round((float) spacing * baseSeparation / baseSpacing), 0, spacing - 1);
	}

	/** Las n casillas cuyo centro está más cerca del 0,0 (empates por z y luego x): deterministas, sin datos guardados. */
	private static Set<Long> nearestCells(int n) {
		int r = (int) Math.ceil(Math.sqrt(n)) + 1;
		List<int[]> all = new ArrayList<>();
		for (int x = -r; x < r; x++) {
			for (int z = -r; z < r; z++) {
				all.add(new int[]{x, z});
			}
		}
		all.sort(Comparator.<int[]>comparingDouble(c -> (c[0] + 0.5) * (c[0] + 0.5) + (c[1] + 0.5) * (c[1] + 0.5))
				.thenComparingInt(c -> c[1]).thenComparingInt(c -> c[0]));
		Set<Long> out = new HashSet<>();
		for (int i = 0; i < n; i++) {
			out.add(ChunkPos.pack(all.get(i)[0], all.get(i)[1]));
		}
		return out;
	}

	private boolean allowed(int chunkX, int chunkZ) {
		return enabled && (cells == null || cells.contains(ChunkPos.pack(Math.floorDiv(chunkX - offsetX, spacing()), Math.floorDiv(chunkZ - offsetZ, spacing()))));
	}

	/** Desfase del origen de la rejilla en chunks: la casilla de un chunk x es floorDiv(x - offsetX(), spacing()). */
	public int offsetX() {
		return offsetX;
	}

	public int offsetZ() {
		return offsetZ;
	}

	/** La de random_spread con la rejilla desplazada: la usan /locate, los mapas y UniqueSeparation. */
	@Override
	public ChunkPos getPotentialStructureChunk(long seed, int chunkX, int chunkZ) {
		if (biome.isPresent()) {
			long c = biomeCandidate(seed, chunkX, chunkZ);
			if (c != NONE) {
				return new ChunkPos((int) (c >> 32), (int) c);
			}
		}
		if (offsetX == 0 && offsetZ == 0) {
			return super.getPotentialStructureChunk(seed, chunkX, chunkZ);
		}
		ChunkPos c = super.getPotentialStructureChunk(seed, chunkX - offsetX, chunkZ - offsetZ);
		return new ChunkPos(c.x() + offsetX, c.z() + offsetZ);
	}

	@Override
	protected boolean isPlacementChunk(ChunkGeneratorStructureState state, int chunkX, int chunkZ) {
		if (!allowed(chunkX, chunkZ)) {
			return false;
		}
		if (biome.isPresent() && context != null) {
			// Solo los puntos de la malla pueden ser candidatos: los demás chunks salen sin tocar la memoria.
			int wx = Math.floorMod(chunkX - offsetX, spacing()) - first(), wz = Math.floorMod(chunkZ - offsetZ, spacing()) - first();
			if (wx < 0 || wz < 0 || wx % STEP != 0 || wz % STEP != 0) {
				return false;
			}
			long c = biomeCandidate(state.getLevelSeed(), chunkX, chunkZ);
			return c != NONE && (int) (c >> 32) == chunkX && (int) c == chunkZ;
		}
		// Ruta caliente (cada chunk): mismo coste que vanilla, una sola ChunkPos y sin pasar por la versión desplazada.
		ChunkPos c = super.getPotentialStructureChunk(state.getLevelSeed(), chunkX - offsetX, chunkZ - offsetZ);
		return c.x() + offsetX == chunkX && c.z() + offsetZ == chunkZ;
	}

	/** /locate no pasa por isPlacementChunk sino por aquí: así no señala casillas desactivadas o fuera del máximo. */
	@Override
	public boolean applyAdditionalChunkRestrictions(int chunkX, int chunkZ, long seed) {
		return allowed(chunkX, chunkZ) && (biome.isEmpty() || context == null || biomeCandidate(seed, chunkX, chunkZ) != NONE)
				&& super.applyAdditionalChunkRestrictions(chunkX, chunkZ, seed);
	}

	/** Ancho (chunks) de la ventana donde random_spread pone la candidata de cada casilla. */
	private int window() {
		return spacing() - separation();
	}

	/**
	 * Candidata de la casilla del chunk (chunkX, chunkZ) según el bioma, empaquetada (x << 32 | z), o NONE si la casilla
	 * no tiene un sitio bueno. Sin mundo cargado (o con otra semilla), NONE: se usa la candidata de siempre.
	 */
	private long biomeCandidate(long seed, int chunkX, int chunkZ) {
		BiomeContext ctx = context;
		if (ctx == null || ctx.seed != seed) {
			return NONE;
		}
		if (cachedFor != ctx) {
			candidates.clear();
			cachedFor = ctx;
		}
		int gx = Math.floorDiv(chunkX - offsetX, spacing()), gz = Math.floorDiv(chunkZ - offsetZ, spacing());
		long cell = ChunkPos.pack(gx, gz);
		Long hit = candidates.get(cell);
		if (hit != null) {
			return hit;
		}
		long t = System.nanoTime();
		long found = search(ctx, seed, gx * spacing() + offsetX, gz * spacing() + offsetZ);
		if (candidates.size() > CACHE_MAX) {
			candidates.clear();
		}
		candidates.put(cell, found);
		if (searchesLogged < 3) {
			searchesLogged++;
			LOGGER.info("Heraldia: rejilla {}: búsqueda del bioma en la casilla {}, {}: {} ({} ms)", group, gx, gz,
					found == NONE ? "sin sitio" : "chunk " + (int) (found >> 32) + ", " + (int) found, (System.nanoTime() - t) / 1_000_000);
		}
		return found;
	}

	/** Primer punto de la malla dentro de la ventana (chunks desde el origen de la casilla). */
	private int first() {
		return window() >= STEP ? HALF : window() / 2;
	}

	/** Malla de STEP chunks en la ventana de la casilla; puntuación = vecinos (de 9, a HALF chunks) en el bioma. */
	private long search(BiomeContext ctx, long seed, int x0, int z0) {
		int win = window(), n = Math.max(1, win / STEP), first = first();
		TagKey<Biome> tag = biome.orElseThrow();
		long best = NONE, bestKey = Long.MIN_VALUE;
		for (int a = 0; a < n; a++) {
			for (int b = 0; b < n; b++) {
				int cx = x0 + first + a * STEP, cz = z0 + first + b * STEP;
				if (!in(ctx, tag, cx, cz, sampleY)) {
					continue;
				}
				int score = 1;
				for (int dx = -HALF; dx <= HALF; dx += HALF) {
					for (int dz = -HALF; dz <= HALF; dz += HALF) {
						if ((dx != 0 || dz != 0) && in(ctx, tag, cx + dx, cz + dz, sampleY)) {
							score++;
						}
					}
				}
				if (score < MIN_SCORE) {
					continue;
				}
				long key = (long) score << 56 | (UniqueSeparation.mix(seed ^ ChunkPos.pack(cx, cz) ^ baseSalt) >>> 8);
				if (best == NONE || key > bestKey) {
					best = (long) cx << 32 | (cz & 0xFFFFFFFFL);
					bestKey = key;
				}
			}
		}
		return best;
	}

	/** El bioma en la esquina del chunk (donde el jigsaw comprueba el suyo), a la altura y (la del mar por defecto). */
	private static boolean in(BiomeContext ctx, TagKey<Biome> tag, int chunkX, int chunkZ, int y) {
		Holder<Biome> b = ctx.resolver.getNoiseBiome(QuartPos.fromBlock(chunkX * 16), QuartPos.fromBlock(y), QuartPos.fromBlock(chunkZ * 16));
		return b.is(tag);
	}

	/** Prepara la búsqueda de bioma al cargar el mundo principal (y la olvida al parar el servidor). Una línea en Heraldia. */
	public static void registerBiomeSearch() {
		ServerLevelEvents.LOAD.register((server, level) -> {
			if (level.dimension() == Level.OVERWORLD) {
				var randomState = level.getChunkSource().getGeneratorState().randomState();
				context = new BiomeContext(level.getSeed(), level.getChunkSource().getGenerator().getBiomeSource()
						.createResolver(randomState.createClimateSampler(SamplerContext.EMPTY_UNCACHED)));
				searchesLogged = 0;
			}
		});
		ServerLifecycleEvents.SERVER_STOPPED.register(server -> context = null);
	}

	@Override
	@SuppressWarnings("unchecked")
	public MapCodec<RandomSpreadStructurePlacement> codec() {
		return (MapCodec<RandomSpreadStructurePlacement>) (MapCodec<?>) CODEC;
	}
}
