package io.github.albertosa23.heraldia.common;

import it.unimi.dsi.fastutil.longs.Long2LongOpenHashMap;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.level.levelgen.structure.Structure;

/**
 * Alturas de generación de una columna (fondo {@code OCEAN_FLOOR_WG} y superficie {@code WORLD_SURFACE_WG}) con caché:
 * cada consulta evalúa el ruido de la columna, así que un mismo punto no se calcula dos veces. Agua = la superficie
 * queda por encima del fondo y el fondo bajo el nivel del mar. La superficie solo se evalúa si se pide. Una instancia por
 * búsqueda (no es segura entre hilos).
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

	/** Sobre otra fuente de alturas (pruebas: la misma búsqueda sin la caché compartida, {@link HeightCache}). */
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

	/** Primera altura libre sobre el fondo (sin contar el agua). Una sola evaluación del terreno por columna. */
	public int floor(int x, int z) {
		return (int) (at(x, z) >> 32);
	}

	/** Primera altura libre contando el agua (se calcula solo si se pide). */
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
