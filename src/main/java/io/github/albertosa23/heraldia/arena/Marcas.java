package io.github.albertosa23.heraldia.arena;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/**
 * Lógica pura de las marcas de la arena (T41), sin clases del juego: cómo se escribe un tiempo y qué logros da una
 * partida acabada. Los logros los escribe el generador (tools/gen/arena_oleadas.py, LOGROS_MODOS) con las mismas cifras.
 */
public final class Marcas {
	/** Oleadas mínimas del contrarreloj para sus logros (con menos, por configuración, no cuentan). */
	public static final int CONTRARRELOJ_OLEADAS = 10;
	/** Tiempo del logro del contrarreloj rápido: 15 minutos de partida. */
	public static final long CONTRARRELOJ_RAPIDO_TICKS = 15 * 60 * 20;
	/** Oleada de supervivencia con logro. */
	public static final int SUPERVIVENCIA_OLEADAS = 15;

	private Marcas() {
	}

	/** Ticks como «m:ss» (o «h:mm:ss» desde una hora); «-» si no se sabe (negativo). */
	public static String tiempo(long ticks) {
		if (ticks < 0) {
			return "-";
		}
		long s = ticks / 20, h = s / 3600, m = (s % 3600) / 60, ss = s % 60;
		return h > 0 ? String.format(Locale.ROOT, "%d:%02d:%02d", h, m, ss) : String.format(Locale.ROOT, "%d:%02d", m, ss);
	}

	/** Id del logro de ganar una semana en un modo (heraldia:arena/campeon_&lt;id&gt;). */
	public static String logroCampeon(Modo m) {
		return "arena/campeon_" + m.id();
	}

	/** Logros (ids bajo heraldia:) que gana un jugador con esta marca al acabar su partida en el modo {@code m}. */
	public static List<String> logros(Modo m, int oleadas, long ticks, int objetivo) {
		List<String> out = new ArrayList<>();
		if (m == Modo.CONTRARRELOJ && objetivo >= CONTRARRELOJ_OLEADAS && oleadas >= objetivo) {
			out.add("arena/contrarreloj");
			if (ticks >= 0 && ticks <= CONTRARRELOJ_RAPIDO_TICKS) {
				out.add("arena/contrarreloj_rapido");
			}
		}
		if (m == Modo.SUPERVIVENCIA && oleadas >= SUPERVIVENCIA_OLEADAS) {
			out.add("arena/supervivencia_" + SUPERVIVENCIA_OLEADAS);
		}
		return out;
	}

	/**
	 * La marca para enseñarla (clave de texto y sus argumentos): el contrarreloj acabado, por su tiempo; a medias, por sus
	 * oleadas de cuántas; el cooperativo y la supervivencia, por sus oleadas.
	 */
	public static Object[] puntos(Modo m, Temporada.Entrada e) {
		if (m == Modo.CONTRARRELOJ) {
			return e.completa() ? new Object[] {"heraldia.arena.puntos.tiempo", tiempo(e.ticks()), e.oleadas()}
					: new Object[] {"heraldia.arena.puntos.parcial", e.oleadas(), Math.max(e.objetivo(), e.oleadas())};
		}
		return new Object[] {"heraldia.arena.puntos.oleadas", e.oleadas()};
	}
}
