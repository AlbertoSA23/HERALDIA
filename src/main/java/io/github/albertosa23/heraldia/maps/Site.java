package io.github.albertosa23.heraldia.maps;

import java.util.Map;
import org.jspecify.annotations.Nullable;

/**
 * A known Heraldia structure (generated in a chunk that has loaded at some point), pure logic: the id of its
 * structure (path without the namespace, e.g. "unicas/castillo"), its layer, what distinguishes its type (family,
 * unique, medium type or mine size: what /heraldia status checks to know whether someone has discovered it) and the
 * position of its box's center.
 */
public record Site(String structure, Layer layer, String sub, int x, int y, int z) {
	/** Stable key: the structure and its position (there are no two starts of the same structure at the same spot). */
	public String key() {
		return structure + "@" + x + "," + y + "," + z;
	}

	/**
	 * Classifies a Heraldia structure by its id path (without "heraldia:"): villages are "&lt;style&gt;" or
	 * "&lt;style&gt;_grande" (family from {@code familyStyle}), uniques "unicas/&lt;id&gt;", mediums
	 * "medianas/&lt;type&gt;/&lt;style&gt;", mine entrances "minas/&lt;size&gt;/..." and lighthouses and shipwrecks
	 * "costa/&lt;type&gt;/...". Anything else (the arena is not a registry structure), null.
	 */
	public static @Nullable Site of(String route, Map<String, String> familyStyle, int x, int y, int z) {
		String[] s = route.split("/");
		if (s.length >= 2 && s[0].equals("unicas") && !s[1].isEmpty()) {
			return new Site(route, Layer.UNIQUES, s[1], x, y, z);
		}
		if (s.length >= 3 && s[0].equals("medianas") && !s[1].isEmpty()) {
			return new Site(route, Layer.MEDIUMS, s[1], x, y, z);
		}
		if (s.length >= 3 && s[0].equals("minas") && !s[1].isEmpty()) {
			return new Site(route, Layer.MINES, s[1], x, y, z);
		}
		if (s.length >= 3 && s[0].equals("costa") && !s[1].isEmpty()) {
			return new Site(route, Layer.COAST, s[1], x, y, z);
		}
		if (s.length == 1) {
			String style = route.endsWith("_grande") ? route.substring(0, route.length() - "_grande".length()) : route;
			String fam = familyStyle.get(style);
			if (fam == null) {
				fam = familyStyle.get(route);
			}
			if (fam != null) {
				return new Site(route, Layer.VILLAGES, fam, x, y, z);
			}
		}
		return null;
	}
}
