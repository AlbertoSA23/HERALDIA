package io.github.albertosa23.heraldia.command;

import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.Collection;
import java.util.HashMap;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.TreeSet;
import java.util.concurrent.ConcurrentHashMap;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerPlayer;

/**
 * Translatable command texts with the .jar's own Spanish as fallback (a client without the mod sees the
 * Spanish, as in the generator's tellraw). For what is delivered to a specific player (the Herald's Guide), the
 * fallback can be in their language (any of those in the .jar, see heraldia/idiomas.json): {@link #language(String)} and
 * {@link #t(Map, String, Object...)}. Each .jar language is read once, the first time it is used. The boss notices use it too (bosses/Bosses).
 */
public final class Texts {
	static final String ES = "es_es", EN = "en_us";
	private static final Map<String, Optional<Map<String, String>>> LANGUAGES = new ConcurrentHashMap<>();
	private static final Map<String, String> LOCALES = readLocales();
	private static final Map<String, String> ES_TEXTS = language(ES);

	private Texts() {
	}

	public static MutableComponent t(String key, Object... args) {
		return t(ES_TEXTS, key, args);
	}

	/** Translatable with the text from `texts` as fallback (what a client without the mod sees); if missing, the Spanish. */
	public static MutableComponent t(Map<String, String> texts, String key, Object... args) {
		String fallback = texts.get(key);
		return Component.translatableWithFallback(key, fallback != null ? fallback : ES_TEXTS.getOrDefault(key, key), args);
	}

	/**
	 * The .jar texts for a client's language (e.g. "fr_ca"): its own if the mod has it; otherwise, that of its language
	 * ("fr_fr" for any French, "pt_br" for any Portuguese, "es_es" for any Spanish) and, failing that,
	 * English. Which code belongs to each language is given by the generator in heraldia/idiomas.json.
	 */
	public static Map<String, String> language(String client) {
		return readLang(code(client, LOCALES)).orElseThrow(
				() -> new IllegalStateException("Falta el idioma " + client + " en el .jar de Heraldia"));
	}

	/**
	 * Texts in a player's language: the one they chose with /heraldia language (T46, {@link Preferences}), which overrides
	 * their client's; if they chose none, their client's (see {@link #language(String)}).
	 */
	public static Map<String, String> language(ServerPlayer p) {
		return language(code(p));
	}

	/** The .jar language code used to write to a player (their preference or their client's). */
	public static String code(ServerPlayer p) {
		return code(Preferences.language(p).orElse(p.clientInformation().language()), LOCALES);
	}

	/** The .jar texts for language {@code code} (or that of its language, or English): see {@link #language(String)}. */
	public static Map<String, String> texts(String code) {
		return language(code);
	}

	/** The language codes the .jar has (es_es, en_us and the translations). */
	public static Collection<String> languages() {
		return new TreeSet<>(LOCALES.values());
	}

	/** {language: .jar code} from heraldia/idiomas.json. */
	static Map<String, String> locales() {
		return LOCALES;
	}

	/**
	 * The .jar language code matching `client` (pure logic, reads nothing): the same one if the .jar has it;
	 * otherwise, that of its language (what comes before "_", e.g. "pt" in "pt_pt") according to `locales` ({language: code});
	 * failing that, English.
	 */
	static String code(String client, Map<String, String> locales) {
		String c = client == null ? EN : client.toLowerCase(Locale.ROOT);
		if (locales.containsValue(c)) {
			return c;
		}
		int i = c.indexOf('_');
		String byLocale = locales.get(i > 0 ? c.substring(0, i) : c);
		return byLocale != null ? byLocale : EN;
	}

	/** The language code of some texts read with {@link #language(String)} (English if they belong to none). */
	static String codeOf(Map<String, String> texts) {
		for (Map.Entry<String, Optional<Map<String, String>>> e : LANGUAGES.entrySet()) {
			if (e.getValue().orElse(null) == texts) {
				return e.getKey();
			}
		}
		return EN;
	}

	/** heraldia/idiomas.json: {"lenguas": {language: .jar code}} (tools/gen/idiomas.py). */
	private static Map<String, String> readLocales() {
		String path = "/heraldia/idiomas.json";
		try (InputStream in = Texts.class.getResourceAsStream(path)) {
			if (in == null) {
				throw new IllegalStateException("Falta " + path + " en el .jar de Heraldia");
			}
			JsonObject o = JsonParser.parseReader(new InputStreamReader(in, StandardCharsets.UTF_8)).getAsJsonObject();
			Map<String, String> m = new HashMap<>();
			for (Map.Entry<String, JsonElement> e : o.getAsJsonObject("lenguas").entrySet()) {
				m.put(e.getKey(), e.getValue().getAsString());
			}
			return Map.copyOf(m);
		} catch (IOException e) {
			throw new IllegalStateException("No se pudo leer " + path, e);
		}
	}

	private static Optional<Map<String, String>> readLang(String code) {
		if (!code.matches("[a-z0-9_]{2,16}")) {
			return Optional.empty();
		}
		return LANGUAGES.computeIfAbsent(code, Texts::read);
	}

	private static Optional<Map<String, String>> read(String code) {
		String path = "/assets/heraldia/lang/" + code + ".json";
		try (InputStream in = Texts.class.getResourceAsStream(path)) {
			if (in == null) {
				if (ES.equals(code) || EN.equals(code)) {
					throw new IllegalStateException("Falta " + path + " en el .jar de Heraldia");
				}
				return Optional.empty();
			}
			JsonObject o = JsonParser.parseReader(new InputStreamReader(in, StandardCharsets.UTF_8)).getAsJsonObject();
			Map<String, String> m = new HashMap<>();
			for (Map.Entry<String, JsonElement> e : o.entrySet()) {
				m.put(e.getKey(), e.getValue().getAsString());
			}
			return Optional.of(Map.copyOf(m));
		} catch (IOException e) {
			throw new IllegalStateException("No se pudo leer " + path, e);
		}
	}
}
