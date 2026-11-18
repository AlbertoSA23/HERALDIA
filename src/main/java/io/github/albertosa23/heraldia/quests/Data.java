package io.github.albertosa23.heraldia.quests;

import com.mojang.serialization.Codec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * What is saved for each player (Fabric persistent attachment in their .dat, not sent to the client): the accepted
 * quests, the reputation with each village, how many they have delivered and the ids of the last delivered ones (so the
 * same one is not paid twice). Immutable: each change gives another value (and {@code setAttached}).
 */
public record Data(List<Active> active, Map<String, Integer> reputation, int completed, List<String> finished) {
	/** Quests accepted at once, at most. */
	public static final int MAX_ACTIVE = 5;
	/** Ids of delivered quests that are remembered (the most recent): more than enough for several periods of all visited villages. */
	public static final int MAX_DONE = 200;
	public static final Data EMPTY = new Data(List.of(), Map.of(), 0, List.of());

	/** An accepted quest and whether what it asks for is already met (bring quests are checked on delivery). */
	public record Active(Quest quest, boolean met) {
		public static final Codec<Active> CODEC = RecordCodecBuilder.create(i -> i.group(
				Quest.CODEC.fieldOf("encargo").forGetter(Active::quest),
				Codec.BOOL.optionalFieldOf("cumplido", false).forGetter(Active::met)).apply(i, Active::new));
	}

	public static final Codec<Data> CODEC = RecordCodecBuilder.create(i -> i.group(
			Active.CODEC.listOf().optionalFieldOf("activos", List.of()).forGetter(Data::active),
			Codec.unboundedMap(Codec.STRING, Codec.INT).optionalFieldOf("reputacion", Map.of()).forGetter(Data::reputation),
			Codec.INT.optionalFieldOf("completados", 0).forGetter(Data::completed),
			Codec.STRING.listOf().optionalFieldOf("hechos", List.of()).forGetter(Data::finished)).apply(i, Data::new));

	public Data {
		active = List.copyOf(active);
		reputation = Map.copyOf(reputation);
		finished = List.copyOf(finished);
	}

	public int reputation(String village) {
		return reputation.getOrDefault(village, 0);
	}

	public Reputation.Tier tier(String village) {
		return Reputation.tier(reputation(village));
	}

	/** Is it accepted (by id)? */
	public boolean has(String id) {
		return active.stream().anyMatch(a -> a.quest().id().equals(id));
	}

	public boolean done(String id) {
		return finished.contains(id);
	}

	/** Why it cannot be accepted (key of the reason) or null if it can. */
	public String notAcceptable(Quest e) {
		if (done(e.id())) {
			return "hecho";
		}
		if (has(e.id())) {
			return "ya";
		}
		if (active.size() >= MAX_ACTIVE) {
			return "lleno";
		}
		return null;
	}

	public Data accept(Quest e) {
		List<Active> l = new ArrayList<>(active);
		l.add(new Active(e, false));
		return new Data(l, reputation, completed, finished);
	}

	/** Removes accepted quest number {@code i} (0..); no change if it does not exist. */
	public Data abandon(int i) {
		if (i < 0 || i >= active.size()) {
			return this;
		}
		List<Active> l = new ArrayList<>(active);
		l.remove(i);
		return new Data(l, reputation, completed, finished);
	}

	/** Marks as met the accepted quests that meet the condition. */
	public Data complete(java.util.function.Predicate<Quest> cond) {
		boolean changes = false;
		List<Active> l = new ArrayList<>(active.size());
		for (Active a : active) {
			if (!a.met() && cond.test(a.quest())) {
				l.add(new Active(a.quest(), true));
				changes = true;
			} else {
				l.add(a);
			}
		}
		return changes ? new Data(l, reputation, completed, finished) : this;
	}

	/**
	 * Delivers the accepted quest with that id: removes it, records it as done, adds one to the completed count and, if
	 * {@code withReputation}, its reputation to its village.
	 */
	public Data deliver(String id, boolean withReputation) {
		Active a = active.stream().filter(x -> x.quest().id().equals(id)).findFirst().orElse(null);
		if (a == null) {
			return this;
		}
		List<Active> l = new ArrayList<>(active);
		l.remove(a);
		List<String> h = new ArrayList<>(finished);
		h.add(id);
		while (h.size() > MAX_DONE) {
			h.remove(0);
		}
		Data d = new Data(l, reputation, completed + 1, h);
		return withReputation ? d.addReputation(a.quest().village(), a.quest().reputation()) : d;
	}

	public Data addReputation(String village, int change) {
		Map<String, Integer> m = new LinkedHashMap<>(reputation);
		m.put(village, Reputation.add(reputation(village), change));
		return new Data(active, m, completed, finished);
	}

	/** How many villages have at least that level with the player. */
	public long villagesWith(Reputation.Tier tier) {
		return reputation.values().stream().filter(v -> Reputation.tier(v).compareTo(tier) >= 0).count();
	}

	/** Best level with any village. */
	public Reputation.Tier bestLevel() {
		return Reputation.tier(reputation.values().stream().mapToInt(Integer::intValue).max().orElse(0));
	}
}
