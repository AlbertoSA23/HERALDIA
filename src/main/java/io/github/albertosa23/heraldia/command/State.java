package io.github.albertosa23.heraldia.command;

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
 * Lógica pura de /heraldia status: qué logros de Heraldia tiene algún jugador (los conectados, de memoria; los demás,
 * de sus ficheros de logros), cuántos tipos de cada clase se han descubierto y la paginación del informe.
 */
public final class State {
	public static final String NS = "heraldia:";
	public static final int PER_PAGE = 8;

	private State() {
	}

	/** Logros de Heraldia conseguidos por algún jugador: los terminados y, de cada uno, los criterios cumplidos. */
	public static final class Achievements {
		final Set<String> finished = new HashSet<>();
		final Map<String, Set<String>> criteria = new HashMap<>();
		int players;

		/** Suma lo de un jugador: un logro (terminado o no) y sus criterios cumplidos. */
		public void add(String advancement, boolean done, Iterable<String> met) {
			if (!advancement.startsWith(NS)) {
				return;
			}
			if (done) {
				finished.add(advancement);
			}
			for (String c : met) {
				criteria.computeIfAbsent(advancement, k -> new HashSet<>()).add(c);
			}
		}

		public void player() {
			players++;
		}

		public int players() {
			return players;
		}

		public boolean done(String advancement) {
			return finished.contains(advancement);
		}

		public boolean criterion(String advancement, String criterion) {
			return criteria.getOrDefault(advancement, Set.of()).contains(criterion);
		}

		/**
		 * Suma un fichero de logros de un jugador (world/advancements/&lt;uuid&gt;.json: {"&lt;logro&gt;": {"criteria":
		 * {"&lt;criterio&gt;": "&lt;fecha&gt;"}, "done": true}, "DataVersion": n}). Lo que no se entienda se ignora.
		 */
		public void addFile(JsonObject o) {
			player();
			for (Map.Entry<String, JsonElement> e : o.entrySet()) {
				if (!e.getKey().startsWith(NS) || !e.getValue().isJsonObject()) {
					continue;
				}
				JsonObject a = e.getValue().getAsJsonObject();
				boolean done = a.has("done") && a.get("done").isJsonPrimitive() && a.get("done").getAsBoolean();
				List<String> cs = new ArrayList<>();
				if (a.has("criteria") && a.get("criteria").isJsonObject()) {
					cs.addAll(a.getAsJsonObject("criteria").keySet());
				}
				add(e.getKey(), done, cs);
			}
		}
	}

	/** Cuántos de {@code total} y cuáles faltan, en el orden dado. */
	public record Tally(int finished, int total, List<String> missing) {
	}

	/** Cuenta los elementos de {@code ids} que cumple {@code done}. */
	public static Tally count(Collection<String> ids, java.util.function.Predicate<String> done) {
		int n = 0;
		List<String> missing = new ArrayList<>();
		for (String id : ids) {
			if (done.test(id)) {
				n++;
			} else {
				missing.add(id);
			}
		}
		return new Tally(n, ids.size(), List.copyOf(missing));
	}

	/** Número de páginas (al menos 1). */
	public static int pages(int lines, int perPage) {
		return Math.max(1, (lines + perPage - 1) / perPage);
	}

	/** Las líneas de la página {@code pagina} (desde 1; se acota a las que hay). */
	public static <T> List<T> pagina(List<T> lines, int pagina, int perPage) {
		int p = Math.clamp(pagina, 1, pages(lines.size(), perPage));
		int from = (p - 1) * perPage;
		return lines.subList(Math.min(from, lines.size()), Math.min(from + perPage, lines.size()));
	}
}
