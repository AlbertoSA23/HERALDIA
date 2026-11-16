package io.github.albertosa23.heraldia.config;

import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonPrimitive;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Optional;
import org.jspecify.annotations.Nullable;

/**
 * Una opción del esquema heraldia/opciones.json (generado por tools/gen/opciones.py): clave, valor por defecto, rango,
 * textos y sección de la pantalla de configuración. La misma validación sirve al leer el fichero y en la pantalla.
 *
 * @param pattern  patrón de las opciones repetidas (p. ej. {@code aldeas.estilos.<estilo>}), o null
 * @param argNames claves de traducción del nombre de cada argumento (null en una posición: el argumento tal cual)
 */
public record ConfigOption(String key, JsonPrimitive defaultValue, @Nullable Integer min, @Nullable Integer max,
						   String help, List<String> args, @Nullable String pattern, String section, String name,
						   List<@Nullable String> argNames) {

	static ConfigOption of(JsonObject o) {
		return new ConfigOption(o.get("clave").getAsString(), o.getAsJsonPrimitive("defecto"),
				o.has("min") ? o.get("min").getAsInt() : null, o.has("max") ? o.get("max").getAsInt() : null,
				o.get("ayuda").getAsString(), strings(o, "args"), o.has("patron") ? o.get("patron").getAsString() : null,
				o.get("seccion").getAsString(), o.get("nombre").getAsString(), strings(o, "args_nombre"));
	}

	private static List<@Nullable String> strings(JsonObject o, String field) {
		if (!o.has(field)) {
			return List.of();
		}
		List<@Nullable String> out = new ArrayList<>();
		for (JsonElement e : o.getAsJsonArray(field)) {
			out.add(e.isJsonNull() ? null : e.getAsString());
		}
		return Collections.unmodifiableList(out);
	}

	public boolean isBoolean() {
		return defaultValue.isBoolean();
	}

	/** Opción con decimales: su valor por defecto se escribe con punto en el esquema (p. ej. 2.0). */
	public boolean decimal() {
		return defaultValue.isNumber() && defaultValue.getAsString().contains(".");
	}

	/** El valor normalizado si es válido para esta opción (booleano, entero o, si es decimal, número dentro del rango). */
	public Optional<JsonPrimitive> accept(JsonPrimitive given) {
		if (isBoolean()) {
			return given.isBoolean() ? Optional.of(given) : Optional.empty();
		}
		if (given.isNumber()) {
			double d = given.getAsDouble();
			if (decimal()) {
				return Double.isFinite(d) && d >= min && d <= max ? Optional.of(new JsonPrimitive(d)) : Optional.empty();
			}
			if (d == Math.rint(d) && d >= min && d <= max) {
				return Optional.of(new JsonPrimitive((int) d));
			}
		}
		return Optional.empty();
	}

	/** Lo que se escribe en una casilla de texto de la pantalla: un entero dentro del rango, sin nada más. */
	public Optional<JsonPrimitive> parse(String text) {
		if (isBoolean()) {
			return "true".equals(text) || "false".equals(text) ? Optional.of(new JsonPrimitive(Boolean.parseBoolean(text))) : Optional.empty();
		}
		String t = text.strip();
		if (decimal()) {
			if (t.isEmpty() || t.length() > 11 || !t.matches("-?\\d+(\\.\\d+)?")) {
				return Optional.empty();
			}
			double d = Double.parseDouble(t);
			return d >= min && d <= max ? Optional.of(new JsonPrimitive(d)) : Optional.empty();
		}
		if (t.isEmpty() || t.length() > 11 || !t.matches("-?\\d+")) {
			return Optional.empty();
		}
		long v = Long.parseLong(t);
		return v >= min && v <= max ? Optional.of(new JsonPrimitive((int) v)) : Optional.empty();
	}
}
