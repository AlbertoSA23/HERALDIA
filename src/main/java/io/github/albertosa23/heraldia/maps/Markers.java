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
 * Which markers show on the web maps and how, pure logic (no game or map classes): the filter of the
 * options (mapas_web.activado, one per layer and mapas_web.solo_descubiertas) and building each marker (position,
 * layer, translated name and description). "Discovered" is the same thing /heraldia status counts: a type counts as
 * discovered as soon as some player has its discovery advancement.
 */
public final class Markers {
	/** Options in use: mapas_web.activado, mapas_web.solo_descubiertas and the enabled layers. */
	public record Options(boolean enabled, boolean onlyDiscovered, Set<Layer> layers) {
		public Options {
			layers = layers.isEmpty() ? Set.of() : Set.copyOf(EnumSet.copyOf(layers));
		}
	}

	private Markers() {
	}

	/**
	 * Has some player discovered the type of this site? The same rules as /heraldia status: villages, the advancement of their
	 * family (heraldia:aldeas/&lt;family&gt;); uniques, heraldia:unicas/&lt;id&gt;/descubrir; mediums, their type's criterion in
	 * heraldia:medianas/todas; mines, heraldia:minas/&lt;size&gt;; lighthouses and shipwrecks, heraldia:costa/&lt;type&gt;. The
	 * arena is placed by an operator: it always counts.
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

	/** Key of a site's name: that of its unique, medium or mine size; villages, that of their family. */
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

	/** Marker name, in the language of {@code texts}: "Village: Plains", "Castle of the Fallen King"... */
	static String name(Layer layer, String sub, Map<String, String> texts) {
		String base = text(texts, nameKey(layer, sub));
		return layer == Layer.VILLAGES ? format(text(texts, "heraldia.mapas_web.aldea"), base) : base;
	}

	/**
	 * The markers that show, in ledger order and, at the end, the arena: nothing if mapas_web.activado is off;
	 * of each site, only those of an enabled layer and, with solo_descubiertas, those of a discovered type.
	 *
	 * @param arena center of the placed arena (x, y, z) or null
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

	/** The markers per layer (all enabled layers, even if empty, so the map clears them). */
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

	/** Layer names in the language of {@code texts}. */
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
