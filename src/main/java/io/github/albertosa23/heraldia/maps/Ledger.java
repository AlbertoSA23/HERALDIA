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
 * Heraldia structures known in this world (those of the chunks that have loaded at some point since there is a web
 * map): the markers come from them. Thread-safe (added from the server thread and read from the web maps'
 * thread) and saved in &lt;world&gt;/{@value #FILE} so there is no wait for the chunks to load again after a restart.
 */
public final class Ledger {
	public static final String FILE = "heraldia_mapas_web.json";
	static final int VERSION = 1;
	private static final Gson GSON = new GsonBuilder().setPrettyPrinting().disableHtmlEscaping().create();

	private final Map<String, Site> sites = new ConcurrentHashMap<>();
	private final AtomicBoolean changed = new AtomicBoolean();

	/** Adds a site; true if it was not there. */
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

	/** Copy of the sites, in a stable order (layer, structure, x, z). */
	public List<Site> all() {
		List<Site> out = new ArrayList<>(sites.values());
		out.sort(Comparator.comparing(Site::layer).thenComparing(Site::structure).thenComparingInt(Site::x)
				.thenComparingInt(Site::z).thenComparingInt(Site::y));
		return out;
	}

	/** Is there anything unsaved? (and marks it as saved). */
	boolean takeChange() {
		return changed.getAndSet(false);
	}

	/** JSON of the ledger: {"version": 1, "sitios": [{"estructura", "capa", "sub", "x", "y", "z"}, ...]}. */
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

	/** Adds the sites of a JSON written by {@link #json()}; whatever is not understood is ignored. Returns how many it read. */
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
					Layer layer = Layer.of(s.get("capa").getAsString());
					Site site = new Site(s.get("estructura").getAsString(), layer, s.get("sub").getAsString(),
							s.get("x").getAsInt(), s.get("y").getAsInt(), s.get("z").getAsInt());
					if (sites.putIfAbsent(site.key(), site) == null) {
						n++;
					}
				} catch (RuntimeException ignored) {
					// broken entry or one from a layer that no longer exists: does not count
				}
			}
		} catch (RuntimeException ignored) {
			// broken file: start from scratch (it is rebuilt as the chunks load)
		}
		return n;
	}

	/** Reads the file if it exists (off the server thread). */
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

	/** Writes the file if it changed since the last time (off the server thread; writes aside and moves it). */
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

	/** For the tests. */
	Collection<String> keys() {
		return sites.keySet();
	}
}
