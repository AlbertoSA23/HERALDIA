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
import java.nio.file.AtomicMoveNotSupportedException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.Collections;
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
		this.values = Collections.unmodifiableMap(new LinkedHashMap<>(values));
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

	/** Valor de una opción con decimales (minas.vanilla.multiplicador); vale también para las enteras. */
	public double getDouble(String key) {
		return values.get(key).getAsDouble();
	}

	/** Valor de una opción de lista (uno de {@link ConfigOption#values()}). */
	public String getString(String key) {
		return values.get(key).getAsString();
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

	/** Valores en uso, en el orden del esquema. */
	public Map<String, JsonPrimitive> values() {
		return values;
	}

	/** Opciones del esquema del .jar, en orden (de ellas sale la pantalla de configuración del cliente). */
	public static List<ConfigOption> options() {
		return Schema.OPTIONS;
	}

	/** Secciones de la pantalla, en orden: id → clave de traducción del título. */
	public static Map<String, String> sections() {
		return Schema.SECTIONS;
	}

	/** Valores por defecto de todas las opciones, en orden. */
	public static Map<String, JsonPrimitive> defaults() {
		Map<String, JsonPrimitive> out = new LinkedHashMap<>();
		for (ConfigOption o : Schema.OPTIONS) {
			out.put(o.key(), o.defaultValue());
		}
		return out;
	}

	/**
	 * Lee el fichero como al arrancar (migración, validación y valores por defecto para lo que falte o no valga),
	 * pero sin reescribirlo ni cambiar la configuración en uso. Lo usa la pantalla del cliente para mostrarlo.
	 */
	public static Map<String, JsonPrimitive> readValues(Path file) {
		return parse(file);
	}

	/**
	 * Escribe el fichero con el mismo formato que al arrancar (versión, valores y ayuda) sin cambiar la configuración
	 * en uso. Exige un valor válido para cada opción del esquema (el resto se ignora).
	 *
	 * @throws IllegalArgumentException si falta una opción o su valor no es válido
	 * @throws IOException si no se puede escribir
	 */
	public static void save(Path file, Map<String, JsonPrimitive> given) throws IOException {
		Map<String, JsonPrimitive> values = new LinkedHashMap<>();
		for (ConfigOption o : Schema.OPTIONS) {
			JsonPrimitive v = given.get(o.key());
			if (v == null) {
				throw new IllegalArgumentException("Falta la opción " + o.key());
			}
			values.put(o.key(), o.accept(v).orElseThrow(() -> new IllegalArgumentException("Valor no válido " + o.key() + "=" + v)));
		}
		writeOrThrow(file, values);
	}

	/** El esquema se lee una vez del .jar. */
	private static final class Schema {
		static final JsonObject JSON = readResource(SCHEMA);
		static final int VERSION = JSON.get("version").getAsInt();
		static final List<ConfigOption> OPTIONS;
		static final Map<String, String> SECTIONS;

		static {
			List<ConfigOption> options = new ArrayList<>();
			JSON.getAsJsonArray("opciones").forEach(o -> options.add(ConfigOption.of(o.getAsJsonObject())));
			OPTIONS = List.copyOf(options);
			Map<String, String> sections = new LinkedHashMap<>();
			JSON.getAsJsonArray("secciones").forEach(e -> sections.put(e.getAsJsonObject().get("id").getAsString(),
					e.getAsJsonObject().get("nombre").getAsString()));
			SECTIONS = Collections.unmodifiableMap(sections);
		}
	}

	private static HeraldiaConfig read(Path file) {
		Map<String, JsonPrimitive> values = parse(file);
		if (file != null) {
			try {
				writeOrThrow(file, values);
			} catch (IOException e) {
				LOGGER.warn("Heraldia: no se pudo escribir {} ({})", file, e.getMessage());
			}
		}
		LOGGER.info("Heraldia: configuración leída ({} opciones, versión {})", values.size(), Schema.VERSION);
		return new HeraldiaConfig(values, Schema.JSON);
	}

	private static Map<String, JsonPrimitive> parse(Path file) {
		int version = Schema.VERSION;
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
		for (ConfigOption o : Schema.OPTIONS) {
			JsonPrimitive given = flat.remove(o.key());
			values.put(o.key(), given == null ? o.defaultValue() : validate(given, o));
		}
		flat.keySet().stream().filter(k -> !k.equals("version") && !k.startsWith("_ayuda"))
				.forEach(k -> LOGGER.warn("Heraldia: opción desconocida {} en la configuración; se ignora", k));
		return values;
	}

	private static JsonPrimitive validate(JsonPrimitive given, ConfigOption o) {
		return o.accept(given).orElseGet(() -> {
			if (o.isBoolean()) {
				LOGGER.warn("Heraldia: valor no válido {}={} (true o false); se usa el valor por defecto {}", o.key(), given, o.defaultValue());
			} else if (o.isChoice()) {
				LOGGER.warn("Heraldia: valor no válido {}={} (uno de {}); se usa el valor por defecto {}", o.key(), given, o.values(), o.defaultValue());
			} else {
				LOGGER.warn("Heraldia: valor no válido {}={} ({} de {} a {}); se usa el valor por defecto {}", o.key(), given,
						o.decimal() ? "número" : "entero", o.min(), o.max(), o.defaultValue());
			}
			return o.defaultValue();
		});
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
	private static void writeOrThrow(Path file, Map<String, JsonPrimitive> values) throws IOException {
		JsonObject root = new JsonObject();
		root.addProperty("version", Schema.VERSION);
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
			for (ConfigOption o : Schema.OPTIONS) {
				String shown = o.pattern() != null ? o.pattern() : o.key();
				if (h.has(shown)) {
					continue;
				}
				String desc = text(texts, o.help(), o.pattern() != null ? shown.substring(shown.indexOf('<'), shown.indexOf('>') + 1) : null);
				String range = o.isChoice()
						? text(texts, "heraldia.config.valores", o.defaultValue().getAsString(), String.join(", ", o.values()))
						: o.min() != null
						? text(texts, "heraldia.config.rango", o.defaultValue().getAsString(), o.min().toString(), o.max().toString())
						: text(texts, "heraldia.config.si_no", o.defaultValue().getAsString());
				h.addProperty(shown, desc + " (" + range + ")");
			}
			help.add(lang, h);
		}
		root.add("_ayuda", help);
		Files.createDirectories(file.toAbsolutePath().getParent());
		// Primero a un temporal y luego se sustituye: un corte a medias no deja el fichero roto.
		Path tmp = file.resolveSibling(file.getFileName() + ".tmp");
		Files.writeString(tmp, GSON.toJson(root) + "\n", StandardCharsets.UTF_8);
		try {
			Files.move(tmp, file, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
		} catch (AtomicMoveNotSupportedException e) {
			Files.move(tmp, file, StandardCopyOption.REPLACE_EXISTING);
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
