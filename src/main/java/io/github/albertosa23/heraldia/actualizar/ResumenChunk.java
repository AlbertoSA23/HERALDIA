package io.github.albertosa23.heraldia.actualizar;

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
 * @param jugador   bloques de jugador, cada uno empaquetado con {@link #empaquetar} (como mucho {@link #MAX_BLOQUES})
 * @param inicios   inicios de estructura de este chunk: id → cajas de sus piezas {minX, minY, minZ, maxX, maxY, maxZ}
 * @param cimas     por cada columna de muestra ({@link #MUESTRA}), la y de su cima (OCEAN_FLOOR) o {@link Integer#MIN_VALUE}
 * @param bloquesCima el bloque de esa cima (null si no se sabe)
 */
public record ResumenChunk(int cx, int cz, boolean completo, long habitado, int minY, int[] jugador, Map<String, List<int[]>> inicios,
						   int[] cimas, String[] bloquesCima) {
	public static final int MAX_BLOQUES = 4096;
	/** Columnas de muestra (x, z dentro del chunk) para comparar con la regeneración: una rejilla de 4 × 4. */
	public static final int[][] MUESTRA;

	static {
		MUESTRA = new int[16][];
		int i = 0;
		for (int z = 2; z < 16; z += 4) {
			for (int x = 2; x < 16; x += 4) {
				MUESTRA[i++] = new int[] {x, z};
			}
		}
	}

	/** Marca de bloque ambiguo ({@link BloquesJugador#ambiguo}) en el valor empaquetado. */
	static final int AMBIGUO = 1 << 24;

	/** Un bloque del chunk en un int: x y z locales (4 bits cada uno) e y sobre la más baja del mundo (16 bits). */
	public static int empaquetar(int lx, int y, int lz, int minY) {
		return lx & 15 | (lz & 15) << 4 | (y - minY & 0xFFFF) << 8;
	}

	/** ¿Es ambiguo el bloque {@code i} de {@link #jugador()}? (también lo pone la generación fuera de las estructuras) */
	public boolean ambiguo(int i) {
		return (jugador[i] & AMBIGUO) != 0;
	}

	/** El bloque {@code i} de {@link #jugador()} en coordenadas del mundo {x, y, z}. */
	public int[] bloqueJugador(int i) {
		int v = jugador[i];
		return new int[] {cx * 16 + (v & 15), minY + (v >>> 8 & 0xFFFF), cz * 16 + (v >> 4 & 15)};
	}

	public long clave() {
		return clave(cx, cz);
	}

	public static long clave(int cx, int cz) {
		return (long) cx & 0xFFFFFFFFL | ((long) cz & 0xFFFFFFFFL) << 32;
	}

	public static int cx(long clave) {
		return (int) clave;
	}

	public static int cz(long clave) {
		return (int) (clave >>> 32);
	}

	/**
	 * Lee el resumen del NBT de un chunk de 26.3 ({@code xPos}, {@code zPos}, {@code Status}, {@code InhabitedTime},
	 * {@code sections} con su {@code block_states}, {@code block_entities}, {@code structures.starts} y
	 * {@code Heightmaps.OCEAN_FLOOR}). Lo que falte o no se entienda se deja vacío.
	 *
	 * @param minY la y más baja del mundo (−64 en el mundo principal)
	 */
	public static ResumenChunk de(CompoundTag nbt, int minY) {
		int cx = nbt.getIntOr("xPos", 0), cz = nbt.getIntOr("zPos", 0);
		String status = nbt.getStringOr("Status", "");
		boolean completo = status.equals("minecraft:full") || status.equals("full");
		long habitado = nbt.getLongOr("InhabitedTime", 0);
		Map<Integer, Seccion> secciones = new LinkedHashMap<>();
		int[] jugador = new int[MAX_BLOQUES];
		int njug = 0;
		ListTag secs = nbt.getListOrEmpty("sections");
		for (int i = 0; i < secs.size(); i++) {
			CompoundTag s = secs.getCompoundOrEmpty(i);
			int sy = s.getIntOr("Y", s.getByteOr("Y", (byte) 0));
			Seccion sec = Seccion.de(s.getCompoundOrEmpty("block_states"));
			if (sec == null) {
				continue;
			}
			secciones.put(sy, sec);
			if (sec.algunoDeJugador()) {
				njug = sec.posicionesDeJugador(sy * 16, minY, jugador, njug);
			}
		}
		Map<String, List<int[]>> inicios = new LinkedHashMap<>();
		CompoundTag starts = nbt.getCompoundOrEmpty("structures").getCompoundOrEmpty("starts");
		for (String id : starts.keySet()) {
			CompoundTag st = starts.getCompoundOrEmpty(id);
			if ("INVALID".equals(st.getStringOr("id", "INVALID"))) {
				continue;
			}
			List<int[]> cajas = new ArrayList<>();
			ListTag hijos = st.getListOrEmpty("Children");
			for (int i = 0; i < hijos.size(); i++) {
				hijos.getCompoundOrEmpty(i).getIntArray("BB").filter(bb -> bb.length == 6).ifPresent(cajas::add);
			}
			inicios.put(id, cajas);
		}
		int[] cimas = new int[MUESTRA.length];
		String[] bloques = new String[MUESTRA.length];
		long[] hm = nbt.getCompoundOrEmpty("Heightmaps").getLongArray("OCEAN_FLOOR").orElse(null);
		for (int i = 0; i < MUESTRA.length; i++) {
			int x = MUESTRA[i][0], z = MUESTRA[i][1];
			int v = hm == null ? -1 : altura(hm, x + z * 16);
			if (v <= 0) {
				cimas[i] = Integer.MIN_VALUE;
				continue;
			}
			int y = minY + v - 1;
			cimas[i] = y;
			Seccion s = secciones.get(Math.floorDiv(y, 16));
			bloques[i] = s == null ? null : s.bloque(x, Math.floorMod(y, 16), z);
		}
		return new ResumenChunk(cx, cz, completo, habitado, minY, java.util.Arrays.copyOf(jugador, njug), inicios, cimas, bloques);
	}

	/** Valor de un mapa de alturas de 26.3: 9 bits por columna, 7 por long, sin cruzar de un long a otro. */
	static int altura(long[] datos, int i) {
		int bits = 9, porLong = 64 / bits;
		int l = i / porLong;
		if (l >= datos.length) {
			return -1;
		}
		return (int) (datos[l] >>> (i % porLong) * bits & (1L << bits) - 1);
	}

	/** Una sección de 16 × 16 × 16: su paleta y sus índices. */
	record Seccion(String[] paleta, long[] datos, boolean[] deJugador, boolean[] ambiguo) {
		static Seccion de(CompoundTag bs) {
			ListTag pal = bs.getListOrEmpty("palette");
			if (pal.isEmpty()) {
				return null;
			}
			String[] p = new String[pal.size()];
			boolean[] j = new boolean[pal.size()], a = new boolean[pal.size()];
			for (int i = 0; i < pal.size(); i++) {
				p[i] = nombre(pal.get(i));
				j[i] = p[i] != null && BloquesJugador.deJugador(p[i]);
				a[i] = j[i] && BloquesJugador.ambiguo(p[i]);
			}
			return new Seccion(p, bs.getLongArray("data").orElse(null), j, a);
		}

		static String nombre(Tag t) {
			if (t instanceof StringTag(String v)) {
				return v;
			}
			if (t instanceof CompoundTag c) {
				return c.getString("Name").or(() -> c.getString("id")).orElse(null);
			}
			return null;
		}

		boolean algunoDeJugador() {
			for (boolean b : deJugador) {
				if (b) {
					return true;
				}
			}
			return false;
		}

		int indice(int i) {
			if (datos == null || paleta.length == 1) {
				return 0;
			}
			int bits = Math.max(4, 32 - Integer.numberOfLeadingZeros(paleta.length - 1));
			int porLong = 64 / bits;
			int l = i / porLong;
			if (l >= datos.length) {
				return 0;
			}
			int v = (int) (datos[l] >>> (i % porLong) * bits & (1L << bits) - 1);
			return v < paleta.length ? v : 0;
		}

		String bloque(int x, int y, int z) {
			return paleta[indice(y * 256 + z * 16 + x)];
		}

		/** Añade a {@code out} (desde {@code n}) los bloques de jugador de la sección; devuelve cuántos hay en total. */
		int posicionesDeJugador(int by, int minY, int[] out, int n) {
			for (int i = 0; i < 4096 && n < out.length; i++) {
				int k = indice(i);
				if (deJugador[k]) {
					out[n++] = empaquetar(i & 15, by + (i >> 8), i >> 4 & 15, minY) | (ambiguo[k] ? AMBIGUO : 0);
				}
			}
			return n;
		}
	}
}
