package io.github.albertosa23.heraldia.quests;

import com.mojang.serialization.Codec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Lo que se guarda de cada jugador (adjunto persistente de Fabric en su .dat, sin enviarlo al cliente): los encargos
 * aceptados, la reputación con cada aldea, cuántos ha entregado y los ids de los últimos entregados (para no cobrar dos
 * veces el mismo). Inmutable: cada cambio da otro valor (y {@code setAttached}).
 */
public record Data(List<Active> active, Map<String, Integer> reputation, int completed, List<String> finished) {
	/** Encargos aceptados a la vez, como mucho. */
	public static final int MAX_ACTIVE = 5;
	/** Ids de entregados que se recuerdan (los más recientes): de sobra para varios periodos de todas las aldeas visitadas. */
	public static final int MAX_DONE = 200;
	public static final Data EMPTY = new Data(List.of(), Map.of(), 0, List.of());

	/** Un encargo aceptado y si ya se cumplió lo que pide (los de traer se comprueban al entregar). */
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

	/** ¿Lo tiene aceptado (por id)? */
	public boolean has(String id) {
		return active.stream().anyMatch(a -> a.quest().id().equals(id));
	}

	public boolean done(String id) {
		return finished.contains(id);
	}

	/** Por qué no se puede aceptar (clave del motivo) o null si se puede. */
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

	/** Quita el aceptado número {@code i} (0..); sin cambios si no existe. */
	public Data abandon(int i) {
		if (i < 0 || i >= active.size()) {
			return this;
		}
		List<Active> l = new ArrayList<>(active);
		l.remove(i);
		return new Data(l, reputation, completed, finished);
	}

	/** Marca como cumplidos los aceptados que cumplen la condición. */
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
	 * Entrega el aceptado con ese id: lo quita, lo apunta como hecho, suma uno a los completados y, si
	 * {@code withReputation}, su reputación a su aldea.
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

	/** Cuántas aldeas tienen al menos ese nivel con el jugador. */
	public long villagesWith(Reputation.Tier tier) {
		return reputation.values().stream().filter(v -> Reputation.tier(v).compareTo(tier) >= 0).count();
	}

	/** Mejor nivel con alguna aldea. */
	public Reputation.Tier bestLevel() {
		return Reputation.tier(reputation.values().stream().mapToInt(Integer::intValue).max().orElse(0));
	}
}
