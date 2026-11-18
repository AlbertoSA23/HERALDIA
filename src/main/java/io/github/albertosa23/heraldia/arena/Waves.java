package io.github.albertosa23.heraldia.arena;

import java.util.ArrayList;
import java.util.List;

/**
 * Lógica pura de las oleadas de la arena (sin clases del juego, para los tests): cuántos mobs trae cada oleada, cuánta
 * vida y daño de más, de qué tipos, cuándo hay mini-jefe, cuántos salen a la vez, la experiencia que dan y la
 * recompensa y el logro de cada oleada superada.
 * <ul>
 * <li>Mobs: {@link #BASE} en la primera y {@code +mobsPct} % de la base por oleada (por defecto +50 %: 4, 6, 8, 10...),
 * redondeando hacia arriba (así nunca crecen menos que la vida y el daño) y siempre al menos uno más que la anterior.</li>
 * <li>Vida y daño: {@code +statsPct} % por oleada (por defecto +10 %: x1, x1,1, x1,2...), siempre algo más. Los mobs
 * crecen proporcionalmente más que las estadísticas: si la configuración pide lo contrario, las estadísticas se
 * recortan al incremento de mobs ({@link #effectiveStats}).</li>
 * <li>Tipos: rotan cada oleada en un ciclo de {@link Batch#values()} (zombis; esqueletos y arañas; mezcla; mezcla
 * dura) y vuelven a empezar con más mobs. Cada {@link #BOSS_EVERY} oleadas, además, un mini-jefe.</li>
 * </ul>
 */
public final class Waves {
	/** Mobs de la primera oleada. */
	public static final int BASE = 4;
	/** Un mini-jefe cada tantas oleadas. */
	public static final int BOSS_EVERY = 5;
	/** Tope de oleadas que se calculan (nadie llega; evita bucles largos con números absurdos). */
	public static final int MAX_WAVE = 1000;
	/** Vida extra del mini-jefe sobre la de su oleada (cantidad de ADD_MULTIPLIED_TOTAL: x4) y daño extra (x1,5). */
	public static final double BOSS_HEALTH = 3.0, BOSS_DAMAGE = 0.5;
	/** Oleadas con logro. */
	public static final int[] ADVANCEMENTS = {5, 10, 20};
	/** Niveles de recompensa (heraldia:arena/recompensa_1..4). */
	public static final int MAX_REWARD = 4;

	private Waves() {
	}

	/** Tandas de tipos de mob, en orden de rotación. */
	public enum Batch {
		ZOMBIES("minecraft:zombie", "minecraft:zombie", "minecraft:husk"),
		SKELETONS_SPIDERS("minecraft:skeleton", "minecraft:spider"),
		MIX("minecraft:zombie", "minecraft:skeleton", "minecraft:spider", "minecraft:creeper"),
		HARD_MIX("minecraft:husk", "minecraft:stray", "minecraft:cave_spider", "minecraft:vindicator", "minecraft:witch");

		private final List<String> mobs;

		Batch(String... mobs) {
			this.mobs = List.of(mobs);
		}

		public List<String> mobs() {
			return mobs;
		}
	}

	/** Mini-jefes, en rotación (uno por cada {@link #BOSS_EVERY} oleadas): tipo y nombre (heraldia.arena.jefe.&lt;i&gt;). */
	public record Boss(int index, String mob, String weapon) {
	}

	public static final List<Boss> BOSSES = List.of(
			new Boss(0, "minecraft:zombie", "minecraft:iron_axe"),
			new Boss(1, "minecraft:skeleton", "minecraft:bow"),
			new Boss(2, "minecraft:vindicator", "minecraft:iron_axe"),
			new Boss(3, "minecraft:wither_skeleton", "minecraft:stone_sword"));

	/** Oleada válida (1..MAX_OLEADA). */
	static int clamp(int wave) {
		return Math.clamp(wave, 1, MAX_WAVE);
	}

	/** Mobs normales de la oleada (sin el mini-jefe): estrictamente creciente. */
	public static int mobs(int wave, int mobsPct) {
		int n = clamp(wave);
		int prev = BASE;
		for (int k = 2; k <= n; k++) {
			prev = Math.max(prev + 1, (int) Math.ceil(BASE * (1 + mobsPct / 100.0 * (k - 1)) - 1e-9));
		}
		return prev;
	}

	/** Incremento de vida y daño que se usa: el configurado, pero nunca mayor que el de mobs (crecen más los mobs). */
	public static int effectiveStats(int mobsPct, int statsPct) {
		return Math.max(1, Math.min(statsPct, mobsPct));
	}

	/** Multiplicador de vida y daño de la oleada: 1 + statsPct % por oleada (estrictamente creciente). */
	public static double stats(int wave, int statsPct) {
		return 1 + statsPct / 100.0 * (clamp(wave) - 1);
	}

	/** Cantidad del modificador ADD_MULTIPLIED_TOTAL de la oleada (0 en la primera: sin modificador). */
	public static double modifier(int wave, int statsPct) {
		return stats(wave, statsPct) - 1;
	}

	public static boolean withBoss(int wave) {
		return wave > 0 && wave % BOSS_EVERY == 0;
	}

	/** Mini-jefe de la oleada (la 5, el primero; la 10, el segundo...). */
	public static Boss boss(int wave) {
		return BOSSES.get((Math.max(1, wave / BOSS_EVERY) - 1) % BOSSES.size());
	}

	/** Enemigos de la oleada en total (mobs normales y, si toca, el mini-jefe). */
	public static int total(int wave, int mobsPct) {
		return mobs(wave, mobsPct) + (withBoss(wave) ? 1 : 0);
	}

	public static Batch batch(int wave) {
		return Batch.values()[(clamp(wave) - 1) % Batch.values().length];
	}

	/** Tipo de cada mob normal de la oleada, en el orden en que salen (repartidos por turnos entre los de su tanda). */
	public static List<String> types(int wave, int mobsPct) {
		List<String> list = batch(wave).mobs();
		int n = mobs(wave, mobsPct);
		List<String> out = new ArrayList<>(n);
		for (int i = 0; i < n; i++) {
			out.add(list.get(i % list.size()));
		}
		return out;
	}

	/** Cuántos salen ahora: los que faltan por salir, sin pasar de {@code maxAlive} vivos a la vez. */
	public static int spawned(int alive, int pending, int maxAlive) {
		return Math.max(0, Math.min(pending, maxAlive - alive));
	}

	/**
	 * Experiencia que suelta un mob de la arena: el {@code pct} % de la vanilla (ya escalada por el juego), con la parte
	 * fraccionaria según {@code rng} en [0, 1) (de media, exactamente el porcentaje).
	 */
	public static int experience(int vanilla, int pct, double rng) {
		if (vanilla <= 0 || pct <= 0) {
			return 0;
		}
		if (pct >= 100) {
			return vanilla;
		}
		double x = vanilla * pct / 100.0;
		int base = (int) Math.floor(x);
		return base + (rng < x - base ? 1 : 0);
	}

	/** Nivel de la recompensa al superar la oleada (1 en la 5, 2 en la 10, 3 en la 15, 4 desde la 20); 0 si no toca. */
	public static int reward(int wave) {
		return withBoss(wave) ? Math.min(MAX_REWARD, wave / BOSS_EVERY) : 0;
	}

	/** ¿Logro al superar esta oleada? */
	public static boolean advancement(int wave) {
		for (int l : ADVANCEMENTS) {
			if (l == wave) {
				return true;
			}
		}
		return false;
	}
}
