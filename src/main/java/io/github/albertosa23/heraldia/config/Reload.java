package io.github.albertosa23.heraldia.config;

import com.google.gson.JsonPrimitive;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Hot reload of the configuration (/heraldia reload and the client's screen), pure logic: which options can
 * be applied without restarting and how the read values are merged with the ones in use.
 * <p>Those that affect generation (grids, frequencies, styles, roads, exclusion zones, arena placement
 * in a new world, the board of new villages...) are read at startup and the generation threads query them: if
 * they changed halfway, two neighboring chunks would be generated with different rules and /locate and the maps would no longer match
 * what was generated. Those keep the value in use until the next startup and are listed as pending.
 * <p>By default an option is NOT reloadable: a new option is only reloaded if it is added here on purpose.
 */
public final class Reload {
	/**
	 * Prefixes (or exact keys) of the options that are read every time they are used, outside generation: the difficulty
	 * (and its recomputation on loaded mobs), the bosses, the loot and its restocking, the arena (except its placement in a
	 * new world), the Guide, the own trades and the siege (rolled when a villager levels up), the golems and the
	 * Atlantis per-player chest and the web maps (which markers show) and the treasure hunt (T40: read when the loot is
	 * rolled and when a clue is used). And the gameplay profile (T36): it only sets options of those prefixes (never
	 * generation ones), so changing it applies fully without restarting. And the board quests and reputation (T38) and the
	 * caravans (T39) and the wayfarers that share their engine: read on each use. And the wizard huts (T43): the probability of an evil wizard and of a prize is
	 * read when each hut is decided. And the /heraldia update margin (T46): read on each analysis. And the ambient effects
	 * (bell, siren, mine drips): read on each check. And the villager conversations (P9a): read on each click.
	 */
	static final List<String> RELOADABLE = List.of("perfil", "dificultad.", "jefes.", "botin.", "arena.", "guia.", "golems.",
			"aldeas.vida.tratos_estilo", "aldeas.vida.asedios", "unicas.atlantida.cofre_unico_por_jugador", "mapas_web.", "encargos.", "reputacion.",
			"tesoro.", "caravanas.", "viajeros.", "chozas_mago.", "actualizar.", "ambiente.", "dialogos.",
			"eventos.");
	/** Exceptions inside a reloadable prefix: only checked at startup. */
	static final List<String> STARTUP_ONLY = List.of("arena.generar_en_mundos_nuevos");

	private Reload() {
	}

	/** Does the option apply without restarting? */
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
	 * Result of merging: the values that come into use, the changed options applied right away and the
	 * changed ones waiting for the next startup (with their value in use and the read one).
	 */
	public record Result(Map<String, JsonPrimitive> optionValues, List<String> applied, List<Pending> pending) {
		public boolean changes() {
			return !applied.isEmpty();
		}
	}

	public record Pending(String key, JsonPrimitive inUse, JsonPrimitive read) {
	}

	/**
	 * Merges the values read from the file with the ones in use: for reloadable ones the read one is taken; for the others,
	 * the one in use (and if it changes, it goes into pending). Same order and same keys as {@code inUse}; a key
	 * missing from {@code loaded} keeps its value.
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

	/** Value equality (2 and 2.0 are the same number). */
	static boolean same(JsonPrimitive a, JsonPrimitive b) {
		if (a.isNumber() && b.isNumber()) {
			return a.getAsDouble() == b.getAsDouble();
		}
		return a.equals(b);
	}
}
