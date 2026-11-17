package io.github.albertosa23.heraldia.mapas;

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
 * mapas web) y guardado en &lt;mundo&gt;/{@value #FICHERO} para no esperar a que vuelvan a cargarse los chunks tras reiniciar.
 */
public final class Registro {
	public static final String FICHERO = "heraldia_mapas_web.json";
	static final int VERSION = 1;
	private static final Gson GSON = new GsonBuilder().setPrettyPrinting().disableHtmlEscaping().create();

	private final Map<String, Sitio> sitios = new ConcurrentHashMap<>();
	private final AtomicBoolean cambiado = new AtomicBoolean();

	/** Añade un sitio; true si no estaba. */
	public boolean anadir(Sitio s) {
		boolean nuevo = sitios.putIfAbsent(s.clave(), s) == null;
		if (nuevo) {
			cambiado.set(true);
		}
		return nuevo;
	}

	public int tamano() {
		return sitios.size();
	}

	/** Copia de los sitios, en un orden estable (capa, estructura, x, z). */
	public List<Sitio> todos() {
		List<Sitio> out = new ArrayList<>(sitios.values());
		out.sort(Comparator.comparing(Sitio::capa).thenComparing(Sitio::estructura).thenComparingInt(Sitio::x)
				.thenComparingInt(Sitio::z).thenComparingInt(Sitio::y));
		return out;
	}

	/** ¿Hay algo sin guardar? (y lo da por guardado). */
	boolean sacarCambio() {
		return cambiado.getAndSet(false);
	}

	/** JSON del registro: {"version": 1, "sitios": [{"estructura", "capa", "sub", "x", "y", "z"}, ...]}. */
	public String json() {
		JsonObject o = new JsonObject();
		o.addProperty("version", VERSION);
		JsonArray a = new JsonArray();
		for (Sitio s : todos()) {
			JsonObject e = new JsonObject();
			e.addProperty("estructura", s.estructura());
			e.addProperty("capa", s.capa().id());
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
	public int sumarJson(String texto) {
		int n = 0;
		try {
			JsonElement raiz = JsonParser.parseString(texto);
			if (!raiz.isJsonObject() || !raiz.getAsJsonObject().has("sitios") || !raiz.getAsJsonObject().get("sitios").isJsonArray()) {
				return 0;
			}
			for (JsonElement e : raiz.getAsJsonObject().getAsJsonArray("sitios")) {
				try {
					JsonObject s = e.getAsJsonObject();
					Capa capa = Capa.valueOf(s.get("capa").getAsString().toUpperCase(Locale.ROOT));
					Sitio sitio = new Sitio(s.get("estructura").getAsString(), capa, s.get("sub").getAsString(),
							s.get("x").getAsInt(), s.get("y").getAsInt(), s.get("z").getAsInt());
					if (sitios.putIfAbsent(sitio.clave(), sitio) == null) {
						n++;
					}
				} catch (RuntimeException ignorada) {
					// entrada rota o de una capa que ya no existe: no cuenta
				}
			}
		} catch (RuntimeException ignorado) {
			// fichero roto: se empieza de cero (se rehace al cargarse los chunks)
		}
		return n;
	}

	/** Lee el fichero si existe (fuera del hilo del servidor). */
	public int leer(Path fichero) {
		if (!Files.isRegularFile(fichero)) {
			return 0;
		}
		try {
			return sumarJson(Files.readString(fichero, StandardCharsets.UTF_8));
		} catch (IOException e) {
			return 0;
		}
	}

	/** Escribe el fichero si ha cambiado desde la última vez (fuera del hilo del servidor; escribe aparte y lo mueve). */
	public void guardar(Path fichero) throws IOException {
		if (!sacarCambio()) {
			return;
		}
		Path tmp = fichero.resolveSibling(fichero.getFileName() + ".tmp");
		Files.writeString(tmp, json(), StandardCharsets.UTF_8);
		try {
			Files.move(tmp, fichero, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
		} catch (AtomicMoveNotSupportedException e) {
			Files.move(tmp, fichero, StandardCopyOption.REPLACE_EXISTING);
		}
	}

	/** Para las pruebas. */
	Collection<String> claves() {
		return sitios.keySet();
	}
}
