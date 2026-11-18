package io.github.albertosa23.heraldia.actualizar;

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
public final class Mapa {
	public static final int MAX_ANCHO = 200;
	public static final String LEYENDA = "# construcción/build  P protegido/protected  R regenerar/regenerate  v virgen/virgin  "
			+ "E estructura nueva/new structure  . generado/generated  ~ incompleto/incomplete  S spawn";

	private Mapa() {
	}

	/** Carácter de un chunk. */
	static char simbolo(Detector.Clase c, boolean regenerar, boolean estructura) {
		if (c == null) {
			return ' ';
		}
		if (estructura) {
			return 'E';
		}
		return switch (c) {
			case CONSTRUCCION -> '#';
			case PROTEGIDO -> 'P';
			case VIRGEN -> regenerar ? 'R' : 'v';
			case NORMAL -> '.';
			case INCOMPLETO -> '~';
		};
	}

	/** Prioridad al juntar varios chunks en un carácter (mayor gana). */
	static int prioridad(char s) {
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
	static int[] limites(Map<Long, Detector.Clase> clases) {
		if (clases.isEmpty()) {
			return null;
		}
		int[] l = {Integer.MAX_VALUE, Integer.MAX_VALUE, Integer.MIN_VALUE, Integer.MIN_VALUE};
		for (long k : clases.keySet()) {
			int cx = ResumenChunk.cx(k), cz = ResumenChunk.cz(k);
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
	public static String texto(Map<Long, Detector.Clase> clases, Set<Long> regenerar, Set<Long> estructuras, int[] spawn) {
		int[] l = limites(clases);
		if (l == null) {
			return "(sin chunks)\n";
		}
		int ancho = l[2] - l[0] + 1, alto = l[3] - l[1] + 1;
		int escala = Math.max(1, (Math.max(ancho, alto) + MAX_ANCHO - 1) / MAX_ANCHO);
		int w = (ancho + escala - 1) / escala, h = (alto + escala - 1) / escala;
		char[][] m = new char[h][w];
		for (char[] fila : m) {
			java.util.Arrays.fill(fila, ' ');
		}
		clases.forEach((k, c) -> {
			int cx = ResumenChunk.cx(k), cz = ResumenChunk.cz(k);
			char s = simbolo(c, regenerar.contains(k), estructuras.contains(k));
			int x = (cx - l[0]) / escala, z = (cz - l[1]) / escala;
			if (prioridad(s) > prioridad(m[z][x])) {
				m[z][x] = s;
			}
		});
		if (spawn != null && spawn[0] >= l[0] && spawn[0] <= l[2] && spawn[1] >= l[1] && spawn[1] <= l[3]) {
			m[(spawn[1] - l[1]) / escala][(spawn[0] - l[0]) / escala] = 'S';
		}
		StringBuilder sb = new StringBuilder();
		sb.append("chunks ").append(l[0]).append(',').append(l[1]).append(" .. ").append(l[2]).append(',').append(l[3])
				.append("  (1 char = ").append(escala).append('x').append(escala).append(" chunks; N ↑)\n");
		for (char[] fila : m) {
			sb.append(new String(fila).stripTrailing()).append('\n');
		}
		sb.append(LEYENDA).append('\n');
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

	/** El mapa como imagen: un píxel por chunk (o por grupo si pasa de {@code maxLado}), {@code zoom} veces más grande. */
	public static BufferedImage imagen(Map<Long, Detector.Clase> clases, Set<Long> regenerar, Set<Long> estructuras, int[] spawn,
									   int maxLado, int zoom) {
		int[] l = limites(clases);
		if (l == null) {
			return new BufferedImage(1, 1, BufferedImage.TYPE_INT_RGB);
		}
		int ancho = l[2] - l[0] + 1, alto = l[3] - l[1] + 1;
		int escala = Math.max(1, (Math.max(ancho, alto) + maxLado - 1) / maxLado);
		int w = (ancho + escala - 1) / escala, h = (alto + escala - 1) / escala;
		char[][] m = new char[h][w];
		clases.forEach((k, c) -> {
			int x = (ResumenChunk.cx(k) - l[0]) / escala, z = (ResumenChunk.cz(k) - l[1]) / escala;
			char s = simbolo(c, regenerar.contains(k), estructuras.contains(k));
			if (prioridad(s) > prioridad(m[z][x])) {
				m[z][x] = s;
			}
		});
		if (spawn != null && spawn[0] >= l[0] && spawn[0] <= l[2] && spawn[1] >= l[1] && spawn[1] <= l[3]) {
			m[(spawn[1] - l[1]) / escala][(spawn[0] - l[0]) / escala] = 'S';
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
