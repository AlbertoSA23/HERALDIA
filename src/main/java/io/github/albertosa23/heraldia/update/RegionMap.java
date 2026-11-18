package io.github.albertosa23.heraldia.update;

import java.awt.image.BufferedImage;
import java.util.Map;
import java.util.Set;

/**
 * Map of the /heraldia update analysis (T46), pure logic: one character (or one pixel) per chunk, with north up.
 * If the world is very large, each character groups several chunks and shows the highest-priority one (protected before what
 * regenerates). Legend: {@code #} build, {@code P} protected, {@code R} regenerates, {@code v} pristine that does not
 * regenerate (it would leave a cut structure), {@code E} a new structure is placed, {@code .} generated,
 * {@code ~} half generated, {@code S} world spawn, space: not generated.
 */
public final class RegionMap {
	public static final int MAX_WIDTH = 200;
	public static final String LEGEND = "# construcción/build  P protegido/protected  R regenerar/regenerate  v virgen/virgin  "
			+ "E estructura nueva/new structure  . generado/generated  ~ incompleto/incomplete  S spawn";

	private RegionMap() {
	}

	/** Character of a chunk. */
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

	/** Priority when grouping several chunks into a character (higher wins). */
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

	/** Bounds {minCx, minCz, maxCx, maxCz} of the classified chunks (or null if there are none). */
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
	 * The text map, with a header (which chunks each character groups and where it starts) and the legend.
	 *
	 * @param spawn spawn chunk {cx, cz}, or null
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

	/** Color (RGB) of each symbol in the image. */
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

	/** The map as an image: one pixel per chunk (or per group if it exceeds {@code maxSide}), {@code zoom} times larger. */
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
