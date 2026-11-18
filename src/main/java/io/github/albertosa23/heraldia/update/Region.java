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
 * Region files (.mca) read and touched directly, without the game (T46): the 4 KiB header with the position of
 * each of the 32 × 32 chunks, the 4 KiB one with their timestamps and, in 4 KiB sectors, each chunk (length, compression
 * type and the NBT). It serves the /heraldia update analysis (read only) and regenerating pristine chunks: deleting a
 * chunk means zeroing its entry in both headers (the game treats it as not generated and generates it again; it reuses the
 * sectors it occupied when saving). It is only written with the server running without the world loaded.
 */
public final class Region {
	public static final int SECTOR = 4096, SIDE = 32;
	private static final Pattern NAME = Pattern.compile("r\\.(-?\\d+)\\.(-?\\d+)\\.mca");

	private Region() {
	}

	/** Region coordinates of an "r.X.Z.mca" file, or empty if it is not one. */
	public static Optional<int[]> coordinatesOf(Path p) {
		Matcher m = NAME.matcher(p.getFileName().toString());
		return m.matches() ? Optional.of(new int[] {Integer.parseInt(m.group(1)), Integer.parseInt(m.group(2))}) : Optional.empty();
	}

	public static String name(int rx, int rz) {
		return "r." + rx + "." + rz + ".mca";
	}

	/** Index of a chunk in its region's header (world chunk coordinates). */
	public static int index(int cx, int cz) {
		return (cx & 31) + (cz & 31) * SIDE;
	}

	/** The header's present entries: indices of the chunks saved in the file. */
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

	/** Reads the positions header (the first 4 KiB); a shorter file is treated as empty. */
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
	 * The NBT of a chunk in the file (header index), or empty if it is not there. It supports the 26.3 compressions
	 * (gzip, zlib, none and LZ4) and large chunks saved separately (.mcc next to the file).
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
			if ((type & 0x80) != 0) {    // chunk over 1 MiB: goes in c.X.Z.mcc
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
	 * Deletes chunks from a region file: zeroes their position and timestamp in the header (the rest of the file is not
	 * touched). Returns how many were there and were deleted. If the file does not exist or is shorter than the headers, nothing.
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
