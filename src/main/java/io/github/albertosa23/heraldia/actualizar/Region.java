package io.github.albertosa23.heraldia.actualizar;

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
	public static final int SECTOR = 4096, LADO = 32;
	private static final Pattern NOMBRE = Pattern.compile("r\\.(-?\\d+)\\.(-?\\d+)\\.mca");

	private Region() {
	}

	/** Coordenadas de región de un fichero «r.X.Z.mca», o vacío si no lo es. */
	public static Optional<int[]> coordenadas(Path p) {
		Matcher m = NOMBRE.matcher(p.getFileName().toString());
		return m.matches() ? Optional.of(new int[] {Integer.parseInt(m.group(1)), Integer.parseInt(m.group(2))}) : Optional.empty();
	}

	public static String nombre(int rx, int rz) {
		return "r." + rx + "." + rz + ".mca";
	}

	/** Índice de un chunk en la cabecera de su región (coordenadas de chunk del mundo). */
	public static int indice(int cx, int cz) {
		return (cx & 31) + (cz & 31) * LADO;
	}

	/** Las entradas presentes de la cabecera: índices de los chunks guardados en el fichero. */
	public static List<Integer> presentes(byte[] cabecera) {
		List<Integer> out = new ArrayList<>();
		for (int i = 0; i < LADO * LADO; i++) {
			if (entrada(cabecera, i) != 0) {
				out.add(i);
			}
		}
		return out;
	}

	static int entrada(byte[] cabecera, int i) {
		return (cabecera[i * 4] & 0xFF) << 24 | (cabecera[i * 4 + 1] & 0xFF) << 16 | (cabecera[i * 4 + 2] & 0xFF) << 8 | cabecera[i * 4 + 3] & 0xFF;
	}

	/** Lee la cabecera de posiciones (los primeros 4 KiB); un fichero más corto se da por vacío. */
	public static byte[] cabecera(Path file) throws IOException {
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
	public static Optional<CompoundTag> leer(Path file, int indice) throws IOException {
		try (RandomAccessFile f = new RandomAccessFile(file.toFile(), "r")) {
			if (f.length() < 2 * SECTOR) {
				return Optional.empty();
			}
			f.seek(indice * 4L);
			int e = f.readInt();
			if (e == 0) {
				return Optional.empty();
			}
			long off = (long) (e >>> 8) * SECTOR;
			if (off + 5 > f.length()) {
				return Optional.empty();
			}
			f.seek(off);
			int largo = f.readInt();
			int tipo = f.readUnsignedByte();
			InputStream datos;
			if ((tipo & 0x80) != 0) {    // chunk de más de 1 MiB: va en c.X.Z.mcc
				coordenadas(file).orElseThrow(() -> new IOException("nombre de región raro: " + file));
				int[] r = coordenadas(file).get();
				int cx = r[0] * LADO + indice % LADO, cz = r[1] * LADO + indice / LADO;
				datos = Files.newInputStream(file.resolveSibling("c." + cx + "." + cz + ".mcc"));
			} else {
				if (largo <= 1 || off + 4 + largo > f.length()) {
					return Optional.empty();
				}
				byte[] b = new byte[largo - 1];
				f.readFully(b);
				datos = new ByteArrayInputStream(b);
			}
			try (DataInputStream in = new DataInputStream(descomprimir(tipo & 0x7F, datos))) {
				return Optional.of(NbtIo.read(in, NbtAccounter.unlimitedHeap()));
			}
		}
	}

	static InputStream descomprimir(int tipo, InputStream in) throws IOException {
		return switch (tipo) {
			case 1 -> new GZIPInputStream(in);
			case 2 -> new InflaterInputStream(in);
			case 3 -> in;
			case 4 -> new net.jpountz.lz4.LZ4BlockInputStream(in);
			default -> throw new IOException("compresión de chunk desconocida: " + tipo);
		};
	}

	/**
	 * Borra chunks de un fichero de región: pone a 0 su posición y su fecha en la cabecera (el resto del fichero no se
	 * toca). Devuelve cuántos estaban y se han borrado. Si el fichero no existe o es más corto que las cabeceras, nada.
	 */
	public static int borrar(Path file, List<Integer> indices) throws IOException {
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
