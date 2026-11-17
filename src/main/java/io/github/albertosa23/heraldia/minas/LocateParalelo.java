package io.github.albertosa23.heraldia.minas;

import io.github.albertosa23.heraldia.config.GridPlacement;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import java.util.concurrent.CancellationException;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.FutureTask;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import it.unimi.dsi.fastutil.longs.Long2ObjectOpenHashMap;
import net.minecraft.core.Holder;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.LevelReader;
import net.minecraft.world.level.chunk.ChunkGenerator;
import net.minecraft.world.level.levelgen.RandomState;
import net.minecraft.world.level.levelgen.densityfunction.SamplerContext;
import net.minecraft.world.level.levelgen.structure.Structure;
import net.minecraft.world.level.levelgen.structure.placement.RandomSpreadStructurePlacement;
import org.jspecify.annotations.Nullable;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * /locate de las entradas a mina (y de los faros y naufragios de la costa) en paralelo. Vanilla (ChunkGenerator.getNearestGeneratedStructure) recorre cada anillo
 * de casillas en orden y, en cada una, comprueba si la entrada sale (bioma y ladera) en el hilo del servidor: casi todo
 * el tiempo es la altura del terreno de las columnas de la ladera. Al empezar un anillo de una rejilla de minas, aquí se
 * mandan sus casillas, en el mismo orden, a unos hilos aparte que solo <em>precalculan</em> esas columnas en la caché
 * compartida de alturas ({@link MinaEntradaStructure#precalcular}); el hilo del servidor sigue haciendo lo de siempre,
 * casilla a casilla, y antes de cada una espera (o hace él mismo, si nadie la ha empezado) su precálculo. Así el
 * resultado es exactamente el mismo (lo decide el mismo código, en el mismo orden, con los mismos valores) y tarda mucho
 * menos. Al acabar el anillo se descarta lo que quede por empezar. Solo /locate y los mapas pasan por aquí; la
 * generación del mundo, nunca.
 */
public final class LocateParalelo {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	/** Hilos aparte: los núcleos menos el del servidor (como poco 1, como mucho 7). */
	static final int HILOS = Math.max(1, Math.min(7, Runtime.getRuntime().availableProcessors() - 1));
	private static volatile @Nullable ThreadPoolExecutor pool;
	private static final ThreadLocal<Anillo> PENDIENTES = new ThreadLocal<>();
	private static final AtomicInteger FALLOS = new AtomicInteger();

	private LocateParalelo() {
	}

	/** Las tareas del anillo en curso, por casilla de la rejilla (la de la candidata: así la encuentra {@link #esperar}). */
	private record Anillo(Long2ObjectOpenHashMap<FutureTask<Void>> tareas, int offsetX, int offsetZ, int spacing) {
		long casilla(int chunkX, int chunkZ) {
			return LocateParalelo.casilla(chunkX, chunkZ, offsetX, offsetZ, spacing);
		}
	}

	/** Casilla de la rejilla (desplazada) a la que pertenece un chunk: la misma para cualquier chunk de ella y su candidata. */
	static long casilla(int chunkX, int chunkZ, int offsetX, int offsetZ, int spacing) {
		return ChunkPos.pack(Math.floorDiv(chunkX - offsetX, spacing), Math.floorDiv(chunkZ - offsetZ, spacing));
	}

	private static ThreadPoolExecutor pool() {
		ThreadPoolExecutor p = pool;
		if (p == null) {
			synchronized (LocateParalelo.class) {
				p = pool;
				if (p == null) {
					AtomicInteger n = new AtomicInteger();
					p = new ThreadPoolExecutor(HILOS, HILOS, 30, TimeUnit.SECONDS, new LinkedBlockingQueue<>(), r -> {
						Thread t = new Thread(r, "Heraldia-locate-" + n.incrementAndGet());
						t.setDaemon(true);
						return t;
					});
					p.allowCoreThreadTimeOut(true);           // sin /locate, ningún hilo vivo
					pool = p;
				}
			}
		}
		return p;
	}

	/** Casillas del anillo r alrededor de (x, z) en el orden de vanilla (chunks de origen de cada casilla). */
	static List<int[]> anillo(int x, int z, int r, int spacing) {
		List<int[]> out = new ArrayList<>();
		for (int i = -r; i <= r; i++) {
			boolean bordeI = i == -r || i == r;
			for (int j = -r; j <= r; j++) {
				if (bordeI || j == -r || j == r) {
					out.add(new int[] {x + spacing * i, z + spacing * j});
				}
			}
		}
		return out;
	}

	/**
	 * Una estructura que sabe adelantar lo caro de su búsqueda (las alturas de la caché compartida) sin crear nada: las
	 * entradas a mina (la ladera) y los faros y naufragios (la orilla, costa/CostaStructure).
	 */
	public interface Precalculable {
		void precalcular(Structure.GenerationContext ctx);
	}

	/** Al empezar un anillo (HEAD de getNearestGeneratedStructure): manda sus casillas si la rejilla es de minas o de la costa. */
	public static void empezar(Set<Holder<Structure>> structures, LevelReader level, int x, int z, int r, long seed,
							   RandomSpreadStructurePlacement placement) {
		terminar();
		if (!(placement instanceof GridPlacement g) || !(g.group().startsWith(Minas.PREFIJO) || g.group().startsWith("costa/"))
				|| !(level instanceof ServerLevel sl)) {
			return;
		}
		List<Structure> minas = new ArrayList<>();
		for (Holder<Structure> h : structures) {
			if (h.value() instanceof Precalculable) {
				minas.add(h.value());
			}
		}
		if (minas.isEmpty()) {
			return;
		}
		ChunkGenerator generator = sl.getChunkSource().getGenerator();
		RandomState randomState = sl.getChunkSource().getGeneratorState().randomState();
		var templates = sl.getStructureTemplateManager();
		var access = sl.registryAccess();
		Anillo a = new Anillo(new Long2ObjectOpenHashMap<>(), g.offsetX(), g.offsetZ(), g.spacing());
		ThreadPoolExecutor p = pool();
		for (int[] c : anillo(x, z, r, placement.spacing())) {
			long casilla = a.casilla(c[0], c[1]);
			if (a.tareas().containsKey(casilla)) {
				continue;
			}
			FutureTask<Void> t = new FutureTask<>(() -> {
				// la candidata de la casilla (con su búsqueda de bioma, que la rejilla guarda) también en este hilo
				ChunkPos pos = placement.getPotentialStructureChunk(seed, c[0], c[1]);
				// el muestreador del clima de StructureCheck guarda caché (no es para varios hilos): uno sin caché por tarea
				var clima = randomState.createClimateSampler(SamplerContext.EMPTY_UNCACHED);
				for (Structure m : minas) {
					((Precalculable) m).precalcular(new Structure.GenerationContext(access, generator, generator.getBiomeSource(), clima,
							randomState, templates, seed, pos, sl, m.biomes()::contains));
				}
				return null;
			});
			a.tareas().put(casilla, t);
			p.execute(t);
		}
		PENDIENTES.set(a);
	}

	/**
	 * Antes de que vanilla mire una casilla (HEAD de getStructureGeneratingAt): su precálculo, hecho por otro hilo o, si
	 * aún nadie lo ha empezado, aquí mismo. Si algo falla, no pasa nada: vanilla lo calcula como siempre.
	 */
	public static void esperar(ChunkPos pos) {
		Anillo a = PENDIENTES.get();
		FutureTask<Void> t = a == null ? null : a.tareas().remove(a.casilla(pos.x(), pos.z()));
		if (t == null) {
			return;
		}
		t.run();                                          // no hace nada si otro hilo ya la tiene
		try {
			t.get();
		} catch (InterruptedException e) {
			Thread.currentThread().interrupt();
		} catch (ExecutionException | CancellationException e) {
			if (FALLOS.getAndIncrement() < 3) {
				LOGGER.warn("Heraldia: /locate de minas: el cálculo adelantado de {} falló ({}); se hace como siempre", pos, e.toString());
			}
		}
	}

	/** Al acabar el anillo (o antes del siguiente): lo que nadie ha empezado ya no hace falta. */
	public static void terminar() {
		Anillo a = PENDIENTES.get();
		if (a != null) {
			a.tareas().values().forEach(t -> t.cancel(false));
			PENDIENTES.remove();
			ThreadPoolExecutor p = pool;
			if (p != null) {
				p.purge();
			}
		}
	}
}
