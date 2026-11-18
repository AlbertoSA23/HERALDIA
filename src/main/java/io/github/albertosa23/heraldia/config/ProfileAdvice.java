package io.github.albertosa23.heraldia.config;

import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Optional;
import java.util.Set;

/**
 * Pure logic of the light profile's notices (command/ProfileNotice does the I/O): which profile to suggest on a first start
 * from the machine, and whether world generation changed in a world already started (seams).
 * <ul>
 * <li>Suggestion: only when the file does not say which profile to use (a first start). With little memory for Java or few
 * cores the light profile is suggested; otherwise nothing (the default profile is fine). It is never applied on its own.</li>
 * <li>Seams: the generation options in use are saved in the world (attachment heraldia:generacion_mundo) at every start; if
 * they differ from those of the previous start in a world already played, only the chunks generated from now on follow the
 * new ones and the mod warns. A world without that record (from before) is only warned if it starts with a profile that
 * changes generation.</li>
 * </ul>
 */
public final class ProfileAdvice {
	/**
	 * Below this much memory for Java (MB; {@code Runtime.maxMemory()}, a bit less than -Xmx) the machine is modest: a server
	 * started with -Xmx3G or less. The light profile saves CPU and server ticks, not RAM (measured with
	 * tools/smoke/generation_cost.py: 441-461 MB at most after GC with either profile, 401-403 without Heraldia); the memory is a
	 * sign of a modest machine because hosting plans with little RAM usually come with few, slow cores.
	 */
	public static final long LOW_MEMORY_MB = 3584;
	/** With this many cores or fewer the machine is modest: world generation runs on (cores - 1) worker threads. */
	public static final int LOW_CORES = 2;
	/** Options left out of the seam check: they place no structure in the land (the arena builds itself next to spawn). */
	static final String[] NOT_SEAMS = {"arena."};

	private ProfileAdvice() {
	}

	/** The profile to suggest for a machine with {@code maxMemoryBytes} for Java and {@code cores} cores; empty: none. */
	public static Optional<String> suggest(long maxMemoryBytes, int cores) {
		boolean modest = maxMemoryBytes / (1024 * 1024) < LOW_MEMORY_MB || cores <= LOW_CORES;
		return modest ? Optional.of(Profiles.LIGHT) : Optional.empty();
	}

	/** Memory in GB with one decimal, as it is shown ("2.9"). */
	public static String gb(long bytes) {
		return String.format(java.util.Locale.ROOT, "%.1f", bytes / (1024.0 * 1024 * 1024));
	}

	/** The generation options in use, as text (what is saved in the world): those of {@code generation}, without the arena. */
	public static Map<String, String> fingerprint(Map<String, com.google.gson.JsonPrimitive> values, Set<String> generation) {
		Map<String, String> out = new LinkedHashMap<>();
		values.forEach((k, v) -> {
			if (generation.contains(k) && !excluded(k)) {
				out.put(k, v.getAsString());
			}
		});
		return out;
	}

	private static boolean excluded(String key) {
		for (String p : NOT_SEAMS) {
			if (key.startsWith(p)) {
				return true;
			}
		}
		return false;
	}

	/** The options whose value changed (or appeared or disappeared) between two starts: {key: [before, now]}, in order. */
	public static Map<String, String[]> changed(Map<String, String> before, Map<String, String> now) {
		Set<String> keys = new LinkedHashSet<>(now.keySet());
		keys.addAll(before.keySet());
		Map<String, String[]> out = new LinkedHashMap<>();
		for (String k : keys) {
			String a = before.get(k), b = now.get(k);
			if (a == null || b == null) {
				continue;                  // an option of another version of the mod: not a change of this world's settings
			}
			if (!same(a, b)) {
				out.put(k, new String[] {a, b});
			}
		}
		return out;
	}

	/** 2 and 2.0 are the same number. */
	private static boolean same(String a, String b) {
		if (a.equals(b)) {
			return true;
		}
		try {
			return Double.parseDouble(a) == Double.parseDouble(b);
		} catch (NumberFormatException e) {
			return false;
		}
	}

	/**
	 * Should the start warn about seams? Only in a world already played: if it was recorded, when the generation options
	 * changed; if not (a world from before this record), when it starts with a profile that changes generation.
	 */
	public static boolean warnSeams(Map<String, String> stored, Map<String, String> now, boolean worldStarted, boolean generationProfile) {
		if (!worldStarted) {
			return false;
		}
		return stored == null ? generationProfile : !changed(stored, now).isEmpty();
	}
}
