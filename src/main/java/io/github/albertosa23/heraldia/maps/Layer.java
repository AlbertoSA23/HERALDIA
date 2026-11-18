package io.github.albertosa23.heraldia.maps;

import java.util.Locale;

/**
 * Marker layers of the web maps, one per structure kind: each is enabled with its option
 * (mapas_web.capas.&lt;id&gt;), shows as its own layer that can be hidden on the map and has its icon and color.
 */
public enum Layer {
	UNIQUES("unicas", 0xFFE0B030), VILLAGES("aldeas", 0xFF4CAF50), MEDIUMS("medianas", 0xFF3F8FD8), MINES("minas", 0xFF8D6E63),
	COAST("costa", 0xFF26A69A), ARENA("arena", 0xFFD84343);

	/** Icon color (ARGB). */
	public final int color;

	/** Saved id (option, map layer, icon and ledger file): never renamed. */
	private final String id;

	Layer(String id, int color) {
		this.id = id;
		this.color = color;
	}

	/** Lowercase id: the option's, the map layer's and the icon's (e.g. "unicas"). */
	public String id() {
		return id;
	}

	/** The layer with that id. */
	public static Layer of(String id) {
		for (Layer t : values()) {
			if (t.id.equals(id)) {
				return t;
			}
		}
		throw new IllegalArgumentException("No layer " + id);
	}

	/** Option that enables the layer. */
	public String option() {
		return "mapas_web.capas." + id();
	}

	/** Key of the layer's name. */
	public String nameKey() {
		return "heraldia.mapas_web.capa." + id();
	}

	/** Key of the short description of its markers. */
	public String descriptionKey() {
		return "heraldia.mapas_web.descripcion." + id();
	}

	/** Layer id on the maps (prefixed so it does not clash with other mods'). */
	public String mapId() {
		return "heraldia_" + id();
	}
}
