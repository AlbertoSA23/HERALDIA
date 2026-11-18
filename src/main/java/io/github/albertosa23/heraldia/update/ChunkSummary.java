package io.github.albertosa23.heraldia.update;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.StringTag;
import net.minecraft.nbt.Tag;

/**
 * Lo que el análisis de /heraldia update necesita de un chunk guardado (T46), sacado de su NBT sin el juego: posición,
 * si está generado del todo, su InhabitedTime, los bloques típicos de jugador (con su posición), los inicios de
 * estructura que guarda (con la caja de cada pieza), y la altura y el bloque de la cima de unas columnas de muestra para
 * compararlas con la regeneración. Se queda con poco (no guarda el NBT): un mundo grande tiene cientos de miles.
 *
 * @param jugador   bloques de jugador, cada uno empaquetado con {@link #pack} (como mucho {@link #MAX_BLOCKS})
 * @param inicios   inicios de estructura de este chunk: id → cajas de sus piezas {minX, minY, minZ, maxX, maxY, maxZ}
 * @param cimas     por cada columna de muestra ({@link #SAMPLE}), la y de su cima (OCEAN_FLOOR) o {@link Integer#MIN_VALUE}
 * @param bloquesCima el bloque de esa cima (null si no se sabe)
 */
public record ChunkSummary(int cx, int cz, boolean complete, long inhabited, int minY, int[] player, Map<String, List<int[]>> structureStarts,
						   int[] tops, String[] topBlocks) {
	public static final int MAX_BLOCKS = 4096;
	/** Columnas de muestra (x, z dentro del chunk) para comparar con la regeneración: una rejilla de 4 × 4. */
	public static final int[][] SAMPLE;

	static {
		SAMPLE = new int[16][];
		int i = 0;
		for (int z = 2; z < 16; z += 4) {
			for (int x = 2; x < 16; x += 4) {
				SAMPLE[i++] = new int[] {x, z};
			}
		}
	}

	/** Marca de bloque ambiguo ({@link PlayerBlocks#ambiguous}) en el valor empaquetado. */
	static final int AMBIGUOUS = 1 << 24;

	/** Un bloque del chunk en un int: x y z locales (4 bits cada uno) e y sobre la más baja del mundo (16 bits). */
	public static int pack(int lx, int y, int lz, int minY) {
		return lx & 15 | (lz & 15) << 4 | (y - minY & 0xFFFF) << 8;
	}

	/** ¿Es ambiguo el bloque {@code i} de {@link #player()}? (también lo pone la generación fuera de las estructuras) */
	public boolean ambiguous(int i) {
		return (player[i] & AMBIGUOUS) != 0;
	}

	/** El bloque {@code i} de {@link #player()} en coordenadas del mundo {x, y, z}. */
	public int[] playerBlock(int i) {
		int v = player[i];
		return new int[] {cx * 16 + (v & 15), minY + (v >>> 8 & 0xFFFF), cz * 16 + (v >> 4 & 15)};
	}

	public long key() {
		return key(cx, cz);
	}

	public static long key(int cx, int cz) {
		return (long) cx & 0xFFFFFFFFL | ((long) cz & 0xFFFFFFFFL) << 32;
	}

	public static int cx(long key) {
		return (int) key;
	}

	public static int cz(long key) {
		return (int) (key >>> 32);
	}

	/**
	 * Lee el resumen del NBT de un chunk de 26.3 ({@code xPos}, {@code zPos}, {@code Status}, {@code InhabitedTime},
	 * {@code sections} con su {@code block_states}, {@code block_entities}, {@code structures.starts} y
	 * {@code Heightmaps.OCEAN_FLOOR}). Lo que falte o no se entienda se deja vacío.
	 *
	 * @param minY la y más baja del mundo (−64 en el mundo principal)
	 */
	public static ChunkSummary of(CompoundTag nbt, int minY) {
		int cx = nbt.getIntOr("xPos", 0), cz = nbt.getIntOr("zPos", 0);
		String status = nbt.getStringOr("Status", "");
		boolean complete = status.equals("minecraft:full") || status.equals("full");
		long inhabited = nbt.getLongOr("InhabitedTime", 0);
		Map<Integer, Section> sections = new LinkedHashMap<>();
		int[] player = new int[MAX_BLOCKS];
		int nPlayer = 0;
		ListTag secs = nbt.getListOrEmpty("sections");
		for (int i = 0; i < secs.size(); i++) {
			CompoundTag s = secs.getCompoundOrEmpty(i);
			int sy = s.getIntOr("Y", s.getByteOr("Y", (byte) 0));
			Section sec = Section.of(s.getCompoundOrEmpty("block_states"));
			if (sec == null) {
				continue;
			}
			sections.put(sy, sec);
			if (sec.anyPlayerBlock()) {
				nPlayer = sec.playerPositions(sy * 16, minY, player, nPlayer);
			}
		}
		Map<String, List<int[]>> structureStarts = new LinkedHashMap<>();
		CompoundTag starts = nbt.getCompoundOrEmpty("structures").getCompoundOrEmpty("starts");
		for (String id : starts.keySet()) {
			CompoundTag st = starts.getCompoundOrEmpty(id);
			if ("INVALID".equals(st.getStringOr("id", "INVALID"))) {
				continue;
			}
			List<int[]> boxes = new ArrayList<>();
			ListTag children = st.getListOrEmpty("Children");
			for (int i = 0; i < children.size(); i++) {
				children.getCompoundOrEmpty(i).getIntArray("BB").filter(bb -> bb.length == 6).ifPresent(boxes::add);
			}
			structureStarts.put(id, boxes);
		}
		int[] tops = new int[SAMPLE.length];
		String[] blocks = new String[SAMPLE.length];
		long[] hm = nbt.getCompoundOrEmpty("Heightmaps").getLongArray("OCEAN_FLOOR").orElse(null);
		for (int i = 0; i < SAMPLE.length; i++) {
			int x = SAMPLE[i][0], z = SAMPLE[i][1];
			int v = hm == null ? -1 : height(hm, x + z * 16);
			if (v <= 0) {
				tops[i] = Integer.MIN_VALUE;
				continue;
			}
			int y = minY + v - 1;
			tops[i] = y;
			Section s = sections.get(Math.floorDiv(y, 16));
			blocks[i] = s == null ? null : s.block(x, Math.floorMod(y, 16), z);
		}
		return new ChunkSummary(cx, cz, complete, inhabited, minY, java.util.Arrays.copyOf(player, nPlayer), structureStarts, tops, blocks);
	}

	/** Valor de un mapa de alturas de 26.3: 9 bits por columna, 7 por long, sin cruzar de un long a otro. */
	static int height(long[] data, int i) {
		int bits = 9, perLong = 64 / bits;
		int l = i / perLong;
		if (l >= data.length) {
			return -1;
		}
		return (int) (data[l] >>> (i % perLong) * bits & (1L << bits) - 1);
	}

	/** Una sección de 16 × 16 × 16: su paleta y sus índices. */
	record Section(String[] palette, long[] data, boolean[] playerSource, boolean[] ambiguous) {
		static Section of(CompoundTag bs) {
			ListTag pal = bs.getListOrEmpty("palette");
			if (pal.isEmpty()) {
				return null;
			}
			String[] p = new String[pal.size()];
			boolean[] j = new boolean[pal.size()], a = new boolean[pal.size()];
			for (int i = 0; i < pal.size(); i++) {
				p[i] = name(pal.get(i));
				j[i] = p[i] != null && PlayerBlocks.playerSource(p[i]);
				a[i] = j[i] && PlayerBlocks.ambiguous(p[i]);
			}
			return new Section(p, bs.getLongArray("data").orElse(null), j, a);
		}

		static String name(Tag t) {
			if (t instanceof StringTag(String v)) {
				return v;
			}
			if (t instanceof CompoundTag c) {
				return c.getString("Name").or(() -> c.getString("id")).orElse(null);
			}
			return null;
		}

		boolean anyPlayerBlock() {
			for (boolean b : playerSource) {
				if (b) {
					return true;
				}
			}
			return false;
		}

		int index(int i) {
			if (data == null || palette.length == 1) {
				return 0;
			}
			int bits = Math.max(4, 32 - Integer.numberOfLeadingZeros(palette.length - 1));
			int perLong = 64 / bits;
			int l = i / perLong;
			if (l >= data.length) {
				return 0;
			}
			int v = (int) (data[l] >>> (i % perLong) * bits & (1L << bits) - 1);
			return v < palette.length ? v : 0;
		}

		String block(int x, int y, int z) {
			return palette[index(y * 256 + z * 16 + x)];
		}

		/** Añade a {@code out} (desde {@code n}) los bloques de jugador de la sección; devuelve cuántos hay en total. */
		int playerPositions(int by, int minY, int[] out, int n) {
			for (int i = 0; i < 4096 && n < out.length; i++) {
				int k = index(i);
				if (playerSource[k]) {
					out[n++] = pack(i & 15, by + (i >> 8), i >> 4 & 15, minY) | (ambiguous[k] ? AMBIGUOUS : 0);
				}
			}
			return n;
		}
	}
}
