package io.github.albertosa23.heraldia.comando;

import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import java.util.ArrayList;
import java.util.Collection;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Lógica pura de /heraldia estado: qué logros de Heraldia tiene algún jugador (los conectados, de memoria; los demás,
 * de sus ficheros de logros), cuántos tipos de cada clase se han descubierto y la paginación del informe.
 */
public final class Estado {
	public static final String NS = "heraldia:";
	public static final int POR_PAGINA = 8;

	private Estado() {
	}

	/** Logros de Heraldia conseguidos por algún jugador: los terminados y, de cada uno, los criterios cumplidos. */
	public static final class Logros {
		final Set<String> hechos = new HashSet<>();
		final Map<String, Set<String>> criterios = new HashMap<>();
		int jugadores;

		/** Suma lo de un jugador: un logro (terminado o no) y sus criterios cumplidos. */
		public void sumar(String logro, boolean hecho, Iterable<String> cumplidos) {
			if (!logro.startsWith(NS)) {
				return;
			}
			if (hecho) {
				hechos.add(logro);
			}
			for (String c : cumplidos) {
				criterios.computeIfAbsent(logro, k -> new HashSet<>()).add(c);
			}
		}

		public void jugador() {
			jugadores++;
		}

		public int jugadores() {
			return jugadores;
		}

		public boolean hecho(String logro) {
			return hechos.contains(logro);
		}

		public boolean criterio(String logro, String criterio) {
			return criterios.getOrDefault(logro, Set.of()).contains(criterio);
		}

		/**
		 * Suma un fichero de logros de un jugador (world/advancements/&lt;uuid&gt;.json: {"&lt;logro&gt;": {"criteria":
		 * {"&lt;criterio&gt;": "&lt;fecha&gt;"}, "done": true}, "DataVersion": n}). Lo que no se entienda se ignora.
		 */
		public void sumarFichero(JsonObject o) {
			jugador();
			for (Map.Entry<String, JsonElement> e : o.entrySet()) {
				if (!e.getKey().startsWith(NS) || !e.getValue().isJsonObject()) {
					continue;
				}
				JsonObject a = e.getValue().getAsJsonObject();
				boolean hecho = a.has("done") && a.get("done").isJsonPrimitive() && a.get("done").getAsBoolean();
				List<String> cs = new ArrayList<>();
				if (a.has("criteria") && a.get("criteria").isJsonObject()) {
					cs.addAll(a.getAsJsonObject("criteria").keySet());
				}
				sumar(e.getKey(), hecho, cs);
			}
		}
	}

	/** Cuántos de {@code total} y cuáles faltan, en el orden dado. */
	public record Cuenta(int hechos, int total, List<String> faltan) {
	}

	/** Cuenta los elementos de {@code ids} que cumple {@code hecho}. */
	public static Cuenta contar(Collection<String> ids, java.util.function.Predicate<String> hecho) {
		int n = 0;
		List<String> faltan = new ArrayList<>();
		for (String id : ids) {
			if (hecho.test(id)) {
				n++;
			} else {
				faltan.add(id);
			}
		}
		return new Cuenta(n, ids.size(), List.copyOf(faltan));
	}

	/** Número de páginas (al menos 1). */
	public static int paginas(int lineas, int porPagina) {
		return Math.max(1, (lineas + porPagina - 1) / porPagina);
	}

	/** Las líneas de la página {@code pagina} (desde 1; se acota a las que hay). */
	public static <T> List<T> pagina(List<T> lineas, int pagina, int porPagina) {
		int p = Math.clamp(pagina, 1, paginas(lineas.size(), porPagina));
		int desde = (p - 1) * porPagina;
		return lineas.subList(Math.min(desde, lineas.size()), Math.min(desde + porPagina, lineas.size()));
	}
}
