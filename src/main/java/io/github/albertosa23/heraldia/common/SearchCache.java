package io.github.albertosa23.heraldia.common;

import com.mojang.serialization.Codec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import it.unimi.dsi.fastutil.longs.Long2IntMap;
import it.unimi.dsi.fastutil.longs.Long2IntOpenHashMap;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.LongStream;
import net.minecraft.world.level.ChunkPos;

/**
 * Pure part of the world's search memory ({@link SearchCaches} does the game side): the answer to "would this structure
 * start in this chunk?" (or "which structure of this grid would?") for the chunks already asked, kept across restarts.
 * <p>What is stored are only values of a pure function: the structure prediction of /locate and the maps
 * (StructureCheck.canCreateStructure with Heraldia's rules) and the search of /heraldia info nearby and the Chronicle folios
 * (InfoCommand.firstViable). With the same seed, configuration, mods, datapacks and .jar they always give the same value,
 * so serving it from here gives exactly the same result as computing it again; what depends on the saved chunks (what
 * is already generated) is still read every time by whoever searches. Positive and negative answers are both kept:
 * a search that finds nothing walks the whole grid, and its "no" are what it would repeat.
 * <p>{@link #stamp}: a hash of everything that decides those values. A memory saved with another stamp is discarded whole on
 * load: a changed option (also through a changed default: the stamp uses the values in use), mod, datapack or .jar never
 * serves an old answer.
 * <p>Bounded: two generations of at most {@link #MAX_ENTRIES}/2 answers each (the young one takes the new answers and
 * the old answers that are used again; when it is full it becomes the old one and the previous old one goes): at most
 * {@link #MAX_ENTRIES} answers in memory and in the save, 8 bytes each (a long per answer: chunk and value).
 * Thread-safe (the searches of /heraldia info run off the server thread): one lock, only around map operations.
 */
public final class SearchCache {
	/**
	 * Answers kept at most (in memory and in the world's save): 8 bytes each, 128 KiB at most plus the keys (measured in
	 * SearchCacheTest: 141 KB uncompressed and 115 KB compressed in the worst case, every answer in a different place of the
	 * world). A /locate stores some hundreds (the 4 searches of generation_cost.py, 1,115).
	 */
	public static final int MAX_ENTRIES = 1 << 14;
	/** Returned by {@link #get} when the answer is not stored. */
	public static final int MISSING = Integer.MIN_VALUE;
	/** Largest storable value (20 bits). */
	public static final int MAX_VALUE = (1 << 20) - 1;
	/** Chunk coordinates that fit in an answer (22 bits with sign: the whole world, whose border is at ±1,875,000 chunks). */
	static final int MAX_CHUNK = (1 << 21) - 1;
	/** Format of the saved memory; a different one is discarded on load. */
	public static final int FORMAT = 1;

	/** What is saved in the world: the format, the stamp and, per key, the packed answers ({@link #pack}). */
	public record Saved(int format, String stamp, Map<String, long[]> entries) {
		public static final Codec<Saved> CODEC = RecordCodecBuilder.create(i -> i.group(
				Codec.INT.fieldOf("formato").forGetter(Saved::format),
				Codec.STRING.fieldOf("sello").forGetter(Saved::stamp),
				Codec.unboundedMap(Codec.STRING, Codec.LONG_STREAM.xmap(LongStream::toArray, Arrays::stream))
						.fieldOf("respuestas").forGetter(Saved::entries)
		).apply(i, Saved::new));

		/** Number of answers. */
		public int size() {
			return entries.values().stream().mapToInt(a -> a.length).sum();
		}
	}

	private final String stamp;
	private final int capacity;
	private Map<String, Long2IntOpenHashMap> young = new HashMap<>(), old = new HashMap<>();
	private int youngSize, oldSize;
	private boolean dirty;
	private long hits, misses;

	/** An empty memory for that stamp, with {@link #MAX_ENTRIES} answers at most. */
	public SearchCache(String stamp) {
		this(stamp, MAX_ENTRIES);
	}

	/** Public for the tests: with {@code capacity} answers at most (even, at least 2). */
	public SearchCache(String stamp, int capacity) {
		if (capacity < 2) {
			throw new IllegalArgumentException("capacity " + capacity);
		}
		this.stamp = stamp;
		this.capacity = capacity & ~1;
	}

	public String stamp() {
		return stamp;
	}

	/**
	 * The memory to use from a saved one: its answers if it has this format and stamp; otherwise an empty one (the
	 * saved one was made with other rules: none of its answers can be trusted).
	 */
	public static SearchCache load(Saved saved, String stamp) {
		SearchCache c = new SearchCache(stamp);
		if (saved == null || saved.format() != FORMAT || !saved.stamp().equals(stamp)) {
			return c;
		}
		int room = c.capacity;
		for (Map.Entry<String, long[]> e : saved.entries().entrySet()) {
			for (long packed : e.getValue()) {
				if (room-- <= 0) {
					return c;
				}
				// everything read goes to the young generation until it is half full, the rest to the old one
				Map<String, Long2IntOpenHashMap> gen = c.youngSize < c.capacity / 2 ? c.young : c.old;
				Long2IntOpenHashMap m = gen.computeIfAbsent(e.getKey(), k -> newMap());
				if (m.put(ChunkPos.pack(unpackX(packed), unpackZ(packed)), unpackValue(packed)) == MISSING) {
					if (gen == c.young) {
						c.youngSize++;
					} else {
						c.oldSize++;
					}
				}
			}
		}
		return c;
	}

	/** Would {@link #load} keep the saved answers? (For the log.) */
	public static boolean compatible(Saved saved, String stamp) {
		return saved != null && saved.format() == FORMAT && saved.stamp().equals(stamp);
	}

	/** The stored answer for key and chunk, or {@link #MISSING}. */
	public synchronized int get(String key, int chunkX, int chunkZ) {
		int v = lookup(key, ChunkPos.pack(chunkX, chunkZ));
		if (v == MISSING) {
			misses++;
		} else {
			hits++;
		}
		return v;
	}

	/** The stored value (an answer used again goes to the young generation), without counting it. */
	private int lookup(String key, long pos) {
		Long2IntOpenHashMap y = young.get(key);
		int v = y == null ? MISSING : y.get(pos);
		if (v == MISSING) {
			Long2IntOpenHashMap o = old.get(key);
			v = o == null ? MISSING : o.get(pos);
			if (v != MISSING) {
				o.remove(pos);           // used again: to the young generation
				oldSize--;
				putYoung(key, pos, v);
			}
		}
		return v;
	}

	/**
	 * Yes/no answers packed in one value (the structures of a structure_set, which share the chunk: one answer per cell
	 * instead of one per structure): {@value #SLOTS} slots of 2 bits, "known" and the answer.
	 */
	public static final int SLOTS = 10;

	/** The yes/no answer of a slot (1 yes, 0 no) or {@link #MISSING}. */
	public synchronized int getSlot(String key, int chunkX, int chunkZ, int slot) {
		int v = lookup(key, ChunkPos.pack(chunkX, chunkZ));
		int out = slotOf(v, slot);
		if (out == MISSING) {
			misses++;
		} else {
			hits++;
		}
		return out;
	}

	/** The same without counting it as used or moving it. */
	public synchronized int peekSlot(String key, int chunkX, int chunkZ, int slot) {
		return slotOf(peek(key, chunkX, chunkZ), slot);
	}

	/** Stores the yes/no answer of a slot, keeping the others of the same value. */
	public synchronized void putSlot(String key, int chunkX, int chunkZ, int slot, boolean value) {
		if (slot < 0 || slot >= SLOTS) {
			return;
		}
		int v = peek(key, chunkX, chunkZ);
		int bits = (v == MISSING ? 0 : v) & ~(3 << 2 * slot) | (value ? 3 : 2) << 2 * slot;
		put(key, chunkX, chunkZ, bits);
	}

	static int slotOf(int v, int slot) {
		if (v == MISSING || slot < 0 || slot >= SLOTS || (v >> 2 * slot & 2) == 0) {
			return MISSING;
		}
		return v >> 2 * slot & 1;
	}

	/** The stored answer or {@link #MISSING}, without counting it as used or moving it. */
	public synchronized int peek(String key, int chunkX, int chunkZ) {
		long pos = ChunkPos.pack(chunkX, chunkZ);
		Long2IntOpenHashMap y = young.get(key), o = old.get(key);
		int v = y == null ? MISSING : y.get(pos);
		return v != MISSING || o == null ? v : o.get(pos);
	}

	/** Is the answer stored? (Without counting it as used or moving it.) */
	public boolean contains(String key, int chunkX, int chunkZ) {
		return peek(key, chunkX, chunkZ) != MISSING;
	}

	/** Marks it as changed: the next save writes it even if empty (it replaces a discarded memory). */
	public synchronized void forget() {
		dirty = true;
	}

	/** Stores an answer (0..{@link #MAX_VALUE}); outside the world's limits it is not stored. */
	public synchronized void put(String key, int chunkX, int chunkZ, int value) {
		if (value < 0 || value > MAX_VALUE || Math.abs(chunkX) > MAX_CHUNK || Math.abs(chunkZ) > MAX_CHUNK) {
			return;
		}
		long pos = ChunkPos.pack(chunkX, chunkZ);
		Long2IntOpenHashMap y = young.get(key);
		if (y != null && y.get(pos) == value) {
			return;
		}
		Long2IntOpenHashMap o = old.get(key);
		if (o != null && o.remove(pos) != MISSING) {
			oldSize--;
		}
		putYoung(key, pos, value);
	}

	private void putYoung(String key, long pos, int value) {
		if (youngSize >= capacity / 2) {       // the young generation is full: it becomes the old one
			old = young;
			oldSize = youngSize;
			young = new HashMap<>();
			youngSize = 0;
		}
		if (young.computeIfAbsent(key, k -> newMap()).put(pos, value) == MISSING) {
			youngSize++;
		}
		dirty = true;
	}

	private static Long2IntOpenHashMap newMap() {
		Long2IntOpenHashMap m = new Long2IntOpenHashMap();
		m.defaultReturnValue(MISSING);
		return m;
	}

	/** Answers in memory. */
	public synchronized int size() {
		return youngSize + oldSize;
	}

	/** Has something changed since the last {@link #save}? */
	public synchronized boolean dirty() {
		return dirty;
	}

	/** {hits, misses} since it was created. */
	public synchronized long[] counts() {
		return new long[] {hits, misses};
	}

	/** What to save (and marks it as saved): every answer, at most {@link #MAX_ENTRIES}, keys in order. */
	public synchronized Saved save() {
		Map<String, Long2IntOpenHashMap> all = new HashMap<>();
		for (Map<String, Long2IntOpenHashMap> gen : List.of(old, young)) {   // young last: it wins
			gen.forEach((k, m) -> all.computeIfAbsent(k, x -> newMap()).putAll(m));
		}
		Map<String, long[]> out = new LinkedHashMap<>();
		all.keySet().stream().sorted().forEach(k -> {
			long[] a = new long[all.get(k).size()];
			int i = 0;
			for (Long2IntMap.Entry e : all.get(k).long2IntEntrySet()) {
				a[i++] = pack(ChunkPos.getX(e.getLongKey()), ChunkPos.getZ(e.getLongKey()), e.getIntValue());
			}
			Arrays.sort(a);
			out.put(k, a);
		});
		dirty = false;
		return new Saved(FORMAT, stamp, out);
	}

	/** An answer in a long: x (22 bits), z (22 bits) and the value (20 bits). */
	static long pack(int chunkX, int chunkZ, int value) {
		return ((long) (chunkX & 0x3FFFFF) << 42) | ((long) (chunkZ & 0x3FFFFF) << 20) | (value & MAX_VALUE);
	}

	static int unpackX(long packed) {
		return (int) (packed >> 42);                   // arithmetic shift: the sign comes back
	}

	static int unpackZ(long packed) {
		return (int) ((packed << 22) >> 42);
	}

	static int unpackValue(long packed) {
		return (int) (packed & MAX_VALUE);
	}

	/** The stamp of some parts (in order): a SHA-256 in hex. The same parts, the same stamp. */
	public static String stamp(List<String> parts) {
		try {
			MessageDigest md = MessageDigest.getInstance("SHA-256");
			for (String p : parts) {
				byte[] b = p.getBytes(StandardCharsets.UTF_8);
				md.update(new byte[] {(byte) (b.length >>> 24), (byte) (b.length >>> 16), (byte) (b.length >>> 8), (byte) b.length});
				md.update(b);
			}
			return HexFormat.of().formatHex(md.digest());
		} catch (NoSuchAlgorithmException e) {
			throw new IllegalStateException(e);
		}
	}
}
