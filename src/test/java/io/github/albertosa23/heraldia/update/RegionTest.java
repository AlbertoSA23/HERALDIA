package io.github.albertosa23.heraldia.update;

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
 * Regiones (.mca) sintéticas con chunks de 26.3: se leen sin el juego ({@link Region}, {@link ChunkSummary}), y borrar
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
	static CompoundTag chunk(int cx, int cz, long inhabited, boolean bedTag) {
		CompoundTag c = new CompoundTag();
		c.putInt("xPos", cx);
		c.putInt("zPos", cz);
		c.putString("Status", "minecraft:full");
		c.putLong("InhabitedTime", inhabited);
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
		if (bedTag) {
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
	static void write(Path f, Map<Integer, CompoundTag> chunks) throws IOException {
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
				int sectors = (z.length + 5 + Region.SECTOR - 1) / Region.SECTOR;
				out.seek((long) sector * Region.SECTOR);
				out.writeInt(z.length + 1);
				out.writeByte(2);
				out.write(z);
				out.seek(e.getKey() * 4L);
				out.writeInt(sector << 8 | sectors);
				out.seek(Region.SECTOR + e.getKey() * 4L);
				out.writeInt(1234);
				sector += sectors;
			}
			out.setLength((long) sector * Region.SECTOR);
		}
	}

	@Test
	void readsChunkSummary() throws IOException {
		Path f = dir.resolve("r.0.0.mca");
		write(f, Map.of(Region.index(3, 4), chunk(3, 4, 77, true)));
		assertEquals(List.of(Region.index(3, 4)), Region.present(Region.header(f)));
		ChunkSummary r = ChunkSummary.of(Region.read(f, Region.index(3, 4)).orElseThrow(), -64);
		assertEquals(3, r.cx());
		assertEquals(4, r.cz());
		assertTrue(r.complete());
		assertEquals(77, r.inhabited());
		assertEquals(1, r.player().length);
		assertArrayEquals(new int[] {3 * 16 + 3, 70, 4 * 16 + 5}, r.playerBlock(0));
		assertEquals(Set.of("minecraft:igloo"), r.structureStarts().keySet());          // el INVALID no cuenta
		assertArrayEquals(new int[] {48, 60, 64, 58, 70, 74}, r.structureStarts().get("minecraft:igloo").get(0));
		assertEquals(75, r.tops()[0]);                                         // MUESTRA[0] = (2, 2)
		assertEquals("minecraft:stone", r.topBlocks()[0]);
		assertTrue(Region.read(f, 5).isEmpty());
	}

	@Test
	void deletingOnlyRemovesChunkEntry() throws IOException {
		Path f = dir.resolve("r.-1.2.mca");
		int a = Region.index(-32, 64), b = Region.index(-31, 64), c = Region.index(-1, 95);
		write(f, Map.of(a, chunk(-32, 64, 0, false), b, chunk(-31, 64, 0, true), c, chunk(-1, 95, 5, false)));
		byte[] before = Files.readAllBytes(f);
		assertEquals(1, Region.delete(f, List.of(b)));
		assertEquals(0, Region.delete(f, List.of(b)));                          // ya no estaba: idempotente
		assertEquals(List.of(a, c).stream().sorted().toList(), Region.present(Region.header(f)));
		assertTrue(Region.read(f, b).isEmpty());
		assertEquals(-32, Region.read(f, a).orElseThrow().getIntOr("xPos", 0));
		assertEquals(5, Region.read(f, c).orElseThrow().getLongOr("InhabitedTime", 0));
		byte[] after = Files.readAllBytes(f);
		int distinct = 0;
		for (int i = 0; i < before.length; i++) {
			if (before[i] != after[i]) {
				distinct++;
			}
		}
		assertTrue(distinct <= 8, distinct + " bytes cambiados");             // solo las dos entradas de la cabecera
		assertEquals(0, Region.delete(dir.resolve("r.9.9.mca"), List.of(0)));  // fichero que no existe
	}

	@Test
	void regionNames() {
		assertArrayEquals(new int[] {-1, 2}, Region.coordinatesOf(Path.of("r.-1.2.mca")).orElseThrow());
		assertFalse(Region.coordinatesOf(Path.of("r.1.mcc")).isPresent());
		assertEquals("r.-1.0.mca", Region.name(-32 >> 5, 5 >> 5));
		assertEquals(31 + 31 * 32, Region.index(-1, -1));
	}

	@Test
	void textMap() {
		Map<Long, Detector.Kind> c = new java.util.LinkedHashMap<>();
		c.put(ChunkSummary.key(0, 0), Detector.Kind.BUILD);
		c.put(ChunkSummary.key(1, 0), Detector.Kind.PROTECTED);
		c.put(ChunkSummary.key(2, 0), Detector.Kind.PRISTINE);
		c.put(ChunkSummary.key(3, 0), Detector.Kind.PRISTINE);
		c.put(ChunkSummary.key(0, 1), Detector.Kind.NORMAL);
		String m = RegionMap.text(c, Set.of(ChunkSummary.key(2, 0)), Set.of(ChunkSummary.key(0, 1)), new int[] {3, 1});
		String[] l = m.split("\n");
		assertEquals("#PRv", l[1]);
		assertEquals("E  S", l[2]);
		assertTrue(l[3].startsWith("# "));
		assertEquals(4 * 2, RegionMap.image(c, Set.of(), Set.of(), null, 1024, 2).getWidth());
	}
}
