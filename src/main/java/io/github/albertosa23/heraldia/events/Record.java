package io.github.albertosa23.heraldia.events;

import com.mojang.serialization.Codec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import java.util.ArrayList;
import java.util.Collection;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import net.minecraft.world.level.block.state.BlockState;

/**
 * What is saved of the village events (Fabric persistent attachment {@code heraldia:eventos_aldea} on the overworld; a
 * world without it starts empty). Only two things:
 * <ul>
 * <li>every block an event has put up and not taken down yet, with its exact state: the only blocks this system will ever
 * remove. It is written <i>before</i> anything is placed and an entry is only dropped once its block is gone or is no
 * longer ours, so a crash or a chunk that unloads mid-event leaves nothing behind: what is left is taken down when its
 * chunk is next loaded (or at the next start);</li>
 * <li>per village (its key, {@code cx,cz} of its start chunk), when its last event ended and which one it was, so a
 * restart does not bring the next one forward.</li>
 * </ul>
 * The entities are never saved here: they carry the tag {@code heraldia_evento}, and any that loads without its event
 * running is removed. Immutable: each change gives another value.
 */
public record Record(List<Placed> placed, Map<String, Village> villages) {
	public static final Record EMPTY = new Record(List.of(), Map.of());

	/** A block an event placed: world position ({@code BlockPos.asLong}) and exact state. */
	public record Placed(long pos, BlockState state) {
		public static final Codec<Placed> CODEC = RecordCodecBuilder.create(i -> i.group(
				Codec.LONG.fieldOf("pos").forGetter(Placed::pos),
				BlockState.CODEC.fieldOf("bloque").forGetter(Placed::state)).apply(i, Placed::new));
	}

	/** A village's last event: the game time it ended and its kind. */
	public record Village(long ended, String kind) {
		public static final Codec<Village> CODEC = RecordCodecBuilder.create(i -> i.group(
				Codec.LONG.fieldOf("fin").forGetter(Village::ended),
				Codec.STRING.optionalFieldOf("tipo", "").forGetter(Village::kind)).apply(i, Village::new));
	}

	public static final Codec<Record> CODEC = RecordCodecBuilder.create(i -> i.group(
			Placed.CODEC.listOf().optionalFieldOf("colocados", List.of()).forGetter(Record::placed),
			Codec.unboundedMap(Codec.STRING, Village.CODEC).optionalFieldOf("aldeas", Map.of()).forGetter(Record::villages))
			.apply(i, Record::new));

	public Record {
		placed = List.copyOf(placed);
		villages = Map.copyOf(villages);
	}

	public boolean isEmpty() {
		return placed.isEmpty() && villages.isEmpty();
	}

	/** The record with these blocks added (they are about to be placed). */
	public Record with(Collection<Placed> added) {
		if (added.isEmpty()) {
			return this;
		}
		List<Placed> l = new ArrayList<>(placed);
		l.addAll(added);
		return new Record(l, villages);
	}

	/** The record without the blocks at these positions (taken down, or no longer ours). */
	public Record without(Collection<Long> gone) {
		if (gone.isEmpty()) {
			return this;
		}
		Set<Long> g = new HashSet<>(gone);
		List<Placed> l = new ArrayList<>();
		for (Placed p : placed) {
			if (!g.contains(p.pos())) {
				l.add(p);
			}
		}
		return new Record(l, villages);
	}

	/** The record after a village's event ended at {@code time}. */
	public Record ended(String village, long time, String kind) {
		Map<String, Village> m = new HashMap<>(villages);
		m.put(village, new Village(time, kind));
		return new Record(placed, m);
	}

	public Village village(String key) {
		return villages.get(key);
	}
}
