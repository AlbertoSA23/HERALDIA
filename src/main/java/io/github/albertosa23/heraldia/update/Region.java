package io.github.albertosa23.heraldia.update;

import java.io.ByteArrayInputStream;
import java.io.DataInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.RandomAccessFile;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.zip.GZIPInputStream;
import java.util.zip.InflaterInputStream;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.NbtAccounter;
import net.minecraft.nbt.NbtIo;

/**
 * Ficheros de región (.mca) leídos y tocados directamente, sin el juego (T46): la cabecera de 4 KiB con la posición de
 * cada uno de los 32 × 32 chunks, la de 4 KiB con sus fechas y, en sectores de 4 KiB, cada chunk (longitud, tipo de
 * compresión y el NBT). Sirve para el análisis de /heraldia update (solo lee) y para regenerar chunks vírgenes: borrar un
 * chunk es poner a 0 su entrada de las dos cabeceras (el juego lo da por no generado y lo vuelve a generar; los
 * sectores que ocupaba los reutiliza al guardar). Solo se escribe con el servidor sin el mundo cargado.
 */
public final class Region {
	public static final int SECTOR = 4096, SIDE = 32;
	private static final Pattern NAME = Pattern.compile("r\\.(-?\\d+)\\.(-?\\d+)\\.mca");

	private Region() {
	}

	/** Coordenadas de región de un fichero «r.X.Z.mca», o vacío si no lo es. */
	public static Optional<int[]> coordinatesOf(Path p) {
		Matcher m = NAME.matcher(p.getFileName().toString());
		return m.matches() ? Optional.of(new int[] {Integer.parseInt(m.group(1)), Integer.parseInt(m.group(2))}) : Optional.empty();
	}

	public static String name(int rx, int rz) {
		return "r." + rx + "." + rz + ".mca";
	}

	/** Índice de un chunk en la cabecera de su región (coordenadas de chunk del mundo). */
	public static int index(int cx, int cz) {
		return (cx & 31) + (cz & 31) * SIDE;
	}

	/** Las entradas presentes de la cabecera: índices de los chunks guardados en el fichero. */
	public static List<Integer> present(byte[] header) {
		List<Integer> out = new ArrayList<>();
		for (int i = 0; i < SIDE * SIDE; i++) {
			if (entry(header, i) != 0) {
				out.add(i);
			}
		}
		return out;
	}

	static int entry(byte[] header, int i) {
		return (header[i * 4] & 0xFF) << 24 | (header[i * 4 + 1] & 0xFF) << 16 | (header[i * 4 + 2] & 0xFF) << 8 | header[i * 4 + 3] & 0xFF;
	}

	/** Lee la cabecera de posiciones (los primeros 4 KiB); un fichero más corto se da por vacío. */
	public static byte[] header(Path file) throws IOException {
		byte[] out = new byte[SECTOR];
		try (RandomAccessFile f = new RandomAccessFile(file.toFile(), "r")) {
			if (f.length() >= SECTOR) {
				f.readFully(out);
			}
		}
		return out;
	}

	/**
	 * El NBT de un chunk del fichero (índice de la cabecera), o vacío si no está. Admite las compresiones de 26.3
	 * (gzip, zlib, ninguna y LZ4) y los chunks grandes guardados aparte (.mcc junto al fichero).
	 */
	public static Optional<CompoundTag> read(Path file, int index) throws IOException {
		try (RandomAccessFile f = new RandomAccessFile(file.toFile(), "r")) {
			if (f.length() < 2 * SECTOR) {
				return Optional.empty();
			}
			f.seek(index * 4L);
			int e = f.readInt();
			if (e == 0) {
				return Optional.empty();
			}
			long off = (long) (e >>> 8) * SECTOR;
			if (off + 5 > f.length()) {
				return Optional.empty();
			}
			f.seek(off);
			int length = f.readInt();
			int type = f.readUnsignedByte();
			InputStream data;
			if ((type & 0x80) != 0) {    // chunk de más de 1 MiB: va en c.X.Z.mcc
				coordinatesOf(file).orElseThrow(() -> new IOException("nombre de región raro: " + file));
				int[] r = coordinatesOf(file).get();
				int cx = r[0] * SIDE + index % SIDE, cz = r[1] * SIDE + index / SIDE;
				data = Files.newInputStream(file.resolveSibling("c." + cx + "." + cz + ".mcc"));
			} else {
				if (length <= 1 || off + 4 + length > f.length()) {
					return Optional.empty();
				}
				byte[] b = new byte[length - 1];
				f.readFully(b);
				data = new ByteArrayInputStream(b);
			}
			try (DataInputStream in = new DataInputStream(decompress(type & 0x7F, data))) {
				return Optional.of(NbtIo.read(in, NbtAccounter.unlimitedHeap()));
			}
		}
	}

	static InputStream decompress(int type, InputStream in) throws IOException {
		return switch (type) {
			case 1 -> new GZIPInputStream(in);
			case 2 -> new InflaterInputStream(in);
			case 3 -> in;
			case 4 -> new net.jpountz.lz4.LZ4BlockInputStream(in);
			default -> throw new IOException("compresión de chunk desconocida: " + type);
		};
	}

	/**
	 * Borra chunks de un fichero de región: pone a 0 su posición y su fecha en la cabecera (el resto del fichero no se
	 * toca). Devuelve cuántos estaban y se han borrado. Si el fichero no existe o es más corto que las cabeceras, nada.
	 */
	public static int delete(Path file, List<Integer> indices) throws IOException {
		if (!Files.isRegularFile(file) || Files.size(file) < 2 * SECTOR) {
			return 0;
		}
		int n = 0;
		try (RandomAccessFile f = new RandomAccessFile(file.toFile(), "rw")) {
			for (int i : indices) {
				f.seek(i * 4L);
				if (f.readInt() != 0) {
					n++;
				}
				f.seek(i * 4L);
				f.writeInt(0);
				f.seek(SECTOR + i * 4L);
				f.writeInt(0);
			}
		}
		return n;
	}
}
