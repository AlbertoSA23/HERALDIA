package io.github.albertosa23.heraldia.config;

import com.google.gson.JsonPrimitive;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Recarga en caliente de la configuración (/heraldia reload y la pantalla del cliente), lógica pura: qué opciones se
 * pueden aplicar sin reiniciar y cómo se mezclan los valores leídos con los que están en uso.
 * <p>Las que afectan a la generación (rejillas, frecuencias, estilos, caminos, zonas de exclusión, colocación de la arena
 * en un mundo nuevo, el tablón de las aldeas nuevas...) se leen al arrancar y las consultan los hilos de generación: si
 * cambiaran a medias, dos chunks vecinos se generarían con reglas distintas y /locate y los mapas dejarían de coincidir
 * con lo generado. Esas se quedan con el valor en uso hasta el siguiente arranque y se listan como pendientes.
 * <p>Por defecto una opción NO es recargable: una opción nueva solo se recarga si se añade aquí a propósito.
 */
public final class Reload {
	/**
	 * Prefijos (o claves exactas) de las opciones que se leen cada vez que se usan, fuera de la generación: la dificultad
	 * (y su recálculo en los mobs cargados), los jefes, el botín y su reposición, la arena (salvo su colocación en un
	 * mundo nuevo), la Guía, los tratos propios y el asedio (se sortean al subir de nivel un aldeano), los gólems y el
	 * cofre por jugador de la Atlántida y los mapas web (qué marcadores salen) y la búsqueda del tesoro (T40: se leen al tirar el botín y al usar una pista). Y el perfil de juego (T36): solo fija opciones de esos prefijos (nunca de la
 * generación), así que cambiarlo se aplica entero sin reiniciar. Y los encargos del tablón y la reputación (T38) y las
	 * caravanas (T39): se leen en cada uso. Y las chozas de mago (T43): la probabilidad de mago malvado y de premio se
	 * leen al decidir cada choza. Y el margen de /heraldia update (T46): se lee en cada análisis.
	 */
	static final List<String> RELOADABLE = List.of("perfil", "dificultad.", "jefes.", "botin.", "arena.", "guia.", "golems.",
			"aldeas.vida.tratos_estilo", "aldeas.vida.asedios", "unicas.atlantida.cofre_unico_por_jugador", "mapas_web.", "encargos.", "reputacion.",
			"tesoro.", "caravanas.", "chozas_mago.", "actualizar.");
	/** Excepciones dentro de un prefijo recargable: solo se miran al arrancar. */
	static final List<String> STARTUP_ONLY = List.of("arena.generar_en_mundos_nuevos");

	private Reload() {
	}

	/** ¿Se aplica la opción sin reiniciar? */
	public static boolean reloadable(String key) {
		if (STARTUP_ONLY.contains(key)) {
			return false;
		}
		for (String p : RELOADABLE) {
			if (p.endsWith(".") ? key.startsWith(p) : key.equals(p)) {
				return true;
			}
		}
		return false;
	}

	/**
	 * Resultado de mezclar: los valores que pasan a estar en uso, las opciones cambiadas que se aplican ya y las
	 * cambiadas que esperan al siguiente arranque (con su valor en uso y el leído).
	 */
	public record Result(Map<String, JsonPrimitive> optionValues, List<String> applied, List<Pending> pending) {
		public boolean changes() {
			return !applied.isEmpty();
		}
	}

	public record Pending(String key, JsonPrimitive inUse, JsonPrimitive read) {
	}

	/**
	 * Mezcla los valores leídos del fichero con los que están en uso: de las recargables se toma el leído; de las demás,
	 * el que está en uso (y si cambia, queda en pendientes). Mismo orden y mismas claves que {@code inUse}; una clave que
	 * falte en {@code loaded} conserva su valor.
	 */
	public static Result merge(Map<String, JsonPrimitive> inUse, Map<String, JsonPrimitive> loaded) {
		Map<String, JsonPrimitive> out = new LinkedHashMap<>();
		List<String> applied = new ArrayList<>();
		List<Pending> pending = new ArrayList<>();
		for (Map.Entry<String, JsonPrimitive> e : inUse.entrySet()) {
			String k = e.getKey();
			JsonPrimitive actual = e.getValue(), newValue = loaded.getOrDefault(k, actual);
			boolean differs = !same(actual, newValue);
			if (reloadable(k)) {
				out.put(k, newValue);
				if (differs) {
					applied.add(k);
				}
			} else {
				out.put(k, actual);
				if (differs) {
					pending.add(new Pending(k, actual, newValue));
				}
			}
		}
		return new Result(out, List.copyOf(applied), List.copyOf(pending));
	}

	/** Igualdad de valores (2 y 2.0 son el mismo número). */
	static boolean same(JsonPrimitive a, JsonPrimitive b) {
		if (a.isNumber() && b.isNumber()) {
			return a.getAsDouble() == b.getAsDouble();
		}
		return a.equals(b);
	}
}
