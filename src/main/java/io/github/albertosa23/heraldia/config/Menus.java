package io.github.albertosa23.heraldia.config;

import com.google.gson.JsonPrimitive;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * Los submenús del panel de configuración en el juego (/heraldia config, T46), lógica pura: en qué orden salen, qué
 * opciones lleva cada uno (de 5 a 8, las que más se tocan; lo técnico va en «avanzado» o en el fichero), el paso del
 * deslizador de cada número y cómo se leen los valores que devuelve el diálogo. El diálogo (comando/PanelConfig) solo
 * pinta lo que dice esta clase.
 */
public final class Menus {
	/** Un submenú: su id (heraldia.panel.menu.&lt;id&gt;) y sus opciones, en el orden en que salen. */
	public record Menu(String id, List<String> claves) {
	}

	/** Los perfiles que se eligen arriba del panel, en orden (personalizado sale solo al fijar opciones a mano). */
	public static final List<String> PERFILES = List.of("casual", Perfiles.ESTANDAR, "hardcore");
	public static final int MIN_OPCIONES = 5, MAX_OPCIONES = 8;

	public static final List<Menu> MENUS = List.of(
			new Menu("mundo", List.of("medianas.activadas", "medianas.frecuencia_porcentaje", "minas.entradas.activado",
					"minas.vanilla.multiplicador", "faros.activado", "naufragios.activado", "unicas.distancia_minima.activada",
					"unicas.distancia_minima.bloques")),
			new Menu("aldeas", List.of("aldeas.separacion_bloques", "aldeas.porcentaje_grandes", "aldeas.caminos.activado",
					"aldeas.caminos.ancho", "aldeas.vida.tratos_estilo", "aldeas.vida.tablon", "aldeas.vida.asedios", "golems.limpieza")),
			new Menu("combate", List.of("dificultad.nivel", "dificultad.escalar_por_jugadores", "jefes.fases.activado",
					"jefes.refuerzos.activado", "jefes.refuerzos.porcentaje", "jefes.barra.activado")),
			new Menu("botin", List.of("botin.reponer.activado", "botin.reponer.dias", "dificultad.escalar_botin", "tesoro.activado",
					"tesoro.probabilidad", "chozas_mago.prob_botin_premium")),
			new Menu("arena", List.of("arena.activado", "arena.max_mobs_vivos", "arena.experiencia_porcentaje",
					"arena.modos.cooperativo", "arena.modos.contrarreloj", "arena.modos.supervivencia", "arena.temporada.dia_reinicio")),
			new Menu("jugadores", List.of("guia.entregar_al_entrar", "encargos.activado", "reputacion.activado",
					"caravanas.activado", "caravanas.frecuencia", "caravanas.prob_asalto")),
			new Menu("avanzado", List.of("unicas.rejilla_compatible", "compatibilidad.zona_estructuras_ajenas_bloques",
					"aldeas.distancia_aldeas_vanilla_bloques", "actualizar.margen_bloques", "update_check.activado",
					"mapas_web.activado", "mapas_web.solo_descubiertas")));

	/** Lo más que salta un deslizador de un extremo a otro: con más pasos no se puede elegir un valor concreto. */
	static final int MAX_PASOS = 100;

	private Menus() {
	}

	public static Optional<Menu> menu(String id) {
		return MENUS.stream().filter(m -> m.id().equals(id)).findFirst();
	}

	/** Paso del deslizador: 1 si el rango cabe en {@link #MAX_PASOS}; si no, un número redondo (2, 5, 10, 25, 50, 100...). */
	public static double paso(ConfigOption o) {
		if (o.decimal()) {
			return 0.1;
		}
		int ancho = o.max() - o.min();
		for (int p : new int[] {1, 2, 5, 10, 25, 50, 100, 250, 500, 1000}) {
			if (ancho / p <= MAX_PASOS) {
				return p;
			}
		}
		return 1000;
	}

	/** El valor más cercano que puede dar el deslizador (los del rango múltiplos del paso desde el mínimo). */
	public static double ajustar(ConfigOption o, double v) {
		double p = paso(o);
		double r = o.min() + Math.round((v - o.min()) / p) * p;
		r = Math.max(o.min(), Math.min(o.max(), r));
		return o.decimal() ? Math.round(r * 10) / 10.0 : r;
	}

	/**
	 * Lo que devuelve el diálogo para una opción («true», «heroica», «1500», «1500.0», «2.5»), validado; vacío si no vale.
	 * Si el valor en uso no cae en la rejilla del deslizador y lo devuelto es el valor ajustado a ella, se conserva el que
	 * estaba (el jugador no lo ha movido: no se cambia una opción sin querer).
	 */
	public static Optional<JsonPrimitive> leer(ConfigOption o, String texto, JsonPrimitive actual) {
		String t = texto == null ? "" : texto.strip();
		if (o.isBoolean() || o.isChoice()) {
			return o.parse(t);
		}
		double d;
		try {
			d = Double.parseDouble(t);
		} catch (NumberFormatException e) {
			return Optional.empty();
		}
		if (!Double.isFinite(d)) {
			return Optional.empty();
		}
		if (actual != null && actual.isNumber() && Math.abs(ajustar(o, actual.getAsDouble()) - d) < 1e-6) {
			return Optional.of(actual);
		}
		JsonPrimitive v = o.decimal() ? new JsonPrimitive(Math.round(d * 10) / 10.0) : new JsonPrimitive(Math.round(d));
		return o.accept(v);
	}

	/**
	 * Los valores de un submenú tal como los devuelve el diálogo (uno por opción, en el orden del menú), leídos con
	 * {@link #leer}. Las que no se entienden se dejan fuera (y salen en {@code invalidas}).
	 */
	public record Leidos(Map<String, JsonPrimitive> valores, List<String> invalidas) {
	}

	public static Leidos leer(Menu menu, List<String> textos, Map<String, ConfigOption> opciones, Map<String, JsonPrimitive> actuales) {
		Map<String, JsonPrimitive> out = new LinkedHashMap<>();
		List<String> malas = new java.util.ArrayList<>();
		for (int i = 0; i < menu.claves().size(); i++) {
			String k = menu.claves().get(i);
			ConfigOption o = opciones.get(k);
			Optional<JsonPrimitive> v = o == null || i >= textos.size() ? Optional.empty() : leer(o, textos.get(i), actuales.get(k));
			if (v.isPresent()) {
				out.put(k, v.get());
			} else {
				malas.add(k);
			}
		}
		return new Leidos(out, List.copyOf(malas));
	}
}
