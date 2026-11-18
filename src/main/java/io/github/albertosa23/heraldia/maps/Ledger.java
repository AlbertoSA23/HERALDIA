package io.github.albertosa23.heraldia.maps;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.AtomicMoveNotSupportedException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * Estructuras de Heraldia conocidas en este mundo (las de los chunks que se han cargado alguna vez desde que hay un mapa
 * web): de ellas salen los marcadores. Seguro entre hilos (se añade desde el hilo del servidor y se lee desde el de los
 * mapas web) y guardado en &lt;mundo&gt;/{@value #FILE} para no esperar a que vuelvan a cargarse los chunks tras reiniciar.
 */
public final class Ledger {
	public static final String FILE = "heraldia_mapas_web.json";
	static final int VERSION = 1;
	private static final Gson GSON = new GsonBuilder().setPrettyPrinting().disableHtmlEscaping().create();

	private final Map<String, Site> sites = new ConcurrentHashMap<>();
	private final AtomicBoolean changed = new AtomicBoolean();

	/** Añade un sitio; true si no estaba. */
	public boolean add(Site s) {
		boolean newValue = sites.putIfAbsent(s.key(), s) == null;
		if (newValue) {
			changed.set(true);
		}
		return newValue;
	}

	public int size() {
		return sites.size();
	}

	/** Copia de los sitios, en un orden estable (capa, estructura, x, z). */
	public List<Site> all() {
		List<Site> out = new ArrayList<>(sites.values());
		out.sort(Comparator.comparing(Site::layer).thenComparing(Site::structure).thenComparingInt(Site::x)
				.thenComparingInt(Site::z).thenComparingInt(Site::y));
		return out;
	}

	/** ¿Hay algo sin guardar? (y lo da por guardado). */
	boolean takeChange() {
		return changed.getAndSet(false);
	}

	/** JSON del registro: {"version": 1, "sitios": [{"estructura", "capa", "sub", "x", "y", "z"}, ...]}. */
	public String json() {
		JsonObject o = new JsonObject();
		o.addProperty("version", VERSION);
		JsonArray a = new JsonArray();
		for (Site s : all()) {
			JsonObject e = new JsonObject();
			e.addProperty("estructura", s.structure());
			e.addProperty("capa", s.layer().id());
			e.addProperty("sub", s.sub());
			e.addProperty("x", s.x());
			e.addProperty("y", s.y());
			e.addProperty("z", s.z());
			a.add(e);
		}
		o.add("sitios", a);
		return GSON.toJson(o);
	}

	/** Suma los sitios de un JSON escrito por {@link #json()}; lo que no se entienda se ignora. Devuelve cuántos ha leído. */
	public int addJson(String text) {
		int n = 0;
		try {
			JsonElement root = JsonParser.parseString(text);
			if (!root.isJsonObject() || !root.getAsJsonObject().has("sitios") || !root.getAsJsonObject().get("sitios").isJsonArray()) {
				return 0;
			}
			for (JsonElement e : root.getAsJsonObject().getAsJsonArray("sitios")) {
				try {
					JsonObject s = e.getAsJsonObject();
					Layer layer = Layer.valueOf(s.get("capa").getAsString().toUpperCase(Locale.ROOT));
					Site site = new Site(s.get("estructura").getAsString(), layer, s.get("sub").getAsString(),
							s.get("x").getAsInt(), s.get("y").getAsInt(), s.get("z").getAsInt());
					if (sites.putIfAbsent(site.key(), site) == null) {
						n++;
					}
				} catch (RuntimeException ignored) {
					// entrada rota o de una capa que ya no existe: no cuenta
				}
			}
		} catch (RuntimeException ignored) {
			// fichero roto: se empieza de cero (se rehace al cargarse los chunks)
		}
		return n;
	}

	/** Lee el fichero si existe (fuera del hilo del servidor). */
	public int read(Path file) {
		if (!Files.isRegularFile(file)) {
			return 0;
		}
		try {
			return addJson(Files.readString(file, StandardCharsets.UTF_8));
		} catch (IOException e) {
			return 0;
		}
	}

	/** Escribe el fichero si ha cambiado desde la última vez (fuera del hilo del servidor; escribe aparte y lo mueve). */
	public void save(Path file) throws IOException {
		if (!takeChange()) {
			return;
		}
		Path tmp = file.resolveSibling(file.getFileName() + ".tmp");
		Files.writeString(tmp, json(), StandardCharsets.UTF_8);
		try {
			Files.move(tmp, file, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
		} catch (AtomicMoveNotSupportedException e) {
			Files.move(tmp, file, StandardCopyOption.REPLACE_EXISTING);
		}
	}

	/** Para las pruebas. */
	Collection<String> keys() {
		return sites.keySet();
	}
}
