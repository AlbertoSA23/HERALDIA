package io.github.albertosa23.heraldia.caminos;

import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.comun.ZonaAjenas;
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
 * Caminos entre aldeas (aldeas.caminos.*): el rasgo heraldia:camino ({@link CaminoFeature}) va en todos los biomas del
 * mundo principal, en el paso STRONGHOLDS de la decoración: después de colocar las estructuras de superficie del chunk
 * (sus piezas ya están, y se esquivan) y antes de la vegetación (los árboles y la hierba no salen encima del camino). En
 * vanilla ese paso no tiene rasgos, así que no cambia el azar de ningún otro. Desactivado, ni se añade a los biomas.
 * <p>Como todo rasgo, solo corre en los chunks que se generan: en un mundo existente, lo ya generado no cambia y los
 * tramos que caerían en chunks viejos no existen.
 * <p>El contexto (rejilla de las aldeas, reglas de la generación, memoria del trazado) se prepara una vez por mundo.
 */
public final class Caminos {
	private static final Logger LOGGER = LoggerFactory.getLogger(Heraldia.MOD_ID);
	public static final String ACTIVADO = "aldeas.caminos.activado", DISTANCIA = "aldeas.caminos.distancia_maxima_bloques",
			ANCHO = "aldeas.caminos.ancho";
	public static final ResourceKey<PlacedFeature> RASGO = ResourceKey.create(Registries.PLACED_FEATURE, Heraldia.id("camino"));
	private static final Identifier ALDEAS = Heraldia.id("aldeas");
	/** Punto de paso junto a una única: la recta debe pasar a menos de HITO_MAX bloques y el camino pasa a HITO_PASO. */
	static final int HITO_MAX = 320, HITO_PASO = 112;

	private static volatile @Nullable Contexto contexto;
	// coste medido (System.nanoTime) en el rasgo: todos los chunks, y los que tienen camino
	static final AtomicLong CHUNKS = new AtomicLong(), CHUNKS_NS = new AtomicLong(), CON_CAMINO = new AtomicLong(),
			CON_CAMINO_NS = new AtomicLong(), COLUMNAS = new AtomicLong();
	// de ello, lo que se calcula una vez por casilla, ruta o vértice (y queda en memoria)
	static final AtomicLong ALDEAS_N = new AtomicLong(), ALDEAS_NS = new AtomicLong(), HITOS_N = new AtomicLong(), HITOS_NS = new AtomicLong(),
			FONDO_N = new AtomicLong(), FONDO_NS = new AtomicLong();

	private Caminos() {
	}

	/** Una línea en Heraldia.onInitialize (la configuración ya está leída). */
	public static void registrar() {
		Registry.register(BuiltInRegistries.FEATURE_TYPE, Heraldia.id("camino"), CaminoFeature.CODEC);
		HeraldiaConfig cfg = HeraldiaConfig.get();
		if (cfg.getBool(ACTIVADO)) {
			BiomeModifications.addFeature(BiomeSelectors.foundInOverworld(), GenerationStep.Decoration.STRONGHOLDS, RASGO);
		}
		LOGGER.info("Heraldia: caminos entre aldeas {} (a menos de {} bloques, {} de ancho)", cfg.getBool(ACTIVADO) ? "activados" : "desactivados",
				cfg.getInt(DISTANCIA), cfg.getInt(ANCHO));
		ServerLifecycleEvents.SERVER_STOPPING.register(server -> {
			informe();
			contexto = null;
		});
	}

	/**
	 * Para /heraldia review: el centro del tramo de camino más cercano a (x, z) (punto medio de una ruta entre dos
	 * aldeas vecinas), o null si los caminos están desactivados o no hay ninguna ruta cerca. Seguro fuera del hilo del
	 * servidor (el contexto es el de la generación); no carga ni genera chunks.
	 */
	public static @Nullable BlockPos tramoCercano(ServerLevel level, int x, int z) {
		if (!HeraldiaConfig.get().getBool(ACTIVADO)) {
			return null;
		}
		Contexto c = de(level, level.getChunkSource().getGenerator());
		if (c == null || c.trazado() == null) {
			return null;
		}
		long p = c.trazado().tramoCercano(x, z, 4);
		return p == Trazado.NONE ? null : new BlockPos(Trazado.px(p), c.sea(), Trazado.pz(p));
	}

	/**
	 * Para los encargos de viaje del tablón (T38): las aldeas vecinas (las que une un camino) de la aldea con el inicio
	 * en el chunk (chunkX, chunkZ), como posiciones empaquetadas ({@link Trazado#pack}) de sus plazas. Vacío con los
	 * caminos desactivados o fuera del mundo principal. Seguro fuera del hilo del servidor; no carga ni genera chunks.
	 */
	public static long[] vecinas(ServerLevel level, int chunkX, int chunkZ) {
		if (!HeraldiaConfig.get().getBool(ACTIVADO)) {
			return new long[0];
		}
		Contexto c = de(level, level.getChunkSource().getGenerator());
		if (c == null || c.trazado() == null) {
			return new long[0];
		}
		return c.trazado().vecinasDe(chunkX * 16 + 8, chunkZ * 16 + 8);
	}

	/** Histograma del coste por chunk: casilla k = de 2^k a 2^(k+1) µs (la 0, menos de 2 µs). */
	static final AtomicLongArray HISTOGRAMA = new AtomicLongArray(24);

	static void medir(long ns) {
		long us = ns / 1000;
		HISTOGRAMA.incrementAndGet(Math.min(23, us <= 1 ? 0 : 63 - Long.numberOfLeadingZeros(us)));
	}

	/** Cota superior (µs) del percentil p del histograma. */
	static long percentil(double p) {
		long total = 0;
		for (int i = 0; i < HISTOGRAMA.length(); i++) {
			total += HISTOGRAMA.get(i);
		}
		long acc = 0;
		for (int i = 0; i < HISTOGRAMA.length(); i++) {
			acc += HISTOGRAMA.get(i);
			if (acc >= Math.ceil(total * p)) {
				return 2L << i;
			}
		}
		return 2L << (HISTOGRAMA.length() - 1);
	}

	/** Coste medido hasta ahora (en el log al parar el servidor y cada 16.384 chunks). */
	static void informe() {
		long n = CHUNKS.get(), c = CON_CAMINO.get();
		if (n == 0) {
			return;
		}
		LOGGER.info("Heraldia: caminos: {} chunks, {} junto a una ruta ({} columnas puestas); media {} µs por chunk, {} µs en los que están junto a una ruta; "
						+ "percentiles 50/90/99 por debajo de {}/{}/{} µs",
				n, c, COLUMNAS.get(), String.format(java.util.Locale.ROOT, "%.1f", CHUNKS_NS.get() / 1000.0 / n),
				c == 0 ? "0" : String.format(java.util.Locale.ROOT, "%.1f", CON_CAMINO_NS.get() / 1000.0 / c),
				percentil(0.5), percentil(0.9), percentil(0.99));
		LOGGER.info("Heraldia: caminos: de ello, una vez: {} ms en saber si hay aldea ({} casillas), {} ms en los puntos de paso ({} rutas), "
						+ "{} ms en el fondo del agua ({} vértices)", ALDEAS_NS.get() / 1_000_000, ALDEAS_N.get(), HITOS_NS.get() / 1_000_000,
				HITOS_N.get(), FONDO_NS.get() / 1_000_000, FONDO_N.get());
	}

	/** Mide una consulta cara que queda en memoria. */
	private static void medida(AtomicLong n, AtomicLong total, long t0) {
		n.incrementAndGet();
		total.addAndGet(System.nanoTime() - t0);
	}

	/** Todo lo que el rasgo necesita de un mundo; inmutable salvo las memorias del trazado (seguras entre hilos). */
	record Contexto(ServerLevel level, @Nullable Trazado trazado, int ancho, int sea, Trazado.Fondo fondo, BiomeResolver biomas) {
	}

	/** El contexto del mundo principal (null en otra dimensión). Se construye una vez por mundo. */
	static @Nullable Contexto de(ServerLevel level, ChunkGenerator generator) {
		if (level.dimension() != Level.OVERWORLD) {
			return null;
		}
		Contexto c = contexto;
		if (c != null && c.level == level) {
			return c;
		}
		synchronized (Caminos.class) {
			c = contexto;
			if (c == null || c.level != level) {
				c = construir(level, generator);
				contexto = c;
			}
		}
		return c;
	}

	private static Contexto construir(ServerLevel level, ChunkGenerator generator) {
		HeraldiaConfig cfg = HeraldiaConfig.get();
		RegistryAccess access = level.registryAccess();
		RandomState randomState = level.getChunkSource().randomState();
		ChunkGeneratorStructureState state = level.getChunkSource().getGeneratorState();
		long seed = state.getLevelSeed();
		Climate.Sampler sampler = randomState.createClimateSampler(SamplerContext.EMPTY_UNCACHED);
		BiomeResolver biomas = generator.getBiomeSource().createResolver(sampler);
		Trazado.Fondo fondo = (x, z) -> {
			long t0 = System.nanoTime();
			int h = generator.getBaseHeight(x, z, Heightmap.Types.OCEAN_FLOOR_WG, level, randomState);
			medida(FONDO_N, FONDO_NS, t0);
			return h;
		};
		StructureSet set = access.lookupOrThrow(Registries.STRUCTURE_SET).getValue(ALDEAS);
		Trazado trazado = null;
		if (set != null && set.placement() instanceof GridPlacement p && p.group().equals("aldeas")) {
			ZonaAjenas.Aldea sale = ZonaAjenas.of(access).aldea(access, generator, generator.getBiomeSource(), sampler, randomState,
					level.getStructureTemplateManager(), seed, level, level.dimension());
			int s = p.spacing(), ox = p.offsetX(), oz = p.offsetZ();
			Trazado.Aldeas aldeas = (gx, gz) -> {
				long t0 = System.nanoTime();
				ChunkPos c = p.getPotentialStructureChunk(seed, gx * s + ox, gz * s + oz);
				// las mismas reglas que la generación: casillas permitidas, zona de exclusión, estilos, bioma y terreno
				long v = p.isStructureChunk(state, c.x(), c.z()) && sale.sale(c.x(), c.z()) ? Trazado.pack(c.x() * 16 + 8, c.z() * 16 + 8) : Trazado.NONE;
				medida(ALDEAS_N, ALDEAS_NS, t0);
				return v;
			};
			Trazado.Hitos h = hitos(level, generator, access, sampler, randomState, state, seed);
			Trazado.Hitos hitos = (ax, az, bx, bz) -> {
				long t0 = System.nanoTime();
				long v = h.entre(ax, az, bx, bz);
				medida(HITOS_N, HITOS_NS, t0);
				return v;
			};
			trazado = new Trazado(seed, s * 16, cfg.getInt(DISTANCIA), aldeas, hitos);
		} else {
			LOGGER.warn("Heraldia: caminos: no está la rejilla de las aldeas ({}); no hay caminos", ALDEAS);
		}
		return new Contexto(level, trazado, cfg.getInt(ANCHO), generator.getSeaLevel(), fondo, biomas);
	}

	/**
	 * Punto de paso junto a la estructura única (de rejilla) más cercana a la recta entre dos aldeas, si la recta pasa a
	 * menos de {@link #HITO_MAX} bloques de ella por su mitad central y sale de verdad ahí (las mismas reglas que /locate y
	 * la generación, con la rejilla en uso: también la antigua con unicas.rejilla_compatible). Una vez por ruta.
	 */
	private static Trazado.Hitos hitos(ServerLevel level, ChunkGenerator generator, RegistryAccess access, Climate.Sampler sampler,
									   RandomState randomState, ChunkGeneratorStructureState state, long seed) {
		UniqueSeparation sep = UniqueSeparation.of(access);
		UniqueSeparation.Viability viability = sep.viability(access, generator, generator.getBiomeSource(), sampler, randomState,
				level.getStructureTemplateManager(), seed, level, level.dimension());
		return (ax, az, bx, bz) -> {
			double dx = bx - ax, dz = bz - az, l2 = dx * dx + dz * dz;
			if (l2 < 400.0 * 400.0) {
				return Trazado.NONE;
			}
			long best = Trazado.NONE;
			double bestD = Double.MAX_VALUE;
			for (int i = 0; i < sep.size(); i++) {
				if (sep.fixed(i)) {
					continue; // la Atlántida: en mar abierto
				}
				RandomSpreadStructurePlacement p = sep.placement(i);
				int s = p.spacing() * 16, ox = UniqueSeparation.offsetX(p), oz = UniqueSeparation.offsetZ(p);
				int x0 = Math.min(ax, bx) - HITO_MAX, x1 = Math.max(ax, bx) + HITO_MAX, z0 = Math.min(az, bz) - HITO_MAX, z1 = Math.max(az, bz) + HITO_MAX;
				for (int gx = Math.floorDiv(x0 - ox * 16, s); gx <= Math.floorDiv(x1 - ox * 16, s); gx++) {
					for (int gz = Math.floorDiv(z0 - oz * 16, s); gz <= Math.floorDiv(z1 - oz * 16, s); gz++) {
						ChunkPos c = p.getPotentialStructureChunk(seed, gx * p.spacing() + ox, gz * p.spacing() + oz);
						double ux = c.x() * 16 + 8, uz = c.z() * 16 + 8;
						double t = ((ux - ax) * dx + (uz - az) * dz) / l2;
						if (t < 0.25 || t > 0.75) {
							continue;
						}
						double qx = ax + dx * t, qz = az + dz * t, d = Math.hypot(qx - ux, qz - uz);
						if (d > HITO_MAX || d >= bestD || !p.isStructureChunk(state, c.x(), c.z())
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
						best = Trazado.pack((int) Math.round(ux + nx * HITO_PASO), (int) Math.round(uz + nz * HITO_PASO));
					}
				}
			}
			return best;
		};
	}
}
