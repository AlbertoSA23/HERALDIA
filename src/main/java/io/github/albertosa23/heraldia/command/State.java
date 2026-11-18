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
 * Pure logic of /heraldia status: which Heraldia advancements some player has (online ones, from memory; the others,
 * from their advancement files), how many types of each kind have been discovered and the report's pagination.
 */
public final class State {
	public static final String NS = "heraldia:";
	public static final int PER_PAGE = 8;

	private State() {
	}

	/** Heraldia advancements earned by some player: the finished ones and, for each, the criteria met. */
	public static final class Achievements {
		final Set<String> finished = new HashSet<>();
		final Map<String, Set<String>> criteria = new HashMap<>();
		int players;

		/** Adds up a player's data: an advancement (finished or not) and its criteria met. */
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
		 * Adds up a player's advancement file (world/advancements/&lt;uuid&gt;.json: {"&lt;advancement&gt;": {"criteria":
		 * {"&lt;criterion&gt;": "&lt;date&gt;"}, "done": true}, "DataVersion": n}). Whatever is not understood is ignored.
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

	/** How many out of {@code total} and which are missing, in the given order. */
	public record Tally(int finished, int total, List<String> missing) {
	}

	/** Counts the elements of {@code ids} that {@code done} accepts. */
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

	/** Number of pages (at least 1). */
	public static int pages(int lines, int perPage) {
		return Math.max(1, (lines + perPage - 1) / perPage);
	}

	/** The lines of page {@code page} (from 1; clamped to the existing ones). */
	public static <T> List<T> page(List<T> lines, int page, int perPage) {
		int p = Math.clamp(page, 1, pages(lines.size(), perPage));
		int from = (p - 1) * perPage;
		return lines.subList(Math.min(from, lines.size()), Math.min(from + perPage, lines.size()));
	}
}
