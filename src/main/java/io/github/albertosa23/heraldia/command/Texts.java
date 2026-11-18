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
 * Textos traducibles de los comandos con el español del propio .jar como respaldo (un cliente sin el mod ve el
 * español, como en los tellraw del generador). Para lo que se entrega a un jugador concreto (la Guía del Heraldo), el
 * respaldo puede ir en su idioma (cualquiera de los del .jar, ver heraldia/idiomas.json): {@link #language(String)} y
 * {@link #t(Map, String, Object...)}. Cada idioma del .jar se lee una vez, la primera vez que se usa. También lo usan los avisos de los jefes (jefes/Jefes).
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

	/** Traducible con el texto de `textos` como respaldo (el que ve un cliente sin el mod); si falta, el español. */
	public static MutableComponent t(Map<String, String> texts, String key, Object... args) {
		String fallback = texts.get(key);
		return Component.translatableWithFallback(key, fallback != null ? fallback : ES_TEXTS.getOrDefault(key, key), args);
	}

	/**
	 * Textos del .jar del idioma de un cliente (p. ej. «fr_ca»): el suyo si el mod lo trae; si no, el de su lengua
	 * («fr_fr» para cualquier francés, «pt_br» para cualquier portugués, «es_es» para cualquier español) y, si tampoco,
	 * el inglés. Qué código corresponde a cada lengua lo dice el generador en heraldia/idiomas.json.
	 */
	public static Map<String, String> language(String client) {
		return readLang(code(client, LOCALES)).orElseThrow(
				() -> new IllegalStateException("Falta el idioma " + client + " en el .jar de Heraldia"));
	}

	/**
	 * Textos del idioma de un jugador: el que eligió con /heraldia language (T46, {@link Preferences}), que manda sobre
	 * el de su cliente; si no eligió ninguno, el de su cliente (ver {@link #language(String)}).
	 */
	public static Map<String, String> language(ServerPlayer p) {
		return language(code(p));
	}

	/** El código de idioma del .jar con que se le escribe a un jugador (su preferencia o el de su cliente). */
	public static String code(ServerPlayer p) {
		return code(Preferences.language(p).orElse(p.clientInformation().language()), LOCALES);
	}

	/** Los textos del .jar del idioma {@code code} (o el de su lengua, o el inglés): ver {@link #language(String)}. */
	public static Map<String, String> texts(String code) {
		return language(code);
	}

	/** Los códigos de idioma que trae el .jar (es_es, en_us y las traducciones). */
	public static Collection<String> languages() {
		return new TreeSet<>(LOCALES.values());
	}

	/** {lengua: código del .jar} de heraldia/idiomas.json. */
	static Map<String, String> locales() {
		return LOCALES;
	}

	/**
	 * El código de idioma del .jar que corresponde a `cliente` (lógica pura, sin leer nada): el mismo si el .jar lo trae;
	 * si no, el de su lengua (lo que va antes de «_», p. ej. «pt» en «pt_pt») según `lenguas` ({lengua: código}); si
	 * tampoco, el inglés.
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

	/** El código de idioma de unos textos leídos con {@link #language(String)} (inglés si no son de ninguno). */
	static String codeOf(Map<String, String> texts) {
		for (Map.Entry<String, Optional<Map<String, String>>> e : LANGUAGES.entrySet()) {
			if (e.getValue().orElse(null) == texts) {
				return e.getKey();
			}
		}
		return EN;
	}

	/** heraldia/idiomas.json: {"lenguas": {lengua: código del .jar}} (tools/gen/idiomas.py). */
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
