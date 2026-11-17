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
 * lo genera tools/gen/opciones.py dentro del .jar. Se lee al arrancar y queda inmutable: la colocación de
 * estructuras la consultan varios hilos de generación a la vez. /heraldia reload ({@link #recargar}) la sustituye por
 * otra con los valores nuevos de las opciones que no afectan a la generación. El perfil de juego ({@link Perfiles}) se
 * aplica al leer (al arrancar y al recargar): los valores en uso ya son los del perfil con lo fijado a mano encima.
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
	private final Perfiles.Aplicado perfil;

	private HeraldiaConfig(Lectura l, JsonObject schema) {
		this.values = Collections.unmodifiableMap(new LinkedHashMap<>(l.values()));
		this.schema = schema;
		this.perfil = l.perfil();
		this.villages = new VillageRules(this);
	}

	/**
	 * Lo leído del fichero: los valores en uso (con el perfil aplicado) y el perfil: el elegido, el efectivo, las opciones
	 * fijadas a mano y las que difieren del perfil.
	 */
	public record Lectura(Map<String, JsonPrimitive> values, Perfiles.Aplicado perfil) {
	}

	/** Perfil de juego en uso: el elegido en el fichero, el efectivo y lo fijado a mano. */
	public Perfiles.Aplicado profile() {
		return perfil;
	}

	/** Los perfiles del esquema del .jar (qué opciones fija cada uno y con qué valor). */
	public static Perfiles profiles() {
		return Schema.PERFILES;
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

	/**
	 * Recarga en caliente (/heraldia reload): lee el fichero como al arrancar, sin reescribirlo, y pone en uso los
	 * valores nuevos de las opciones recargables ({@link Recarga#recargable}); las que afectan a la generación conservan
	 * el valor en uso hasta el siguiente arranque y salen en {@link Recarga.Resultado#pendientes()}. La configuración en
	 * uso se sustituye entera (es inmutable), así que los hilos de generación nunca ven una a medias.
	 */
	public static synchronized Recarga.Resultado recargar(Path file) {
		HeraldiaConfig actual = get();
		Lectura l = parse(file);                         // con el perfil ya aplicado: recargar el perfil lo cambia todo junto
		Recarga.Resultado r = Recarga.mezclar(actual.values, l.values());
		if (r.cambia()) {
			instance = new HeraldiaConfig(new Lectura(r.valores(), l.perfil()), actual.schema);
			logPerfil(l.perfil());
		}
		LOGGER.info("Heraldia: configuración recargada: {} opciones aplicadas {}, {} esperan al reinicio {}", r.aplicadas().size(),
				r.aplicadas(), r.pendientes().size(), r.pendientes().stream().map(Recarga.Pendiente::clave).toList());
		return r;
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
		return parse(file).values();
	}

	/** Como {@link #readValues}, con el perfil (qué opciones están fijadas a mano): para la pantalla y las pruebas. */
	public static Lectura readWithProfile(Path file) {
		return parse(file);
	}

	/**
	 * Escribe el fichero con el mismo formato que al arrancar (versión, valores y ayuda) sin cambiar la configuración
	 * en uso. Exige un valor válido para cada opción del esquema (el resto se ignora). De las opciones del perfil se
	 * escriben (fijadas a mano) las que no tienen el valor del perfil elegido: lo demás lo sigue dando el perfil.
	 *
	 * @throws IllegalArgumentException si falta una opción o su valor no es válido
	 * @throws IOException si no se puede escribir
	 */
	public static void save(Path file, Map<String, JsonPrimitive> given) throws IOException {
		JsonPrimitive p = given.get(Perfiles.CLAVE);
		String elegido = p != null && p.isString() ? p.getAsString() : Perfiles.ESTANDAR;
		save(file, given, Schema.PERFILES.fijadasPorDiferencia(elegido, given));
	}

	/** Como {@link #save(Path, Map)}, con las opciones del perfil fijadas a mano que se escriben (las demás, no). */
	public static void save(Path file, Map<String, JsonPrimitive> given, Set<String> fijadas) throws IOException {
		Map<String, JsonPrimitive> values = new LinkedHashMap<>();
		for (ConfigOption o : Schema.OPTIONS) {
			JsonPrimitive v = given.get(o.key());
			if (v == null) {
				throw new IllegalArgumentException("Falta la opción " + o.key());
			}
			values.put(o.key(), o.accept(v).orElseThrow(() -> new IllegalArgumentException("Valor no válido " + o.key() + "=" + v)));
		}
		writeOrThrow(file, values, fijadas, perfilDe(values, fijadas));
	}

	/** El perfil que resulta de unos valores ya resueltos con esas opciones fijadas a mano. */
	private static Perfiles.Aplicado perfilDe(Map<String, JsonPrimitive> values, Set<String> fijadas) {
		Map<String, JsonPrimitive> mano = new LinkedHashMap<>();
		fijadas.forEach(k -> {
			if (values.containsKey(k)) {
				mano.put(k, values.get(k));
			}
		});
		return Schema.PERFILES.aplicar(values.get(Perfiles.CLAVE).getAsString(), mano);
	}

	/** El esquema se lee una vez del .jar. */
	private static final class Schema {
		static final JsonObject JSON = readResource(SCHEMA);
		static final int VERSION = JSON.get("version").getAsInt();
		static final List<ConfigOption> OPTIONS;
		static final Map<String, String> SECTIONS;
		static final Perfiles PERFILES = new Perfiles(JSON);

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
		Lectura l = parse(file);
		if (file != null) {
			try {
				writeOrThrow(file, l.values(), l.perfil().fijadas().keySet(), l.perfil());
			} catch (IOException e) {
				LOGGER.warn("Heraldia: no se pudo escribir {} ({})", file, e.getMessage());
			}
		}
		LOGGER.info("Heraldia: configuración leída ({} opciones, versión {})", l.values().size(), Schema.VERSION);
		logPerfil(l.perfil());
		return new HeraldiaConfig(l, Schema.JSON);
	}

	private static void logPerfil(Perfiles.Aplicado p) {
		if (p.difieren().isEmpty()) {
			LOGGER.info("Heraldia: perfil {}{}", p.elegido(), p.fijadas().isEmpty() ? "" : " (fijadas a mano: " + String.join(", ", p.fijadas().keySet()) + ")");
		} else {
			List<String> d = new ArrayList<>();
			p.difieren().forEach((k, v) -> d.add(k + "=" + v[0] + " (perfil: " + v[1] + ")"));
			LOGGER.info("Heraldia: perfil {} con opciones fijadas a mano en el fichero, que mandan sobre el perfil: {}; el perfil queda como {}",
					p.elegido(), String.join(", ", d), p.efectivo());
		}
	}

	private static Lectura parse(Path file) {
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
		Map<String, JsonPrimitive> mano = new LinkedHashMap<>();         // opciones del perfil que trae el fichero (válidas)
		Set<String> delPerfil = Set.copyOf(Schema.PERFILES.claves());
		for (ConfigOption o : Schema.OPTIONS) {
			JsonPrimitive given = flat.remove(o.key());
			if (delPerfil.contains(o.key())) {
				if (given != null) {
					JsonPrimitive v = validate(given, o, "el del perfil");
					if (o.accept(given).isPresent()) {
						mano.put(o.key(), v);
					}
				}
				values.put(o.key(), null);                                  // lo pone el perfil (abajo), en su sitio
			} else {
				values.put(o.key(), given == null ? o.defaultValue() : validate(given, o, null));
			}
		}
		flat.keySet().stream().filter(k -> !k.equals("version") && !k.startsWith("_"))
				.forEach(k -> LOGGER.warn("Heraldia: opción desconocida {} en la configuración; se ignora", k));
		Perfiles.Aplicado perfil = Schema.PERFILES.aplicar(values.get(Perfiles.CLAVE).getAsString(), mano);
		values.putAll(perfil.valores());
		return new Lectura(values, perfil);
	}

	/** El valor si vale; si no, avisa y da el de por defecto (o, si se dice en `enSuLugar`, se avisa de ese otro). */
	private static JsonPrimitive validate(JsonPrimitive given, ConfigOption o, String enSuLugar) {
		return o.accept(given).orElseGet(() -> {
			Object usa = enSuLugar != null ? enSuLugar : o.defaultValue();
			if (o.isBoolean()) {
				LOGGER.warn("Heraldia: valor no válido {}={} (true o false); se usa el valor por defecto {}", o.key(), given, usa);
			} else if (o.isChoice()) {
				LOGGER.warn("Heraldia: valor no válido {}={} (uno de {}); se usa el valor por defecto {}", o.key(), given, o.values(), usa);
			} else {
				LOGGER.warn("Heraldia: valor no válido {}={} ({} de {} a {}); se usa el valor por defecto {}", o.key(), given,
						o.decimal() ? "número" : "entero", o.min(), o.max(), usa);
			}
			return o.defaultValue();
		});
	}

	/** Cambios de formato entre versiones del fichero. La versión 0 (sin campo) es la de un fichero escrito a mano. */
	private static void migrate(JsonObject root, int from, int to) {
		for (int v = from; v < to; v++) {
			switch (v) {
				case 0 -> { } // 0 → 1: mismo formato; solo se añade el campo de versión
				case 1 -> { // 1 → 2: perfiles (T36); lo que escribía el mod deja de estar «fijado a mano» (uno a mano, el 0, no)
					if (from == 1) {
						quitarDelPerfil(root);
					}
				}
				default -> LOGGER.warn("Heraldia: no hay migración de la versión {} de la configuración", v);
			}
		}
		root.addProperty("version", to);
	}

	/**
	 * Migración 1 → 2: el mod escribía todas las opciones, así que en un fichero de la versión 1 las que fija el perfil
	 * con su valor por defecto no las puso nadie a mano: se quitan (con el perfil estándar dan lo mismo). Las que tienen
	 * otro valor se quedan, fijadas a mano: nada cambia en el mundo.
	 */
	private static void quitarDelPerfil(JsonObject root) {
		for (String k : Schema.PERFILES.claves()) {
			String[] parts = k.split("\\.");
			JsonObject node = root;
			for (int i = 0; i < parts.length - 1 && node != null; i++) {
				node = node.has(parts[i]) && node.get(parts[i]).isJsonObject() ? node.getAsJsonObject(parts[i]) : null;
			}
			String hoja = parts[parts.length - 1];
			if (node != null && node.has(hoja) && node.get(hoja).isJsonPrimitive()) {
				ConfigOption o = Schema.OPTIONS.stream().filter(x -> x.key().equals(k)).findFirst().orElseThrow();
				if (o.accept(node.getAsJsonPrimitive(hoja)).map(o.defaultValue()::equals).orElse(false)) {
					node.remove(hoja);
				}
			}
		}
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

	/**
	 * Reescribe el fichero con los valores en uso y una ayuda en español e inglés (se regenera en cada arranque). De las
	 * opciones del perfil solo van las fijadas a mano; el bloque «_perfil» (informativo, no se lee) dice el perfil efectivo
	 * y los valores que da.
	 */
	private static void writeOrThrow(Path file, Map<String, JsonPrimitive> values, Set<String> fijadas, Perfiles.Aplicado perfil)
			throws IOException {
		JsonObject root = new JsonObject();
		root.addProperty("version", Schema.VERSION);
		Set<String> delPerfil = Set.copyOf(Schema.PERFILES.claves());
		for (Map.Entry<String, JsonPrimitive> e : values.entrySet()) {
			if (delPerfil.contains(e.getKey()) && !fijadas.contains(e.getKey())) {
				continue;
			}
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
				if (delPerfil.contains(o.key())) {
					Perfiles ps = Schema.PERFILES;
					range += "; " + text(texts, "heraldia.config.perfiles", ps.valores("casual").get(o.key()).getAsString(),
							ps.valores(Perfiles.ESTANDAR).get(o.key()).getAsString(), ps.valores("hardcore").get(o.key()).getAsString());
				}
				h.addProperty(shown, desc + " (" + range + ")");
			}
			help.add(lang, h);
		}
		root.add("_ayuda", help);
		JsonObject info = new JsonObject();
		info.addProperty("efectivo", perfil.efectivo());
		JsonObject dados = new JsonObject();
		perfil.valores().forEach(dados::add);
		info.add("valores", dados);
		JsonObject dif = new JsonObject();
		perfil.difieren().forEach((k, v) -> {
			JsonObject d = new JsonObject();
			d.add("fichero", v[0]);
			d.add("perfil", v[1]);
			dif.add(k, d);
		});
		info.add("difieren", dif);
		root.add("_perfil", info);
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
