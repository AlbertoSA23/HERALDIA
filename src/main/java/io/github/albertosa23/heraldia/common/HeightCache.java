package io.github.albertosa23.heraldia.common;

import it.unimi.dsi.fastutil.longs.Long2LongLinkedOpenHashMap;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.LevelHeightAccessor;
import net.minecraft.world.level.chunk.ChunkGenerator;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.level.levelgen.RandomState;
import net.minecraft.world.level.levelgen.structure.Structure;
import org.jspecify.annotations.Nullable;

/**
 * Generation heights shared between searches and between threads: the same as {@link Heights} (floor
 * {@code OCEAN_FLOOR_WG}, and the surface {@code WORLD_SURFACE_WG} only on request), but a single cache per world
 * (generator and {@code RandomState}) instead of one per search. A column's generation height only depends on the
 * seed and the generator, so the stored value is exactly what {@code getBaseHeight} would give: the result of
 * whoever uses it does not change, it just stops paying twice for the same column (mine entrances: each style and variant of the
 * structure_set looks at the same center, /locate looks again at the chunks the placement rule already looked at...).
 * <p>Bounded: {@link #BANDS} bands with their lock, each with at most {@code capacity / BANDS} columns; when
 * full, the oldest goes (FIFO). Two threads asking at once for a new column both compute it (same value):
 * the computation runs outside the lock so as not to block generation.
 */
public final class HeightCache {
	/** Default maximum columns: about 65,000 (≈ 2-3 MB), more than a thousand mine candidate chunks. */
	public static final int CAPACITY = 1 << 16;
	static final int BANDS = 64;
	private static final int NO_SURFACE = Integer.MIN_VALUE;
	private static final long EMPTY = Long.MIN_VALUE;
	private static volatile @Nullable HeightCache actual;

	/** Where the heights come from (in the game, {@code ChunkGenerator.getBaseHeight}; in the tests, whatever). */
	@FunctionalInterface
	public interface Source {
		int height(int x, int z, Heightmap.Types type);
	}

	public final int sea;
	private final Object generator, state;
	private final int minY, high;
	private final Source source;
	private final Long2LongLinkedOpenHashMap[] bands = new Long2LongLinkedOpenHashMap[BANDS];
	private final int perBand;

	/** Public for the tests: a cache over that source, with the given sea level and at most {@code capacity} columns. */
	public HeightCache(Source source, int sea, int capacity) {
		this(source, sea, capacity, null, null, 0, 0);
	}

	private HeightCache(Source source, int sea, int capacity, @Nullable Object generator, @Nullable Object state, int minY, int high) {
		this.source = source;
		this.sea = sea;
		this.perBand = Math.max(1, capacity / BANDS);
		this.generator = generator;
		this.state = state;
		this.minY = minY;
		this.high = high;
		for (int i = 0; i < BANDS; i++) {
			bands[i] = new Long2LongLinkedOpenHashMap();
			bands[i].defaultReturnValue(EMPTY);
		}
	}

	/** The world cache of that context (the same while the generator, the RandomState or the world height do not change). */
	public static HeightCache of(Structure.GenerationContext ctx) {
		ChunkGenerator g = ctx.chunkGenerator();
		RandomState r = ctx.randomState();
		int minY = ctx.heightAccessor().getMinY(), high = ctx.heightAccessor().getHeight();
		HeightCache c = actual;
		if (c == null || c.generator != g || c.state != r || c.minY != minY || c.high != high) {
			// only its height: the generation context carries the chunk, which must not stay in memory
			LevelHeightAccessor height = LevelHeightAccessor.create(minY, high);
			c = new HeightCache((x, z, type) -> g.getBaseHeight(x, z, type, height, r), g.getSeaLevel(), CAPACITY, g, r, minY, high);
			actual = c;
		}
		return c;
	}

	private Long2LongLinkedOpenHashMap band(long key) {
		long h = key * 0x9E3779B97F4A7C15L;
		return bands[(int) (h >>> 58)];             // 64 bands: the top 6 bits of the hash
	}

	private long read(long key) {
		Long2LongLinkedOpenHashMap f = band(key);
		synchronized (f) {
			return f.get(key);
		}
	}

	private void save(long key, long v) {
		Long2LongLinkedOpenHashMap f = band(key);
		synchronized (f) {
			if (!f.containsKey(key) && f.size() >= perBand) {
				f.removeFirstLong();                    // the oldest one
			}
			f.put(key, v);
		}
	}

	private long at(int x, int z) {
		long key = BlockPos.asLong(x, 0, z);
		long v = read(key);
		if (v == EMPTY) {
			v = ((long) source.height(x, z, Heightmap.Types.OCEAN_FLOOR_WG) << 32) | (NO_SURFACE & 0xFFFFFFFFL);
			save(key, v);
		}
		return v;
	}

	/** First free height above the floor (not counting water), like {@link Heights#floor}. */
	public int floor(int x, int z) {
		return (int) (at(x, z) >> 32);
	}

	/** First free height counting water (only computed on request), like {@link Heights#surface}. */
	public int surface(int x, int z) {
		long v = at(x, z);
		int surface = (int) v;
		if (surface == NO_SURFACE) {
			surface = source.height(x, z, Heightmap.Types.WORLD_SURFACE_WG);
			save(BlockPos.asLong(x, 0, z), (v & 0xFFFFFFFF00000000L) | (surface & 0xFFFFFFFFL));
		}
		return surface;
	}

	/** Like {@link Heights#water}. */
	public boolean water(int x, int z) {
		int floor = floor(x, z);
		return floor < sea && surface(x, z) > floor;
	}

	/** Columns stored now (tests). */
	public int size() {
		int n = 0;
		for (Long2LongLinkedOpenHashMap f : bands) {
			synchronized (f) {
				n += f.size();
			}
		}
		return n;
	}

	/** Maximum columns. */
	public int capacity() {
		return perBand * BANDS;
	}
}
