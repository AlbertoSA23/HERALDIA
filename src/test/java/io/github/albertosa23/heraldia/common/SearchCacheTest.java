package io.github.albertosa23.heraldia.common;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.mojang.serialization.JsonOps;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import java.io.ByteArrayOutputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.function.IntBinaryOperator;
import net.minecraft.nbt.NbtIo;
import net.minecraft.nbt.NbtOps;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.Tag;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * The world's search memory (pure part): it serves exactly what was stored, stays bounded, survives a save and a load with
 * the same stamp, and is discarded whole with another one (another option value, also through a changed default).
 */
class SearchCacheTest {
	@TempDir
	Path dir;

	@AfterEach
	void restore() {
		HeraldiaConfig.load(null);
	}

	@Test
	void packsEveryChunkOfTheWorldAndEveryValue() {
		int[] coords = {0, 1, -1, 12345, -12345, 1_874_999, -1_874_999, SearchCache.MAX_CHUNK, -SearchCache.MAX_CHUNK};
		int[] values = {0, 1, 72, SearchCache.MAX_VALUE};
		for (int x : coords) {
			for (int z : coords) {
				for (int v : values) {
					long p = SearchCache.pack(x, z, v);
					assertEquals(x, SearchCache.unpackX(p));
					assertEquals(z, SearchCache.unpackZ(p));
					assertEquals(v, SearchCache.unpackValue(p));
				}
			}
		}
	}

	@Test
	void servesWhatWasStoredAndNothingElse() {
		SearchCache c = new SearchCache("s");
		assertEquals(SearchCache.MISSING, c.get("a", 3, 4));
		c.put("a", 3, 4, 0);                         // a "no" is an answer too (the searches that find nothing)
		c.put("a", -3, 4, 1);
		c.put("b", 3, 4, 7);
		assertEquals(0, c.get("a", 3, 4));
		assertEquals(1, c.get("a", -3, 4));
		assertEquals(7, c.get("b", 3, 4));
		assertEquals(SearchCache.MISSING, c.get("a", 4, 3));
		assertEquals(SearchCache.MISSING, c.get("c", 3, 4));
		assertTrue(c.contains("a", 3, 4));
		assertFalse(c.contains("a", 4, 3));
		assertEquals(3, c.size());
		assertArrayEquals(new long[] {3, 3}, c.counts(), "hits and misses");
	}

	/** The structures of a structure_set share one answer per chunk: each slot comes back on its own, unknown until stored. */
	@Test
	void slotsKeepEachStructureOfASetApart() {
		SearchCache c = new SearchCache("s");
		for (int i = 0; i < SearchCache.SLOTS; i++) {
			assertEquals(SearchCache.MISSING, c.getSlot("set", 5, -5, i));
		}
		c.putSlot("set", 5, -5, 3, true);
		c.putSlot("set", 5, -5, 0, false);
		c.putSlot("set", 5, -5, 9, true);
		assertEquals(1, c.getSlot("set", 5, -5, 3));
		assertEquals(0, c.getSlot("set", 5, -5, 0));
		assertEquals(1, c.getSlot("set", 5, -5, 9));
		assertEquals(SearchCache.MISSING, c.getSlot("set", 5, -5, 1), "another structure of the set: not asked yet");
		assertEquals(SearchCache.MISSING, c.getSlot("set", 5, -6, 3), "another chunk");
		assertEquals(SearchCache.MISSING, c.peekSlot("set", 5, -5, SearchCache.SLOTS), "out of the slots");
		assertEquals(1, c.size(), "one answer for the whole set");
		c.putSlot("set", 5, -5, 3, false);
		assertEquals(0, c.getSlot("set", 5, -5, 3), "rewritten");
		assertEquals(1, c.getSlot("set", 5, -5, 9), "the others stay");
		assertTrue(c.peek("set", 5, -5) <= SearchCache.MAX_VALUE);
	}

	@Test
	void throughTheSlotsTheAnswerIsAlwaysTheComputedOne() {
		SearchCache c = new SearchCache("s", 32);
		Random r = new Random(9);
		for (int i = 0; i < 20_000; i++) {
			int x = r.nextInt(30) - 15, z = r.nextInt(30) - 15, slot = r.nextInt(SearchCache.SLOTS);
			boolean pure = ((x * 7 + z * 13 + slot * 5) & 4) != 0;
			int v = c.getSlot("set" + (x & 1), x, z, slot);
			if (v == SearchCache.MISSING) {
				c.putSlot("set" + (x & 1), x, z, slot, pure);
			} else {
				assertEquals(pure ? 1 : 0, v);
			}
			assertTrue(c.size() <= 32);
		}
	}

	@Test
	void doesNotStoreWhatDoesNotFit() {
		SearchCache c = new SearchCache("s");
		c.put("a", SearchCache.MAX_CHUNK + 1, 0, 1);
		c.put("a", 0, -SearchCache.MAX_CHUNK - 1, 1);
		c.put("a", 0, 0, SearchCache.MAX_VALUE + 1);
		c.put("a", 0, 0, -1);
		assertEquals(0, c.size());
		assertFalse(c.dirty());
	}

	/**
	 * The property that matters: a search that asks through the memory gets exactly what it would compute, even when the
	 * memory is much smaller than what is asked and answers come and go (random queries, a pure function).
	 */
	@Test
	void throughTheMemoryTheAnswerIsAlwaysTheComputedOne() {
		IntBinaryOperator pure = (x, z) -> Math.floorMod(x * 31 + z * 17 + (x ^ z), 5);      // 0..4, like an index in a group
		SearchCache c = new SearchCache("s", 64);
		Random r = new Random(42);
		int served = 0;
		for (int i = 0; i < 20_000; i++) {
			int x = r.nextInt(40) - 20, z = r.nextInt(40) - 20;
			String key = "k" + r.nextInt(3);
			int v = c.get(key, x, z);
			if (v == SearchCache.MISSING) {
				v = pure.applyAsInt(x, z);
				c.put(key, x, z, v);
			} else {
				served++;
			}
			assertEquals(pure.applyAsInt(x, z), v);
			assertTrue(c.size() <= 64, "bounded: " + c.size());
		}
		assertTrue(served > 0, "the memory served something");
	}

	@Test
	void isBoundedAndKeepsWhatIsUsedAgain() {
		SearchCache c = new SearchCache("s", 8);
		c.put("a", 0, 0, 1);
		for (int i = 1; i < 100; i++) {
			c.put("a", i, 0, 0);
			assertEquals(1, c.get("a", 0, 0), "used on every round: it never goes");
			assertTrue(c.size() <= 8);
		}
		assertEquals(SearchCache.MISSING, c.get("a", 1, 0), "an old answer nobody asked for again goes");
		assertTrue(c.save().size() <= 8);
	}

	@Test
	void theDefaultCapacityIsTheDocumentedOneAndItsWorstCaseSize() throws IOException {
		assertEquals(16_384, SearchCache.MAX_ENTRIES);
		SearchCache c = new SearchCache("x".repeat(64));
		Random r = new Random(1);
		for (int i = 0; c.size() < SearchCache.MAX_ENTRIES && i < 1_000_000; i++) {
			// many keys (structures), coordinates all over the world: what compresses worst
			c.put("minecraft:overworld|p|heraldia:unicas/estructura_" + r.nextInt(200), r.nextInt(3_000_000) - 1_500_000,
					r.nextInt(3_000_000) - 1_500_000, r.nextInt(2));
		}
		assertEquals(SearchCache.MAX_ENTRIES, c.size());
		Tag tag = SearchCache.Saved.CODEC.encodeStart(NbtOps.INSTANCE, c.save()).getOrThrow();
		ByteArrayOutputStream raw = new ByteArrayOutputStream();
		NbtIo.write((CompoundTag) tag, new DataOutputStream(raw));
		Path f = dir.resolve("m.dat");
		NbtIo.writeCompressed((CompoundTag) tag, f);
		long compressed = Files.size(f);
		// docs/CONFIGURATION.md ("Search memory"): 128 KiB of answers plus the keys at most; on disk, compressed, less
		assertTrue(raw.size() <= 128 * 1024 + 200 * 80, "uncompressed " + raw.size());
		assertTrue(compressed <= raw.size(), "compressed " + compressed);
		System.out.println("SearchCacheTest: worst case " + raw.size() + " bytes uncompressed, " + compressed + " compressed");
	}

	@Test
	void saveAndLoadWithTheSameStampGiveTheSameAnswers() {
		SearchCache c = new SearchCache("s");
		Map<String, Integer> expected = new HashMap<>();
		Random r = new Random(7);
		for (int i = 0; i < 2000; i++) {
			int x = r.nextInt(2000) - 1000, z = r.nextInt(2000) - 1000, v = r.nextInt(73);
			String k = "minecraft:overworld|v|heraldia:g" + r.nextInt(5);
			c.put(k, x, z, v);
			expected.put(k + "@" + x + "," + z, v);
		}
		assertTrue(c.dirty());
		SearchCache.Saved saved = c.save();
		assertFalse(c.dirty());
		// through NBT, as in the world
		SearchCache.Saved read = SearchCache.Saved.CODEC.parse(NbtOps.INSTANCE,
				SearchCache.Saved.CODEC.encodeStart(NbtOps.INSTANCE, saved).getOrThrow()).getOrThrow();
		assertTrue(SearchCache.compatible(read, "s"));
		SearchCache back = SearchCache.load(read, "s");
		assertEquals(expected.size(), back.size());
		expected.forEach((k, v) -> {
			String[] p = k.split("@");
			String[] xz = p[1].split(",");
			assertEquals(v, back.get(p[0], Integer.parseInt(xz[0]), Integer.parseInt(xz[1])), k);
		});
		assertFalse(back.dirty(), "nothing changed since it was read");
		// the save is stable: the same answers, the same data
		assertEquals(SearchCache.Saved.CODEC.encodeStart(JsonOps.INSTANCE, back.save()).getOrThrow(),
				SearchCache.Saved.CODEC.encodeStart(JsonOps.INSTANCE, saved).getOrThrow());
	}

	@Test
	void anotherStampOrFormatDiscardsEverything() {
		SearchCache c = new SearchCache("before");
		c.put("a", 1, 1, 1);
		SearchCache.Saved saved = c.save();
		assertFalse(SearchCache.compatible(saved, "after"));
		assertEquals(0, SearchCache.load(saved, "after").size());
		SearchCache.Saved otherFormat = new SearchCache.Saved(SearchCache.FORMAT + 1, "before", saved.entries());
		assertEquals(0, SearchCache.load(otherFormat, "before").size());
		assertEquals(0, SearchCache.load(null, "before").size());
		SearchCache discarded = SearchCache.load(saved, "after");
		discarded.forget();
		assertTrue(discarded.dirty(), "the next save replaces the discarded one");
		assertEquals(0, discarded.save().size());
	}

	@Test
	void theStampDependsOnEveryPartAndItsOrder() {
		String a = SearchCache.stamp(List.of("semilla=1", "mod heraldia@0.1.0"));
		assertEquals(a, SearchCache.stamp(List.of("semilla=1", "mod heraldia@0.1.0")));
		assertNotEquals(a, SearchCache.stamp(List.of("semilla=2", "mod heraldia@0.1.0")));
		assertNotEquals(a, SearchCache.stamp(List.of("mod heraldia@0.1.0", "semilla=1")));
		assertNotEquals(SearchCache.stamp(List.of("ab", "c")), SearchCache.stamp(List.of("a", "bc")), "the parts do not run together");
	}

	/**
	 * The generation options enter the stamp with their value in use: a world saved when medianas.frecuencia_porcentaje
	 * was 100 by default (not written in the file) gets another stamp now that the default is 60, and the memory of its old
	 * searches is not served (the grid of the medium structures moved); writing 100 by hand gives back the old stamp.
	 */
	@Test
	void aChangedDefaultChangesTheStamp() throws IOException {
		String key = "medianas.frecuencia_porcentaje";
		List<String> now = SearchCaches.optionParts(HeraldiaConfig.load(null));
		assertTrue(now.contains("opcion " + key + "=" + HeraldiaConfig.defaults().get(key).getAsString()));
		Path f = dir.resolve("heraldia.json");
		Files.writeString(f, "{\"version\": 3, \"medianas\": {\"frecuencia_porcentaje\": 100}}");
		List<String> old = SearchCaches.optionParts(HeraldiaConfig.load(f));
		assertNotEquals(SearchCache.stamp(now), SearchCache.stamp(old));
		Files.writeString(f, "{\"version\": 3, \"medianas\": {\"frecuencia_porcentaje\": " + HeraldiaConfig.defaults().get(key).getAsString() + "}}");
		assertEquals(SearchCache.stamp(now), SearchCache.stamp(SearchCaches.optionParts(HeraldiaConfig.load(f))),
				"the default written by hand: the same value in use, the same answers");
		// every generation option is in it, none of the gameplay ones
		assertTrue(now.stream().anyMatch(p -> p.startsWith("opcion aldeas.separacion_bloques=")));
		assertTrue(now.stream().anyMatch(p -> p.startsWith("opcion minas.")));
		assertTrue(now.stream().noneMatch(p -> p.startsWith("opcion dificultad.") || p.startsWith("opcion botin.")));
	}

	@Test
	void anyGenerationOptionChangesTheStamp() throws IOException {
		String base = SearchCache.stamp(SearchCaches.optionParts(HeraldiaConfig.load(null)));
		Path f = dir.resolve("heraldia.json");
		for (String json : List.of("{\"version\": 3, \"aldeas\": {\"separacion_bloques\": 2000}}",
				"{\"version\": 3, \"minas\": {\"entradas\": {\"activado\": false}}}",
				"{\"version\": 3, \"unicas\": {\"distancia_minima\": {\"bloques\": 1500}}}")) {
			Files.writeString(f, json);
			assertNotEquals(base, SearchCache.stamp(SearchCaches.optionParts(HeraldiaConfig.load(f))), json);
		}
		Files.writeString(f, "{\"version\": 3, \"dificultad\": {\"nivel\": \"dificil\"}}");
		assertEquals(base, SearchCache.stamp(SearchCaches.optionParts(HeraldiaConfig.load(f))), "a gameplay option does not");
	}

	@Test
	void theDatapacksFolderCountsEveryFile() throws IOException {
		assertEquals("", SearchCaches.datapacksFolder(dir.resolve("none")));
		Path d = dir.resolve("datapacks");
		Files.createDirectories(d.resolve("p/data"));
		Files.writeString(d.resolve("p/data/a.json"), "{}");
		String one = SearchCaches.datapacksFolder(d);
		Files.writeString(d.resolve("p/data/a.json"), "{\"spacing\": 12}");
		assertNotEquals(one, SearchCaches.datapacksFolder(d), "an edited datapack keeps its name");
	}
}
