package io.github.albertosa23.heraldia.command;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.AtomicMoveNotSupportedException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.time.Instant;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;
import java.util.UUID;
import java.util.function.Function;
import java.util.function.Predicate;
import org.jspecify.annotations.Nullable;

/**
 * Ruta de revisión de /heraldia review, lógica pura (sin clases del juego): las paradas, en orden, de cada tipo de
 * contenido visual (aldeas por familia, cada única, cada tipo de mediana, minas de cada tamaño, el faro y el naufragio, la arena y un tramo de
 * camino), la navegación, el progreso de cada jugador (marcas y notas), su fichero JSON y el resumen en Markdown.
 */
public final class Revision {
	public static final String FILE = "heraldia_revision.json", REPORT = "heraldia_revision.md";
	/** Tamaños de las minas en el orden de la ruta (los de tools/gen/minas: pequeña, mediana, grande). */
	static final List<String> SIZES = List.of("pequena", "mediana", "grande");
	/** Tipos de la costa en el orden de la ruta (los de tools/gen/litoral). */
	static final List<String> COAST = List.of("faro", "naufragio");
	private static final Gson GSON = new GsonBuilder().setPrettyPrinting().disableHtmlEscaping().create();
	private static final int NOTE_MAX = 256;

	private Revision() {
	}

	public enum Type { VILLAGE, UNIQUE, MEDIUM, MINE, COAST, ARENA, ROAD }

	/** Una parada: id estable (p. ej. «unica/castillo»), su tipo y lo que la distingue (familia, única, tipo o tamaño). */
	public record Stop(String id, Type type, String sub) {
		static Stop of(Type t, String sub) {
			return new Stop(t.name().toLowerCase(Locale.ROOT) + (sub.isEmpty() ? "" : "/" + sub), t, sub);
		}
	}

	/**
	 * Las paradas, en orden: aldeas (una por familia, en el orden de {@code familyStyle}), únicas, medianas (por id),
	 * minas (pequeña, mediana, grande y, si hubiera otras, por id), la arena (si hay) y un tramo de camino (si los hay).
	 *
	 * @param estructuras   rutas de los ids de estructura de Heraldia registrados (p. ej. «unicas/castillo», «medianas/posada/llanura»)
	 * @param estiloFamilia estilo de aldea → familia, en el orden del esquema
	 * @param activa        si una parada puede salir en este mundo (familia, única o tipo activado)
	 */
	public static List<Stop> route(Collection<String> structures, Map<String, String> familyStyle, Predicate<Stop> active,
									boolean arena, boolean roads) {
		Set<String> families = new LinkedHashSet<>();
		Set<String> present = new TreeSet<>(structures);
		for (Map.Entry<String, String> e : familyStyle.entrySet()) {
			if (present.contains(e.getKey()) || present.contains(e.getKey() + "_grande")) {
				families.add(e.getValue());
			}
		}
		Set<String> uniques = new TreeSet<>(), mediums = new TreeSet<>(), mines = new TreeSet<>(Revision::mineOrder),
				coast = new TreeSet<>(Revision::coastOrder);
		for (String p : present) {
			String[] s = p.split("/");
			if (s.length >= 2 && s[0].equals("unicas")) {
				uniques.add(s[1]);
			} else if (s.length >= 3 && s[0].equals("medianas")) {
				mediums.add(s[1]);
			} else if (s.length >= 3 && s[0].equals("minas")) {
				mines.add(s[1]);
			} else if (s.length >= 3 && s[0].equals("costa")) {
				coast.add(s[1]);
			}
		}
		List<Stop> out = new ArrayList<>();
		families.forEach(f -> out.add(Stop.of(Type.VILLAGE, f)));
		uniques.forEach(u -> out.add(Stop.of(Type.UNIQUE, u)));
		mediums.forEach(m -> out.add(Stop.of(Type.MEDIUM, m)));
		mines.forEach(m -> out.add(Stop.of(Type.MINE, m)));
		coast.forEach(c -> out.add(Stop.of(Type.COAST, c)));
		if (arena) {
			out.add(Stop.of(Type.ARENA, ""));
		}
		if (roads) {
			out.add(Stop.of(Type.ROAD, ""));
		}
		out.removeIf(active.negate());
		return List.copyOf(out);
	}

	/** Faro antes que naufragio (y, si hubiera otros, por id). */
	private static int coastOrder(String a, String b) {
		int ia = COAST.indexOf(a), ib = COAST.indexOf(b);
		if (ia >= 0 || ib >= 0) {
			return ia < 0 ? 1 : ib < 0 ? -1 : Integer.compare(ia, ib);
		}
		return a.compareTo(b);
	}

	private static int mineOrder(String a, String b) {
		int ia = SIZES.indexOf(a), ib = SIZES.indexOf(b);
		if (ia >= 0 || ib >= 0) {
			return ia < 0 ? 1 : ib < 0 ? -1 : Integer.compare(ia, ib);
		}
		return a.compareTo(b);
	}

	/** Índice de la parada {@code id}, o -1. */
	public static int index(List<Stop> route, String id) {
		for (int i = 0; i < route.size(); i++) {
			if (route.get(i).id().equals(id)) {
				return i;
			}
		}
		return -1;
	}

	/** Siguiente posición (ruta.size() = terminada). */
	public static int next(List<Stop> route, int actual) {
		return Math.min(route.size(), Math.max(0, actual) + 1);
	}

	public static int previous(List<Stop> route, int actual) {
		return Math.max(0, Math.min(actual, route.size()) - 1);
	}

	// --- progreso ---

	public enum Mark { REVIEWED, PROBLEM, SKIPPED }

	/** Marca de una parada: cuándo (milisegundos de época) y una nota opcional (vacía si no hay). */
	public record Note(Mark mark, String note, long when) {
	}

	/** Progreso de un jugador: la parada en la que está y sus marcas (por id de parada, en el orden en que las puso). */
	public static final class Progress {
		String name;
		int actual;
		final Map<String, Note> notes = new LinkedHashMap<>();

		Progress(String name) {
			this.name = name;
		}

		public int actual() {
			return actual;
		}

		public @Nullable Note note(String stop) {
			return notes.get(stop);
		}

		public Map<String, Note> notes() {
			return notes;
		}

		public String name() {
			return name;
		}
	}

	/** El progreso de todos los jugadores (lo que se guarda en {@link #FILE}). Lo usa solo el hilo del servidor. */
	public static final class Ledger {
		final Map<UUID, Progress> players = new LinkedHashMap<>();

		public Progress of(UUID id, String name) {
			Progress p = players.computeIfAbsent(id, k -> new Progress(name));
			p.name = name;
			return p;
		}

		public Map<UUID, Progress> players() {
			return players;
		}

		/** Marca la parada (sustituye una marca anterior). La nota se recorta y se limpia de saltos de línea. */
		public void markStop(UUID id, String name, String stop, Mark m, String note, long when) {
			of(id, name).notes.put(stop, new Note(m, clean(note), when));
		}

		public void reset(UUID id) {
			players.remove(id);
		}

		public JsonObject json() {
			JsonObject root = new JsonObject();
			root.addProperty("version", 1);
			JsonObject js = new JsonObject();
			players.forEach((id, p) -> {
				JsonObject o = new JsonObject();
				o.addProperty("nombre", p.name);
				o.addProperty("actual", p.actual);
				JsonObject ns = new JsonObject();
				p.notes.forEach((k, n) -> {
					JsonObject x = new JsonObject();
					x.addProperty("marca", n.mark().name().toLowerCase(Locale.ROOT));
					if (!n.note().isEmpty()) {
						x.addProperty("nota", n.note());
					}
					x.addProperty("cuando", n.when());
					ns.add(k, x);
				});
				o.add("paradas", ns);
				js.add(id.toString(), o);
			});
			root.add("jugadores", js);
			return root;
		}

		/** Lee lo que escribe {@link #json()}; lo que no se entienda se ignora (nunca falla). */
		public static Ledger from(JsonObject root) {
			Ledger r = new Ledger();
			if (root == null || !root.has("jugadores") || !root.get("jugadores").isJsonObject()) {
				return r;
			}
			for (Map.Entry<String, JsonElement> e : root.getAsJsonObject("jugadores").entrySet()) {
				try {
					UUID id = UUID.fromString(e.getKey());
					JsonObject o = e.getValue().getAsJsonObject();
					Progress p = r.of(id, o.has("nombre") ? o.get("nombre").getAsString() : e.getKey());
					p.actual = o.has("actual") ? Math.max(0, o.get("actual").getAsInt()) : 0;
					if (o.has("paradas") && o.get("paradas").isJsonObject()) {
						for (Map.Entry<String, JsonElement> n : o.getAsJsonObject("paradas").entrySet()) {
							JsonObject x = n.getValue().getAsJsonObject();
							Mark m = Mark.valueOf(x.get("marca").getAsString().toUpperCase(Locale.ROOT));
							p.notes.put(n.getKey(), new Note(m, x.has("nota") ? clean(x.get("nota").getAsString()) : "",
									x.has("cuando") ? x.get("cuando").getAsLong() : 0));
						}
					}
				} catch (RuntimeException ignored) {
					// jugador o parada mal escritos: se ignora ese, el resto se conserva
				}
			}
			return r;
		}

		/** Copia profunda (para escribirla fuera del hilo del servidor). */
		public Ledger backup() {
			return from(json());
		}
	}

	static String clean(@Nullable String note) {
		if (note == null) {
			return "";
		}
		String s = note.replaceAll("[\\r\\n\\t]+", " ").strip();
		return s.length() > NOTE_MAX ? s.substring(0, NOTE_MAX) : s;
	}

	/** Lee el fichero; si no existe o no se entiende, un registro vacío. */
	public static Ledger read(Path file) {
		if (!Files.isRegularFile(file)) {
			return new Ledger();
		}
		try {
			JsonElement e = JsonParser.parseString(Files.readString(file, StandardCharsets.UTF_8));
			return e.isJsonObject() ? Ledger.from(e.getAsJsonObject()) : new Ledger();
		} catch (IOException | RuntimeException e) {
			return new Ledger();
		}
	}

	/** Escribe a un temporal y lo sustituye (un corte a medias no deja el fichero roto). */
	public static void write(Path file, String text) throws IOException {
		Path tmp = file.resolveSibling(file.getFileName() + ".tmp");
		Files.writeString(tmp, text, StandardCharsets.UTF_8);
		try {
			Files.move(tmp, file, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
		} catch (AtomicMoveNotSupportedException e) {
			Files.move(tmp, file, StandardCopyOption.REPLACE_EXISTING);
		}
	}

	public static String json(Ledger r) {
		return GSON.toJson(r.json()) + "\n";
	}

	/** Cuántas paradas de la ruta tienen cada marca y cuántas quedan sin marcar (pendientes). */
	public record Tally(int reviewedCount, int problems, int skipped, int pending) {
	}

	public static Tally tally(List<Stop> route, @Nullable Progress p) {
		int[] n = new int[3];
		int pending = 0;
		for (Stop stop : route) {
			Note note = p == null ? null : p.notes.get(stop.id());
			if (note == null) {
				pending++;
			} else {
				n[note.mark().ordinal()]++;
			}
		}
		return new Tally(n[0], n[1], n[2], pending);
	}

	/**
	 * Resumen en Markdown (heraldia_revision.md en la carpeta del mundo): por jugador, cada parada de la ruta con su
	 * marca, su nota y la fecha (UTC), primero las que tienen un problema.
	 *
	 * @param nombre nombre legible de cada parada (en español)
	 */
	public static String markdown(List<Stop> route, Ledger r, Function<Stop, String> name, long now) {
		DateTimeFormatter f = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm").withZone(ZoneOffset.UTC);
		StringBuilder sb = new StringBuilder();
		sb.append("# Revisión de Heraldia\n\n");
		sb.append("Generado el ").append(f.format(Instant.ofEpochMilli(now))).append(" (UTC) con /heraldia review. ")
				.append(route.size()).append(" paradas.\n");
		if (r.players.isEmpty()) {
			sb.append("\nNadie ha marcado aún ninguna parada.\n");
		}
		for (Progress p : r.players.values()) {
			Tally c = tally(route, p);
			sb.append("\n## ").append(md(p.name)).append("\n\n");
			sb.append(c.reviewedCount()).append(" revisadas, ").append(c.problems()).append(" con problema, ")
					.append(c.skipped()).append(" saltadas, ").append(c.pending()).append(" pendientes.\n\n");
			sb.append("| Parada | Id | Estado | Nota | Fecha |\n| --- | --- | --- | --- | --- |\n");
			List<Stop> order = new ArrayList<>();
			route.stream().filter(x -> mark(p, x) == Mark.PROBLEM).forEach(order::add);
			route.stream().filter(x -> mark(p, x) != Mark.PROBLEM).forEach(order::add);
			for (Stop x : order) {
				Note n = p.notes.get(x.id());
				sb.append("| ").append(md(name.apply(x))).append(" | `").append(x.id()).append("` | ")
						.append(n == null ? "pendiente" : state(n.mark())).append(" | ")
						.append(n == null ? "" : md(n.note())).append(" | ")
						.append(n == null || n.when() == 0 ? "" : f.format(Instant.ofEpochMilli(n.when()))).append(" |\n");
			}
			// marcas de paradas que ya no están en la ruta (una estructura desactivada después)
			for (Map.Entry<String, Note> e : p.notes.entrySet()) {
				if (index(route, e.getKey()) < 0) {
					sb.append("| (fuera de la ruta) | `").append(e.getKey()).append("` | ").append(state(e.getValue().mark()))
							.append(" | ").append(md(e.getValue().note())).append(" | |\n");
				}
			}
		}
		return sb.toString();
	}

	private static @Nullable Mark mark(Progress p, Stop x) {
		Note n = p.notes.get(x.id());
		return n == null ? null : n.mark();
	}

	static String state(Mark m) {
		return switch (m) {
			case REVIEWED -> "revisada";
			case PROBLEM -> "**problema**";
			case SKIPPED -> "saltada";
		};
	}

	/** Texto seguro dentro de una celda de tabla de Markdown. */
	static String md(String s) {
		return s.replace("\\", "\\\\").replace("|", "\\|").replace("<", "&lt;");
	}
}
