package io.github.albertosa23.heraldia.mines;

import io.github.albertosa23.heraldia.common.SearchCaches;
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
 * Parallel /locate for the mine entrances (and the coast's lighthouses and shipwrecks). Vanilla
 * (ChunkGenerator.getNearestGeneratedStructure) walks each ring of cells in order and, in each one, checks whether the
 * entrance wins (biome and hillside) on the server thread: almost all the time goes to the terrain height of the hillside
 * columns. When a ring of a mine grid starts, its cells are sent here, in the same order, to separate threads that only
 * <em>precompute</em> those columns into the shared height cache ({@link MineEntranceStructure#precompute}); the server
 * thread keeps doing the usual, cell by cell, and before each one it waits for (or does itself, if nobody has started it)
 * its precomputation. So the result is exactly the same (the same code decides, in the same order, with the same
 * values) and it takes much less time. When the ring ends, whatever is left to start is discarded. Only /locate and the
 * maps go through here; world generation, never.
 */
public final class ParallelLocate {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	/** Separate threads: the cores minus the server's (at least 1, at most 7). */
	static final int THREADS = Math.max(1, Math.min(7, Runtime.getRuntime().availableProcessors() - 1));
	private static volatile @Nullable ThreadPoolExecutor pool;
	private static final ThreadLocal<Ring> PENDING = new ThreadLocal<>();
	private static final AtomicInteger FAILURES = new AtomicInteger();

	private ParallelLocate() {
	}

	/** The current ring's tasks, per grid cell (the candidate's: so {@link #await} finds it). */
	private record Ring(Long2ObjectOpenHashMap<FutureTask<Void>> tasks, int offsetX, int offsetZ, int spacing) {
		long cell(int chunkX, int chunkZ) {
			return ParallelLocate.cell(chunkX, chunkZ, offsetX, offsetZ, spacing);
		}
	}

	/** Grid cell (shifted) a chunk belongs to: the same for any of its chunks and its candidate. */
	static long cell(int chunkX, int chunkZ, int offsetX, int offsetZ, int spacing) {
		return ChunkPos.pack(Math.floorDiv(chunkX - offsetX, spacing), Math.floorDiv(chunkZ - offsetZ, spacing));
	}

	private static ThreadPoolExecutor pool() {
		ThreadPoolExecutor p = pool;
		if (p == null) {
			synchronized (ParallelLocate.class) {
				p = pool;
				if (p == null) {
					AtomicInteger n = new AtomicInteger();
					p = new ThreadPoolExecutor(THREADS, THREADS, 30, TimeUnit.SECONDS, new LinkedBlockingQueue<>(), r -> {
						Thread t = new Thread(r, "Heraldia-locate-" + n.incrementAndGet());
						t.setDaemon(true);
						return t;
					});
					p.allowCoreThreadTimeOut(true);           // without /locate, no thread alive
					pool = p;
				}
			}
		}
		return p;
	}

	/** Cells of ring r around (x, z) in vanilla's order (origin chunks of each cell). */
	static List<int[]> ring(int x, int z, int r, int spacing) {
		List<int[]> out = new ArrayList<>();
		for (int i = -r; i <= r; i++) {
			boolean edgeI = i == -r || i == r;
			for (int j = -r; j <= r; j++) {
				if (edgeI || j == -r || j == r) {
					out.add(new int[] {x + spacing * i, z + spacing * j});
				}
			}
		}
		return out;
	}

	/**
	 * A structure that knows how to run the expensive part of its search ahead (the heights in the shared cache) without creating anything: the
	 * mine entrances (the hillside) and the lighthouses and shipwrecks (the shore, coast/CoastStructure).
	 */
	public interface Precomputable {
		void precompute(Structure.GenerationContext ctx);
	}

	/** When a ring starts (HEAD of getNearestGeneratedStructure): sends its cells if the grid belongs to the mines or the coast. */
	public static void start(Set<Holder<Structure>> structures, LevelReader level, int x, int z, int r, long seed,
							   RandomSpreadStructurePlacement placement) {
		finish();
		if (!(placement instanceof GridPlacement g) || !(g.group().startsWith(Mines.PREFIX) || g.group().startsWith("costa/"))
				|| !(level instanceof ServerLevel sl)) {
			return;
		}
		List<Structure> mines = new ArrayList<>();
		List<Holder<Structure>> holders = new ArrayList<>();
		for (Holder<Structure> h : structures) {
			if (h.value() instanceof Precomputable) {
				mines.add(h.value());
				holders.add(h);
			}
		}
		if (mines.isEmpty()) {
			return;
		}
		ChunkGenerator generator = sl.getChunkSource().getGenerator();
		RandomState randomState = sl.getChunkSource().getGeneratorState().randomState();
		var templates = sl.getStructureTemplateManager();
		var access = sl.registryAccess();
		Ring a = new Ring(new Long2ObjectOpenHashMap<>(), g.offsetX(), g.offsetZ(), g.spacing());
		ThreadPoolExecutor p = pool();
		for (int[] c : ring(x, z, r, placement.spacing())) {
			long cell = a.cell(c[0], c[1]);
			if (a.tasks().containsKey(cell)) {
				continue;
			}
			FutureTask<Void> t = new FutureTask<>(() -> {
				// the cell's candidate (with its biome search, which the grid memoizes) also on this thread
				ChunkPos pos = placement.getPotentialStructureChunk(seed, c[0], c[1]);
				if (!placement.applyAdditionalChunkRestrictions(pos.x(), pos.z(), seed)) {
					return null;                      // vanilla stops there (no spot in the cell): it asks for no height
				}
				// StructureCheck's climate sampler keeps a cache (not for several threads): one without a cache per task
				var climate = randomState.createClimateSampler(SamplerContext.EMPTY_UNCACHED);
				for (int i = 0; i < mines.size(); i++) {
					// the world's search memory already has its answer: nothing to precompute; and vanilla, which asks the
					// structures in this same order, stops at the first one that would start here
					int known = SearchCaches.peekPrediction(sl.dimension(), holders.get(i), pos.x(), pos.z());
					if (known == 1) {
						break;
					} else if (known == 0) {
						continue;
					}
					Structure m = mines.get(i);
					((Precomputable) m).precompute(new Structure.GenerationContext(access, generator, generator.getBiomeSource(), climate,
							randomState, templates, seed, pos, sl, m.biomes()::contains));
				}
				return null;
			});
			a.tasks().put(cell, t);
			p.execute(t);
		}
		PENDING.set(a);
	}

	/**
	 * Before vanilla looks at a cell (HEAD of getStructureGeneratingAt): its precomputation, done by another thread or, if
	 * nobody has started it yet, right here. If something fails, nothing happens: vanilla computes it as usual.
	 */
	public static void await(ChunkPos pos) {
		Ring a = PENDING.get();
		FutureTask<Void> t = a == null ? null : a.tasks().remove(a.cell(pos.x(), pos.z()));
		if (t == null) {
			return;
		}
		t.run();                                          // does nothing if another thread already has it
		try {
			t.get();
		} catch (InterruptedException e) {
			Thread.currentThread().interrupt();
		} catch (ExecutionException | CancellationException e) {
			if (FAILURES.getAndIncrement() < 3) {
				LOGGER.warn("Heraldia: /locate de minas: el cálculo adelantado de {} falló ({}); se hace como siempre", pos, e.toString());
			}
		}
	}

	/** When the ring ends (or before the next one): what nobody has started is no longer needed. */
	public static void finish() {
		Ring a = PENDING.get();
		if (a != null) {
			a.tasks().values().forEach(t -> t.cancel(false));
			PENDING.remove();
			ThreadPoolExecutor p = pool;
			if (p != null) {
				p.purge();
			}
		}
	}
}
