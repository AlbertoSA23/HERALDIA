package io.github.albertosa23.heraldia.arena;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/**
 * Lógica pura de las marcas de la arena (T41), sin clases del juego: cómo se escribe un tiempo y qué logros da una
 * partida acabada. Los logros los escribe el generador (tools/gen/arena_oleadas.py, LOGROS_MODOS) con las mismas cifras.
 */
public final class Marks {
	/** Oleadas mínimas del contrarreloj para sus logros (con menos, por configuración, no cuentan). */
	public static final int TIME_TRIAL_WAVES = 10;
	/** Tiempo del logro del contrarreloj rápido: 15 minutos de partida. */
	public static final long TIME_TRIAL_FAST_TICKS = 15 * 60 * 20;
	/** Oleada de supervivencia con logro. */
	public static final int SURVIVAL_WAVES = 15;

	private Marks() {
	}

	/** Ticks como «m:ss» (o «h:mm:ss» desde una hora); «-» si no se sabe (negativo). */
	public static String time(long ticks) {
		if (ticks < 0) {
			return "-";
		}
		long s = ticks / 20, h = s / 3600, m = (s % 3600) / 60, ss = s % 60;
		return h > 0 ? String.format(Locale.ROOT, "%d:%02d:%02d", h, m, ss) : String.format(Locale.ROOT, "%d:%02d", m, ss);
	}

	/** Id del logro de ganar una semana en un modo (heraldia:arena/campeon_&lt;id&gt;). */
	public static String championAdvancement(Mode m) {
		return "arena/campeon_" + m.id();
	}

	/** Logros (ids bajo heraldia:) que gana un jugador con esta marca al acabar su partida en el modo {@code m}. */
	public static List<String> advancements(Mode m, int waves, long ticks, int target) {
		List<String> out = new ArrayList<>();
		if (m == Mode.TIME_TRIAL && target >= TIME_TRIAL_WAVES && waves >= target) {
			out.add("arena/contrarreloj");
			if (ticks >= 0 && ticks <= TIME_TRIAL_FAST_TICKS) {
				out.add("arena/contrarreloj_rapido");
			}
		}
		if (m == Mode.SURVIVAL && waves >= SURVIVAL_WAVES) {
			out.add("arena/supervivencia_" + SURVIVAL_WAVES);
		}
		return out;
	}

	/**
	 * La marca para enseñarla (clave de texto y sus argumentos): el contrarreloj acabado, por su tiempo; a medias, por sus
	 * oleadas de cuántas; el cooperativo y la supervivencia, por sus oleadas.
	 */
	public static Object[] points(Mode m, Season.Entry e) {
		if (m == Mode.TIME_TRIAL) {
			return e.complete() ? new Object[] {"heraldia.arena.puntos.tiempo", time(e.ticks()), e.waves()}
					: new Object[] {"heraldia.arena.puntos.parcial", e.waves(), Math.max(e.target(), e.waves())};
		}
		return new Object[] {"heraldia.arena.puntos.oleadas", e.waves()};
	}
}
