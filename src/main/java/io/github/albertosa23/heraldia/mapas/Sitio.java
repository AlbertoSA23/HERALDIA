package io.github.albertosa23.heraldia.mapas;

import java.util.Map;
import org.jspecify.annotations.Nullable;

/**
 * Una estructura de Heraldia conocida (generada en un chunk que se ha cargado alguna vez), lógica pura: el id de su
 * estructura (ruta sin el espacio de nombres, p. ej. «unicas/castillo»), su capa, lo que distingue su tipo (familia,
 * única, tipo de mediana o tamaño de mina: lo que mira /heraldia status para saber si alguien la ha descubierto) y la
 * posición del centro de su caja.
 */
public record Sitio(String estructura, Capa capa, String sub, int x, int y, int z) {
	/** Clave estable: la estructura y su posición (no hay dos inicios de la misma estructura en el mismo sitio). */
	public String clave() {
		return estructura + "@" + x + "," + y + "," + z;
	}

	/**
	 * Clasifica una estructura de Heraldia por la ruta de su id (sin «heraldia:»): las aldeas son «&lt;estilo&gt;» o
	 * «&lt;estilo&gt;_grande» (familia de {@code estiloFamilia}), las únicas «unicas/&lt;id&gt;», las medianas
	 * «medianas/&lt;tipo&gt;/&lt;estilo&gt;» y las entradas de mina «minas/&lt;tamaño&gt;/...». Lo demás (la arena no es una
	 * estructura del registro), null.
	 */
	public static @Nullable Sitio de(String ruta, Map<String, String> estiloFamilia, int x, int y, int z) {
		String[] s = ruta.split("/");
		if (s.length >= 2 && s[0].equals("unicas") && !s[1].isEmpty()) {
			return new Sitio(ruta, Capa.UNICAS, s[1], x, y, z);
		}
		if (s.length >= 3 && s[0].equals("medianas") && !s[1].isEmpty()) {
			return new Sitio(ruta, Capa.MEDIANAS, s[1], x, y, z);
		}
		if (s.length >= 3 && s[0].equals("minas") && !s[1].isEmpty()) {
			return new Sitio(ruta, Capa.MINAS, s[1], x, y, z);
		}
		if (s.length == 1) {
			String estilo = ruta.endsWith("_grande") ? ruta.substring(0, ruta.length() - "_grande".length()) : ruta;
			String fam = estiloFamilia.get(estilo);
			if (fam == null) {
				fam = estiloFamilia.get(ruta);
			}
			if (fam != null) {
				return new Sitio(ruta, Capa.ALDEAS, fam, x, y, z);
			}
		}
		return null;
	}
}
