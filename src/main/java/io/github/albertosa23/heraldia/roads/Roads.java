package io.github.albertosa23.heraldia.roads;

import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.common.ForeignZone;
import io.github.albertosa23.heraldia.config.GridPlacement;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.config.UniqueSeparation;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.atomic.AtomicLongArray;
import net.fabricmc.fabric.api.biome.v1.BiomeModifications;
import net.fabricmc.fabric.api.biome.v1.BiomeSelectors;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.minecraft.core.Registry;
import net.minecraft.core.RegistryAccess;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.Identifier;
import net.minecraft.resources.ResourceKey;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.biome.BiomeResolver;
import net.minecraft.world.level.biome.Climate;
import net.minecraft.world.level.chunk.ChunkGenerator;
import net.minecraft.world.level.chunk.ChunkGeneratorStructureState;
import net.minecraft.world.level.levelgen.GenerationStep;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.level.levelgen.RandomState;
import net.minecraft.world.level.levelgen.densityfunction.SamplerContext;
import net.minecraft.world.level.levelgen.placement.PlacedFeature;
import net.minecraft.world.level.levelgen.structure.StructureSet;
import net.minecraft.world.level.levelgen.structure.placement.RandomSpreadStructurePlacement;
import org.jspecify.annotations.Nullable;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Roads between villages (aldeas.caminos.*): the heraldia:camino feature ({@link RoadFeature}) goes in every biome of the
 * overworld, in the STRONGHOLDS decoration step: after the chunk's surface structures are placed
 * (their pieces are already there, and are avoided) and before vegetation (trees and grass do not spawn on the road). In
 * vanilla that step has no features, so it does not change the randomness of any other. Disabled, it is not even added to the biomes.
 * <p>Like any feature, it only runs in chunks being generated: in an existing world, what is already generated does not change and the
 * segments that would fall in old chunks do not exist.
 * <p>The context (villages' grid, generation rules, layout memo) is prepared once per world.
 */
public final class Roads {
	private static final Logger LOGGER = LoggerFactory.getLogger(Heraldia.MOD_ID);
	public static final String ENABLED = "aldeas.caminos.activado", DISTANCE = "aldeas.caminos.distancia_maxima_bloques",
			WIDTH = "aldeas.caminos.ancho";
	public static final ResourceKey<PlacedFeature> FEATURE = ResourceKey.create(Registries.PLACED_FEATURE, Heraldia.id("camino"));
	private static final Identifier VILLAGES = Heraldia.id("aldeas");
	/** Waypoint next to a unique: the straight line must pass within MILESTONE_MAX blocks and the road passes at MILESTONE_STEP. */
	static final int MILESTONE_MAX = 320, MILESTONE_STEP = 112;

	private static volatile @Nullable Context context;
	// cost measured (System.nanoTime) in the feature: all chunks, and those that have a road
	static final AtomicLong CHUNKS = new AtomicLong(), CHUNKS_NS = new AtomicLong(), WITH_ROAD = new AtomicLong(),
			WITH_ROAD_NS = new AtomicLong(), COLUMNS = new AtomicLong();
	// of that, what is computed once per cell, route or vertex (and memoized)
	static final AtomicLong VILLAGES_N = new AtomicLong(), VILLAGES_NS = new AtomicLong(), MILESTONES_N = new AtomicLong(), MILESTONES_NS = new AtomicLong(),
			SEABED_N = new AtomicLong(), SEABED_NS = new AtomicLong();

	private Roads() {
	}

	/** One line in Heraldia.onInitialize (the configuration is already read). */
	public static void register() {
		Registry.register(BuiltInRegistries.FEATURE_TYPE, Heraldia.id("camino"), RoadFeature.CODEC);
		HeraldiaConfig cfg = HeraldiaConfig.get();
		if (cfg.getBool(ENABLED)) {
			BiomeModifications.addFeature(BiomeSelectors.foundInOverworld(), GenerationStep.Decoration.STRONGHOLDS, FEATURE);
		}
		LOGGER.info("Heraldia: caminos entre aldeas {} (a menos de {} bloques, {} de ancho)", cfg.getBool(ENABLED) ? "activados" : "desactivados",
				cfg.getInt(DISTANCE), cfg.getInt(WIDTH));
		ServerLifecycleEvents.SERVER_STOPPING.register(server -> {
			report();
			context = null;
		});
	}

	/**
	 * For /heraldia review: the center of the road segment nearest to (x, z) (midpoint of a route between two
	 * neighboring villages), or null if roads are disabled or there is no route nearby. Safe off the server
	 * thread (the context is generation's); it neither loads nor generates chunks.
	 */
	public static @Nullable BlockPos nearestSegment(ServerLevel level, int x, int z) {
		if (!HeraldiaConfig.get().getBool(ENABLED)) {
			return null;
		}
		Context c = of(level, level.getChunkSource().getGenerator());
		if (c == null || c.layout() == null) {
			return null;
		}
		long p = c.layout().nearestSegment(x, z, 4);
		return p == RoadLayout.NONE ? null : new BlockPos(RoadLayout.px(p), c.sea(), RoadLayout.pz(p));
	}

	/**
	 * For the board's journey quests (T38): the neighboring villages (those a road joins) of the village starting
	 * in chunk (chunkX, chunkZ), as packed positions ({@link RoadLayout#pack}) of their plazas. Empty with
	 * roads disabled or outside the overworld. Safe off the server thread; it neither loads nor generates chunks.
	 */
	public static long[] neighbors(ServerLevel level, int chunkX, int chunkZ) {
		if (!HeraldiaConfig.get().getBool(ENABLED)) {
			return new long[0];
		}
		Context c = of(level, level.getChunkSource().getGenerator());
		if (c == null || c.layout() == null) {
			return new long[0];
		}
		return c.layout().neighborsOf(chunkX * 16 + 8, chunkZ * 16 + 8);
	}

	/**
	 * For the caravans (T39): the overworld's road layout (the same routes as generation), or null
	 * with roads disabled, in another dimension or without the villages' grid. Safe off the server thread;
	 * it neither loads nor generates chunks.
	 */
	public static @Nullable RoadLayout layout(ServerLevel level) {
		if (!HeraldiaConfig.get().getBool(ENABLED)) {
			return null;
		}
		Context c = of(level, level.getChunkSource().getGenerator());
		return c == null ? null : c.layout();
	}

	/** Histogram of the cost per chunk: bin k = from 2^k to 2^(k+1) µs (bin 0, under 2 µs). */
	static final AtomicLongArray HISTOGRAM = new AtomicLongArray(24);

	static void measure(long ns) {
		long us = ns / 1000;
		HISTOGRAM.incrementAndGet(Math.min(23, us <= 1 ? 0 : 63 - Long.numberOfLeadingZeros(us)));
	}

	/** Upper bound (µs) of the histogram's percentile p. */
	static long percentile(double p) {
		long total = 0;
		for (int i = 0; i < HISTOGRAM.length(); i++) {
			total += HISTOGRAM.get(i);
		}
		long acc = 0;
		for (int i = 0; i < HISTOGRAM.length(); i++) {
			acc += HISTOGRAM.get(i);
			if (acc >= Math.ceil(total * p)) {
				return 2L << i;
			}
		}
		return 2L << (HISTOGRAM.length() - 1);
	}

	/** Cost measured so far (logged when the server stops and every 16,384 chunks). */
	static void report() {
		long n = CHUNKS.get(), c = WITH_ROAD.get();
		if (n == 0) {
			return;
		}
		LOGGER.info("Heraldia: caminos: {} chunks, {} junto a una ruta ({} columnas puestas); media {} µs por chunk, {} µs en los que están junto a una ruta; "
						+ "percentiles 50/90/99 por debajo de {}/{}/{} µs",
				n, c, COLUMNS.get(), String.format(java.util.Locale.ROOT, "%.1f", CHUNKS_NS.get() / 1000.0 / n),
				c == 0 ? "0" : String.format(java.util.Locale.ROOT, "%.1f", WITH_ROAD_NS.get() / 1000.0 / c),
				percentile(0.5), percentile(0.9), percentile(0.99));
		LOGGER.info("Heraldia: caminos: de ello, una vez: {} ms en saber si hay aldea ({} casillas), {} ms en los puntos de paso ({} rutas), "
						+ "{} ms en el fondo del agua ({} vértices)", VILLAGES_NS.get() / 1_000_000, VILLAGES_N.get(), MILESTONES_NS.get() / 1_000_000,
				MILESTONES_N.get(), SEABED_NS.get() / 1_000_000, SEABED_N.get());
	}

	/** Measures an expensive query that gets memoized. */
	private static void measurement(AtomicLong n, AtomicLong total, long t0) {
		n.incrementAndGet();
		total.addAndGet(System.nanoTime() - t0);
	}

	/** Everything the feature needs from a world; immutable except the layout's memos (thread-safe). */
	record Context(ServerLevel level, @Nullable RoadLayout layout, int width, int sea, RoadLayout.Seabed depth, BiomeResolver biomes) {
	}

	/** The overworld's context (null in another dimension). Built once per world. */
	static @Nullable Context of(ServerLevel level, ChunkGenerator generator) {
		if (level.dimension() != Level.OVERWORLD) {
			return null;
		}
		Context c = context;
		if (c != null && c.level == level) {
			return c;
		}
		synchronized (Roads.class) {
			c = context;
			if (c == null || c.level != level) {
				c = build(level, generator);
				context = c;
			}
		}
		return c;
	}

	private static Context build(ServerLevel level, ChunkGenerator generator) {
		HeraldiaConfig cfg = HeraldiaConfig.get();
		RegistryAccess access = level.registryAccess();
		RandomState randomState = level.getChunkSource().randomState();
		ChunkGeneratorStructureState state = level.getChunkSource().getGeneratorState();
		long seed = state.getLevelSeed();
		Climate.Sampler sampler = randomState.createClimateSampler(SamplerContext.EMPTY_UNCACHED);
		BiomeResolver biomes = generator.getBiomeSource().createResolver(sampler);
		RoadLayout.Seabed depth = (x, z) -> {
			long t0 = System.nanoTime();
			int h = generator.getBaseHeight(x, z, Heightmap.Types.OCEAN_FLOOR_WG, level, randomState);
			measurement(SEABED_N, SEABED_NS, t0);
			return h;
		};
		StructureSet set = access.lookupOrThrow(Registries.STRUCTURE_SET).getValue(VILLAGES);
		RoadLayout layout = null;
		if (set != null && set.placement() instanceof GridPlacement p && p.group().equals("aldeas")) {
			ForeignZone.Village outcome = ForeignZone.of(access).village(access, generator, generator.getBiomeSource(), sampler, randomState,
					level.getStructureTemplateManager(), seed, level, level.dimension());
			int s = p.spacing(), ox = p.offsetX(), oz = p.offsetZ();
			RoadLayout.Villages villages = (gx, gz) -> {
				long t0 = System.nanoTime();
				ChunkPos c = p.getPotentialStructureChunk(seed, gx * s + ox, gz * s + oz);
				// the same rules as generation: allowed cells, exclusion zone, styles, biome and terrain
				long v = p.isStructureChunk(state, c.x(), c.z()) && outcome.outcome(c.x(), c.z()) ? RoadLayout.pack(c.x() * 16 + 8, c.z() * 16 + 8) : RoadLayout.NONE;
				measurement(VILLAGES_N, VILLAGES_NS, t0);
				return v;
			};
			RoadLayout.Milestones h = milestones(level, generator, access, sampler, randomState, state, seed);
			RoadLayout.Milestones milestones = (ax, az, bx, bz) -> {
				long t0 = System.nanoTime();
				long v = h.between(ax, az, bx, bz);
				measurement(MILESTONES_N, MILESTONES_NS, t0);
				return v;
			};
			layout = new RoadLayout(seed, s * 16, cfg.getInt(DISTANCE), villages, milestones);
		} else {
			LOGGER.warn("Heraldia: caminos: no está la rejilla de las aldeas ({}); no hay caminos", VILLAGES);
		}
		return new Context(level, layout, cfg.getInt(WIDTH), generator.getSeaLevel(), depth, biomes);
	}

	/**
	 * Waypoint next to the (grid) unique structure closest to the straight line between two villages, if the line passes
	 * within {@link #MILESTONE_MAX} blocks of it along its central half and it really wins there (the same rules as /locate and
	 * generation, with the grid in use: also the old one with unicas.rejilla_compatible). Once per route.
	 */
	private static RoadLayout.Milestones milestones(ServerLevel level, ChunkGenerator generator, RegistryAccess access, Climate.Sampler sampler,
									   RandomState randomState, ChunkGeneratorStructureState state, long seed) {
		UniqueSeparation sep = UniqueSeparation.of(access);
		UniqueSeparation.Viability viability = sep.viability(access, generator, generator.getBiomeSource(), sampler, randomState,
				level.getStructureTemplateManager(), seed, level, level.dimension());
		return (ax, az, bx, bz) -> {
			double dx = bx - ax, dz = bz - az, l2 = dx * dx + dz * dz;
			if (l2 < 400.0 * 400.0) {
				return RoadLayout.NONE;
			}
			long best = RoadLayout.NONE;
			double bestD = Double.MAX_VALUE;
			for (int i = 0; i < sep.size(); i++) {
				if (sep.fixed(i)) {
					continue; // Atlantis: in the open sea
				}
				RandomSpreadStructurePlacement p = sep.placement(i);
				int s = p.spacing() * 16, ox = UniqueSeparation.offsetX(p), oz = UniqueSeparation.offsetZ(p);
				int x0 = Math.min(ax, bx) - MILESTONE_MAX, x1 = Math.max(ax, bx) + MILESTONE_MAX, z0 = Math.min(az, bz) - MILESTONE_MAX, z1 = Math.max(az, bz) + MILESTONE_MAX;
				for (int gx = Math.floorDiv(x0 - ox * 16, s); gx <= Math.floorDiv(x1 - ox * 16, s); gx++) {
					for (int gz = Math.floorDiv(z0 - oz * 16, s); gz <= Math.floorDiv(z1 - oz * 16, s); gz++) {
						ChunkPos c = p.getPotentialStructureChunk(seed, gx * p.spacing() + ox, gz * p.spacing() + oz);
						double ux = c.x() * 16 + 8, uz = c.z() * 16 + 8;
						double t = ((ux - ax) * dx + (uz - az) * dz) / l2;
						if (t < 0.25 || t > 0.75) {
							continue;
						}
						double qx = ax + dx * t, qz = az + dz * t, d = Math.hypot(qx - ux, qz - uz);
						if (d > MILESTONE_MAX || d >= bestD || !p.isStructureChunk(state, c.x(), c.z())
								|| !viability.valid(i, c.x(), c.z()) || sep.blocked(i, c.x(), c.z(), seed, viability)) {
							continue;
						}
						bestD = d;
						double nx, nz;
						if (d < 1) { // the line passes over it: to one side
							double l = Math.sqrt(l2);
							nx = -dz / l;
							nz = dx / l;
						} else {
							nx = (qx - ux) / d;
							nz = (qz - uz) / d;
						}
						best = RoadLayout.pack((int) Math.round(ux + nx * MILESTONE_STEP), (int) Math.round(uz + nz * MILESTONE_STEP));
					}
				}
			}
			return best;
		};
	}
}
