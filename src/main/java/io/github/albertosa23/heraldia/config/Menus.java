package io.github.albertosa23.heraldia.config;

import com.google.gson.JsonPrimitive;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * The submenus of the in-game configuration panel (/heraldia config, T46), pure logic: the order they appear in, which
 * options each one has (5 to 8, the most tweaked ones; the technical ones go in "advanced" or in the file), the
 * slider step of each number and how the values the dialog returns are read. The dialog (command/ConfigPanel) only
 * draws what this class says.
 */
public final class Menus {
	/** A submenu: its id (heraldia.panel.menu.&lt;id&gt;) and its options, in the order they appear. */
	public record Menu(String id, List<String> keys) {
	}

	/** The profiles chosen at the top of the panel, in order (custom only appears when options are set by hand). */
	public static final List<String> PROFILES = List.of("casual", Profiles.STANDARD, "hardcore");
	public static final int MIN_OPTIONS = 5, MAX_OPTIONS = 8;

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

	/** The most a slider can jump from one end to the other: with more steps a specific value cannot be chosen. */
	static final int MAX_STEPS = 100;

	private Menus() {
	}

	public static Optional<Menu> menu(String id) {
		return MENUS.stream().filter(m -> m.id().equals(id)).findFirst();
	}

	/** Slider step: 1 if the range fits in {@link #MAX_STEPS}; otherwise, a round number (2, 5, 10, 25, 50, 100...). */
	public static double step(ConfigOption o) {
		if (o.decimal()) {
			return 0.1;
		}
		int width = o.max() - o.min();
		for (int p : new int[] {1, 2, 5, 10, 25, 50, 100, 250, 500, 1000}) {
			if (width / p <= MAX_STEPS) {
				return p;
			}
		}
		return 1000;
	}

	/** The closest value the slider can give (those of the range that are multiples of the step from the minimum). */
	public static double adjust(ConfigOption o, double v) {
		double p = step(o);
		double r = o.min() + Math.round((v - o.min()) / p) * p;
		r = Math.max(o.min(), Math.min(o.max(), r));
		return o.decimal() ? Math.round(r * 10) / 10.0 : r;
	}

	/**
	 * What the dialog returns for an option ("true", "heroica", "1500", "1500.0", "2.5"), validated; empty if invalid.
	 * If the value in use does not fall on the slider's grid and what was returned is the value snapped to it, the existing
	 * one is kept (the player did not move it: an option is not changed by accident).
	 */
	public static Optional<JsonPrimitive> read(ConfigOption o, String text, JsonPrimitive actual) {
		String t = text == null ? "" : text.strip();
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
		if (actual != null && actual.isNumber() && Math.abs(adjust(o, actual.getAsDouble()) - d) < 1e-6) {
			return Optional.of(actual);
		}
		JsonPrimitive v = o.decimal() ? new JsonPrimitive(Math.round(d * 10) / 10.0) : new JsonPrimitive(Math.round(d));
		return o.accept(v);
	}

	/**
	 * The values of a submenu as the dialog returns them (one per option, in menu order), read with
	 * {@link #read}. Those that cannot be understood are left out (and show up in {@code invalid}).
	 */
	public record Loaded(Map<String, JsonPrimitive> optionValues, List<String> invalid) {
	}

	public static Loaded read(Menu menu, List<String> texts, Map<String, ConfigOption> options, Map<String, JsonPrimitive> current) {
		Map<String, JsonPrimitive> out = new LinkedHashMap<>();
		List<String> bad = new java.util.ArrayList<>();
		for (int i = 0; i < menu.keys().size(); i++) {
			String k = menu.keys().get(i);
			ConfigOption o = options.get(k);
			Optional<JsonPrimitive> v = o == null || i >= texts.size() ? Optional.empty() : read(o, texts.get(i), current.get(k));
			if (v.isPresent()) {
				out.put(k, v.get());
			} else {
				bad.add(k);
			}
		}
		return new Loaded(out, List.copyOf(bad));
	}
}
