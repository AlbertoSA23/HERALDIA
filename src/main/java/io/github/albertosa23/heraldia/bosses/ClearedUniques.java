package io.github.albertosa23.heraldia.bosses;

import com.mojang.serialization.Codec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import java.util.ArrayList;
import java.util.Collection;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

/**
 * Pure logic of the unique structures whose guardian has fallen (option jefes.apagar_generadores), without world classes.
 * Saved per dimension in the {@code heraldia:unicas_vencidas} attachment of each {@code ServerLevel}:
 * <ul>
 * <li>{@code vencidas}: the cleared structures, one key per structure start ({@link #key}): a second death in the same
 * structure (a guardian brought back with /place, another mod) finds it already there and does nothing (idempotent).</li>
 * <li>{@code pendientes}: the template spawners of those structures that were in unloaded chunks when the guardian fell
 * ({@code BlockPos.asLong}); each one is turned off when its chunk loads and then leaves the list.</li>
 * </ul>
 */
public record ClearedUniques(List<String> cleared, List<Long> pending) {
	public static final ClearedUniques EMPTY = new ClearedUniques(List.of(), List.of());
	public static final Codec<ClearedUniques> CODEC = RecordCodecBuilder.create(i -> i.group(
			Codec.STRING.listOf().optionalFieldOf("vencidas", List.of()).forGetter(ClearedUniques::cleared),
			Codec.LONG.listOf().optionalFieldOf("pendientes", List.of()).forGetter(ClearedUniques::pending)).apply(i, ClearedUniques::new));

	public ClearedUniques {
		cleared = List.copyOf(cleared);
		pending = List.copyOf(pending);
	}

	/** Key of a structure start: its structure id and the start chunk ({@code ChunkPos.pack}), e.g. {@code heraldia:unicas/castillo@123}. */
	public static String key(String structure, long startChunk) {
		return structure + "@" + startChunk;
	}

	/** Was this structure already cleared? */
	public boolean has(String key) {
		return cleared.contains(key);
	}

	/** With the structure {@code key} cleared and its {@code stillPending} spawners added (no duplicates). Unchanged if it was already there. */
	public ClearedUniques with(String key, Collection<Long> stillPending) {
		if (has(key)) {
			return this;
		}
		List<String> c = new ArrayList<>(cleared);
		c.add(key);
		Set<Long> p = new LinkedHashSet<>(pending);
		p.addAll(stillPending);
		return new ClearedUniques(c, new ArrayList<>(p));
	}

	/** Without the spawners already handled. */
	public ClearedUniques without(Collection<Long> done) {
		if (done.isEmpty()) {
			return this;
		}
		List<Long> p = new ArrayList<>(pending);
		p.removeAll(done);
		return p.size() == pending.size() ? this : new ClearedUniques(cleared, p);
	}

	/**
	 * The pending spawners inside the chunk {@code (chunkX, chunkZ)}. {@code toChunkX}/{@code toChunkZ} unpack a position (in the
	 * game, {@code BlockPos.getX(l) >> 4}); kept as parameters so the logic is tested without game classes.
	 */
	public List<Long> pendingIn(int chunkX, int chunkZ, java.util.function.LongToIntFunction toChunkX, java.util.function.LongToIntFunction toChunkZ) {
		if (pending.isEmpty()) {
			return List.of();
		}
		List<Long> out = new ArrayList<>(2);
		for (long l : pending) {
			if (toChunkX.applyAsInt(l) == chunkX && toChunkZ.applyAsInt(l) == chunkZ) {
				out.add(l);
			}
		}
		return out;
	}
}
