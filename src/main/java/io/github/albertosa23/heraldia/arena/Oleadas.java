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
 * recortan al incremento de mobs ({@link #statsEfectivo}).</li>
 * <li>Tipos: rotan cada oleada en un ciclo de {@link Tanda#values()} (zombis; esqueletos y arañas; mezcla; mezcla
 * dura) y vuelven a empezar con más mobs. Cada {@link #JEFE_CADA} oleadas, además, un mini-jefe.</li>
 * </ul>
 */
public final class Oleadas {
	/** Mobs de la primera oleada. */
	public static final int BASE = 4;
	/** Un mini-jefe cada tantas oleadas. */
	public static final int JEFE_CADA = 5;
	/** Tope de oleadas que se calculan (nadie llega; evita bucles largos con números absurdos). */
	public static final int MAX_OLEADA = 1000;
	/** Vida extra del mini-jefe sobre la de su oleada (cantidad de ADD_MULTIPLIED_TOTAL: x4) y daño extra (x1,5). */
	public static final double JEFE_VIDA = 3.0, JEFE_DANO = 0.5;
	/** Oleadas con logro. */
	public static final int[] LOGROS = {5, 10, 20};
	/** Niveles de recompensa (heraldia:arena/recompensa_1..4). */
	public static final int MAX_RECOMPENSA = 4;

	private Oleadas() {
	}

	/** Tandas de tipos de mob, en orden de rotación. */
	public enum Tanda {
		ZOMBIS("minecraft:zombie", "minecraft:zombie", "minecraft:husk"),
		ESQUELETOS_ARANAS("minecraft:skeleton", "minecraft:spider"),
		MEZCLA("minecraft:zombie", "minecraft:skeleton", "minecraft:spider", "minecraft:creeper"),
		MEZCLA_DURA("minecraft:husk", "minecraft:stray", "minecraft:cave_spider", "minecraft:vindicator", "minecraft:witch");

		private final List<String> mobs;

		Tanda(String... mobs) {
			this.mobs = List.of(mobs);
		}

		public List<String> mobs() {
			return mobs;
		}
	}

	/** Mini-jefes, en rotación (uno por cada {@link #JEFE_CADA} oleadas): tipo y nombre (heraldia.arena.jefe.&lt;i&gt;). */
	public record Jefe(int indice, String mob, String arma) {
	}

	public static final List<Jefe> JEFES = List.of(
			new Jefe(0, "minecraft:zombie", "minecraft:iron_axe"),
			new Jefe(1, "minecraft:skeleton", "minecraft:bow"),
			new Jefe(2, "minecraft:vindicator", "minecraft:iron_axe"),
			new Jefe(3, "minecraft:wither_skeleton", "minecraft:stone_sword"));

	/** Oleada válida (1..MAX_OLEADA). */
	static int acotar(int oleada) {
		return Math.clamp(oleada, 1, MAX_OLEADA);
	}

	/** Mobs normales de la oleada (sin el mini-jefe): estrictamente creciente. */
	public static int mobs(int oleada, int mobsPct) {
		int n = acotar(oleada);
		int prev = BASE;
		for (int k = 2; k <= n; k++) {
			prev = Math.max(prev + 1, (int) Math.ceil(BASE * (1 + mobsPct / 100.0 * (k - 1)) - 1e-9));
		}
		return prev;
	}

	/** Incremento de vida y daño que se usa: el configurado, pero nunca mayor que el de mobs (crecen más los mobs). */
	public static int statsEfectivo(int mobsPct, int statsPct) {
		return Math.max(1, Math.min(statsPct, mobsPct));
	}

	/** Multiplicador de vida y daño de la oleada: 1 + statsPct % por oleada (estrictamente creciente). */
	public static double stats(int oleada, int statsPct) {
		return 1 + statsPct / 100.0 * (acotar(oleada) - 1);
	}

	/** Cantidad del modificador ADD_MULTIPLIED_TOTAL de la oleada (0 en la primera: sin modificador). */
	public static double modificador(int oleada, int statsPct) {
		return stats(oleada, statsPct) - 1;
	}

	public static boolean conJefe(int oleada) {
		return oleada > 0 && oleada % JEFE_CADA == 0;
	}

	/** Mini-jefe de la oleada (la 5, el primero; la 10, el segundo...). */
	public static Jefe jefe(int oleada) {
		return JEFES.get((Math.max(1, oleada / JEFE_CADA) - 1) % JEFES.size());
	}

	/** Enemigos de la oleada en total (mobs normales y, si toca, el mini-jefe). */
	public static int total(int oleada, int mobsPct) {
		return mobs(oleada, mobsPct) + (conJefe(oleada) ? 1 : 0);
	}

	public static Tanda tanda(int oleada) {
		return Tanda.values()[(acotar(oleada) - 1) % Tanda.values().length];
	}

	/** Tipo de cada mob normal de la oleada, en el orden en que salen (repartidos por turnos entre los de su tanda). */
	public static List<String> tipos(int oleada, int mobsPct) {
		List<String> lista = tanda(oleada).mobs();
		int n = mobs(oleada, mobsPct);
		List<String> out = new ArrayList<>(n);
		for (int i = 0; i < n; i++) {
			out.add(lista.get(i % lista.size()));
		}
		return out;
	}

	/** Cuántos salen ahora: los que faltan por salir, sin pasar de {@code maxVivos} vivos a la vez. */
	public static int aparecen(int vivos, int pendientes, int maxVivos) {
		return Math.max(0, Math.min(pendientes, maxVivos - vivos));
	}

	/**
	 * Experiencia que suelta un mob de la arena: el {@code pct} % de la vanilla (ya escalada por el juego), con la parte
	 * fraccionaria según {@code azar} en [0, 1) (de media, exactamente el porcentaje).
	 */
	public static int experiencia(int vanilla, int pct, double azar) {
		if (vanilla <= 0 || pct <= 0) {
			return 0;
		}
		if (pct >= 100) {
			return vanilla;
		}
		double x = vanilla * pct / 100.0;
		int base = (int) Math.floor(x);
		return base + (azar < x - base ? 1 : 0);
	}

	/** Nivel de la recompensa al superar la oleada (1 en la 5, 2 en la 10, 3 en la 15, 4 desde la 20); 0 si no toca. */
	public static int recompensa(int oleada) {
		return conJefe(oleada) ? Math.min(MAX_RECOMPENSA, oleada / JEFE_CADA) : 0;
	}

	/** ¿Logro al superar esta oleada? */
	public static boolean logro(int oleada) {
		for (int l : LOGROS) {
			if (l == oleada) {
				return true;
			}
		}
		return false;
	}
}
