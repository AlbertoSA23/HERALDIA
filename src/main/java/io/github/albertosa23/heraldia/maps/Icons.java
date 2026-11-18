package io.github.albertosa23.heraldia.maps;

import java.awt.image.BufferedImage;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.util.EnumMap;
import java.util.Map;
import javax.imageio.ImageIO;

/**
 * Layer icons, drawn once in memory (no files in the .jar): a circle in the layer's color with a dark
 * border and a white 8 x 8 pixel drawing at double size (crown, house, tower, pickaxe, lighthouse, crossed swords).
 */
public final class Icons {
	/** Icon side, in pixels. */
	public static final int SIDE = 24;
	private static final Map<Layer, String[]> DRAWINGS = new EnumMap<>(Map.of(
			Layer.UNIQUES, new String[]{"........", "#..##..#", "##.##.##", "########", "########", ".######.", ".######.", "........"},
			Layer.VILLAGES, new String[]{"...##...", "..####..", ".######.", "########", ".##..##.", ".##..##.", ".######.", "........"},
			Layer.MEDIUMS, new String[]{"#.#.#.#.", "#######.", ".#####..", ".##.##..", ".#####..", ".##.##..", ".#####..", "........"},
			Layer.MINES, new String[]{".#####..", "#.....#.", "...#....", "...#....", "...#....", "...#....", "...#....", "........"},
			Layer.COAST, new String[]{"..###...", "..#.#...", "..###...", "..#.#...", ".##.##..", ".#...#..", "#######.", "........"},
			Layer.ARENA, new String[]{"#......#", ".#....#.", "..#..#..", "...##...", "...##...", "..#..#..", ".#....#.", "##....##"}));
	private static final Map<Layer, BufferedImage> CACHE = new EnumMap<>(Layer.class);

	private Icons() {
	}

	/** A layer's icon (the same image every time: it must not be modified). */
	public static synchronized BufferedImage image(Layer layer) {
		return CACHE.computeIfAbsent(layer, Icons::draw);
	}

	/** A layer's icon as PNG. */
	public static byte[] png(Layer layer) {
		ByteArrayOutputStream out = new ByteArrayOutputStream();
		try {
			ImageIO.write(image(layer), "png", out);
		} catch (IOException e) {
			throw new UncheckedIOException(e);
		}
		return out.toByteArray();
	}

	private static BufferedImage draw(Layer layer) {
		BufferedImage img = new BufferedImage(SIDE, SIDE, BufferedImage.TYPE_INT_ARGB);
		double c = (SIDE - 1) / 2.0, r = SIDE / 2.0 - 0.5;
		int edge = darken(layer.color);
		for (int y = 0; y < SIDE; y++) {
			for (int x = 0; x < SIDE; x++) {
				double d = Math.hypot(x - c, y - c);
				if (d <= r - 1.5) {
					img.setRGB(x, y, layer.color);
				} else if (d <= r) {
					img.setRGB(x, y, edge);
				}
			}
		}
		String[] drawing = DRAWINGS.get(layer);
		int x0 = (SIDE - 16) / 2, y0 = (SIDE - 16) / 2;
		for (int fy = 0; fy < 8; fy++) {
			for (int fx = 0; fx < 8; fx++) {
				if (drawing[fy].charAt(fx) == '#') {
					for (int k = 0; k < 4; k++) {
						img.setRGB(x0 + fx * 2 + (k & 1), y0 + fy * 2 + (k >> 1), 0xFFFFFFFF);
					}
				}
			}
		}
		return img;
	}

	private static int darken(int argb) {
		int r = (argb >> 16 & 0xFF) / 2, g = (argb >> 8 & 0xFF) / 2, b = (argb & 0xFF) / 2;
		return 0xFF000000 | r << 16 | g << 8 | b;
	}
}
