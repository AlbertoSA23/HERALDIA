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
 * Gameplay profiles (option {@value #KEY}: casual, estandar, hardcore or personalizado; tools/gen/options.py): each
 * one sets at once a set of gameplay options (difficulty, guardian reinforcements, restocking loot,
 * arena), never world generation ones. Pure logic: the schema comes in as JSON and the file as the options it
 * has.
 * <ul>
 * <li>"estandar" gives the default values: exactly the usual behavior.</li>
 * <li>A profile option written in the file is <em>set by hand</em> and overrides the profile; if its value is not
 * the profile's, the effective profile becomes "personalizado" and the differing ones are reported.</li>
 * <li>"personalizado" sets nothing: each option with its value from the file or, if absent, the default.</li>
 * </ul>
 * When the file is written, the profile options are only written if they are set by hand (otherwise, changing the profile in the
 * file would do nothing).
 */
public final class Profiles {
	public static final String KEY = "perfil";
	public static final String STANDARD = "estandar", CUSTOM = "personalizado";

	private final Map<String, Map<String, JsonPrimitive>> profiles;
	private final List<String> keys;
	private final Set<String> generation;
	private final Map<String, JsonPrimitive> defaults;

	/**
	 * @param schema   the one from heraldia/opciones.json: {@code perfiles} ({profile: {key: value}}) and in each option
	 *                 {@code perfil} (the profile sets it) and {@code generacion} (it is a generation option)
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

	/** Options a profile sets, in the schema's order. */
	public List<String> keys() {
		return keys;
	}

	/** World generation options (a profile never touches them). */
	public Set<String> generation() {
		return generation;
	}

	/** Names of the profiles that set values (without "personalizado"), in order. */
	public Set<String> names() {
		return profiles.keySet();
	}

	/** Values the profile gives its options; "personalizado" (or an unknown one), the defaults. */
	public Map<String, JsonPrimitive> optionValues(String profile) {
		return profiles.getOrDefault(profile, defaults);
	}

	/**
	 * Result of applying a profile: the values of its options, those set by hand (with the file's value) and those
	 * that differ from the profile ({key: [file, profile]}).
	 */
	public record Applied(String chosen, String effective, Map<String, JsonPrimitive> optionValues, Map<String, JsonPrimitive> pinned,
						   Map<String, JsonPrimitive[]> differing) {
	}

	/**
	 * Applies the chosen profile to its options. {@code fromFile} are the profile options the file has, already
	 * validated (invalid ones must not get here: they do not count as set).
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
	 * What the configuration screen saves as set by hand: the profile options whose value is not the
	 * chosen profile's (what matches the profile is still given by the profile).
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

	/** Default value of a profile option (that of "estandar"). */
	JsonPrimitive defaults(String key) {
		return defaults.get(key);
	}
}
