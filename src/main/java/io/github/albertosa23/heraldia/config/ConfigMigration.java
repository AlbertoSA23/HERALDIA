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
 * Migraciones del fichero de configuración entre versiones de su formato (T46, generaliza la 1 → 2 de los perfiles).
 * Cada paso pasa de la versión {@code n} a la {@code n + 1} y recibe la raíz del JSON y la versión con que llegó el
 * fichero (la 0 es un fichero escrito a mano, sin campo de versión). Antes de reescribir un fichero de una versión
 * anterior se guarda una copia, {@code heraldia.json.v<versión>.bak} (si ya existe, con un número detrás), para poder
 * volver atrás a mano. Lógica pura salvo {@link #copy}.
 * <p>Para cambiar el formato del fichero: sube {@code options.VERSION} en el generador y añade aquí el paso
 * {@code VERSION - 1 → VERSION} (con su test en {@code ConfigMigrationTest}).
 */
public final class ConfigMigration {
	private final Map<Integer, BiConsumer<JsonObject, Integer>> steps;

	/** @param pasos versión de origen de cada paso → cambio (raíz, versión con que llegó el fichero) */
	public ConfigMigration(Map<Integer, BiConsumer<JsonObject, Integer>> steps) {
		this.steps = new TreeMap<>(steps);
	}

	/** Resultado: la versión final y los pasos que no existían (se avisa en el log). */
	public record Result(int from, int until, List<Integer> noStep) {
		public boolean migrated() {
			return from < until;
		}
	}

	/** Lleva {@code root} de la versión {@code from} a la {@code until} y le pone el campo de versión. */
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

	/** Nombre de la copia de un fichero de la versión {@code version}, sin pisar otra que ya exista. */
	static Path backupTarget(Path file, int version) {
		Path p = file.resolveSibling(file.getFileName() + ".v" + version + ".bak");
		for (int i = 2; Files.exists(p); i++) {
			p = file.resolveSibling(file.getFileName() + ".v" + version + "." + i + ".bak");
		}
		return p;
	}

	/** Copia el fichero tal cual estaba antes de migrarlo; devuelve dónde quedó. */
	public static Path copy(Path file, int version) throws IOException {
		Path p = backupTarget(file, version);
		Files.copy(file, p, StandardCopyOption.COPY_ATTRIBUTES);
		return p;
	}
}
