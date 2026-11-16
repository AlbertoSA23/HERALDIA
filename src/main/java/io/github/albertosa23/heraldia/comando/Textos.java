package io.github.albertosa23.heraldia.comando;

import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;

/**
 * Textos traducibles de los comandos con el español del propio .jar como respaldo (un cliente sin el mod ve el
 * español, como en los tellraw del generador). Para lo que se entrega a un jugador concreto (la Guía del Heraldo), el
 * respaldo puede ir en su idioma: {@link #idioma(String)} y {@link #t(Map, String, Object...)}. Cada idioma del .jar se
 * lee una vez, la primera vez que se usa. También lo usan los avisos de los jefes (jefes/Jefes).
 */
public final class Textos {
	static final String ES = "es_es", EN = "en_us";
	private static final Map<String, Optional<Map<String, String>>> IDIOMAS = new ConcurrentHashMap<>();
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
	 * Textos del .jar del idioma de un cliente (p. ej. «es_mx»): el suyo si el mod lo trae; si no, el de su lengua
	 * («es_es» para cualquier español) y, si tampoco, el inglés.
	 */
	static Map<String, String> idioma(String cliente) {
		return leer(codigo(cliente, c -> leer(c).isPresent())).orElseThrow(
				() -> new IllegalStateException("Falta el idioma " + cliente + " en el .jar de Heraldia"));
	}

	/** El código de idioma del .jar que corresponde a `cliente` según `existe` (lógica pura, sin leer nada). */
	static String codigo(String cliente, java.util.function.Predicate<String> existe) {
		String c = cliente == null ? EN : cliente.toLowerCase(Locale.ROOT);
		if (existe.test(c)) {
			return c;
		}
		int i = c.indexOf('_');
		String base = (i > 0 ? c.substring(0, i) : c) + "_" + (i > 0 ? c.substring(0, i) : c);
		return existe.test(base) ? base : EN;
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
