package io.github.albertosa23.heraldia.comando;

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
	public static final String FICHERO = "heraldia_revision.json", INFORME = "heraldia_revision.md";
	/** Tamaños de las minas en el orden de la ruta (los de tools/gen/minas: pequeña, mediana, grande). */
	static final List<String> TAMANOS = List.of("pequena", "mediana", "grande");
	/** Tipos de la costa en el orden de la ruta (los de tools/gen/litoral). */
	static final List<String> COSTA = List.of("faro", "naufragio");
	private static final Gson GSON = new GsonBuilder().setPrettyPrinting().disableHtmlEscaping().create();
	private static final int NOTA_MAX = 256;

	private Revision() {
	}

	public enum Tipo { ALDEA, UNICA, MEDIANA, MINA, COSTA, ARENA, CAMINO }

	/** Una parada: id estable (p. ej. «unica/castillo»), su tipo y lo que la distingue (familia, única, tipo o tamaño). */
	public record Parada(String id, Tipo tipo, String sub) {
		static Parada de(Tipo t, String sub) {
			return new Parada(t.name().toLowerCase(Locale.ROOT) + (sub.isEmpty() ? "" : "/" + sub), t, sub);
		}
	}

	/**
	 * Las paradas, en orden: aldeas (una por familia, en el orden de {@code estiloFamilia}), únicas, medianas (por id),
	 * minas (pequeña, mediana, grande y, si hubiera otras, por id), la arena (si hay) y un tramo de camino (si los hay).
	 *
	 * @param estructuras   rutas de los ids de estructura de Heraldia registrados (p. ej. «unicas/castillo», «medianas/posada/llanura»)
	 * @param estiloFamilia estilo de aldea → familia, en el orden del esquema
	 * @param activa        si una parada puede salir en este mundo (familia, única o tipo activado)
	 */
	public static List<Parada> ruta(Collection<String> estructuras, Map<String, String> estiloFamilia, Predicate<Parada> activa,
									boolean arena, boolean caminos) {
		Set<String> familias = new LinkedHashSet<>();
		Set<String> presentes = new TreeSet<>(estructuras);
		for (Map.Entry<String, String> e : estiloFamilia.entrySet()) {
			if (presentes.contains(e.getKey()) || presentes.contains(e.getKey() + "_grande")) {
				familias.add(e.getValue());
			}
		}
		Set<String> unicas = new TreeSet<>(), medianas = new TreeSet<>(), minas = new TreeSet<>(Revision::ordenMina),
				costa = new TreeSet<>(Revision::ordenCosta);
		for (String p : presentes) {
			String[] s = p.split("/");
			if (s.length >= 2 && s[0].equals("unicas")) {
				unicas.add(s[1]);
			} else if (s.length >= 3 && s[0].equals("medianas")) {
				medianas.add(s[1]);
			} else if (s.length >= 3 && s[0].equals("minas")) {
				minas.add(s[1]);
			} else if (s.length >= 3 && s[0].equals("costa")) {
				costa.add(s[1]);
			}
		}
		List<Parada> out = new ArrayList<>();
		familias.forEach(f -> out.add(Parada.de(Tipo.ALDEA, f)));
		unicas.forEach(u -> out.add(Parada.de(Tipo.UNICA, u)));
		medianas.forEach(m -> out.add(Parada.de(Tipo.MEDIANA, m)));
		minas.forEach(m -> out.add(Parada.de(Tipo.MINA, m)));
		costa.forEach(c -> out.add(Parada.de(Tipo.COSTA, c)));
		if (arena) {
			out.add(Parada.de(Tipo.ARENA, ""));
		}
		if (caminos) {
			out.add(Parada.de(Tipo.CAMINO, ""));
		}
		out.removeIf(activa.negate());
		return List.copyOf(out);
	}

	/** Faro antes que naufragio (y, si hubiera otros, por id). */
	private static int ordenCosta(String a, String b) {
		int ia = COSTA.indexOf(a), ib = COSTA.indexOf(b);
		if (ia >= 0 || ib >= 0) {
			return ia < 0 ? 1 : ib < 0 ? -1 : Integer.compare(ia, ib);
		}
		return a.compareTo(b);
	}

	private static int ordenMina(String a, String b) {
		int ia = TAMANOS.indexOf(a), ib = TAMANOS.indexOf(b);
		if (ia >= 0 || ib >= 0) {
			return ia < 0 ? 1 : ib < 0 ? -1 : Integer.compare(ia, ib);
		}
		return a.compareTo(b);
	}

	/** Índice de la parada {@code id}, o -1. */
	public static int indice(List<Parada> ruta, String id) {
		for (int i = 0; i < ruta.size(); i++) {
			if (ruta.get(i).id().equals(id)) {
				return i;
			}
		}
		return -1;
	}

	/** Siguiente posición (ruta.size() = terminada). */
	public static int siguiente(List<Parada> ruta, int actual) {
		return Math.min(ruta.size(), Math.max(0, actual) + 1);
	}

	public static int anterior(List<Parada> ruta, int actual) {
		return Math.max(0, Math.min(actual, ruta.size()) - 1);
	}

	// --- progreso ---

	public enum Marca { REVISADA, PROBLEMA, SALTADA }

	/** Marca de una parada: cuándo (milisegundos de época) y una nota opcional (vacía si no hay). */
	public record Nota(Marca marca, String nota, long cuando) {
	}

	/** Progreso de un jugador: la parada en la que está y sus marcas (por id de parada, en el orden en que las puso). */
	public static final class Progreso {
		String nombre;
		int actual;
		final Map<String, Nota> notas = new LinkedHashMap<>();

		Progreso(String nombre) {
			this.nombre = nombre;
		}

		public int actual() {
			return actual;
		}

		public @Nullable Nota nota(String parada) {
			return notas.get(parada);
		}

		public Map<String, Nota> notas() {
			return notas;
		}

		public String nombre() {
			return nombre;
		}
	}

	/** El progreso de todos los jugadores (lo que se guarda en {@link #FICHERO}). Lo usa solo el hilo del servidor. */
	public static final class Registro {
		final Map<UUID, Progreso> jugadores = new LinkedHashMap<>();

		public Progreso de(UUID id, String nombre) {
			Progreso p = jugadores.computeIfAbsent(id, k -> new Progreso(nombre));
			p.nombre = nombre;
			return p;
		}

		public Map<UUID, Progreso> jugadores() {
			return jugadores;
		}

		/** Marca la parada (sustituye una marca anterior). La nota se recorta y se limpia de saltos de línea. */
		public void marcar(UUID id, String nombre, String parada, Marca m, String nota, long cuando) {
			de(id, nombre).notas.put(parada, new Nota(m, limpiar(nota), cuando));
		}

		public void reiniciar(UUID id) {
			jugadores.remove(id);
		}

		public JsonObject json() {
			JsonObject root = new JsonObject();
			root.addProperty("version", 1);
			JsonObject js = new JsonObject();
			jugadores.forEach((id, p) -> {
				JsonObject o = new JsonObject();
				o.addProperty("nombre", p.nombre);
				o.addProperty("actual", p.actual);
				JsonObject ns = new JsonObject();
				p.notas.forEach((k, n) -> {
					JsonObject x = new JsonObject();
					x.addProperty("marca", n.marca().name().toLowerCase(Locale.ROOT));
					if (!n.nota().isEmpty()) {
						x.addProperty("nota", n.nota());
					}
					x.addProperty("cuando", n.cuando());
					ns.add(k, x);
				});
				o.add("paradas", ns);
				js.add(id.toString(), o);
			});
			root.add("jugadores", js);
			return root;
		}

		/** Lee lo que escribe {@link #json()}; lo que no se entienda se ignora (nunca falla). */
		public static Registro desde(JsonObject root) {
			Registro r = new Registro();
			if (root == null || !root.has("jugadores") || !root.get("jugadores").isJsonObject()) {
				return r;
			}
			for (Map.Entry<String, JsonElement> e : root.getAsJsonObject("jugadores").entrySet()) {
				try {
					UUID id = UUID.fromString(e.getKey());
					JsonObject o = e.getValue().getAsJsonObject();
					Progreso p = r.de(id, o.has("nombre") ? o.get("nombre").getAsString() : e.getKey());
					p.actual = o.has("actual") ? Math.max(0, o.get("actual").getAsInt()) : 0;
					if (o.has("paradas") && o.get("paradas").isJsonObject()) {
						for (Map.Entry<String, JsonElement> n : o.getAsJsonObject("paradas").entrySet()) {
							JsonObject x = n.getValue().getAsJsonObject();
							Marca m = Marca.valueOf(x.get("marca").getAsString().toUpperCase(Locale.ROOT));
							p.notas.put(n.getKey(), new Nota(m, x.has("nota") ? limpiar(x.get("nota").getAsString()) : "",
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
		public Registro copia() {
			return desde(json());
		}
	}

	static String limpiar(@Nullable String nota) {
		if (nota == null) {
			return "";
		}
		String s = nota.replaceAll("[\\r\\n\\t]+", " ").strip();
		return s.length() > NOTA_MAX ? s.substring(0, NOTA_MAX) : s;
	}

	/** Lee el fichero; si no existe o no se entiende, un registro vacío. */
	public static Registro leer(Path file) {
		if (!Files.isRegularFile(file)) {
			return new Registro();
		}
		try {
			JsonElement e = JsonParser.parseString(Files.readString(file, StandardCharsets.UTF_8));
			return e.isJsonObject() ? Registro.desde(e.getAsJsonObject()) : new Registro();
		} catch (IOException | RuntimeException e) {
			return new Registro();
		}
	}

	/** Escribe a un temporal y lo sustituye (un corte a medias no deja el fichero roto). */
	public static void escribir(Path file, String texto) throws IOException {
		Path tmp = file.resolveSibling(file.getFileName() + ".tmp");
		Files.writeString(tmp, texto, StandardCharsets.UTF_8);
		try {
			Files.move(tmp, file, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
		} catch (AtomicMoveNotSupportedException e) {
			Files.move(tmp, file, StandardCopyOption.REPLACE_EXISTING);
		}
	}

	public static String json(Registro r) {
		return GSON.toJson(r.json()) + "\n";
	}

	/** Cuántas paradas de la ruta tienen cada marca y cuántas quedan sin marcar (pendientes). */
	public record Cuenta(int revisadas, int problemas, int saltadas, int pendientes) {
	}

	public static Cuenta cuenta(List<Parada> ruta, @Nullable Progreso p) {
		int[] n = new int[3];
		int pendientes = 0;
		for (Parada parada : ruta) {
			Nota nota = p == null ? null : p.notas.get(parada.id());
			if (nota == null) {
				pendientes++;
			} else {
				n[nota.marca().ordinal()]++;
			}
		}
		return new Cuenta(n[0], n[1], n[2], pendientes);
	}

	/**
	 * Resumen en Markdown (heraldia_revision.md en la carpeta del mundo): por jugador, cada parada de la ruta con su
	 * marca, su nota y la fecha (UTC), primero las que tienen un problema.
	 *
	 * @param nombre nombre legible de cada parada (en español)
	 */
	public static String markdown(List<Parada> ruta, Registro r, Function<Parada, String> nombre, long ahora) {
		DateTimeFormatter f = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm").withZone(ZoneOffset.UTC);
		StringBuilder sb = new StringBuilder();
		sb.append("# Revisión de Heraldia\n\n");
		sb.append("Generado el ").append(f.format(Instant.ofEpochMilli(ahora))).append(" (UTC) con /heraldia review. ")
				.append(ruta.size()).append(" paradas.\n");
		if (r.jugadores.isEmpty()) {
			sb.append("\nNadie ha marcado aún ninguna parada.\n");
		}
		for (Progreso p : r.jugadores.values()) {
			Cuenta c = cuenta(ruta, p);
			sb.append("\n## ").append(md(p.nombre)).append("\n\n");
			sb.append(c.revisadas()).append(" revisadas, ").append(c.problemas()).append(" con problema, ")
					.append(c.saltadas()).append(" saltadas, ").append(c.pendientes()).append(" pendientes.\n\n");
			sb.append("| Parada | Id | Estado | Nota | Fecha |\n| --- | --- | --- | --- | --- |\n");
			List<Parada> orden = new ArrayList<>();
			ruta.stream().filter(x -> marca(p, x) == Marca.PROBLEMA).forEach(orden::add);
			ruta.stream().filter(x -> marca(p, x) != Marca.PROBLEMA).forEach(orden::add);
			for (Parada x : orden) {
				Nota n = p.notas.get(x.id());
				sb.append("| ").append(md(nombre.apply(x))).append(" | `").append(x.id()).append("` | ")
						.append(n == null ? "pendiente" : estado(n.marca())).append(" | ")
						.append(n == null ? "" : md(n.nota())).append(" | ")
						.append(n == null || n.cuando() == 0 ? "" : f.format(Instant.ofEpochMilli(n.cuando()))).append(" |\n");
			}
			// marcas de paradas que ya no están en la ruta (una estructura desactivada después)
			for (Map.Entry<String, Nota> e : p.notas.entrySet()) {
				if (indice(ruta, e.getKey()) < 0) {
					sb.append("| (fuera de la ruta) | `").append(e.getKey()).append("` | ").append(estado(e.getValue().marca()))
							.append(" | ").append(md(e.getValue().nota())).append(" | |\n");
				}
			}
		}
		return sb.toString();
	}

	private static @Nullable Marca marca(Progreso p, Parada x) {
		Nota n = p.notas.get(x.id());
		return n == null ? null : n.marca();
	}

	static String estado(Marca m) {
		return switch (m) {
			case REVISADA -> "revisada";
			case PROBLEMA -> "**problema**";
			case SALTADA -> "saltada";
		};
	}

	/** Texto seguro dentro de una celda de tabla de Markdown. */
	static String md(String s) {
		return s.replace("\\", "\\\\").replace("|", "\\|").replace("<", "&lt;");
	}
}
