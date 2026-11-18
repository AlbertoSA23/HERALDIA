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
 * Alturas de generación compartidas entre búsquedas y entre hilos: lo mismo que {@link Heights} (fondo
 * {@code OCEAN_FLOOR_WG}, y la superficie {@code WORLD_SURFACE_WG} solo si se pide), pero una sola caché por mundo
 * (generador y {@code RandomState}) en vez de una por búsqueda. La altura de generación de una columna solo depende de la
 * semilla y del generador, así que el valor guardado es exactamente el que daría {@code getBaseHeight}: el resultado de
 * quien la use no cambia, solo deja de pagar dos veces la misma columna (las entradas a mina: cada estilo y variante del
 * structure_set mira el mismo centro, /locate vuelve a mirar los chunks que la regla de colocación ya miró...).
 * <p>Acotada: {@link #BANDS} franjas con su cerrojo, cada una con {@code capacity / BANDS} columnas como mucho; al
 * llenarse, sale la más antigua (FIFO). Dos hilos que piden a la vez una columna nueva la calculan los dos (mismo valor):
 * el cálculo va fuera del cerrojo para no bloquear la generación.
 */
public final class HeightCache {
	/** Columnas como mucho por defecto: unas 65.000 (≈ 2-3 MB), más de mil chunks candidatos de mina. */
	public static final int CAPACITY = 1 << 16;
	static final int BANDS = 64;
	private static final int NO_SURFACE = Integer.MIN_VALUE;
	private static final long EMPTY = Long.MIN_VALUE;
	private static volatile @Nullable HeightCache actual;

	/** De dónde salen las alturas (en el juego, {@code ChunkGenerator.getBaseHeight}; en las pruebas, lo que sea). */
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

	/** Pública para las pruebas: una caché sobre esa fuente, con el nivel del mar dado y como mucho {@code capacity} columnas. */
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

	/** La caché del mundo de ese contexto (la misma mientras no cambien el generador, el RandomState o la altura del mundo). */
	public static HeightCache of(Structure.GenerationContext ctx) {
		ChunkGenerator g = ctx.chunkGenerator();
		RandomState r = ctx.randomState();
		int minY = ctx.heightAccessor().getMinY(), high = ctx.heightAccessor().getHeight();
		HeightCache c = actual;
		if (c == null || c.generator != g || c.state != r || c.minY != minY || c.high != high) {
			// solo su altura: el contexto de la generación trae el chunk, que no debe quedarse en memoria
			LevelHeightAccessor height = LevelHeightAccessor.create(minY, high);
			c = new HeightCache((x, z, type) -> g.getBaseHeight(x, z, type, height, r), g.getSeaLevel(), CAPACITY, g, r, minY, high);
			actual = c;
		}
		return c;
	}

	private Long2LongLinkedOpenHashMap band(long key) {
		long h = key * 0x9E3779B97F4A7C15L;
		return bands[(int) (h >>> 58)];             // 64 franjas: los 6 bits altos del hash
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
				f.removeFirstLong();                    // la más antigua
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

	/** Primera altura libre sobre el fondo (sin contar el agua), como {@link Heights#floor}. */
	public int floor(int x, int z) {
		return (int) (at(x, z) >> 32);
	}

	/** Primera altura libre contando el agua (se calcula solo si se pide), como {@link Heights#surface}. */
	public int surface(int x, int z) {
		long v = at(x, z);
		int surface = (int) v;
		if (surface == NO_SURFACE) {
			surface = source.height(x, z, Heightmap.Types.WORLD_SURFACE_WG);
			save(BlockPos.asLong(x, 0, z), (v & 0xFFFFFFFF00000000L) | (surface & 0xFFFFFFFFL));
		}
		return surface;
	}

	/** Como {@link Heights#water}. */
	public boolean water(int x, int z) {
		int floor = floor(x, z);
		return floor < sea && surface(x, z) > floor;
	}

	/** Columnas guardadas ahora (pruebas). */
	public int size() {
		int n = 0;
		for (Long2LongLinkedOpenHashMap f : bands) {
			synchronized (f) {
				n += f.size();
			}
		}
		return n;
	}

	/** Columnas como mucho. */
	public int capacity() {
		return perBand * BANDS;
	}
}
