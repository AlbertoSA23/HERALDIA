package io.github.albertosa23.heraldia.config;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.google.gson.JsonPrimitive;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.Reader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Configuración del servidor (config/heraldia.json). El esquema (opciones, valores por defecto, rangos y textos de ayuda)
 * lo genera tools/gen/opciones.py dentro del .jar. Se lee una vez al arrancar y queda inmutable: la colocación de
 * estructuras la consultan varios hilos de generación a la vez.
 */
public final class HeraldiaConfig {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	private static final Gson GSON = new GsonBuilder().setPrettyPrinting().disableHtmlEscaping().create();
	private static final String SCHEMA = "/heraldia/opciones.json";
	private static final String[] LANGS = {"es_es", "en_us"};
	private static volatile HeraldiaConfig instance;

	private final Map<String, JsonPrimitive> values;
	private final JsonObject schema;
	private final VillageRules villages;

	private HeraldiaConfig(Map<String, JsonPrimitive> values, JsonObject schema) {
		this.values = Map.copyOf(values);
		this.schema = schema;
		this.villages = new VillageRules(this);
	}

	/** Estilos activados y proporción de grandes, precalculados para el hilo de generación. */
	public VillageRules villages() {
		return villages;
	}

	/** Configuración leída al arrancar; si aún no se ha leído (no debería pasar), la de por defecto sin tocar el disco. */
	public static HeraldiaConfig get() {
		HeraldiaConfig c = instance;
		if (c == null) {
			c = read(null);
			instance = c;
		}
		return c;
	}

	/** Lee (o crea) el fichero, corrige lo que no valga avisando en el log y lo reescribe normalizado. */
	public static HeraldiaConfig load(Path file) {
		HeraldiaConfig c = read(file);
		instance = c;
		return c;
	}

	public int getInt(String key) {
		return values.get(key).getAsInt();
	}

	public boolean getBool(String key) {
		return values.get(key).getAsBoolean();
	}

	public boolean has(String key) {
		return values.containsKey(key);
	}

	/** Esquema del .jar: rejilla base de las aldeas, estilo → familia y rejilla por defecto de cada estructura única. */
	public JsonObject schema() {
		return schema;
	}

	public Set<String> keys() {
		return values.keySet();
	}

	private static HeraldiaConfig read(Path file) {
		JsonObject schema = readResource(SCHEMA);
		int version = schema.get("version").getAsInt();
		JsonObject root = new JsonObject();
		boolean exists = file != null && Files.isRegularFile(file);
		if (exists) {
			try (Reader r = Files.newBufferedReader(file, StandardCharsets.UTF_8)) {
				JsonElement e = JsonParser.parseReader(r);
				if (e.isJsonObject()) {
					root = e.getAsJsonObject();
				} else {
					LOGGER.warn("Heraldia: {} no es un objeto JSON; se usan los valores por defecto", file);
				}
			} catch (IOException | RuntimeException e) {
				LOGGER.warn("Heraldia: no se pudo leer {} ({}); se usan los valores por defecto", file, e.getMessage());
			}
		}
		int fileVersion = root.has("version") && root.get("version").isJsonPrimitive() ? root.get("version").getAsInt() : 0;
		if (exists && fileVersion < version) {
			migrate(root, fileVersion, version);
			LOGGER.info("Heraldia: configuración migrada de la versión {} a la {}", fileVersion, version);
		} else if (fileVersion > version) {
			LOGGER.warn("Heraldia: la configuración es de la versión {}, más nueva que la {} de este mod; se lee lo que se entiende", fileVersion, version);
		}

		Map<String, JsonPrimitive> flat = new LinkedHashMap<>();
		flatten("", root, flat);
		Map<String, JsonPrimitive> values = new LinkedHashMap<>();
		List<JsonObject> options = new ArrayList<>();
		schema.getAsJsonArray("opciones").forEach(o -> options.add(o.getAsJsonObject()));
		for (JsonObject o : options) {
			String key = o.get("clave").getAsString();
			JsonPrimitive def = o.getAsJsonPrimitive("defecto");
			JsonPrimitive given = flat.remove(key);
			values.put(key, given == null ? def : validate(key, given, def, o));
		}
		flat.keySet().stream().filter(k -> !k.equals("version") && !k.startsWith("_ayuda"))
				.forEach(k -> LOGGER.warn("Heraldia: opción desconocida {} en la configuración; se ignora", k));

		if (file != null) {
			write(file, values, options, version);
		}
		LOGGER.info("Heraldia: configuración leída ({} opciones, versión {})", values.size(), version);
		return new HeraldiaConfig(values, schema);
	}

	private static JsonPrimitive validate(String key, JsonPrimitive given, JsonPrimitive def, JsonObject o) {
		if (def.isBoolean()) {
			if (given.isBoolean()) {
				return given;
			}
			LOGGER.warn("Heraldia: valor no válido {}={} (true o false); se usa el valor por defecto {}", key, given, def);
			return def;
		}
		int min = o.get("min").getAsInt(), max = o.get("max").getAsInt();
		if (given.isNumber()) {
			double d = given.getAsDouble();
			if (d == Math.rint(d) && d >= min && d <= max) {
				return new JsonPrimitive((int) d);
			}
		}
		LOGGER.warn("Heraldia: valor no válido {}={} (entero de {} a {}); se usa el valor por defecto {}", key, given, min, max, def);
		return def;
	}

	/** Cambios de formato entre versiones del fichero. La versión 0 (sin campo) es la de un fichero escrito a mano. */
	private static void migrate(JsonObject root, int from, int to) {
		for (int v = from; v < to; v++) {
			switch (v) {
				case 0 -> { } // 0 → 1: mismo formato; solo se añade el campo de versión
				default -> LOGGER.warn("Heraldia: no hay migración de la versión {} de la configuración", v);
			}
		}
		root.addProperty("version", to);
	}

	private static void flatten(String prefix, JsonObject obj, Map<String, JsonPrimitive> out) {
		for (Map.Entry<String, JsonElement> e : obj.entrySet()) {
			String key = prefix.isEmpty() ? e.getKey() : prefix + "." + e.getKey();
			if (e.getValue().isJsonObject()) {
				flatten(key, e.getValue().getAsJsonObject(), out);
			} else if (e.getValue().isJsonPrimitive()) {
				out.put(key, e.getValue().getAsJsonPrimitive());
			} else {
				out.put(key, new JsonPrimitive(e.getValue().toString()));
			}
		}
	}

	/** Reescribe el fichero con los valores en uso y una ayuda en español e inglés (se regenera en cada arranque). */
	private static void write(Path file, Map<String, JsonPrimitive> values, List<JsonObject> options, int version) {
		JsonObject root = new JsonObject();
		root.addProperty("version", version);
		for (Map.Entry<String, JsonPrimitive> e : values.entrySet()) {
			String[] parts = e.getKey().split("\\.");
			JsonObject node = root;
			for (int i = 0; i < parts.length - 1; i++) {
				if (!node.has(parts[i])) {
					node.add(parts[i], new JsonObject());
				}
				node = node.getAsJsonObject(parts[i]);
			}
			node.add(parts[parts.length - 1], e.getValue());
		}
		JsonObject help = new JsonObject();
		for (String lang : LANGS) {
			JsonObject texts = readResource("/assets/heraldia/lang/" + lang + ".json");
			JsonObject h = new JsonObject();
			for (JsonObject o : options) {
				String shown = o.has("patron") ? o.get("patron").getAsString() : o.get("clave").getAsString();
				if (h.has(shown)) {
					continue;
				}
				String desc = text(texts, o.get("ayuda").getAsString(), o.has("patron") ? shown.substring(shown.indexOf('<'), shown.indexOf('>') + 1) : null);
				String range = o.has("min")
						? text(texts, "heraldia.config.rango", o.get("defecto").getAsString(), o.get("min").getAsString(), o.get("max").getAsString())
						: text(texts, "heraldia.config.si_no", o.get("defecto").getAsString());
				h.addProperty(shown, desc + " (" + range + ")");
			}
			help.add(lang, h);
		}
		root.add("_ayuda", help);
		try {
			Files.createDirectories(file.getParent());
			Files.writeString(file, GSON.toJson(root) + "\n", StandardCharsets.UTF_8);
		} catch (IOException e) {
			LOGGER.warn("Heraldia: no se pudo escribir {} ({})", file, e.getMessage());
		}
	}

	private static String text(JsonObject texts, String key, String... args) {
		String t = texts.has(key) ? texts.get(key).getAsString() : key;
		return args.length == 0 || args[0] == null ? t : String.format(t, (Object[]) args);
	}

	private static JsonObject readResource(String path) {
		try (InputStream in = HeraldiaConfig.class.getResourceAsStream(path)) {
			if (in == null) {
				throw new IllegalStateException("Falta " + path + " en el .jar de Heraldia");
			}
			return JsonParser.parseReader(new InputStreamReader(in, StandardCharsets.UTF_8)).getAsJsonObject();
		} catch (IOException e) {
			throw new IllegalStateException("No se pudo leer " + path, e);
		}
	}
}
