package io.github.albertosa23.heraldia.jefes;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.Reader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.jspecify.annotations.Nullable;

/**
 * Qué refuerzos llama cada guardián: heraldia/jefes.json (tools/gen/jefes.py), leído una vez del .jar. Por única (su
 * REFUERZOS o la familia de su guardián, ya resuelto por el generador) y, para un guardián que no se reconozca (sin
 * {@code heraldia_guardian.<id>} o de una única que ya no existe), la familia de su tipo de mob o la genérica.
 * Sin clases del juego: lo prueban los tests.
 */
public final class Refuerzos {
	/** Un refuerzo: tipo de mob ({@code minecraft:husk}) y equipo por ranura ({@code mainhand} → {@code minecraft:iron_sword}). */
	public record Refuerzo(String mob, Map<String, String> equipo) {
	}

	private final Map<String, List<Refuerzo>> unicas;
	private final Map<String, List<Refuerzo>> familias;
	private final Map<String, String> mobFamilia;
	private final List<Refuerzo> generica;

	private Refuerzos(Map<String, List<Refuerzo>> unicas, Map<String, List<Refuerzo>> familias, Map<String, String> mobFamilia,
			List<Refuerzo> generica) {
		this.unicas = unicas;
		this.familias = familias;
		this.mobFamilia = mobFamilia;
		this.generica = generica;
	}

	/** Refuerzos de un guardián de la única {@code sid} (null si no se sabe) y tipo {@code mob}. */
	public List<Refuerzo> para(@Nullable String sid, String mob) {
		if (sid != null) {
			List<Refuerzo> r = unicas.get(sid);
			if (r != null) {
				return r;
			}
		}
		String fam = mobFamilia.get(mob);
		return fam != null && familias.containsKey(fam) ? familias.get(fam) : generica;
	}

	public static Refuerzos leer(Reader r) {
		JsonObject o = JsonParser.parseReader(r).getAsJsonObject();
		Map<String, List<Refuerzo>> unicas = lista(o.getAsJsonObject("unicas"));
		Map<String, List<Refuerzo>> familias = lista(o.getAsJsonObject("familias"));
		Map<String, String> mobFamilia = new LinkedHashMap<>();
		o.getAsJsonObject("mob_familia").entrySet().forEach(e -> mobFamilia.put(e.getKey(), e.getValue().getAsString()));
		List<Refuerzo> generica = familias.getOrDefault(o.get("generica").getAsString(), List.of());
		return new Refuerzos(Map.copyOf(unicas), Map.copyOf(familias), Map.copyOf(mobFamilia), generica);
	}

	/** El del .jar (heraldia/jefes.json). */
	public static Refuerzos delJar() {
		String path = "/heraldia/jefes.json";
		try (InputStream in = Refuerzos.class.getResourceAsStream(path)) {
			if (in == null) {
				throw new IllegalStateException("Falta " + path + " en el .jar de Heraldia");
			}
			return leer(new InputStreamReader(in, StandardCharsets.UTF_8));
		} catch (IOException e) {
			throw new IllegalStateException("No se pudo leer " + path, e);
		}
	}

	private static Map<String, List<Refuerzo>> lista(JsonObject o) {
		Map<String, List<Refuerzo>> out = new LinkedHashMap<>();
		for (Map.Entry<String, JsonElement> e : o.entrySet()) {
			List<Refuerzo> l = new ArrayList<>();
			for (JsonElement x : (JsonArray) e.getValue()) {
				JsonObject r = x.getAsJsonObject();
				Map<String, String> equipo = new LinkedHashMap<>();
				if (r.has("equipo")) {
					r.getAsJsonObject("equipo").entrySet().forEach(q -> equipo.put(q.getKey(), q.getValue().getAsString()));
				}
				l.add(new Refuerzo(r.get("mob").getAsString(), Map.copyOf(equipo)));
			}
			out.put(e.getKey(), List.copyOf(l));
		}
		return out;
	}
}
