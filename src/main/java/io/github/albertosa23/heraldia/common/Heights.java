package io.github.albertosa23.heraldia.common;

import it.unimi.dsi.fastutil.longs.Long2LongOpenHashMap;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.level.levelgen.structure.Structure;

/**
 * Generation heights of a column (floor {@code OCEAN_FLOOR_WG} and surface {@code WORLD_SURFACE_WG}) with a cache:
 * each query evaluates the column's noise, so the same point is never computed twice. Water = the surface
 * is above the floor and the floor below sea level. The surface is only evaluated on request. One instance per
 * search (not thread-safe).
 */
public final class Heights {
	private static final int NO_SURFACE = Integer.MIN_VALUE;
	public final int sea;
	private final HeightCache.Source source;
	private final Long2LongOpenHashMap cache = new Long2LongOpenHashMap();

	public Heights(Structure.GenerationContext ctx) {
		this((x, z, type) -> ctx.chunkGenerator().getBaseHeight(x, z, type, ctx.heightAccessor(), ctx.randomState()),
				ctx.chunkGenerator().getSeaLevel());
	}

	/** Over another height source (tests: the same search without the shared cache, {@link HeightCache}). */
	public Heights(HeightCache.Source source, int sea) {
		this.source = source;
		this.sea = sea;
	}

	private long at(int x, int z) {
		long key = BlockPos.asLong(x, 0, z);
		long v = cache.getOrDefault(key, Long.MIN_VALUE);
		if (v == Long.MIN_VALUE) {
			v = ((long) height(x, z, Heightmap.Types.OCEAN_FLOOR_WG) << 32) | (NO_SURFACE & 0xFFFFFFFFL);
			cache.put(key, v);
		}
		return v;
	}

	private int height(int x, int z, Heightmap.Types type) {
		return source.height(x, z, type);
	}

	/** First free height above the floor (not counting water). A single terrain evaluation per column. */
	public int floor(int x, int z) {
		return (int) (at(x, z) >> 32);
	}

	/** First free height counting water (only computed on request). */
	public int surface(int x, int z) {
		long v = at(x, z);
		int surface = (int) v;
		if (surface == NO_SURFACE) {
			surface = height(x, z, Heightmap.Types.WORLD_SURFACE_WG);
			cache.put(BlockPos.asLong(x, 0, z), (v & 0xFFFFFFFF00000000L) | (surface & 0xFFFFFFFFL));
		}
		return surface;
	}

	public boolean water(int x, int z) {
		int floor = floor(x, z);
		return floor < sea && surface(x, z) > floor;
	}
}
