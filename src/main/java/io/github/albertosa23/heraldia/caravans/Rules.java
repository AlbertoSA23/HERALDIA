package io.github.albertosa23.heraldia.caravans;

import java.util.List;
import java.util.Set;
import java.util.UUID;

/**
 * Reglas de las caravanas (lógica pura): cuándo sale una, cómo es (llamas, guardia, asalto, bandidos), qué paga y qué
 * entidades sobran. Los números al azar llegan como argumentos en [0, 1) para que los tests los fijen.
 */
public final class Rules {
	/** Cada cuántos ticks se sortea una caravana nueva (1 min), y la espera tras acabar una (2 min). */
	public static final int DRAW_TICKS = 60 * 20, WAIT_TICKS = 2 * 60 * 20;
	/** Etiquetas (Tags) de todas sus entidades y de cada papel. */
	public static final String TAG = "heraldia_caravana", MERCHANT = "heraldia_caravana.mercader", LLAMA = "heraldia_caravana.llama",
			GUARD = "heraldia_caravana.guardia", BANDIT = "heraldia_caravana.bandido";

	private Rules() {
	}

	/**
	 * ¿Sale una caravana en este sorteo? Con las caravanas activadas, por debajo del límite de activas, pasada la espera
	 * desde la última y con probabilidad {@code rate} % (0: nunca sola, solo con el comando).
	 */
	public static boolean outcome(boolean enabled, int active, int maxActive, long tick, long lastEnd, int rate, double rng) {
		return enabled && active < maxActive && rate > 0 && tick - lastEnd >= WAIT_TICKS && rng * 100 < rate;
	}

	/** ¿La asaltan? Con probabilidad {@code ambushProb} %. */
	public static boolean ambush(int ambushProb, double rng) {
		return ambushProb > 0 && rng * 100 < ambushProb;
	}

	/** Llamas de carga: de 1 a 3. */
	public static int llamas(double rng) {
		return 1 + Math.min(2, (int) (rng * 3));
	}

	/** ¿Lleva guardia (un gólem de hierro)? Una de cada cuatro. */
	public static boolean guard(double rng) {
		return rng < 0.25;
	}

	/** Bandidos del asalto: uno más que jugadores cerca, de 2 a 4; con 3 o más, uno es el jefe (vindicador). */
	public static int bandits(int players) {
		return Math.max(2, Math.min(4, players + 1));
	}

	public static boolean withBoss(int bandits) {
		return bandits >= 3;
	}

	/**
	 * Lo que gana cada jugador que la acompaña al llegar: esmeraldas (2 más una por cada 4 vértices; 4 más y un objeto
	 * si superó un asalto), reputación con la aldea de destino (5, o 15 tras un asalto) y, tras un asalto, el logro.
	 */
	public record Reward(int emeralds, int reputation, String item, int amount, boolean advancement) {
		public boolean withItem() {
			return item != null;
		}
	}

	/** Objetos de una caravana defendida: (id, cantidad). Modestos, como el botín de una mediana. */
	public static final List<Object[]> ITEMS = List.of(new Object[]{"minecraft:name_tag", 1}, new Object[]{"minecraft:spyglass", 1},
			new Object[]{"minecraft:lead", 2}, new Object[]{"minecraft:golden_carrot", 4}, new Object[]{"minecraft:honey_bottle", 3},
			new Object[]{"minecraft:map", 1}, new Object[]{"minecraft:bundle", 1}, new Object[]{"minecraft:saddle", 1});

	public static Reward reward(int vertices, boolean cleared, double rng) {
		int emeralds = 2 + vertices / 4 + (cleared ? 4 : 0);
		if (!cleared) {
			return new Reward(emeralds, 5, null, 0, false);
		}
		Object[] o = ITEMS.get(Math.min(ITEMS.size() - 1, (int) (rng * ITEMS.size())));
		return new Reward(emeralds, 15, (String) o[0], (Integer) o[1], true);
	}

	/**
	 * Chunk del inicio de la aldea cuya plaza da el trazado ({@code RoadLayout.pack(cx * 16 + 8, cz * 16 + 8)}): el que usa la
	 * reputación de los encargos ({@code Quests.addReputation}) para saber de qué aldea se habla.
	 */
	public static int[] chunk(long village) {
		return new int[]{Math.floorDiv(io.github.albertosa23.heraldia.roads.RoadLayout.px(village), 16),
				Math.floorDiv(io.github.albertosa23.heraldia.roads.RoadLayout.pz(village), 16)};
	}

	/** ¿Sobra esta entidad? Es de una caravana y no de ninguna activa (de antes de reiniciar, o de una ya terminada). */
	public static boolean orphan(Set<String> tags, UUID uuid, Set<UUID> active) {
		return !tags.isEmpty() && tags.contains(TAG) && !active.contains(uuid);
	}
}
