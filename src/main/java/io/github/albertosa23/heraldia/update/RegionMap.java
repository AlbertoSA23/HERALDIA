package io.github.albertosa23.heraldia.update;

import java.awt.image.BufferedImage;
import java.util.Map;
import java.util.Set;

/**
 * Mapa del análisis de /heraldia update (T46), lógica pura: un carácter (o un píxel) por chunk, con el norte arriba.
 * Si el mundo es muy grande, cada carácter junta varios chunks y enseña el de más prioridad (lo protegido antes que lo
 * que se regenera). Leyenda: {@code #} construcción, {@code P} protegido, {@code R} se regenera, {@code v} virgen que no
 * se regenera (dejaría una estructura cortada), {@code E} se coloca una estructura nueva, {@code .} generado,
 * {@code ~} a medio generar, {@code S} spawn del mundo, espacio: sin generar.
 */
public final class RegionMap {
	public static final int MAX_WIDTH = 200;
	public static final String LEGEND = "# construcción/build  P protegido/protected  R regenerar/regenerate  v virgen/virgin  "
			+ "E estructura nueva/new structure  . generado/generated  ~ incompleto/incomplete  S spawn";

	private RegionMap() {
	}

	/** Carácter de un chunk. */
	static char symbol(Detector.Kind c, boolean regenerate, boolean structure) {
		if (c == null) {
			return ' ';
		}
		if (structure) {
			return 'E';
		}
		return switch (c) {
			case BUILD -> '#';
			case PROTECTED -> 'P';
			case PRISTINE -> regenerate ? 'R' : 'v';
			case NORMAL -> '.';
			case INCOMPLETE -> '~';
		};
	}

	/** Prioridad al juntar varios chunks en un carácter (mayor gana). */
	static int priority(char s) {
		return switch (s) {
			case 'S' -> 9;
			case '#' -> 8;
			case 'P' -> 7;
			case 'E' -> 6;
			case 'R' -> 5;
			case 'v' -> 4;
			case '~' -> 3;
			case '.' -> 2;
			default -> 0;
		};
	}

	/** Límites {minCx, minCz, maxCx, maxCz} de los chunks clasificados (o null si no hay ninguno). */
	static int[] bounds(Map<Long, Detector.Kind> classes) {
		if (classes.isEmpty()) {
			return null;
		}
		int[] l = {Integer.MAX_VALUE, Integer.MAX_VALUE, Integer.MIN_VALUE, Integer.MIN_VALUE};
		for (long k : classes.keySet()) {
			int cx = ChunkSummary.cx(k), cz = ChunkSummary.cz(k);
			l[0] = Math.min(l[0], cx);
			l[1] = Math.min(l[1], cz);
			l[2] = Math.max(l[2], cx);
			l[3] = Math.max(l[3], cz);
		}
		return l;
	}

	/**
	 * El mapa en texto, con una cabecera (qué chunks junta cada carácter y dónde empieza) y la leyenda.
	 *
	 * @param spawn chunk del spawn {cx, cz}, o null
	 */
	public static String text(Map<Long, Detector.Kind> classes, Set<Long> regenerate, Set<Long> structures, int[] spawn) {
		int[] l = bounds(classes);
		if (l == null) {
			return "(sin chunks)\n";
		}
		int width = l[2] - l[0] + 1, high = l[3] - l[1] + 1;
		int scale = Math.max(1, (Math.max(width, high) + MAX_WIDTH - 1) / MAX_WIDTH);
		int w = (width + scale - 1) / scale, h = (high + scale - 1) / scale;
		char[][] m = new char[h][w];
		for (char[] row : m) {
			java.util.Arrays.fill(row, ' ');
		}
		classes.forEach((k, c) -> {
			int cx = ChunkSummary.cx(k), cz = ChunkSummary.cz(k);
			char s = symbol(c, regenerate.contains(k), structures.contains(k));
			int x = (cx - l[0]) / scale, z = (cz - l[1]) / scale;
			if (priority(s) > priority(m[z][x])) {
				m[z][x] = s;
			}
		});
		if (spawn != null && spawn[0] >= l[0] && spawn[0] <= l[2] && spawn[1] >= l[1] && spawn[1] <= l[3]) {
			m[(spawn[1] - l[1]) / scale][(spawn[0] - l[0]) / scale] = 'S';
		}
		StringBuilder sb = new StringBuilder();
		sb.append("chunks ").append(l[0]).append(',').append(l[1]).append(" .. ").append(l[2]).append(',').append(l[3])
				.append("  (1 char = ").append(scale).append('x').append(scale).append(" chunks; N ↑)\n");
		for (char[] row : m) {
			sb.append(new String(row).stripTrailing()).append('\n');
		}
		sb.append(LEGEND).append('\n');
		return sb.toString();
	}

	/** Color (RGB) de cada símbolo en la imagen. */
	static int color(char s) {
		return switch (s) {
			case '#' -> 0xC62828;
			case 'P' -> 0xF9A825;
			case 'R' -> 0x2E7D32;
			case 'v' -> 0x81C784;
			case 'E' -> 0x1565C0;
			case '.' -> 0x9E9E9E;
			case '~' -> 0x616161;
			case 'S' -> 0x000000;
			default -> 0xFFFFFF;
		};
	}

	/** El mapa como imagen: un píxel por chunk (o por grupo si pasa de {@code maxSide}), {@code zoom} veces más grande. */
	public static BufferedImage image(Map<Long, Detector.Kind> classes, Set<Long> regenerate, Set<Long> structures, int[] spawn,
									   int maxSide, int zoom) {
		int[] l = bounds(classes);
		if (l == null) {
			return new BufferedImage(1, 1, BufferedImage.TYPE_INT_RGB);
		}
		int width = l[2] - l[0] + 1, high = l[3] - l[1] + 1;
		int scale = Math.max(1, (Math.max(width, high) + maxSide - 1) / maxSide);
		int w = (width + scale - 1) / scale, h = (high + scale - 1) / scale;
		char[][] m = new char[h][w];
		classes.forEach((k, c) -> {
			int x = (ChunkSummary.cx(k) - l[0]) / scale, z = (ChunkSummary.cz(k) - l[1]) / scale;
			char s = symbol(c, regenerate.contains(k), structures.contains(k));
			if (priority(s) > priority(m[z][x])) {
				m[z][x] = s;
			}
		});
		if (spawn != null && spawn[0] >= l[0] && spawn[0] <= l[2] && spawn[1] >= l[1] && spawn[1] <= l[3]) {
			m[(spawn[1] - l[1]) / scale][(spawn[0] - l[0]) / scale] = 'S';
		}
		BufferedImage img = new BufferedImage(w * zoom, h * zoom, BufferedImage.TYPE_INT_RGB);
		for (int z = 0; z < h; z++) {
			for (int x = 0; x < w; x++) {
				int rgb = color(m[z][x]);
				for (int dz = 0; dz < zoom; dz++) {
					for (int dx = 0; dx < zoom; dx++) {
						img.setRGB(x * zoom + dx, z * zoom + dz, rgb);
					}
				}
			}
		}
		return img;
	}
}
