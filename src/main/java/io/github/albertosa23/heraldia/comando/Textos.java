package io.github.albertosa23.heraldia.comando;

import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;

/**
 * Textos traducibles de los comandos con el español del propio .jar como respaldo (un cliente sin el mod ve el
 * español, como en los tellraw del generador). El es_es se lee una vez, la primera vez que se usa.
 */
final class Textos {
	private static final Map<String, String> ES = read();

	private Textos() {
	}

	static MutableComponent t(String key, Object... args) {
		return Component.translatableWithFallback(key, ES.getOrDefault(key, key), args);
	}

	private static Map<String, String> read() {
		String path = "/assets/heraldia/lang/es_es.json";
		try (InputStream in = Textos.class.getResourceAsStream(path)) {
			if (in == null) {
				throw new IllegalStateException("Falta " + path + " en el .jar de Heraldia");
			}
			JsonObject o = JsonParser.parseReader(new InputStreamReader(in, StandardCharsets.UTF_8)).getAsJsonObject();
			Map<String, String> m = new HashMap<>();
			for (Map.Entry<String, JsonElement> e : o.entrySet()) {
				m.put(e.getKey(), e.getValue().getAsString());
			}
			return Map.copyOf(m);
		} catch (IOException e) {
			throw new IllegalStateException("No se pudo leer " + path, e);
		}
	}
}
