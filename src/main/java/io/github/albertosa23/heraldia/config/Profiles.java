package io.github.albertosa23.heraldia.config;

import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonPrimitive;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Perfiles de juego (opción {@value #CLAVE}: casual, estándar, hardcore o personalizado; tools/gen/opciones.py): cada
 * uno fija de golpe un conjunto de opciones de juego (dificultad, refuerzos de los guardianes, botín que se repone,
 * arena), nunca de la generación del mundo. Lógica pura: el esquema llega como JSON y el fichero como las opciones que
 * trae.
 * <ul>
 * <li>«estándar» da los valores por defecto: exactamente el comportamiento de siempre.</li>
 * <li>Una opción del perfil escrita en el fichero está <em>fijada a mano</em> y manda sobre el perfil; si su valor no es
 * el del perfil, el perfil efectivo pasa a ser «personalizado» y se informa de cuáles difieren.</li>
 * <li>«personalizado» no fija nada: cada opción con su valor del fichero o, si no está, el de por defecto.</li>
 * </ul>
 * Al escribir el fichero, las opciones del perfil solo se escriben si están fijadas a mano (si no, cambiar de perfil en el
 * fichero no haría nada).
 */
public final class Profiles {
	public static final String CLAVE = "perfil";
	public static final String STANDARD = "estandar", CUSTOM = "personalizado";

	private final Map<String, Map<String, JsonPrimitive>> profiles;
	private final List<String> keys;
	private final Set<String> generation;
	private final Map<String, JsonPrimitive> defaults;

	/**
	 * @param esquema  el de heraldia/opciones.json: {@code perfiles} ({perfil: {clave: valor}}) y en cada opción
	 *                 {@code perfil} (la fija el perfil) y {@code generacion} (es de la generación)
	 */
	Profiles(JsonObject schema) {
		Map<String, Map<String, JsonPrimitive>> p = new LinkedHashMap<>();
		JsonObject all = schema.has("perfiles") ? schema.getAsJsonObject("perfiles") : new JsonObject();
		for (Map.Entry<String, JsonElement> e : all.entrySet()) {
			Map<String, JsonPrimitive> v = new LinkedHashMap<>();
			e.getValue().getAsJsonObject().entrySet().forEach(kv -> v.put(kv.getKey(), kv.getValue().getAsJsonPrimitive()));
			p.put(e.getKey(), Collections.unmodifiableMap(v));
		}
		List<String> c = new ArrayList<>();
		Set<String> g = new LinkedHashSet<>();
		Map<String, JsonPrimitive> d = new LinkedHashMap<>();
		schema.getAsJsonArray("opciones").forEach(e -> {
			JsonObject o = e.getAsJsonObject();
			String k = o.get("clave").getAsString();
			if (o.has("perfil") && o.get("perfil").getAsBoolean()) {
				c.add(k);
				d.put(k, o.getAsJsonPrimitive("defecto"));
			}
			if (o.has("generacion") && o.get("generacion").getAsBoolean()) {
				g.add(k);
			}
		});
		this.profiles = Collections.unmodifiableMap(p);
		this.keys = List.copyOf(c);
		this.generation = Collections.unmodifiableSet(g);
		this.defaults = Collections.unmodifiableMap(d);
		for (String k : keys) {
			if (generation.contains(k)) {
				throw new IllegalStateException("el perfil no puede fijar " + k + ": es de la generación del mundo");
			}
		}
	}

	/** Opciones que fija un perfil, en el orden del esquema. */
	public List<String> keys() {
		return keys;
	}

	/** Opciones de la generación del mundo (un perfil nunca las toca). */
	public Set<String> generation() {
		return generation;
	}

	/** Nombres de los perfiles que fijan valores (sin «personalizado»), en orden. */
	public Set<String> names() {
		return profiles.keySet();
	}

	/** Valores que da el perfil a sus opciones; «personalizado» (o uno desconocido), los de por defecto. */
	public Map<String, JsonPrimitive> optionValues(String profile) {
		return profiles.getOrDefault(profile, defaults);
	}

	/**
	 * Resultado de aplicar un perfil: los valores de sus opciones, las fijadas a mano (con el valor del fichero) y las
	 * que difieren del perfil ({clave: [fichero, perfil]}).
	 */
	public record Applied(String chosen, String effective, Map<String, JsonPrimitive> optionValues, Map<String, JsonPrimitive> pinned,
						   Map<String, JsonPrimitive[]> differing) {
	}

	/**
	 * Aplica el perfil elegido a sus opciones. {@code fromFile} son las opciones del perfil que trae el fichero, ya
	 * validadas (las que no valen no deben llegar: no cuentan como fijadas).
	 */
	public Applied apply(String chosen, Map<String, JsonPrimitive> fromFile) {
		Map<String, JsonPrimitive> profile = optionValues(chosen);
		Map<String, JsonPrimitive> optionValues = new LinkedHashMap<>(), pinned = new LinkedHashMap<>();
		Map<String, JsonPrimitive[]> differing = new LinkedHashMap<>();
		for (String k : keys) {
			JsonPrimitive hand = fromFile.get(k);
			if (hand != null) {
				pinned.put(k, hand);
				if (!hand.equals(profile.get(k)) && !CUSTOM.equals(chosen)) {
					differing.put(k, new JsonPrimitive[] {hand, profile.get(k)});
				}
			}
			optionValues.put(k, hand != null ? hand : profile.get(k));
		}
		String effective = CUSTOM.equals(chosen) || !differing.isEmpty() ? CUSTOM : chosen;
		return new Applied(chosen, effective, Collections.unmodifiableMap(optionValues), Collections.unmodifiableMap(pinned),
				Collections.unmodifiableMap(differing));
	}

	/**
	 * Lo que la pantalla de configuración guarda como fijado a mano: las opciones del perfil cuyo valor no es el del
	 * perfil elegido (lo que coincide con el perfil lo sigue dando el perfil).
	 */
	public Set<String> pinnedByDifference(String chosen, Map<String, JsonPrimitive> optionValues) {
		Map<String, JsonPrimitive> profile = optionValues(chosen);
		Set<String> out = new LinkedHashSet<>();
		for (String k : keys) {
			JsonPrimitive v = optionValues.get(k);
			if (v != null && !v.equals(profile.get(k))) {
				out.add(k);
			}
		}
		return out;
	}

	/** Valor por defecto de una opción del perfil (el de «estándar»). */
	JsonPrimitive defaults(String key) {
		return defaults.get(key);
	}
}
