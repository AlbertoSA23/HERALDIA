package io.github.albertosa23.heraldia.dialogue;

import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * The villagers' lines of one language (P9a), read from heraldia/dialogos/&lt;code&gt;.json inside the .jar (written by
 * tools/gen/dialogue.py: {pool: {id: text}}). The Spanish file is the reference: its pools and ids are the set of lines;
 * a line missing in the player's language falls back to the English one and, failing that, to the Spanish one, so a
 * language that does not ship a group of lines yet still talks. Each language is read once, the first time it is used.
 */
public final class Lines {
	static final String ES = "es_es", EN = "en_us";
	private static final Map<String, Lines> CACHE = new ConcurrentHashMap<>();

	/** A line: its pool ("profession.farmer"), its id ("3") and its text in this language. */
	public record Line(String pool, String id, String text) {
		/** What each player's memory of recent lines stores: "profession.farmer.3". */
		public String key() {
			return pool + "." + id;
		}
	}

	private final Map<String, List<Line>> pools;

	Lines(Map<String, List<Line>> pools) {
		this.pools = pools;
	}

	/** The lines of a pool (empty if it has none). */
	public List<Line> pool(String pool) {
		return pools.getOrDefault(pool, List.of());
	}

	public boolean has(String pool) {
		return !pool(pool).isEmpty();
	}

	public int size() {
		return pools.values().stream().mapToInt(List::size).sum();
	}

	/** The lines in a .jar language ("es_es", "fr_fr"...); a code without its own file gets the English lines. */
	public static Lines of(String code) {
		return CACHE.computeIfAbsent(code, c -> resolve(read(ES), read(EN), ES.equals(c) ? Map.of() : read(c)));
	}

	/**
	 * The lines of a language from the three files (pure logic): every pool and id of the Spanish, in its order, with the
	 * text of {@code language}, or of the English, or of the Spanish.
	 */
	static Lines resolve(Map<String, Map<String, String>> es, Map<String, Map<String, String>> en, Map<String, Map<String, String>> language) {
		Map<String, List<Line>> out = new LinkedHashMap<>();
		for (Map.Entry<String, Map<String, String>> p : es.entrySet()) {
			List<Line> l = new ArrayList<>();
			for (Map.Entry<String, String> line : p.getValue().entrySet()) {
				String text = text(language, p.getKey(), line.getKey());
				if (text == null) {
					text = text(en, p.getKey(), line.getKey());
				}
				l.add(new Line(p.getKey(), line.getKey(), text != null ? text : line.getValue()));
			}
			out.put(p.getKey(), Collections.unmodifiableList(l));
		}
		return new Lines(Collections.unmodifiableMap(out));
	}

	private static String text(Map<String, Map<String, String>> file, String pool, String id) {
		Map<String, String> p = file.get(pool);
		String t = p == null ? null : p.get(id);
		return t == null || t.isBlank() ? null : t;
	}

	/** {pool: {id: text}} of a JSON object (pure logic). */
	static Map<String, Map<String, String>> parse(JsonObject o) {
		Map<String, Map<String, String>> out = new LinkedHashMap<>();
		for (Map.Entry<String, JsonElement> p : o.entrySet()) {
			if (!p.getValue().isJsonObject()) {
				continue;
			}
			Map<String, String> lines = new LinkedHashMap<>();
			for (Map.Entry<String, JsonElement> l : p.getValue().getAsJsonObject().entrySet()) {
				if (l.getValue().isJsonPrimitive()) {
					lines.put(l.getKey(), l.getValue().getAsString());
				}
			}
			out.put(p.getKey(), lines);
		}
		return out;
	}

	private static Map<String, Map<String, String>> read(String code) {
		if (!code.matches("[a-z0-9_]{2,16}")) {
			return Map.of();
		}
		String path = "/heraldia/dialogos/" + code + ".json";
		try (InputStream in = Lines.class.getResourceAsStream(path)) {
			if (in == null) {
				if (ES.equals(code)) {
					throw new IllegalStateException("Falta " + path + " en el .jar de Heraldia");
				}
				return Map.of();
			}
			return parse(JsonParser.parseReader(new InputStreamReader(in, StandardCharsets.UTF_8)).getAsJsonObject());
		} catch (IOException e) {
			throw new IllegalStateException("No se pudo leer " + path, e);
		}
	}
}
