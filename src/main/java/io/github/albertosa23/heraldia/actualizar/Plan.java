package io.github.albertosa23.heraldia.actualizar;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.AtomicMoveNotSupportedException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.TreeSet;

/**
 * El trabajo que /heraldia update apply deja para el siguiente arranque (T46), en
 * {@code <mundo>/heraldia/actualizar/plan.json}. Fases: {@link #PENDIENTE} (se acaba de confirmar; al arrancar, antes
 * de cargar el mundo, se copia lo afectado si se pidió y se borran los chunks vírgenes), {@link #REGENERADO} (con el
 * servidor en marcha, se colocan las estructuras nuevas) y {@link #HECHO} (queda el informe). Un plan de deshacer
 * ({@link #DESHACER}) restaura la copia antes de cargar el mundo.
 */
public final class Plan {
	public static final String PENDIENTE = "pendiente", REGENERADO = "regenerado", HECHO = "hecho", DESHACER = "deshacer";
	private static final Gson GSON = new GsonBuilder().setPrettyPrinting().disableHtmlEscaping().create();

	/** Un chunk a regenerar y su InhabitedTime al analizar (si ha subido al arrancar, ya no se borra). */
	public record Chunk(int cx, int cz, long habitado) {
	}

	/** Una estructura nueva que colocar: su id, su chunk de inicio y su caja al analizar {minX, minY, minZ, maxX, maxY, maxZ}. */
	public record Colocacion(String estructura, int cx, int cz, int[] caja) {
	}

	public String id;
	public String fecha;
	public String fase = PENDIENTE;
	public boolean copia;
	public int margen;
	public List<Chunk> regenerar = new ArrayList<>();
	public List<Colocacion> colocar = new ArrayList<>();
	// resultado
	public int regenerados, omitidos, colocadas, colocacionesOmitidas;
	public String carpetaCopia;
	public List<String> notas = new ArrayList<>();

	/** Los ficheros de región que tocan los chunks a regenerar y las cajas de las estructuras a colocar. */
	public TreeSet<String> regiones() {
		TreeSet<String> out = new TreeSet<>();
		regenerar.forEach(c -> out.add(Region.nombre(c.cx() >> 5, c.cz() >> 5)));
		for (Colocacion c : colocar) {
			for (int rx = Math.floorDiv(c.caja()[0], 512); rx <= Math.floorDiv(c.caja()[3], 512); rx++) {
				for (int rz = Math.floorDiv(c.caja()[2], 512); rz <= Math.floorDiv(c.caja()[5], 512); rz++) {
					out.add(Region.nombre(rx, rz));
				}
			}
		}
		return out;
	}

	public static Optional<Plan> leer(Path file) {
		if (!Files.isRegularFile(file)) {
			return Optional.empty();
		}
		try {
			return Optional.ofNullable(GSON.fromJson(Files.readString(file, StandardCharsets.UTF_8), Plan.class));
		} catch (IOException | RuntimeException e) {
			return Optional.empty();
		}
	}

	public void guardar(Path file) throws IOException {
		Files.createDirectories(file.toAbsolutePath().getParent());
		Path tmp = file.resolveSibling(file.getFileName() + ".tmp");
		Files.writeString(tmp, GSON.toJson(this) + "\n", StandardCharsets.UTF_8);
		try {
			Files.move(tmp, file, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
		} catch (AtomicMoveNotSupportedException e) {
			Files.move(tmp, file, StandardCopyOption.REPLACE_EXISTING);
		}
	}
}
