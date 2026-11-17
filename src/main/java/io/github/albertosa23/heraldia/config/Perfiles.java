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
public final class Perfiles {
	public static final String CLAVE = "perfil";
	public static final String ESTANDAR = "estandar", PERSONALIZADO = "personalizado";

	private final Map<String, Map<String, JsonPrimitive>> perfiles;
	private final List<String> claves;
	private final Set<String> generacion;
	private final Map<String, JsonPrimitive> defecto;

	/**
	 * @param esquema  el de heraldia/opciones.json: {@code perfiles} ({perfil: {clave: valor}}) y en cada opción
	 *                 {@code perfil} (la fija el perfil) y {@code generacion} (es de la generación)
	 */
	Perfiles(JsonObject esquema) {
		Map<String, Map<String, JsonPrimitive>> p = new LinkedHashMap<>();
		JsonObject todos = esquema.has("perfiles") ? esquema.getAsJsonObject("perfiles") : new JsonObject();
		for (Map.Entry<String, JsonElement> e : todos.entrySet()) {
			Map<String, JsonPrimitive> v = new LinkedHashMap<>();
			e.getValue().getAsJsonObject().entrySet().forEach(kv -> v.put(kv.getKey(), kv.getValue().getAsJsonPrimitive()));
			p.put(e.getKey(), Collections.unmodifiableMap(v));
		}
		List<String> c = new ArrayList<>();
		Set<String> g = new LinkedHashSet<>();
		Map<String, JsonPrimitive> d = new LinkedHashMap<>();
		esquema.getAsJsonArray("opciones").forEach(e -> {
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
		this.perfiles = Collections.unmodifiableMap(p);
		this.claves = List.copyOf(c);
		this.generacion = Collections.unmodifiableSet(g);
		this.defecto = Collections.unmodifiableMap(d);
		for (String k : claves) {
			if (generacion.contains(k)) {
				throw new IllegalStateException("el perfil no puede fijar " + k + ": es de la generación del mundo");
			}
		}
	}

	/** Opciones que fija un perfil, en el orden del esquema. */
	public List<String> claves() {
		return claves;
	}

	/** Opciones de la generación del mundo (un perfil nunca las toca). */
	public Set<String> generacion() {
		return generacion;
	}

	/** Nombres de los perfiles que fijan valores (sin «personalizado»), en orden. */
	public Set<String> nombres() {
		return perfiles.keySet();
	}

	/** Valores que da el perfil a sus opciones; «personalizado» (o uno desconocido), los de por defecto. */
	public Map<String, JsonPrimitive> valores(String perfil) {
		return perfiles.getOrDefault(perfil, defecto);
	}

	/**
	 * Resultado de aplicar un perfil: los valores de sus opciones, las fijadas a mano (con el valor del fichero) y las
	 * que difieren del perfil ({clave: [fichero, perfil]}).
	 */
	public record Aplicado(String elegido, String efectivo, Map<String, JsonPrimitive> valores, Map<String, JsonPrimitive> fijadas,
						   Map<String, JsonPrimitive[]> difieren) {
	}

	/**
	 * Aplica el perfil elegido a sus opciones. {@code delFichero} son las opciones del perfil que trae el fichero, ya
	 * validadas (las que no valen no deben llegar: no cuentan como fijadas).
	 */
	public Aplicado aplicar(String elegido, Map<String, JsonPrimitive> delFichero) {
		Map<String, JsonPrimitive> perfil = valores(elegido);
		Map<String, JsonPrimitive> valores = new LinkedHashMap<>(), fijadas = new LinkedHashMap<>();
		Map<String, JsonPrimitive[]> difieren = new LinkedHashMap<>();
		for (String k : claves) {
			JsonPrimitive mano = delFichero.get(k);
			if (mano != null) {
				fijadas.put(k, mano);
				if (!mano.equals(perfil.get(k)) && !PERSONALIZADO.equals(elegido)) {
					difieren.put(k, new JsonPrimitive[] {mano, perfil.get(k)});
				}
			}
			valores.put(k, mano != null ? mano : perfil.get(k));
		}
		String efectivo = PERSONALIZADO.equals(elegido) || !difieren.isEmpty() ? PERSONALIZADO : elegido;
		return new Aplicado(elegido, efectivo, Collections.unmodifiableMap(valores), Collections.unmodifiableMap(fijadas),
				Collections.unmodifiableMap(difieren));
	}

	/**
	 * Lo que la pantalla de configuración guarda como fijado a mano: las opciones del perfil cuyo valor no es el del
	 * perfil elegido (lo que coincide con el perfil lo sigue dando el perfil).
	 */
	public Set<String> fijadasPorDiferencia(String elegido, Map<String, JsonPrimitive> valores) {
		Map<String, JsonPrimitive> perfil = valores(elegido);
		Set<String> out = new LinkedHashSet<>();
		for (String k : claves) {
			JsonPrimitive v = valores.get(k);
			if (v != null && !v.equals(perfil.get(k))) {
				out.add(k);
			}
		}
		return out;
	}

	/** Valor por defecto de una opción del perfil (el de «estándar»). */
	JsonPrimitive defecto(String clave) {
		return defecto.get(clave);
	}
}
