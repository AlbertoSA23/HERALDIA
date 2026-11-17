package io.github.albertosa23.heraldia.mapas;

import java.util.Locale;

/**
 * Capas de marcadores de los mapas web, una por clase de estructura: cada una se activa con su opción
 * (mapas_web.capas.&lt;id&gt;), sale como capa propia que se puede ocultar en el mapa y lleva su icono y su color.
 */
public enum Capa {
	UNICAS(0xFFE0B030), ALDEAS(0xFF4CAF50), MEDIANAS(0xFF3F8FD8), MINAS(0xFF8D6E63), ARENA(0xFFD84343);

	/** Color del icono (ARGB). */
	public final int color;

	Capa(int color) {
		this.color = color;
	}

	/** Id en minúsculas: el de la opción, el de la capa en el mapa y el del icono (p. ej. «unicas»). */
	public String id() {
		return name().toLowerCase(Locale.ROOT);
	}

	/** Opción que activa la capa. */
	public String opcion() {
		return "mapas_web.capas." + id();
	}

	/** Clave del nombre de la capa. */
	public String claveNombre() {
		return "heraldia.mapas_web.capa." + id();
	}

	/** Clave de la descripción breve de sus marcadores. */
	public String claveDescripcion() {
		return "heraldia.mapas_web.descripcion." + id();
	}

	/** Id de la capa en los mapas (prefijado para no chocar con las de otros mods). */
	public String idMapa() {
		return "heraldia_" + id();
	}
}
