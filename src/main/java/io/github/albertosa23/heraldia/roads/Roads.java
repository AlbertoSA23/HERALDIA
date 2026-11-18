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
 * Caminos entre aldeas (aldeas.caminos.*): el rasgo heraldia:camino ({@link RoadFeature}) va en todos los biomas del
 * mundo principal, en el paso STRONGHOLDS de la decoración: después de colocar las estructuras de superficie del chunk
 * (sus piezas ya están, y se esquivan) y antes de la vegetación (los árboles y la hierba no salen encima del camino). En
 * vanilla ese paso no tiene rasgos, así que no cambia el azar de ningún otro. Desactivado, ni se añade a los biomas.
 * <p>Como todo rasgo, solo corre en los chunks que se generan: en un mundo existente, lo ya generado no cambia y los
 * tramos que caerían en chunks viejos no existen.
 * <p>El contexto (rejilla de las aldeas, reglas de la generación, memoria del trazado) se prepara una vez por mundo.
 */
public final class Roads {
	private static final Logger LOGGER = LoggerFactory.getLogger(Heraldia.MOD_ID);
	public static final String ENABLED = "aldeas.caminos.activado", DISTANCE = "aldeas.caminos.distancia_maxima_bloques",
			WIDTH = "aldeas.caminos.ancho";
	public static final ResourceKey<PlacedFeature> FEATURE = ResourceKey.create(Registries.PLACED_FEATURE, Heraldia.id("camino"));
	private static final Identifier VILLAGES = Heraldia.id("aldeas");
	/** Punto de paso junto a una única: la recta debe pasar a menos de HITO_MAX bloques y el camino pasa a HITO_PASO. */
	static final int MILESTONE_MAX = 320, MILESTONE_STEP = 112;

	private static volatile @Nullable Context context;
	// coste medido (System.nanoTime) en el rasgo: todos los chunks, y los que tienen camino
	static final AtomicLong CHUNKS = new AtomicLong(), CHUNKS_NS = new AtomicLong(), WITH_ROAD = new AtomicLong(),
			WITH_ROAD_NS = new AtomicLong(), COLUMNS = new AtomicLong();
	// de ello, lo que se calcula una vez por casilla, ruta o vértice (y queda en memoria)
	static final AtomicLong VILLAGES_N = new AtomicLong(), VILLAGES_NS = new AtomicLong(), MILESTONES_N = new AtomicLong(), MILESTONES_NS = new AtomicLong(),
			SEABED_N = new AtomicLong(), SEABED_NS = new AtomicLong();

	private Roads() {
	}

	/** Una línea en Heraldia.onInitialize (la configuración ya está leída). */
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
	 * Para /heraldia review: el centro del tramo de camino más cercano a (x, z) (punto medio de una ruta entre dos
	 * aldeas vecinas), o null si los caminos están desactivados o no hay ninguna ruta cerca. Seguro fuera del hilo del
	 * servidor (el contexto es el de la generación); no carga ni genera chunks.
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
	 * Para los encargos de viaje del tablón (T38): las aldeas vecinas (las que une un camino) de la aldea con el inicio
	 * en el chunk (chunkX, chunkZ), como posiciones empaquetadas ({@link RoadLayout#pack}) de sus plazas. Vacío con los
	 * caminos desactivados o fuera del mundo principal. Seguro fuera del hilo del servidor; no carga ni genera chunks.
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
	 * Para las caravanas (T39): el trazado de los caminos del mundo principal (las mismas rutas que la generación), o null
	 * con los caminos desactivados, en otra dimensión o sin la rejilla de las aldeas. Seguro fuera del hilo del servidor;
	 * no carga ni genera chunks.
	 */
	public static @Nullable RoadLayout layout(ServerLevel level) {
		if (!HeraldiaConfig.get().getBool(ENABLED)) {
			return null;
		}
		Context c = of(level, level.getChunkSource().getGenerator());
		return c == null ? null : c.layout();
	}

	/** Histograma del coste por chunk: casilla k = de 2^k a 2^(k+1) µs (la 0, menos de 2 µs). */
	static final AtomicLongArray HISTOGRAM = new AtomicLongArray(24);

	static void measure(long ns) {
		long us = ns / 1000;
		HISTOGRAM.incrementAndGet(Math.min(23, us <= 1 ? 0 : 63 - Long.numberOfLeadingZeros(us)));
	}

	/** Cota superior (µs) del percentil p del histograma. */
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

	/** Coste medido hasta ahora (en el log al parar el servidor y cada 16.384 chunks). */
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

	/** Mide una consulta cara que queda en memoria. */
	private static void measurement(AtomicLong n, AtomicLong total, long t0) {
		n.incrementAndGet();
		total.addAndGet(System.nanoTime() - t0);
	}

	/** Todo lo que el rasgo necesita de un mundo; inmutable salvo las memorias del trazado (seguras entre hilos). */
	record Context(ServerLevel level, @Nullable RoadLayout layout, int width, int sea, RoadLayout.Seabed depth, BiomeResolver biomes) {
	}

	/** El contexto del mundo principal (null en otra dimensión). Se construye una vez por mundo. */
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
				// las mismas reglas que la generación: casillas permitidas, zona de exclusión, estilos, bioma y terreno
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
	 * Punto de paso junto a la estructura única (de rejilla) más cercana a la recta entre dos aldeas, si la recta pasa a
	 * menos de {@link #MILESTONE_MAX} bloques de ella por su mitad central y sale de verdad ahí (las mismas reglas que /locate y
	 * la generación, con la rejilla en uso: también la antigua con unicas.rejilla_compatible). Una vez por ruta.
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
					continue; // la Atlántida: en mar abierto
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
						if (d < 1) { // la recta pasa por encima: a un lado
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
