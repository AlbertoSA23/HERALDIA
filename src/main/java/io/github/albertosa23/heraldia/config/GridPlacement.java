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
 * heraldia:rejilla: a random_spread whose separation, activation, maximum cells and exclusion zone come from
 * config/heraldia.json. The datapack JSON's values (spacing, separation, exclusion_zone) are the defaults
 * and set the ratio; the group ("aldeas", "unicas/&lt;id&gt;" or "medianas/&lt;id&gt;") says which options apply.
 * The mediums, like the uniques, with the origin shifted per type; their separation is divided by the square root of the
 * common frequency (medianas.frecuencia_porcentaje) and the internal one is the minimum distance between mediums. Everything is
 * computed when the datapack is read and stays immutable. It extends random_spread so /locate walks it like vanilla ones.
 * <p>In the uniques the datapack's separation is not used: the minimum is the minimum distance between uniques (so two of the
 * same type are not closer either) and the grid's origin is shifted per type (by the salt). With the 190/250
 * ratio and a common origin, the candidates of all types fell in the same 960-block corner of each cell.
 * <p>With "bioma" (an optional biome tag) the candidate of each cell is no longer a random chunk: it is the
 * point of a 128-block lattice, inside the same window as the random_spread (so the minimum separation is kept), that
 * falls in that biome and has the most neighbors at 64 blocks also in it (the one deepest in the biome). It serves
 * biomes so rare that a random candidate almost never hits them (mushroom fields). The search only reads the
 * overworld's biome noise (without loading chunks), is done once per cell and is memoized.
 * "bioma_y" (optional, 64 by default) is the height at which the biome is checked: for cave ones (the Lost Mine),
 * that of the structure's center. "bioma_vecinos" (optional, 1-9, 6 by default) is how many lattice points, of the 9
 * of the point and its neighbors, must fall in the biome: with 6 a strip narrower than ~100 blocks (beaches) almost
 * never works; with fewer it is accepted, and the point with the most neighbors still wins.
 * <p>"rejilla_antigua" marks the uniques that already existed in 0.1.0. With the option unicas.rejilla_compatible (worlds
 * created with that version) they use the grid of back then: internal separation with the datapack's ratio (190/250),
 * common origin and no biome search; isPlacementChunk and getPotentialStructureChunk end up in vanilla's random_spread
 * with offset 0, the same cost as back then. So /locate, the maps and the minimum distance find the already generated
 * ones again. The others keep the new grid (and {@link UniqueSeparation} gives priority to the old ones).
 */
@SuppressWarnings("deprecation") // ExclusionZone is marked deprecated in vanilla, but it is the one its villages use
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
			Codec.intRange(1, 9).optionalFieldOf("bioma_vecinos", 6).forGetter(p -> p.minScore),
			Codec.BOOL.optionalFieldOf("rejilla_antigua", false).forGetter(p -> p.oldGrid)
	).apply(i, GridPlacement::create));
	/** Biome search lattice (chunks), neighbors at half a step and minimum neighbors (out of 9) to accept a point. */
	private static final int STEP = 8, HALF = STEP / 2, MIN_SCORE = 6, SAMPLE_Y = 64, CACHE_MAX = 1 << 14;
	private static final long NONE = Long.MIN_VALUE;
	/** Is the point (in quarter blocks) in the tag? In the game, the overworld's biome noise. */
	@FunctionalInterface
	interface BiomeSample {
		boolean in(TagKey<Biome> tag, int quartX, int quartY, int quartZ);
	}
	private record BiomeContext(long seed, BiomeSample sample) {
	}
	/** Candidates per cell of one context: they go together so that a thread still computing with the previous context (another
	 *  world) never leaves its result in the new one's memo. */
	private record Memory(BiomeContext ctx, ConcurrentHashMap<Long, Long> candidates) {
	}
	private static volatile @Nullable BiomeContext context;
	private static volatile int searchesLogged;

	private final String group;
	private final boolean oldGrid; // marked in the datapack (it existed in 0.1.0)
	private final boolean legacy;  // and the option unicas.rejilla_compatible is enabled: the 0.1.0 grid
	private final int baseSpacing, baseSeparation, baseSalt;
	private final Optional<AbstractSpreadingStructurePlacement.ExclusionZone> baseExclusion;
	private final boolean enabled;
	private final Set<Long> cells; // null = no limit
	private final int offsetX, offsetZ; // offset of the grid's origin, in chunks (0 for villages)
	private final Optional<TagKey<Biome>> biome;
	private final int sampleY; // height at which the biome is checked (sea level; lower, for cave biomes)
	private final int minScore; // lattice points (out of 9) that must fall in the biome (MIN_SCORE; fewer, strip-shaped biomes)
	private volatile @Nullable Memory memory; // cell -> chunk (or NONE) of the context in use

	private GridPlacement(String group, int baseSpacing, int baseSeparation, int salt,
						  Optional<AbstractSpreadingStructurePlacement.ExclusionZone> baseExclusion, Optional<TagKey<Biome>> biome, int sampleY,
						  int minScore, boolean oldGrid, Settings s) {
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
		this.minScore = minScore;
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
										int sampleY, int minScore, boolean oldGrid) {
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
			if (oldGrid && cfg.getBool(LEGACY_OPTION)) { // the 0.1.0 one, as is: the datapack's ratio and a common origin
				s = new Settings(cfg.getBool(key + ".activada"), sp, scaled(sp, spacing, separation), -1, exclusion, false, true);
			} else {
				int sep = Math.clamp((cfg.getInt("unicas.distancia_minima.bloques") + 15) / 16, 0, sp - 1);
				s = new Settings(cfg.getBool(key + ".activada"), sp, sep, -1, exclusion, true, false);
			}
		} else if (group.startsWith("medianas/") && cfg.has(group.replace('/', '.') + ".separacion_bloques")) {
			// medium structures: their separation scaled by the common frequency (density x f -> separation / sqrt of f);
			// internal separation (two of the same type) = the minimum distance between mediums, at most half a cell
			String key = group.replace('/', '.');
			double f = cfg.getInt("medianas.frecuencia_porcentaje") / 100.0;
			int sp = chunks((int) Math.round(cfg.getInt(key + ".separacion_bloques") / Math.sqrt(f)));
			int sep = Math.clamp((cfg.getInt("medianas.distancia_minima.bloques") + 15) / 16, 0, sp / 2);
			s = new Settings(cfg.getBool("medianas.activadas") && cfg.getBool(key + ".activada"), sp, sep, -1, exclusion, true, false);
		} else if (group.startsWith("minas/")) {
			// mine entrances: the datapack's separation is the default of its size; the option (the small ones')
			// scales all three proportionally. Internal separation = the minimum distance between mediums
			int defaults = HeraldiaConfig.defaults().get("minas.entradas.separacion_bloques").getAsInt();
			int sp = chunks((int) Math.round((double) cfg.getInt("minas.entradas.separacion_bloques") * spacing * 16 / defaults));
			int sep = Math.clamp((cfg.getInt("medianas.distancia_minima.bloques") + 15) / 16, 0, sp / 2);
			s = new Settings(cfg.getBool("minas.entradas.activado"), sp, sep, -1, exclusion, true, false);
		} else if (group.startsWith("costa/") && io.github.albertosa23.heraldia.coast.Coast.option(group.substring("costa/".length())) != null) {
			// lighthouses and shipwrecks: their separation (blocks) and activation; internal separation = the minimum distance between
			// mediums, at most half a cell
			String key = io.github.albertosa23.heraldia.coast.Coast.option(group.substring("costa/".length()));
			int sp = chunks(cfg.getInt(key + ".separacion_bloques"));
			int sep = Math.clamp((cfg.getInt("medianas.distancia_minima.bloques") + 15) / 16, 0, sp / 2);
			s = new Settings(cfg.getBool(key + ".activado"), sp, sep, -1, exclusion, true, false);
		} else {
			LOGGER.warn("Heraldia: grupo de colocación sin opciones {}; se usan los valores del datapack", group);
			s = new Settings(true, spacing, Math.min(separation, spacing - 1), -1, exclusion, false, false);
		}
		LOGGER.info("Heraldia: rejilla {}: {}, cada {} chunks (separación mínima {}{}), {}, exclusión {}{}", group,
				s.enabled ? "activada" : "desactivada", s.spacing, s.separation,
				s.shifted ? ", origen desplazado" : s.legacy ? ", rejilla antigua" : "",
				s.maxCells < 0 ? "sin máximo" : "máximo " + s.maxCells + " casillas",
				s.exclusion.map(z -> z.chunkCount() + " chunks").orElse("ninguna"),
				biome.filter(b -> !s.legacy).map(b -> ", candidata en el bioma #" + b.location() + (sampleY != SAMPLE_Y ? " a y = " + sampleY : "")
						+ (minScore != MIN_SCORE ? ", " + minScore + " de 9 vecinos" : "")).orElse(""));
		return new GridPlacement(group, spacing, separation, salt, exclusion, biome, sampleY, minScore, oldGrid, s);
	}

	/** Biome search context without a world (tests): null removes it. */
	static void testContext(long seed, @Nullable BiomeSample sample) {
		context = sample == null ? null : new BiomeContext(seed, sample);
	}

	/** Options group of the grid ("aldeas", "unicas/&lt;id&gt;", "medianas/&lt;id&gt;", "minas/&lt;size&gt;" or "costa/&lt;type&gt;"). */
	public String group() {
		return group;
	}

	/** Option for worlds created with 0.1.0: the uniques of back then go back to their grid. */
	public static final String LEGACY_OPTION = "unicas.rejilla_compatible";

	/** Uses the 0.1.0 grid (marked in the datapack and with unicas.rejilla_compatible enabled). */
	public boolean legacy() {
		return legacy;
	}

	private static int chunks(int blocks) {
		return Math.clamp(Math.round(blocks / 16.0F), 2, 4096);
	}

	/** Minimum separation with the same ratio as the datapack's (62/94 for villages). */
	private static int scaled(int spacing, int baseSpacing, int baseSeparation) {
		return Math.clamp(Math.round((float) spacing * baseSeparation / baseSpacing), 0, spacing - 1);
	}

	/** The n cells whose center is closest to 0,0 (ties by z and then x): deterministic, no saved data. */
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

	/** Offset of the grid's origin in chunks: the cell of a chunk x is floorDiv(x - offsetX(), spacing()). */
	public int offsetX() {
		return offsetX;
	}

	public int offsetZ() {
		return offsetZ;
	}

	/** random_spread's one with the shifted grid: /locate, the maps and UniqueSeparation use it. */
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
			// Only lattice points can be candidates: the other chunks return without touching the memo.
			int wx = Math.floorMod(chunkX - offsetX, spacing()) - first(), wz = Math.floorMod(chunkZ - offsetZ, spacing()) - first();
			if (wx < 0 || wz < 0 || wx % STEP != 0 || wz % STEP != 0) {
				return false;
			}
			long c = biomeCandidate(state.getLevelSeed(), chunkX, chunkZ);
			return c != NONE && (int) (c >> 32) == chunkX && (int) c == chunkZ;
		}
		// Hot path (every chunk): same cost as vanilla, a single ChunkPos and without going through the shifted version.
		ChunkPos c = super.getPotentialStructureChunk(state.getLevelSeed(), chunkX - offsetX, chunkZ - offsetZ);
		return c.x() + offsetX == chunkX && c.z() + offsetZ == chunkZ;
	}

	/** /locate does not go through isPlacementChunk but through here: so it does not point at disabled cells or cells past the maximum. */
	@Override
	public boolean applyAdditionalChunkRestrictions(int chunkX, int chunkZ, long seed) {
		return allowed(chunkX, chunkZ) && (biome.isEmpty() || context == null || biomeCandidate(seed, chunkX, chunkZ) != NONE)
				&& super.applyAdditionalChunkRestrictions(chunkX, chunkZ, seed);
	}

	/** Width (chunks) of the window where random_spread puts each cell's candidate. */
	private int window() {
		return spacing() - separation();
	}

	/**
	 * Candidate of the cell of chunk (chunkX, chunkZ) by biome, packed (x << 32 | z), or NONE if the cell
	 * has no good spot. Without a loaded world (or with another seed), NONE: the usual candidate is used.
	 */
	private long biomeCandidate(long seed, int chunkX, int chunkZ) {
		BiomeContext ctx = context;
		if (ctx == null || ctx.seed != seed) {
			return NONE;
		}
		Memory mem = memory;
		if (mem == null || mem.ctx != ctx) { // another world: a new memo (the previous one stays with the threads still using it)
			mem = new Memory(ctx, new ConcurrentHashMap<>());
			memory = mem;
		}
		ConcurrentHashMap<Long, Long> candidates = mem.candidates;
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

	/** First lattice point inside the window (chunks from the cell's origin). */
	private int first() {
		return window() >= STEP ? HALF : window() / 2;
	}

	/**
	 * Lattice of STEP chunks in the cell's window; score = neighbors (out of 9, at HALF chunks) in the biome. The neighbors
	 * of two lattice points touch (they fall on the same grid of HALF chunks): each point of that grid is checked only
	 * once per search ({@code seen}), with the same result as checking it every time.
	 */
	private long search(BiomeContext ctx, long seed, int x0, int z0) {
		int win = window(), n = Math.max(1, win / STEP), first = first();
		TagKey<Biome> tag = biome.orElseThrow();
		int side = 2 * n + 1;
		byte[] seen = new byte[side * side];          // 0 not checked, 1 outside, 2 inside the biome
		long best = NONE, bestKey = Long.MIN_VALUE;
		for (int a = 0; a < n; a++) {
			for (int b = 0; b < n; b++) {
				int cx = x0 + first + a * STEP, cz = z0 + first + b * STEP;
				if (!in(ctx, tag, seen, side, 2 * a + 1, 2 * b + 1, cx, cz, sampleY)) {
					continue;
				}
				int score = 1;
				for (int dx = -HALF; dx <= HALF; dx += HALF) {
					for (int dz = -HALF; dz <= HALF; dz += HALF) {
						if ((dx != 0 || dz != 0) && in(ctx, tag, seen, side, 2 * a + 1 + dx / HALF, 2 * b + 1 + dz / HALF, cx + dx, cz + dz, sampleY)) {
							score++;
						}
					}
				}
				if (score < minScore) {
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

	/** {@link #in(BiomeContext, TagKey, int, int, int)} with the search's memo (point i, j of the grid). */
	private static boolean in(BiomeContext ctx, TagKey<Biome> tag, byte[] seen, int side, int i, int j, int chunkX, int chunkZ, int y) {
		int k = i * side + j;
		if (seen[k] == 0) {
			seen[k] = in(ctx, tag, chunkX, chunkZ, y) ? (byte) 2 : (byte) 1;
		}
		return seen[k] == 2;
	}

	/** The biome at the chunk's corner (where the jigsaw checks its own), at height y (sea level by default). */
	private static boolean in(BiomeContext ctx, TagKey<Biome> tag, int chunkX, int chunkZ, int y) {
		return ctx.sample.in(tag, QuartPos.fromBlock(chunkX * 16), QuartPos.fromBlock(y), QuartPos.fromBlock(chunkZ * 16));
	}

	/** Prepares the biome search when the overworld loads (and forgets it when the server stops). One line in Heraldia. */
	public static void registerBiomeSearch() {
		ServerLevelEvents.LOAD.register((server, level) -> {
			if (level.dimension() == Level.OVERWORLD) {
				var randomState = level.getChunkSource().getGeneratorState().randomState();
				BiomeResolver resolver = level.getChunkSource().getGenerator().getBiomeSource()
						.createResolver(randomState.createClimateSampler(SamplerContext.EMPTY_UNCACHED));
				context = new BiomeContext(level.getSeed(), (tag, x, y, z) -> resolver.getNoiseBiome(x, y, z).is(tag));
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
