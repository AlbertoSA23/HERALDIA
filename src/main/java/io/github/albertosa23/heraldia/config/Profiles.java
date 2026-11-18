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
 * Gameplay profiles (option {@value #KEY}: casual, estandar, hardcore, ligero or personalizado; tools/gen/options.py): each
 * one sets at once a set of options. The gameplay profiles (casual, estandar, hardcore) set gameplay options only
 * (difficulty, guardian reinforcements, restocking loot, arena...), never world generation ones; the generation profiles
 * ({@code perfiles_generacion} in the schema: "ligero", for modest machines) also set some generation options. Pure logic:
 * the schema comes in as JSON and the file as the options it has.
 * <ul>
 * <li>"estandar" gives the default values: exactly the usual behavior.</li>
 * <li>A profile option written in the file is <em>set by hand</em> and overrides the profile; if the chosen profile sets
 * that option and the value is not the profile's, the effective profile becomes "personalizado" and the differing ones are
 * reported. An option the chosen profile does not set (a generation option with a gameplay profile) is a plain option: its
 * value from the file or, if absent, the default.</li>
 * <li>"personalizado" sets nothing: each option with its value from the file or, if absent, the default.</li>
 * </ul>
 * When the file is written, the profile options are only written if they are set by hand (otherwise, changing the profile in the
 * file would do nothing).
 */
public final class Profiles {
	public static final String KEY = "perfil";
	public static final String STANDARD = "estandar", CUSTOM = "personalizado", LIGHT = "ligero";

	private final Map<String, Map<String, JsonPrimitive>> profiles;
	private final Map<String, Map<String, JsonPrimitive>> full;
	private final List<String> keys;
	private final Set<String> generation;
	private final Set<String> generationProfiles;
	private final Map<String, JsonPrimitive> defaults;

	/**
	 * @param schema   the one from heraldia/opciones.json: {@code perfiles} ({profile: {key: value}}, each with the options it
	 *                 sets), {@code perfiles_generacion} (the profiles that may set generation options) and in each option
	 *                 {@code perfil} (some profile sets it) and {@code generacion} (it is a generation option)
	 */
	Profiles(JsonObject schema) {
		Map<String, Map<String, JsonPrimitive>> p = new LinkedHashMap<>();
		JsonObject all = schema.has("perfiles") ? schema.getAsJsonObject("perfiles") : new JsonObject();
		for (Map.Entry<String, JsonElement> e : all.entrySet()) {
			Map<String, JsonPrimitive> v = new LinkedHashMap<>();
			e.getValue().getAsJsonObject().entrySet().forEach(kv -> v.put(kv.getKey(), kv.getValue().getAsJsonPrimitive()));
			p.put(e.getKey(), Collections.unmodifiableMap(v));
		}
		Set<String> gp = new LinkedHashSet<>();
		if (schema.has("perfiles_generacion")) {
			schema.getAsJsonArray("perfiles_generacion").forEach(e -> gp.add(e.getAsString()));
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
		this.generationProfiles = Collections.unmodifiableSet(gp);
		this.defaults = Collections.unmodifiableMap(d);
		Map<String, Map<String, JsonPrimitive>> f = new LinkedHashMap<>();
		p.forEach((name, values) -> {
			for (String k : values.keySet()) {
				if (!defaults.containsKey(k)) {
					throw new IllegalStateException("el perfil " + name + " fija " + k + ", que no es una opción de perfil");
				}
				if (generation.contains(k) && !generationProfiles.contains(name)) {
					throw new IllegalStateException("el perfil " + name + " no puede fijar " + k + ": es de la generación del mundo");
				}
			}
			Map<String, JsonPrimitive> v = new LinkedHashMap<>(defaults);
			v.putAll(values);
			f.put(name, Collections.unmodifiableMap(v));
		});
		this.full = Collections.unmodifiableMap(f);
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

	/**
	 * Values the profile gives all the profile options (those it does not set, the default); "personalizado" (or an unknown
	 * one), the defaults.
	 */
	public Map<String, JsonPrimitive> optionValues(String profile) {
		return full.getOrDefault(profile, defaults);
	}

	/** The options the profile itself sets ("personalizado" or an unknown one: those of "estandar"), in the schema's order. */
	public List<String> keysOf(String profile) {
		Map<String, JsonPrimitive> own = profiles.getOrDefault(profile, profiles.get(STANDARD));
		return own == null ? keys : keys.stream().filter(own::containsKey).toList();
	}

	/** Does the profile change world generation? (only in the chunks generated from then on) */
	public boolean touchesGeneration(String profile) {
		return generationProfiles.contains(profile);
	}

	/** The generation options the profile sets (empty for a gameplay profile). */
	public List<String> generationKeysOf(String profile) {
		return touchesGeneration(profile) ? keysOf(profile).stream().filter(generation::contains).toList() : List.of();
	}

	/**
	 * Changes the profile in some already resolved values (the client's screen and the in-game panel): the profile options
	 * that had the previous profile's value (or all of them, coming from "personalizado") take the new one's; those set by hand
	 * (another value) stay. Going to "personalizado" keeps every value. Returns a new map with {@value #KEY} changed too.
	 */
	public Map<String, JsonPrimitive> switchTo(String from, String to, Map<String, JsonPrimitive> values) {
		Map<String, JsonPrimitive> before = optionValues(from), now = optionValues(to);
		Map<String, JsonPrimitive> out = new LinkedHashMap<>(values);
		for (String k : keys) {
			if (!CUSTOM.equals(to) && (CUSTOM.equals(from) || before.get(k).equals(values.get(k)))) {
				out.put(k, now.get(k));
			}
		}
		out.put(KEY, new JsonPrimitive(to));
		return out;
	}

	/** Options that became profile options with the generation profiles (file format 3): those "estandar" does not set. */
	List<String> addedInVersion3() {
		List<String> own = keysOf(STANDARD);
		return keys.stream().filter(k -> !own.contains(k)).toList();
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
		Set<String> own = Set.copyOf(keysOf(chosen));
		Map<String, JsonPrimitive> optionValues = new LinkedHashMap<>(), pinned = new LinkedHashMap<>();
		Map<String, JsonPrimitive[]> differing = new LinkedHashMap<>();
		for (String k : keys) {
			JsonPrimitive hand = fromFile.get(k);
			if (hand != null) {
				pinned.put(k, hand);
				if (!hand.equals(profile.get(k)) && !CUSTOM.equals(chosen) && own.contains(k)) {
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
