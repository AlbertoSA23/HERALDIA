package io.github.albertosa23.heraldia.maps;

import java.util.Map;
import org.jspecify.annotations.Nullable;

/**
 * Una estructura de Heraldia conocida (generada en un chunk que se ha cargado alguna vez), lógica pura: el id de su
 * estructura (ruta sin el espacio de nombres, p. ej. «unicas/castillo»), su capa, lo que distingue su tipo (familia,
 * única, tipo de mediana o tamaño de mina: lo que mira /heraldia status para saber si alguien la ha descubierto) y la
 * posición del centro de su caja.
 */
public record Site(String structure, Layer layer, String sub, int x, int y, int z) {
	/** Clave estable: la estructura y su posición (no hay dos inicios de la misma estructura en el mismo sitio). */
	public String key() {
		return structure + "@" + x + "," + y + "," + z;
	}

	/**
	 * Clasifica una estructura de Heraldia por la ruta de su id (sin «heraldia:»): las aldeas son «&lt;estilo&gt;» o
	 * «&lt;estilo&gt;_grande» (familia de {@code familyStyle}), las únicas «unicas/&lt;id&gt;», las medianas
	 * «medianas/&lt;tipo&gt;/&lt;estilo&gt;» las entradas de mina «minas/&lt;tamaño&gt;/...» y los faros y naufragios «costa/&lt;tipo&gt;/...». Lo demás (la arena no es una
	 * estructura del registro), null.
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
