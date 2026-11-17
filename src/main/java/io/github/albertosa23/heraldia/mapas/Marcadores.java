package io.github.albertosa23.heraldia.mapas;

import io.github.albertosa23.heraldia.comando.Estado;
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
public final class Marcadores {
	/** Opciones en uso: mapas_web.activado, mapas_web.solo_descubiertas y las capas activadas. */
	public record Opciones(boolean activado, boolean soloDescubiertas, Set<Capa> capas) {
		public Opciones {
			capas = capas.isEmpty() ? Set.of() : Set.copyOf(EnumSet.copyOf(capas));
		}
	}

	private Marcadores() {
	}

	/**
	 * ¿Ha descubierto algún jugador el tipo de este sitio? Las mismas reglas que /heraldia status: aldeas, el logro de su
	 * familia (heraldia:aldeas/&lt;familia&gt;); únicas, heraldia:unicas/&lt;id&gt;/descubrir; medianas, el criterio de su tipo en
	 * heraldia:medianas/todas; minas, heraldia:minas/&lt;tamaño&gt;; faros y naufragios, heraldia:costa/&lt;tipo&gt;. La arena la coloca un operador: siempre cuenta.
	 */
	public static boolean descubierto(Capa capa, String sub, Estado.Logros l) {
		return switch (capa) {
			case ALDEAS -> l.hecho(Estado.NS + "aldeas/" + sub);
			case UNICAS -> l.hecho(Estado.NS + "unicas/" + sub + "/descubrir");
			case MEDIANAS -> l.criterio(Estado.NS + "medianas/todas", sub);
			case MINAS -> l.hecho(Estado.NS + "minas/" + sub);
			case COSTA -> l.hecho(Estado.NS + "costa/" + sub);
			case ARENA -> true;
		};
	}

	/** Clave del nombre de un sitio: el de su única, mediana o tamaño de mina; las aldeas, el de su familia. */
	static String claveNombre(Capa capa, String sub) {
		return switch (capa) {
			case ALDEAS -> "heraldia.familia." + sub;
			case UNICAS -> "heraldia.unicas." + sub + ".nombre";
			case MEDIANAS -> "heraldia.medianas." + sub + ".nombre";
			case MINAS -> "heraldia.minas." + sub + ".nombre";
			case COSTA -> "heraldia.costa." + sub + ".nombre";
			case ARENA -> "heraldia.arena.nombre";
		};
	}

	/** Nombre del marcador, en el idioma de {@code textos}: «Aldea: Llanuras», «Castillo del Rey Caído»... */
	static String nombre(Capa capa, String sub, Map<String, String> textos) {
		String base = texto(textos, claveNombre(capa, sub));
		return capa == Capa.ALDEAS ? formato(texto(textos, "heraldia.mapas_web.aldea"), base) : base;
	}

	/**
	 * Los marcadores que salen, en el orden del registro y, al final, la arena: nada si mapas_web.activado está apagado;
	 * de cada sitio, solo los de una capa activada y, con solo_descubiertas, los de un tipo descubierto.
	 *
	 * @param arena centro de la arena colocada (x, y, z) o null
	 */
	public static List<Marcador> construir(Collection<Sitio> sitios, int @Nullable [] arena, Estado.Logros logros, Opciones o,
										   Map<String, String> textos) {
		List<Marcador> out = new ArrayList<>();
		if (!o.activado()) {
			return out;
		}
		for (Sitio s : sitios) {
			if (!o.capas().contains(s.capa()) || o.soloDescubiertas() && !descubierto(s.capa(), s.sub(), logros)) {
				continue;
			}
			out.add(new Marcador(s.clave(), s.capa(), s.x(), s.y(), s.z(), nombre(s.capa(), s.sub(), textos),
					texto(textos, s.capa().claveDescripcion())));
		}
		if (arena != null && o.capas().contains(Capa.ARENA)) {
			out.add(new Marcador("arena", Capa.ARENA, arena[0], arena[1], arena[2], nombre(Capa.ARENA, "", textos),
					texto(textos, Capa.ARENA.claveDescripcion())));
		}
		return out;
	}

	/** Los marcadores por capa (todas las capas activadas, aunque estén vacías, para que el mapa las vacíe). */
	public static Map<Capa, List<Marcador>> porCapa(List<Marcador> marcadores, Opciones o) {
		Map<Capa, List<Marcador>> out = new EnumMap<>(Capa.class);
		if (o.activado()) {
			o.capas().forEach(c -> out.put(c, new ArrayList<>()));
		}
		for (Marcador m : marcadores) {
			out.computeIfAbsent(m.capa(), c -> new ArrayList<>()).add(m);
		}
		return out;
	}

	/** Nombres de las capas en el idioma de {@code textos}. */
	public static Map<Capa, String> nombresCapas(Map<String, String> textos) {
		Map<Capa, String> out = new EnumMap<>(Capa.class);
		for (Capa c : Capa.values()) {
			out.put(c, texto(textos, c.claveNombre()));
		}
		return out;
	}

	static String texto(Map<String, String> textos, String clave) {
		String t = textos.get(clave);
		return t != null ? t : clave;
	}

	private static String formato(String patron, String arg) {
		try {
			return String.format(Locale.ROOT, patron, arg);
		} catch (IllegalFormatException e) {
			return patron + " " + arg;
		}
	}
}
