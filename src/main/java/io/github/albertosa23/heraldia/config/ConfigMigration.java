package io.github.albertosa23.heraldia.config;

import com.google.gson.JsonObject;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.function.BiConsumer;

/**
 * Migrations of the configuration file between versions of its format (T46, generalizes the profiles' 1 → 2).
 * Each step goes from version {@code n} to {@code n + 1} and receives the JSON root and the version the file came
 * with (0 is a hand-written file, without a version field). Before rewriting a file from an earlier
 * version a copy is kept, {@code heraldia.json.v<version>.bak} (if it already exists, with a number after it), so one can
 * go back by hand. Pure logic except {@link #copy}.
 * <p>To change the file format: bump {@code opciones.VERSION} in the generator and add the step
 * {@code VERSION - 1 → VERSION} here (with its test in {@code ConfigMigrationTest}).
 */
public final class ConfigMigration {
	private final Map<Integer, BiConsumer<JsonObject, Integer>> steps;

	/** @param steps source version of each step → change (root, version the file came with) */
	public ConfigMigration(Map<Integer, BiConsumer<JsonObject, Integer>> steps) {
		this.steps = new TreeMap<>(steps);
	}

	/** Result: the final version and the steps that did not exist (logged as a warning). */
	public record Result(int from, int until, List<Integer> noStep) {
		public boolean migrated() {
			return from < until;
		}
	}

	/** Takes {@code root} from version {@code from} to {@code until} and sets the version field. */
	public Result migrate(JsonObject root, int from, int until) {
		List<Integer> noStep = new ArrayList<>();
		for (int v = from; v < until; v++) {
			BiConsumer<JsonObject, Integer> step = steps.get(v);
			if (step == null) {
				noStep.add(v);
			} else {
				step.accept(root, from);
			}
		}
		if (from < until) {
			root.addProperty("version", until);
		}
		return new Result(from, until, List.copyOf(noStep));
	}

	/** Name of the backup of a file of version {@code version}, without overwriting an existing one. */
	static Path backupTarget(Path file, int version) {
		Path p = file.resolveSibling(file.getFileName() + ".v" + version + ".bak");
		for (int i = 2; Files.exists(p); i++) {
			p = file.resolveSibling(file.getFileName() + ".v" + version + "." + i + ".bak");
		}
		return p;
	}

	/** Copies the file as it was before migrating it; returns where it ended up. */
	public static Path copy(Path file, int version) throws IOException {
		Path p = backupTarget(file, version);
		Files.copy(file, p, StandardCopyOption.COPY_ATTRIBUTES);
		return p;
	}
}
