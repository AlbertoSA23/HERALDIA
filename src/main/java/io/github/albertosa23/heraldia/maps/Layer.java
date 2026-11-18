package io.github.albertosa23.heraldia.maps;

import java.util.Locale;

/**
 * Capas de marcadores de los mapas web, una por clase de estructura: cada una se activa con su opción
 * (mapas_web.capas.&lt;id&gt;), sale como capa propia que se puede ocultar en el mapa y lleva su icono y su color.
 */
public enum Layer {
	UNIQUES("unicas", 0xFFE0B030), VILLAGES("aldeas", 0xFF4CAF50), MEDIUMS("medianas", 0xFF3F8FD8), MINES("minas", 0xFF8D6E63),
	COAST("costa", 0xFF26A69A), ARENA("arena", 0xFFD84343);

	/** Color del icono (ARGB). */
	public final int color;

	/** Saved id (option, map layer, icon and ledger file): never renamed. */
	private final String id;

	Layer(String id, int color) {
		this.id = id;
		this.color = color;
	}

	/** Id en minúsculas: el de la opción, el de la capa en el mapa y el del icono (p. ej. «unicas»). */
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

	/** Opción que activa la capa. */
	public String option() {
		return "mapas_web.capas." + id();
	}

	/** Clave del nombre de la capa. */
	public String nameKey() {
		return "heraldia.mapas_web.capa." + id();
	}

	/** Clave de la descripción breve de sus marcadores. */
	public String descriptionKey() {
		return "heraldia.mapas_web.descripcion." + id();
	}

	/** Id de la capa en los mapas (prefijado para no chocar con las de otros mods). */
	public String mapId() {
		return "heraldia_" + id();
	}
}
