package io.github.albertosa23.heraldia.bosses;

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
public final class Reinforcements {
	/** Un refuerzo: tipo de mob ({@code minecraft:husk}) y equipo por ranura ({@code mainhand} → {@code minecraft:iron_sword}). */
	public record Reinforcement(String mob, Map<String, String> equipment) {
	}

	private final Map<String, List<Reinforcement>> uniques;
	private final Map<String, List<Reinforcement>> families;
	private final Map<String, String> mobFamily;
	private final List<Reinforcement> generic;

	private Reinforcements(Map<String, List<Reinforcement>> uniques, Map<String, List<Reinforcement>> families, Map<String, String> mobFamily,
			List<Reinforcement> generic) {
		this.uniques = uniques;
		this.families = families;
		this.mobFamily = mobFamily;
		this.generic = generic;
	}

	/** Refuerzos de un guardián de la única {@code sid} (null si no se sabe) y tipo {@code mob}. */
	public List<Reinforcement> stop(@Nullable String sid, String mob) {
		if (sid != null) {
			List<Reinforcement> r = uniques.get(sid);
			if (r != null) {
				return r;
			}
		}
		String fam = mobFamily.get(mob);
		return fam != null && families.containsKey(fam) ? families.get(fam) : generic;
	}

	public static Reinforcements read(Reader r) {
		JsonObject o = JsonParser.parseReader(r).getAsJsonObject();
		Map<String, List<Reinforcement>> uniques = list(o.getAsJsonObject("unicas"));
		Map<String, List<Reinforcement>> families = list(o.getAsJsonObject("familias"));
		Map<String, String> mobFamily = new LinkedHashMap<>();
		o.getAsJsonObject("mob_familia").entrySet().forEach(e -> mobFamily.put(e.getKey(), e.getValue().getAsString()));
		List<Reinforcement> generic = families.getOrDefault(o.get("generica").getAsString(), List.of());
		return new Reinforcements(Map.copyOf(uniques), Map.copyOf(families), Map.copyOf(mobFamily), generic);
	}

	/** El del .jar (heraldia/jefes.json). */
	public static Reinforcements fromJar() {
		String path = "/heraldia/jefes.json";
		try (InputStream in = Reinforcements.class.getResourceAsStream(path)) {
			if (in == null) {
				throw new IllegalStateException("Falta " + path + " en el .jar de Heraldia");
			}
			return read(new InputStreamReader(in, StandardCharsets.UTF_8));
		} catch (IOException e) {
			throw new IllegalStateException("No se pudo leer " + path, e);
		}
	}

	private static Map<String, List<Reinforcement>> list(JsonObject o) {
		Map<String, List<Reinforcement>> out = new LinkedHashMap<>();
		for (Map.Entry<String, JsonElement> e : o.entrySet()) {
			List<Reinforcement> l = new ArrayList<>();
			for (JsonElement x : (JsonArray) e.getValue()) {
				JsonObject r = x.getAsJsonObject();
				Map<String, String> equipment = new LinkedHashMap<>();
				if (r.has("equipo")) {
					r.getAsJsonObject("equipo").entrySet().forEach(q -> equipment.put(q.getKey(), q.getValue().getAsString()));
				}
				l.add(new Reinforcement(r.get("mob").getAsString(), Map.copyOf(equipment)));
			}
			out.put(e.getKey(), List.copyOf(l));
		}
		return out;
	}
}
