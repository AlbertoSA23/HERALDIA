package io.github.albertosa23.heraldia.comun;

import it.unimi.dsi.fastutil.longs.Long2LongLinkedOpenHashMap;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.LevelHeightAccessor;
import net.minecraft.world.level.chunk.ChunkGenerator;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.level.levelgen.RandomState;
import net.minecraft.world.level.levelgen.structure.Structure;
import org.jspecify.annotations.Nullable;

/**
 * Alturas de generación compartidas entre búsquedas y entre hilos: lo mismo que {@link Alturas} (fondo
 * {@code OCEAN_FLOOR_WG}, y la superficie {@code WORLD_SURFACE_WG} solo si se pide), pero una sola caché por mundo
 * (generador y {@code RandomState}) en vez de una por búsqueda. La altura de generación de una columna solo depende de la
 * semilla y del generador, así que el valor guardado es exactamente el que daría {@code getBaseHeight}: el resultado de
 * quien la use no cambia, solo deja de pagar dos veces la misma columna (las entradas a mina: cada estilo y variante del
 * structure_set mira el mismo centro, /locate vuelve a mirar los chunks que la regla de colocación ya miró...).
 * <p>Acotada: {@link #FRANJAS} franjas con su cerrojo, cada una con {@code capacidad / FRANJAS} columnas como mucho; al
 * llenarse, sale la más antigua (FIFO). Dos hilos que piden a la vez una columna nueva la calculan los dos (mismo valor):
 * el cálculo va fuera del cerrojo para no bloquear la generación.
 */
public final class CacheAlturas {
	/** Columnas como mucho por defecto: unas 65.000 (≈ 2-3 MB), más de mil chunks candidatos de mina. */
	public static final int CAPACIDAD = 1 << 16;
	static final int FRANJAS = 64;
	private static final int NO_SURFACE = Integer.MIN_VALUE;
	private static final long VACIO = Long.MIN_VALUE;
	private static volatile @Nullable CacheAlturas actual;

	/** De dónde salen las alturas (en el juego, {@code ChunkGenerator.getBaseHeight}; en las pruebas, lo que sea). */
	@FunctionalInterface
	public interface Fuente {
		int altura(int x, int z, Heightmap.Types tipo);
	}

	public final int sea;
	private final Object generador, estado;
	private final int minY, alto;
	private final Fuente fuente;
	private final Long2LongLinkedOpenHashMap[] franjas = new Long2LongLinkedOpenHashMap[FRANJAS];
	private final int porFranja;

	/** Pública para las pruebas: una caché sobre esa fuente, con el nivel del mar dado y como mucho {@code capacidad} columnas. */
	public CacheAlturas(Fuente fuente, int sea, int capacidad) {
		this(fuente, sea, capacidad, null, null, 0, 0);
	}

	private CacheAlturas(Fuente fuente, int sea, int capacidad, @Nullable Object generador, @Nullable Object estado, int minY, int alto) {
		this.fuente = fuente;
		this.sea = sea;
		this.porFranja = Math.max(1, capacidad / FRANJAS);
		this.generador = generador;
		this.estado = estado;
		this.minY = minY;
		this.alto = alto;
		for (int i = 0; i < FRANJAS; i++) {
			franjas[i] = new Long2LongLinkedOpenHashMap();
			franjas[i].defaultReturnValue(VACIO);
		}
	}

	/** La caché del mundo de ese contexto (la misma mientras no cambien el generador, el RandomState o la altura del mundo). */
	public static CacheAlturas de(Structure.GenerationContext ctx) {
		ChunkGenerator g = ctx.chunkGenerator();
		RandomState r = ctx.randomState();
		int minY = ctx.heightAccessor().getMinY(), alto = ctx.heightAccessor().getHeight();
		CacheAlturas c = actual;
		if (c == null || c.generador != g || c.estado != r || c.minY != minY || c.alto != alto) {
			// solo su altura: el contexto de la generación trae el chunk, que no debe quedarse en memoria
			LevelHeightAccessor height = LevelHeightAccessor.create(minY, alto);
			c = new CacheAlturas((x, z, tipo) -> g.getBaseHeight(x, z, tipo, height, r), g.getSeaLevel(), CAPACIDAD, g, r, minY, alto);
			actual = c;
		}
		return c;
	}

	private Long2LongLinkedOpenHashMap franja(long key) {
		long h = key * 0x9E3779B97F4A7C15L;
		return franjas[(int) (h >>> 58)];             // 64 franjas: los 6 bits altos del hash
	}

	private long leer(long key) {
		Long2LongLinkedOpenHashMap f = franja(key);
		synchronized (f) {
			return f.get(key);
		}
	}

	private void guardar(long key, long v) {
		Long2LongLinkedOpenHashMap f = franja(key);
		synchronized (f) {
			if (!f.containsKey(key) && f.size() >= porFranja) {
				f.removeFirstLong();                    // la más antigua
			}
			f.put(key, v);
		}
	}

	private long at(int x, int z) {
		long key = BlockPos.asLong(x, 0, z);
		long v = leer(key);
		if (v == VACIO) {
			v = ((long) fuente.altura(x, z, Heightmap.Types.OCEAN_FLOOR_WG) << 32) | (NO_SURFACE & 0xFFFFFFFFL);
			guardar(key, v);
		}
		return v;
	}

	/** Primera altura libre sobre el fondo (sin contar el agua), como {@link Alturas#floor}. */
	public int floor(int x, int z) {
		return (int) (at(x, z) >> 32);
	}

	/** Primera altura libre contando el agua (se calcula solo si se pide), como {@link Alturas#surface}. */
	public int surface(int x, int z) {
		long v = at(x, z);
		int surface = (int) v;
		if (surface == NO_SURFACE) {
			surface = fuente.altura(x, z, Heightmap.Types.WORLD_SURFACE_WG);
			guardar(BlockPos.asLong(x, 0, z), (v & 0xFFFFFFFF00000000L) | (surface & 0xFFFFFFFFL));
		}
		return surface;
	}

	/** Como {@link Alturas#water}. */
	public boolean water(int x, int z) {
		int floor = floor(x, z);
		return floor < sea && surface(x, z) > floor;
	}

	/** Columnas guardadas ahora (pruebas). */
	public int tamano() {
		int n = 0;
		for (Long2LongLinkedOpenHashMap f : franjas) {
			synchronized (f) {
				n += f.size();
			}
		}
		return n;
	}

	/** Columnas como mucho. */
	public int capacidad() {
		return porFranja * FRANJAS;
	}
}
