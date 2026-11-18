package io.github.albertosa23.heraldia.welcome;

import com.mojang.serialization.Codec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import java.util.ArrayList;
import java.util.Collection;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import net.minecraft.world.level.block.state.BlockState;
import org.jspecify.annotations.Nullable;

/**
 * What is saved of the villages' look (Fabric persistent attachment {@code heraldia:reputacion_visible} on the overworld;
 * a world without it starts empty). Per village (its key, {@link io.github.albertosa23.heraldia.quests.Reputation#key}):
 * the reputation of each player who has dealt with it (so the look also counts the players who are offline; the
 * player's own data stays where it was, in their attachment {@code heraldia:encargos}), every block this mod put up there
 * with its exact state (the only blocks it will ever take down) and the spots declined because something else is there
 * now. Immutable: each change gives another value.
 */
public record Shown(Map<String, Village> villages) {
	public static final Shown EMPTY = new Shown(Map.of());

	/** A block this mod placed: world position ({@code BlockPos.asLong}) and exact state. */
	public record Placed(long pos, BlockState state) {
		public static final Codec<Placed> CODEC = RecordCodecBuilder.create(i -> i.group(
				Codec.LONG.fieldOf("pos").forGetter(Placed::pos),
				BlockState.CODEC.fieldOf("bloque").forGetter(Placed::state)).apply(i, Placed::new));
	}

	/** One village: player UUID → reputation (never 0), the blocks placed and the declined spots. */
	public record Village(Map<String, Integer> points, List<Placed> placed, List<Long> declined) {
		public static final Village EMPTY = new Village(Map.of(), List.of(), List.of());
		public static final Codec<Village> CODEC = RecordCodecBuilder.create(i -> i.group(
				Codec.unboundedMap(Codec.STRING, Codec.INT).optionalFieldOf("jugadores", Map.of()).forGetter(Village::points),
				Placed.CODEC.listOf().optionalFieldOf("colocados", List.of()).forGetter(Village::placed),
				Codec.LONG.listOf().optionalFieldOf("rechazados", List.of()).forGetter(Village::declined)).apply(i, Village::new));

		public Village {
			points = Map.copyOf(points);
			placed = List.copyOf(placed);
			declined = List.copyOf(declined);
		}

		/** What was placed at that position, or null. */
		public @Nullable BlockState placedAt(long pos) {
			for (Placed p : placed) {
				if (p.pos() == pos) {
					return p.state();
				}
			}
			return null;
		}

		public boolean isDeclined(long pos) {
			return declined.contains(pos);
		}

		public Village withPoints(String player, int value) {
			Map<String, Integer> m = new LinkedHashMap<>(points);
			if (value == 0) {
				m.remove(player);
			} else {
				m.put(player, value);
			}
			return new Village(m, placed, declined);
		}

		/** The village after a reconciliation: what was placed and removed, and the spots declined now. */
		public Village with(Map<Long, BlockState> added, Collection<Long> removed, Collection<Long> newlyDeclined) {
			if (added.isEmpty() && removed.isEmpty() && newlyDeclined.isEmpty()) {
				return this;
			}
			Set<Long> gone = new java.util.HashSet<>(removed);
			gone.addAll(newlyDeclined);
			List<Placed> l = new ArrayList<>();
			for (Placed p : placed) {
				if (!gone.contains(p.pos()) && !added.containsKey(p.pos())) {
					l.add(p);
				}
			}
			added.forEach((pos, state) -> l.add(new Placed(pos, state)));
			List<Long> d = new ArrayList<>(declined);
			for (long pos : newlyDeclined) {
				if (!d.contains(pos)) {
					d.add(pos);
				}
			}
			return new Village(points, l, d);
		}
	}

	public static final Codec<Shown> CODEC = RecordCodecBuilder.create(i -> i.group(
			Codec.unboundedMap(Codec.STRING, Village.CODEC).optionalFieldOf("aldeas", Map.of()).forGetter(Shown::villages))
			.apply(i, Shown::new));

	public Shown {
		villages = Map.copyOf(villages);
	}

	public Village village(String key) {
		return villages.getOrDefault(key, Village.EMPTY);
	}

	public Shown with(String key, Village v) {
		Map<String, Village> m = new HashMap<>(villages);
		if (v.points().isEmpty() && v.placed().isEmpty() && v.declined().isEmpty()) {
			m.remove(key);
		} else {
			m.put(key, v);
		}
		return new Shown(m);
	}

	/**
	 * The record after a player's reputation is synchronized: their points with every village they have dealt with
	 * ({@code reputation}, as in their own data). Returns the keys of the villages whose points changed through {@code changed}.
	 */
	public Shown sync(String player, Map<String, Integer> reputation, Collection<String> changed) {
		Shown s = this;
		for (Map.Entry<String, Integer> e : reputation.entrySet()) {
			Village v = s.village(e.getKey());
			if (v.points().getOrDefault(player, 0).intValue() != e.getValue()) {
				s = s.with(e.getKey(), v.withPoints(player, e.getValue()));
				changed.add(e.getKey());
			}
		}
		return s;
	}
}
