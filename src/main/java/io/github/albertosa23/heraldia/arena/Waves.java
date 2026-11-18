package io.github.albertosa23.heraldia.arena;

import java.util.ArrayList;
import java.util.List;

/**
 * Pure logic of the arena waves (no game classes, for the tests): how many mobs each wave brings, how much extra
 * health and damage, of which types, when there is a mini-boss, how many spawn at once, the experience they give and the
 * reward and advancement of each cleared wave.
 * <ul>
 * <li>Mobs: {@link #BASE} in the first and {@code +mobsPct} % of the base per wave (by default +50 %: 4, 6, 8, 10...),
 * rounding up (so they never grow less than health and damage) and always at least one more than the previous.</li>
 * <li>Health and damage: {@code +statsPct} % per wave (by default +10 %: x1, x1.1, x1.2...), always somewhat more. Mobs
 * grow proportionally more than the stats: if the configuration asks for the opposite, the stats are clamped to the
 * mob increment ({@link #effectiveStats}).</li>
 * <li>Types: they rotate each wave in a cycle of {@link Batch#values()} (zombies; skeletons and spiders; mix; hard
 * mix) and start over with more mobs. Every {@link #BOSS_EVERY} waves, a mini-boss as well.</li>
 * </ul>
 */
public final class Waves {
	/** Mobs in the first wave. */
	public static final int BASE = 4;
	/** One mini-boss every so many waves. */
	public static final int BOSS_EVERY = 5;
	/** Cap on computed waves (nobody gets there; avoids long loops with absurd numbers). */
	public static final int MAX_WAVE = 1000;
	/** Extra health of the mini-boss over its wave's (ADD_MULTIPLIED_TOTAL amount: x4) and extra damage (x1.5). */
	public static final double BOSS_HEALTH = 3.0, BOSS_DAMAGE = 0.5;
	/** Waves with an advancement. */
	public static final int[] ADVANCEMENTS = {5, 10, 20};
	/** Reward levels (heraldia:arena/recompensa_1..4). */
	public static final int MAX_REWARD = 4;

	private Waves() {
	}

	/** Mob type batches, in rotation order. */
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

	/** Mini-bosses, in rotation (one every {@link #BOSS_EVERY} waves): type and name (heraldia.arena.jefe.&lt;i&gt;). */
	public record Boss(int index, String mob, String weapon) {
	}

	public static final List<Boss> BOSSES = List.of(
			new Boss(0, "minecraft:zombie", "minecraft:iron_axe"),
			new Boss(1, "minecraft:skeleton", "minecraft:bow"),
			new Boss(2, "minecraft:vindicator", "minecraft:iron_axe"),
			new Boss(3, "minecraft:wither_skeleton", "minecraft:stone_sword"));

	/** Valid wave (1..MAX_WAVE). */
	static int clamp(int wave) {
		return Math.clamp(wave, 1, MAX_WAVE);
	}

	/** Normal mobs of the wave (without the mini-boss): strictly increasing. */
	public static int mobs(int wave, int mobsPct) {
		int n = clamp(wave);
		int prev = BASE;
		for (int k = 2; k <= n; k++) {
			prev = Math.max(prev + 1, (int) Math.ceil(BASE * (1 + mobsPct / 100.0 * (k - 1)) - 1e-9));
		}
		return prev;
	}

	/** Health and damage increment in use: the configured one, but never more than the mobs' (mobs grow more). */
	public static int effectiveStats(int mobsPct, int statsPct) {
		return Math.max(1, Math.min(statsPct, mobsPct));
	}

	/** Health and damage multiplier of the wave: 1 + statsPct % per wave (strictly increasing). */
	public static double stats(int wave, int statsPct) {
		return 1 + statsPct / 100.0 * (clamp(wave) - 1);
	}

	/** Amount of the wave's ADD_MULTIPLIED_TOTAL modifier (0 in the first: no modifier). */
	public static double modifier(int wave, int statsPct) {
		return stats(wave, statsPct) - 1;
	}

	public static boolean withBoss(int wave) {
		return wave > 0 && wave % BOSS_EVERY == 0;
	}

	/** The wave's mini-boss (wave 5, the first; wave 10, the second...). */
	public static Boss boss(int wave) {
		return BOSSES.get((Math.max(1, wave / BOSS_EVERY) - 1) % BOSSES.size());
	}

	/** Total enemies of the wave (normal mobs and, when due, the mini-boss). */
	public static int total(int wave, int mobsPct) {
		return mobs(wave, mobsPct) + (withBoss(wave) ? 1 : 0);
	}

	public static Batch batch(int wave) {
		return Batch.values()[(clamp(wave) - 1) % Batch.values().length];
	}

	/** Type of each normal mob of the wave, in spawn order (dealt in turns among those of its batch). */
	public static List<String> types(int wave, int mobsPct) {
		List<String> list = batch(wave).mobs();
		int n = mobs(wave, mobsPct);
		List<String> out = new ArrayList<>(n);
		for (int i = 0; i < n; i++) {
			out.add(list.get(i % list.size()));
		}
		return out;
	}

	/** How many spawn now: those still to spawn, without going over {@code maxAlive} alive at once. */
	public static int spawned(int alive, int pending, int maxAlive) {
		return Math.max(0, Math.min(pending, maxAlive - alive));
	}

	/**
	 * Experience an arena mob drops: {@code pct} % of vanilla's (already scaled by the game), with the fractional
	 * part decided by {@code rng} in [0, 1) (on average, exactly the percentage).
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

	/** Reward level for clearing the wave (1 at 5, 2 at 10, 3 at 15, 4 from 20); 0 if none is due. */
	public static int reward(int wave) {
		return withBoss(wave) ? Math.min(MAX_REWARD, wave / BOSS_EVERY) : 0;
	}

	/** Advancement for clearing this wave? */
	public static boolean advancement(int wave) {
		for (int l : ADVANCEMENTS) {
			if (l == wave) {
				return true;
			}
		}
		return false;
	}
}
