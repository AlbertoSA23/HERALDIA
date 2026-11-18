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
 * Releases of the mod (pure logic, no network): reads the response of the GitHub Releases API
 * (GET /repos/&lt;owner&gt;/&lt;repo&gt;/releases, where .github/workflows/publish.yml on main publishes) or that of
 * Modrinth's versions (GET /v2/project/&lt;id&gt;/version), and picks the newest one that works on this server. Tolerant: whatever it
 * does not understand it skips; a response that is not a list throws {@link IllegalArgumentException}.
 */
public final class Releases {
	/** At most how many GitHub releases are checked to know their Minecraft (one request each). */
	public static final int MAX_MC_QUERIES = 3;

	private Releases() {
	}

	/**
	 * A release. `minecraft`: the Minecraft versions it declares (Modrinth); empty if the source does not say
	 * (GitHub: it is looked up in its tag's gradle.properties). `loaders`: empty if it does not say (GitHub: the mod is only
	 * for Fabric).
	 */
	public record Release(String name, Version version, boolean prerelease, String url, String tag,
			List<String> minecraft, List<String> loaders) {
		public Release {
			minecraft = List.copyOf(minecraft);
			loaders = List.copyOf(loaders);
		}
	}

	/** Reads a GitHub Releases or Modrinth response (they are told apart by their fields). */
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

	/** A GitHub release without any .jar of the mod (neither -sources nor -dev) has nothing to download. */
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
	 * The newest one above `actual`, for this Minecraft and with Fabric (no prereleases unless `prereleases`).
	 * `minecraftOf` gives the Minecraft of a release that does not declare it (GitHub); it is asked at most
	 * {@link #MAX_MC_QUERIES} times, from newest to oldest. Empty if there is none (or it is unknown which one it works for).
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
	 * The minecraft_version of a gradle.properties (that of the release's tag, from GitHub's contents API): the
	 * plain text or the API's JSON with the content in base64.
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

	/** Web links only: what is offered for clicking cannot be anything else. */
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
