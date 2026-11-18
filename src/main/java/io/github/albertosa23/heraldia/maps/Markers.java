package io.github.albertosa23.heraldia.maps;

import io.github.albertosa23.heraldia.command.State;
import java.util.ArrayList;
import java.util.Collection;
import java.util.EnumMap;
import java.util.EnumSet;
import java.util.IllegalFormatException;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import org.jspecify.annotations.Nullable;

/**
 * Qué marcadores salen en los mapas web y cómo, lógica pura (sin clases del juego ni de los mapas): el filtro de las
 * opciones (mapas_web.activado, una por capa y mapas_web.solo_descubiertas) y la construcción de cada marcador (posición,
 * capa, nombre traducido y descripción). Lo «descubierto» es lo mismo que cuenta /heraldia status: un tipo cuenta como
 * descubierto en cuanto algún jugador tiene su logro de descubrimiento.
 */
public final class Markers {
	/** Opciones en uso: mapas_web.activado, mapas_web.solo_descubiertas y las capas activadas. */
	public record Options(boolean enabled, boolean onlyDiscovered, Set<Layer> layers) {
		public Options {
			layers = layers.isEmpty() ? Set.of() : Set.copyOf(EnumSet.copyOf(layers));
		}
	}

	private Markers() {
	}

	/**
	 * ¿Ha descubierto algún jugador el tipo de este sitio? Las mismas reglas que /heraldia status: aldeas, el logro de su
	 * familia (heraldia:aldeas/&lt;familia&gt;); únicas, heraldia:unicas/&lt;id&gt;/descubrir; medianas, el criterio de su tipo en
	 * heraldia:medianas/todas; minas, heraldia:minas/&lt;tamaño&gt;; faros y naufragios, heraldia:costa/&lt;tipo&gt;. La arena la coloca un operador: siempre cuenta.
	 */
	public static boolean discovered(Layer layer, String sub, State.Achievements l) {
		return switch (layer) {
			case VILLAGES -> l.done(State.NS + "aldeas/" + sub);
			case UNIQUES -> l.done(State.NS + "unicas/" + sub + "/descubrir");
			case MEDIUMS -> l.criterion(State.NS + "medianas/todas", sub);
			case MINES -> l.done(State.NS + "minas/" + sub);
			case COAST -> l.done(State.NS + "costa/" + sub);
			case ARENA -> true;
		};
	}

	/** Clave del nombre de un sitio: el de su única, mediana o tamaño de mina; las aldeas, el de su familia. */
	static String nameKey(Layer layer, String sub) {
		return switch (layer) {
			case VILLAGES -> "heraldia.familia." + sub;
			case UNIQUES -> "heraldia.unicas." + sub + ".nombre";
			case MEDIUMS -> "heraldia.medianas." + sub + ".nombre";
			case MINES -> "heraldia.minas." + sub + ".nombre";
			case COAST -> "heraldia.costa." + sub + ".nombre";
			case ARENA -> "heraldia.arena.nombre";
		};
	}

	/** Nombre del marcador, en el idioma de {@code texts}: «Aldea: Llanuras», «Castillo del Rey Caído»... */
	static String name(Layer layer, String sub, Map<String, String> texts) {
		String base = text(texts, nameKey(layer, sub));
		return layer == Layer.VILLAGES ? format(text(texts, "heraldia.mapas_web.aldea"), base) : base;
	}

	/**
	 * Los marcadores que salen, en el orden del registro y, al final, la arena: nada si mapas_web.activado está apagado;
	 * de cada sitio, solo los de una capa activada y, con solo_descubiertas, los de un tipo descubierto.
	 *
	 * @param arena centro de la arena colocada (x, y, z) o null
	 */
	public static List<MapMarker> build(Collection<Site> sites, int @Nullable [] arena, State.Achievements advancements, Options o,
										   Map<String, String> texts) {
		List<MapMarker> out = new ArrayList<>();
		if (!o.enabled()) {
			return out;
		}
		for (Site s : sites) {
			if (!o.layers().contains(s.layer()) || o.onlyDiscovered() && !discovered(s.layer(), s.sub(), advancements)) {
				continue;
			}
			out.add(new MapMarker(s.key(), s.layer(), s.x(), s.y(), s.z(), name(s.layer(), s.sub(), texts),
					text(texts, s.layer().descriptionKey())));
		}
		if (arena != null && o.layers().contains(Layer.ARENA)) {
			out.add(new MapMarker("arena", Layer.ARENA, arena[0], arena[1], arena[2], name(Layer.ARENA, "", texts),
					text(texts, Layer.ARENA.descriptionKey())));
		}
		return out;
	}

	/** Los marcadores por capa (todas las capas activadas, aunque estén vacías, para que el mapa las vacíe). */
	public static Map<Layer, List<MapMarker>> byLayer(List<MapMarker> markers, Options o) {
		Map<Layer, List<MapMarker>> out = new EnumMap<>(Layer.class);
		if (o.enabled()) {
			o.layers().forEach(c -> out.put(c, new ArrayList<>()));
		}
		for (MapMarker m : markers) {
			out.computeIfAbsent(m.layer(), c -> new ArrayList<>()).add(m);
		}
		return out;
	}

	/** Nombres de las capas en el idioma de {@code texts}. */
	public static Map<Layer, String> layerNames(Map<String, String> texts) {
		Map<Layer, String> out = new EnumMap<>(Layer.class);
		for (Layer c : Layer.values()) {
			out.put(c, text(texts, c.nameKey()));
		}
		return out;
	}

	static String text(Map<String, String> texts, String key) {
		String t = texts.get(key);
		return t != null ? t : key;
	}

	private static String format(String pattern, String arg) {
		try {
			return String.format(Locale.ROOT, pattern, arg);
		} catch (IllegalFormatException e) {
			return pattern + " " + arg;
		}
	}
}
