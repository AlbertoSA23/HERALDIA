package io.github.albertosa23.heraldia.mapas;

import java.awt.image.BufferedImage;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.util.EnumMap;
import java.util.Map;
import javax.imageio.ImageIO;

/**
 * Iconos de las capas, dibujados una vez en memoria (sin ficheros en el .jar): un círculo del color de la capa con borde
 * oscuro y un dibujo blanco de 8 x 8 píxeles a doble tamaño (corona, casa, torre, pico, espadas cruzadas).
 */
public final class Iconos {
	/** Lado del icono, en píxeles. */
	public static final int LADO = 24;
	private static final Map<Capa, String[]> DIBUJOS = new EnumMap<>(Map.of(
			Capa.UNICAS, new String[]{"........", "#..##..#", "##.##.##", "########", "########", ".######.", ".######.", "........"},
			Capa.ALDEAS, new String[]{"...##...", "..####..", ".######.", "########", ".##..##.", ".##..##.", ".######.", "........"},
			Capa.MEDIANAS, new String[]{"#.#.#.#.", "#######.", ".#####..", ".##.##..", ".#####..", ".##.##..", ".#####..", "........"},
			Capa.MINAS, new String[]{".#####..", "#.....#.", "...#....", "...#....", "...#....", "...#....", "...#....", "........"},
			Capa.ARENA, new String[]{"#......#", ".#....#.", "..#..#..", "...##...", "...##...", "..#..#..", ".#....#.", "##....##"}));
	private static final Map<Capa, BufferedImage> CACHE = new EnumMap<>(Capa.class);

	private Iconos() {
	}

	/** El icono de una capa (la misma imagen cada vez: no se debe modificar). */
	public static synchronized BufferedImage imagen(Capa capa) {
		return CACHE.computeIfAbsent(capa, Iconos::dibujar);
	}

	/** El icono de una capa en PNG. */
	public static byte[] png(Capa capa) {
		ByteArrayOutputStream out = new ByteArrayOutputStream();
		try {
			ImageIO.write(imagen(capa), "png", out);
		} catch (IOException e) {
			throw new UncheckedIOException(e);
		}
		return out.toByteArray();
	}

	private static BufferedImage dibujar(Capa capa) {
		BufferedImage img = new BufferedImage(LADO, LADO, BufferedImage.TYPE_INT_ARGB);
		double c = (LADO - 1) / 2.0, r = LADO / 2.0 - 0.5;
		int borde = oscurecer(capa.color);
		for (int y = 0; y < LADO; y++) {
			for (int x = 0; x < LADO; x++) {
				double d = Math.hypot(x - c, y - c);
				if (d <= r - 1.5) {
					img.setRGB(x, y, capa.color);
				} else if (d <= r) {
					img.setRGB(x, y, borde);
				}
			}
		}
		String[] dibujo = DIBUJOS.get(capa);
		int x0 = (LADO - 16) / 2, y0 = (LADO - 16) / 2;
		for (int fy = 0; fy < 8; fy++) {
			for (int fx = 0; fx < 8; fx++) {
				if (dibujo[fy].charAt(fx) == '#') {
					for (int k = 0; k < 4; k++) {
						img.setRGB(x0 + fx * 2 + (k & 1), y0 + fy * 2 + (k >> 1), 0xFFFFFFFF);
					}
				}
			}
		}
		return img;
	}

	private static int oscurecer(int argb) {
		int r = (argb >> 16 & 0xFF) / 2, g = (argb >> 8 & 0xFF) / 2, b = (argb & 0xFF) / 2;
		return 0xFF000000 | r << 16 | g << 8 | b;
	}
}
