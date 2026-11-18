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
public final class Releases {
	/** Cuántas publicaciones de GitHub, como mucho, se miran para saber su Minecraft (una petición cada una). */
	public static final int MAX_MC_QUERIES = 3;

	private Releases() {
	}

	/**
	 * Una publicación. `minecraft`: las versiones de Minecraft que declara (Modrinth); vacía si la fuente no lo dice
	 * (GitHub: se mira en el gradle.properties de su etiqueta). `cargadores`: vacía si no lo dice (GitHub: el mod solo
	 * es de Fabric).
	 */
	public record Release(String name, Version version, boolean prerelease, String url, String tag,
			List<String> minecraft, List<String> loaders) {
		public Release {
			minecraft = List.copyOf(minecraft);
			loaders = List.copyOf(loaders);
		}
	}

	/** Lee una respuesta de GitHub Releases o de Modrinth (se distinguen por sus campos). */
	public static List<Release> read(String json) {
		JsonElement root;
		try {
			root = JsonParser.parseString(json == null ? "" : json);
		} catch (RuntimeException e) {
			throw new IllegalArgumentException("la respuesta no es JSON: " + e.getMessage(), e);
		}
		if (!root.isJsonArray()) {
			throw new IllegalArgumentException("la respuesta no es una lista de publicaciones");
		}
		List<Release> out = new ArrayList<>();
		for (JsonElement e : root.getAsJsonArray()) {
			if (!e.isJsonObject()) {
				continue;
			}
			JsonObject o = e.getAsJsonObject();
			Optional<Release> p = o.has("tag_name") ? fromGitHub(o) : o.has("version_number") ? fromModrinth(o) : Optional.empty();
			p.ifPresent(out::add);
		}
		return out;
	}

	static Optional<Release> fromGitHub(JsonObject o) {
		if (bool(o, "draft")) {
			return Optional.empty();
		}
		String tag = text(o, "tag_name");
		Optional<Version> v = Version.of(tag);
		String url = text(o, "html_url");
		if (v.isEmpty() || !web(url) || !withJar(o)) {
			return Optional.empty();
		}
		String name = text(o, "name");
		return Optional.of(new Release(name.isBlank() ? tag : name, v.get(),
				bool(o, "prerelease") || v.get().prerelease(), url, tag, List.of(), List.of()));
	}

	/** Una publicación de GitHub sin ningún .jar del mod (ni -sources ni -dev) no tiene nada que descargar. */
	private static boolean withJar(JsonObject o) {
		if (!o.has("assets") || !o.get("assets").isJsonArray()) {
			return true;
		}
		for (JsonElement a : o.getAsJsonArray("assets")) {
			String n = a.isJsonObject() ? text(a.getAsJsonObject(), "name").toLowerCase(Locale.ROOT) : "";
			if (n.endsWith(".jar") && !n.endsWith("-sources.jar") && !n.endsWith("-dev.jar") && !n.endsWith("-javadoc.jar")) {
				return true;
			}
		}
		return false;
	}

	static Optional<Release> fromModrinth(JsonObject o) {
		String state = text(o, "status");
		if (!state.isEmpty() && !state.equals("listed")) {
			return Optional.empty();
		}
		Optional<Version> v = Version.of(text(o, "version_number"));
		String project = text(o, "project_id"), id = text(o, "id");
		if (v.isEmpty() || project.isEmpty() || id.isEmpty() || !project.matches("[A-Za-z0-9_-]+") || !id.matches("[A-Za-z0-9_-]+")) {
			return Optional.empty();
		}
		String type = text(o, "version_type");
		String name = text(o, "name");
		return Optional.of(new Release(name.isBlank() ? text(o, "version_number") : name, v.get(),
				!type.equals("release") || v.get().prerelease(), "https://modrinth.com/mod/" + project + "/version/" + id,
				text(o, "version_number"), texts(o, "game_versions"), texts(o, "loaders")));
	}

	/**
	 * La más nueva que la `actual`, para este Minecraft y con Fabric (sin pre-publicaciones salvo `prepublicaciones`).
	 * `minecraftDe` da el Minecraft de una publicación que no lo declara (GitHub); se pregunta como mucho por
	 * {@link #MAX_MC_QUERIES}, de la más nueva a la más vieja. Vacío si no hay ninguna (o no se sabe para cuál sirve).
	 */
	public static Optional<Release> choose(List<Release> all, Version actual, String minecraft, boolean prereleases,
			Function<Release, Optional<String>> minecraftOf) {
		List<Release> candidates = new ArrayList<>();
		for (Release p : all) {
			if (p.version().compareTo(actual) > 0 && (prereleases || !p.prerelease())
					&& (p.loaders().isEmpty() || p.loaders().contains("fabric"))) {
				candidates.add(p);
			}
		}
		candidates.sort(Comparator.comparing(Release::version).reversed());
		int queries = 0;
		for (Release p : candidates) {
			if (!p.minecraft().isEmpty()) {
				if (p.minecraft().contains(minecraft.toLowerCase(Locale.ROOT))) {
					return Optional.of(p);
				}
				continue;
			}
			if (queries++ >= MAX_MC_QUERIES) {
				break;
			}
			Optional<String> mc = minecraftOf.apply(p);
			if (mc.isPresent() && Version.sameMinecraft(mc.get(), minecraft)) {
				return Optional.of(p);
			}
		}
		return Optional.empty();
	}

	/**
	 * El minecraft_version de un gradle.properties (el de la etiqueta de la publicación, de la API de contenidos de
	 * GitHub): el texto tal cual o el JSON de la API con el contenido en base64.
	 */
	public static Optional<String> minecraftFromProperties(String response) {
		if (response == null) {
			return Optional.empty();
		}
		String text = response;
		if (text.stripLeading().startsWith("{")) {
			try {
				JsonObject o = JsonParser.parseString(text).getAsJsonObject();
				text = new String(Base64.getMimeDecoder().decode(text(o, "content")), StandardCharsets.UTF_8);
			} catch (RuntimeException e) {
				return Optional.empty();
			}
		}
		for (String line : text.split("\\R")) {
			String l = line.strip();
			if (l.startsWith("minecraft_version") && l.contains("=")) {
				String k = l.substring(0, l.indexOf('=')).strip();
				String v = l.substring(l.indexOf('=') + 1).strip();
				if (k.equals("minecraft_version") && Version.of(v).isPresent()) {
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

	private static String text(JsonObject o, String k) {
		JsonElement e = o.get(k);
		return e != null && e.isJsonPrimitive() ? e.getAsString() : "";
	}

	private static boolean bool(JsonObject o, String k) {
		JsonElement e = o.get(k);
		return e != null && e.isJsonPrimitive() && e.getAsJsonPrimitive().isBoolean() && e.getAsBoolean();
	}

	private static List<String> texts(JsonObject o, String k) {
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
