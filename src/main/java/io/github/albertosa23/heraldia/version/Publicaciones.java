package io.github.albertosa23.heraldia.version;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Base64;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import java.util.Optional;
import java.util.function.Function;

/**
 * Publicaciones del mod (lógica pura, sin red): lee la respuesta de la API de GitHub Releases
 * (GET /repos/&lt;dueño&gt;/&lt;repo&gt;/releases, donde publica .github/workflows/publish.yml de main) o la de versiones de
 * Modrinth (GET /v2/project/&lt;id&gt;/version), y elige la más nueva que sirve en este servidor. Tolerante: lo que no
 * entiende lo salta; una respuesta que no es una lista lanza {@link IllegalArgumentException}.
 */
public final class Publicaciones {
	/** Cuántas publicaciones de GitHub, como mucho, se miran para saber su Minecraft (una petición cada una). */
	public static final int MAX_CONSULTAS_MC = 3;

	private Publicaciones() {
	}

	/**
	 * Una publicación. `minecraft`: las versiones de Minecraft que declara (Modrinth); vacía si la fuente no lo dice
	 * (GitHub: se mira en el gradle.properties de su etiqueta). `cargadores`: vacía si no lo dice (GitHub: el mod solo
	 * es de Fabric).
	 */
	public record Publicacion(String nombre, Version version, boolean prepublicacion, String url, String etiqueta,
			List<String> minecraft, List<String> cargadores) {
		public Publicacion {
			minecraft = List.copyOf(minecraft);
			cargadores = List.copyOf(cargadores);
		}
	}

	/** Lee una respuesta de GitHub Releases o de Modrinth (se distinguen por sus campos). */
	public static List<Publicacion> leer(String json) {
		JsonElement raiz;
		try {
			raiz = JsonParser.parseString(json == null ? "" : json);
		} catch (RuntimeException e) {
			throw new IllegalArgumentException("la respuesta no es JSON: " + e.getMessage(), e);
		}
		if (!raiz.isJsonArray()) {
			throw new IllegalArgumentException("la respuesta no es una lista de publicaciones");
		}
		List<Publicacion> out = new ArrayList<>();
		for (JsonElement e : raiz.getAsJsonArray()) {
			if (!e.isJsonObject()) {
				continue;
			}
			JsonObject o = e.getAsJsonObject();
			Optional<Publicacion> p = o.has("tag_name") ? deGitHub(o) : o.has("version_number") ? deModrinth(o) : Optional.empty();
			p.ifPresent(out::add);
		}
		return out;
	}

	static Optional<Publicacion> deGitHub(JsonObject o) {
		if (bool(o, "draft")) {
			return Optional.empty();
		}
		String etiqueta = texto(o, "tag_name");
		Optional<Version> v = Version.de(etiqueta);
		String url = texto(o, "html_url");
		if (v.isEmpty() || !web(url) || !conJar(o)) {
			return Optional.empty();
		}
		String nombre = texto(o, "name");
		return Optional.of(new Publicacion(nombre.isBlank() ? etiqueta : nombre, v.get(),
				bool(o, "prerelease") || v.get().prepublicacion(), url, etiqueta, List.of(), List.of()));
	}

	/** Una publicación de GitHub sin ningún .jar del mod (ni -sources ni -dev) no tiene nada que descargar. */
	private static boolean conJar(JsonObject o) {
		if (!o.has("assets") || !o.get("assets").isJsonArray()) {
			return true;
		}
		for (JsonElement a : o.getAsJsonArray("assets")) {
			String n = a.isJsonObject() ? texto(a.getAsJsonObject(), "name").toLowerCase(Locale.ROOT) : "";
			if (n.endsWith(".jar") && !n.endsWith("-sources.jar") && !n.endsWith("-dev.jar") && !n.endsWith("-javadoc.jar")) {
				return true;
			}
		}
		return false;
	}

	static Optional<Publicacion> deModrinth(JsonObject o) {
		String estado = texto(o, "status");
		if (!estado.isEmpty() && !estado.equals("listed")) {
			return Optional.empty();
		}
		Optional<Version> v = Version.de(texto(o, "version_number"));
		String proyecto = texto(o, "project_id"), id = texto(o, "id");
		if (v.isEmpty() || proyecto.isEmpty() || id.isEmpty() || !proyecto.matches("[A-Za-z0-9_-]+") || !id.matches("[A-Za-z0-9_-]+")) {
			return Optional.empty();
		}
		String tipo = texto(o, "version_type");
		String nombre = texto(o, "name");
		return Optional.of(new Publicacion(nombre.isBlank() ? texto(o, "version_number") : nombre, v.get(),
				!tipo.equals("release") || v.get().prepublicacion(), "https://modrinth.com/mod/" + proyecto + "/version/" + id,
				texto(o, "version_number"), textos(o, "game_versions"), textos(o, "loaders")));
	}

	/**
	 * La más nueva que la `actual`, para este Minecraft y con Fabric (sin pre-publicaciones salvo `prepublicaciones`).
	 * `minecraftDe` da el Minecraft de una publicación que no lo declara (GitHub); se pregunta como mucho por
	 * {@link #MAX_CONSULTAS_MC}, de la más nueva a la más vieja. Vacío si no hay ninguna (o no se sabe para cuál sirve).
	 */
	public static Optional<Publicacion> elegir(List<Publicacion> todas, Version actual, String minecraft, boolean prepublicaciones,
			Function<Publicacion, Optional<String>> minecraftDe) {
		List<Publicacion> candidatas = new ArrayList<>();
		for (Publicacion p : todas) {
			if (p.version().compareTo(actual) > 0 && (prepublicaciones || !p.prepublicacion())
					&& (p.cargadores().isEmpty() || p.cargadores().contains("fabric"))) {
				candidatas.add(p);
			}
		}
		candidatas.sort(Comparator.comparing(Publicacion::version).reversed());
		int consultas = 0;
		for (Publicacion p : candidatas) {
			if (!p.minecraft().isEmpty()) {
				if (p.minecraft().contains(minecraft.toLowerCase(Locale.ROOT))) {
					return Optional.of(p);
				}
				continue;
			}
			if (consultas++ >= MAX_CONSULTAS_MC) {
				break;
			}
			Optional<String> mc = minecraftDe.apply(p);
			if (mc.isPresent() && Version.mismoMinecraft(mc.get(), minecraft)) {
				return Optional.of(p);
			}
		}
		return Optional.empty();
	}

	/**
	 * El minecraft_version de un gradle.properties (el de la etiqueta de la publicación, de la API de contenidos de
	 * GitHub): el texto tal cual o el JSON de la API con el contenido en base64.
	 */
	public static Optional<String> minecraftDePropiedades(String respuesta) {
		if (respuesta == null) {
			return Optional.empty();
		}
		String texto = respuesta;
		if (texto.stripLeading().startsWith("{")) {
			try {
				JsonObject o = JsonParser.parseString(texto).getAsJsonObject();
				texto = new String(Base64.getMimeDecoder().decode(texto(o, "content")), StandardCharsets.UTF_8);
			} catch (RuntimeException e) {
				return Optional.empty();
			}
		}
		for (String linea : texto.split("\\R")) {
			String l = linea.strip();
			if (l.startsWith("minecraft_version") && l.contains("=")) {
				String k = l.substring(0, l.indexOf('=')).strip();
				String v = l.substring(l.indexOf('=') + 1).strip();
				if (k.equals("minecraft_version") && Version.de(v).isPresent()) {
					return Optional.of(v);
				}
			}
		}
		return Optional.empty();
	}

	/** Solo enlaces web: lo que se ofrece para hacer clic no puede ser otra cosa. */
	static boolean web(String url) {
		return url.startsWith("https://") || url.startsWith("http://");
	}

	private static String texto(JsonObject o, String k) {
		JsonElement e = o.get(k);
		return e != null && e.isJsonPrimitive() ? e.getAsString() : "";
	}

	private static boolean bool(JsonObject o, String k) {
		JsonElement e = o.get(k);
		return e != null && e.isJsonPrimitive() && e.getAsJsonPrimitive().isBoolean() && e.getAsBoolean();
	}

	private static List<String> textos(JsonObject o, String k) {
		List<String> out = new ArrayList<>();
		JsonElement e = o.get(k);
		if (e != null && e.isJsonArray()) {
			for (JsonElement x : (JsonArray) e) {
				if (x.isJsonPrimitive()) {
					out.add(x.getAsString().toLowerCase(Locale.ROOT));
				}
			}
		}
		return out;
	}
}
