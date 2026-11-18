package io.github.albertosa23.heraldia.actualizar;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.ByteArrayOutputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.io.RandomAccessFile;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.zip.DeflaterOutputStream;
import net.minecraft.SharedConstants;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.IntArrayTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.LongArrayTag;
import net.minecraft.nbt.NbtIo;
import net.minecraft.nbt.StringTag;
import net.minecraft.server.Bootstrap;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * Regiones (.mca) sintéticas con chunks de 26.3: se leen sin el juego ({@link Region}, {@link ResumenChunk}), y borrar
 * un chunk solo quita su entrada de la cabecera (los demás siguen igual). También el mapa en texto.
 */
class RegionTest {
	@TempDir
	Path dir;

	@BeforeAll
	static void bootstrap() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	/** Un chunk de 26.3: una sección en y = 4 (64..79) de piedra con una cama en (3, 70, 5) y un inicio de estructura. */
	static CompoundTag chunk(int cx, int cz, long habitado, boolean cama) {
		CompoundTag c = new CompoundTag();
		c.putInt("xPos", cx);
		c.putInt("zPos", cz);
		c.putString("Status", "minecraft:full");
		c.putLong("InhabitedTime", habitado);
		ListTag secs = new ListTag();
		CompoundTag s = new CompoundTag();
		s.putByte("Y", (byte) 4);
		CompoundTag bs = new CompoundTag();
		ListTag pal = new ListTag();
		pal.add(StringTag.valueOf("minecraft:stone"));
		CompoundTag bed = new CompoundTag();
		bed.putString("Name", "minecraft:red_bed");
		pal.add(bed);
		bs.put("palette", pal);
		long[] data = new long[256];      // 4 bits por bloque, 16 por long
		if (cama) {
			int i = (70 - 64) * 256 + 5 * 16 + 3;
			data[i / 16] |= 1L << (i % 16) * 4;
		}
		bs.put("data", new LongArrayTag(data));
		s.put("block_states", bs);
		secs.add(s);
		c.put("sections", secs);
		CompoundTag starts = new CompoundTag();
		CompoundTag st = new CompoundTag();
		st.putString("id", "minecraft:igloo");
		ListTag ch = new ListTag();
		CompoundTag piece = new CompoundTag();
		piece.put("BB", new IntArrayTag(new int[] {cx * 16, 60, cz * 16, cx * 16 + 10, 70, cz * 16 + 10}));
		ch.add(piece);
		st.put("Children", ch);
		starts.put("minecraft:igloo", st);
		CompoundTag invalid = new CompoundTag();
		invalid.putString("id", "INVALID");
		starts.put("minecraft:mansion", invalid);
		CompoundTag structures = new CompoundTag();
		structures.put("starts", starts);
		c.put("structures", structures);
		// alturas: la columna (2, 2) a y = 75 (valor 75 - (-64) + 1 = 140)
		long[] hm = new long[37];
		int col = 2 + 2 * 16;
		hm[col / 7] |= 140L << (col % 7) * 9;
		CompoundTag hms = new CompoundTag();
		hms.put("OCEAN_FLOOR", new LongArrayTag(hm));
		c.put("Heightmaps", hms);
		return c;
	}

	/** Escribe una región con los chunks dados (zlib), como el juego. */
	static void escribir(Path f, Map<Integer, CompoundTag> chunks) throws IOException {
		try (RandomAccessFile out = new RandomAccessFile(f.toFile(), "rw")) {
			out.setLength(0);
			out.write(new byte[Region.SECTOR * 2]);
			int sector = 2;
			for (Map.Entry<Integer, CompoundTag> e : chunks.entrySet()) {
				ByteArrayOutputStream b = new ByteArrayOutputStream();
				try (DataOutputStream d = new DataOutputStream(new DeflaterOutputStream(b))) {
					NbtIo.write(e.getValue(), d);
				}
				byte[] z = b.toByteArray();
				int sectores = (z.length + 5 + Region.SECTOR - 1) / Region.SECTOR;
				out.seek((long) sector * Region.SECTOR);
				out.writeInt(z.length + 1);
				out.writeByte(2);
				out.write(z);
				out.seek(e.getKey() * 4L);
				out.writeInt(sector << 8 | sectores);
				out.seek(Region.SECTOR + e.getKey() * 4L);
				out.writeInt(1234);
				sector += sectores;
			}
			out.setLength((long) sector * Region.SECTOR);
		}
	}

	@Test
	void leeElResumenDeUnChunk() throws IOException {
		Path f = dir.resolve("r.0.0.mca");
		escribir(f, Map.of(Region.indice(3, 4), chunk(3, 4, 77, true)));
		assertEquals(List.of(Region.indice(3, 4)), Region.presentes(Region.cabecera(f)));
		ResumenChunk r = ResumenChunk.de(Region.leer(f, Region.indice(3, 4)).orElseThrow(), -64);
		assertEquals(3, r.cx());
		assertEquals(4, r.cz());
		assertTrue(r.completo());
		assertEquals(77, r.habitado());
		assertEquals(1, r.jugador().length);
		assertArrayEquals(new int[] {3 * 16 + 3, 70, 4 * 16 + 5}, r.bloqueJugador(0));
		assertEquals(Set.of("minecraft:igloo"), r.inicios().keySet());          // el INVALID no cuenta
		assertArrayEquals(new int[] {48, 60, 64, 58, 70, 74}, r.inicios().get("minecraft:igloo").get(0));
		assertEquals(75, r.cimas()[0]);                                         // MUESTRA[0] = (2, 2)
		assertEquals("minecraft:stone", r.bloquesCima()[0]);
		assertTrue(Region.leer(f, 5).isEmpty());
	}

	@Test
	void borrarSoloQuitaLaEntradaDelChunk() throws IOException {
		Path f = dir.resolve("r.-1.2.mca");
		int a = Region.indice(-32, 64), b = Region.indice(-31, 64), c = Region.indice(-1, 95);
		escribir(f, Map.of(a, chunk(-32, 64, 0, false), b, chunk(-31, 64, 0, true), c, chunk(-1, 95, 5, false)));
		byte[] antes = Files.readAllBytes(f);
		assertEquals(1, Region.borrar(f, List.of(b)));
		assertEquals(0, Region.borrar(f, List.of(b)));                          // ya no estaba: idempotente
		assertEquals(List.of(a, c).stream().sorted().toList(), Region.presentes(Region.cabecera(f)));
		assertTrue(Region.leer(f, b).isEmpty());
		assertEquals(-32, Region.leer(f, a).orElseThrow().getIntOr("xPos", 0));
		assertEquals(5, Region.leer(f, c).orElseThrow().getLongOr("InhabitedTime", 0));
		byte[] despues = Files.readAllBytes(f);
		int distintos = 0;
		for (int i = 0; i < antes.length; i++) {
			if (antes[i] != despues[i]) {
				distintos++;
			}
		}
		assertTrue(distintos <= 8, distintos + " bytes cambiados");             // solo las dos entradas de la cabecera
		assertEquals(0, Region.borrar(dir.resolve("r.9.9.mca"), List.of(0)));  // fichero que no existe
	}

	@Test
	void nombresDeRegion() {
		assertArrayEquals(new int[] {-1, 2}, Region.coordenadas(Path.of("r.-1.2.mca")).orElseThrow());
		assertFalse(Region.coordenadas(Path.of("r.1.mcc")).isPresent());
		assertEquals("r.-1.0.mca", Region.nombre(-32 >> 5, 5 >> 5));
		assertEquals(31 + 31 * 32, Region.indice(-1, -1));
	}

	@Test
	void mapaEnTexto() {
		Map<Long, Detector.Clase> c = new java.util.LinkedHashMap<>();
		c.put(ResumenChunk.clave(0, 0), Detector.Clase.CONSTRUCCION);
		c.put(ResumenChunk.clave(1, 0), Detector.Clase.PROTEGIDO);
		c.put(ResumenChunk.clave(2, 0), Detector.Clase.VIRGEN);
		c.put(ResumenChunk.clave(3, 0), Detector.Clase.VIRGEN);
		c.put(ResumenChunk.clave(0, 1), Detector.Clase.NORMAL);
		String m = Mapa.texto(c, Set.of(ResumenChunk.clave(2, 0)), Set.of(ResumenChunk.clave(0, 1)), new int[] {3, 1});
		String[] l = m.split("\n");
		assertEquals("#PRv", l[1]);
		assertEquals("E  S", l[2]);
		assertTrue(l[3].startsWith("# "));
		assertEquals(4 * 2, Mapa.imagen(c, Set.of(), Set.of(), null, 1024, 2).getWidth());
	}
}
