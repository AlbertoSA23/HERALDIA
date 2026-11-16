package io.github.albertosa23.heraldia.comando;

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

/**
 * Textos traducibles de los comandos con el español del propio .jar como respaldo (un cliente sin el mod ve el
 * español, como en los tellraw del generador). Para lo que se entrega a un jugador concreto (la Guía del Heraldo), el
 * respaldo puede ir en su idioma (cualquiera de los del .jar, ver heraldia/idiomas.json): {@link #idioma(String)} y
 * {@link #t(Map, String, Object...)}. Cada idioma del .jar se lee una vez, la primera vez que se usa. También lo usan los avisos de los jefes (jefes/Jefes).
 */
public final class Textos {
	static final String ES = "es_es", EN = "en_us";
	private static final Map<String, Optional<Map<String, String>>> IDIOMAS = new ConcurrentHashMap<>();
	private static final Map<String, String> LENGUAS = leerLenguas();
	private static final Map<String, String> ES_TEXTOS = idioma(ES);

	private Textos() {
	}

	public static MutableComponent t(String key, Object... args) {
		return t(ES_TEXTOS, key, args);
	}

	/** Traducible con el texto de `textos` como respaldo (el que ve un cliente sin el mod); si falta, el español. */
	static MutableComponent t(Map<String, String> textos, String key, Object... args) {
		String fallback = textos.get(key);
		return Component.translatableWithFallback(key, fallback != null ? fallback : ES_TEXTOS.getOrDefault(key, key), args);
	}

	/**
	 * Textos del .jar del idioma de un cliente (p. ej. «fr_ca»): el suyo si el mod lo trae; si no, el de su lengua
	 * («fr_fr» para cualquier francés, «pt_br» para cualquier portugués, «es_es» para cualquier español) y, si tampoco,
	 * el inglés. Qué código corresponde a cada lengua lo dice el generador en heraldia/idiomas.json.
	 */
	static Map<String, String> idioma(String cliente) {
		return leer(codigo(cliente, LENGUAS)).orElseThrow(
				() -> new IllegalStateException("Falta el idioma " + cliente + " en el .jar de Heraldia"));
	}

	/** Los códigos de idioma que trae el .jar (es_es, en_us y las traducciones). */
	public static Collection<String> idiomas() {
		return new TreeSet<>(LENGUAS.values());
	}

	/** {lengua: código del .jar} de heraldia/idiomas.json. */
	static Map<String, String> lenguas() {
		return LENGUAS;
	}

	/**
	 * El código de idioma del .jar que corresponde a `cliente` (lógica pura, sin leer nada): el mismo si el .jar lo trae;
	 * si no, el de su lengua (lo que va antes de «_», p. ej. «pt» en «pt_pt») según `lenguas` ({lengua: código}); si
	 * tampoco, el inglés.
	 */
	static String codigo(String cliente, Map<String, String> lenguas) {
		String c = cliente == null ? EN : cliente.toLowerCase(Locale.ROOT);
		if (lenguas.containsValue(c)) {
			return c;
		}
		int i = c.indexOf('_');
		String porLengua = lenguas.get(i > 0 ? c.substring(0, i) : c);
		return porLengua != null ? porLengua : EN;
	}

	/** El código de idioma de unos textos leídos con {@link #idioma(String)} (inglés si no son de ninguno). */
	static String codigoDe(Map<String, String> textos) {
		for (Map.Entry<String, Optional<Map<String, String>>> e : IDIOMAS.entrySet()) {
			if (e.getValue().orElse(null) == textos) {
				return e.getKey();
			}
		}
		return EN;
	}

	/** heraldia/idiomas.json: {"lenguas": {lengua: código del .jar}} (tools/gen/idiomas.py). */
	private static Map<String, String> leerLenguas() {
		String path = "/heraldia/idiomas.json";
		try (InputStream in = Textos.class.getResourceAsStream(path)) {
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

	private static Optional<Map<String, String>> leer(String code) {
		if (!code.matches("[a-z0-9_]{2,16}")) {
			return Optional.empty();
		}
		return IDIOMAS.computeIfAbsent(code, Textos::read);
	}

	private static Optional<Map<String, String>> read(String code) {
		String path = "/assets/heraldia/lang/" + code + ".json";
		try (InputStream in = Textos.class.getResourceAsStream(path)) {
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
