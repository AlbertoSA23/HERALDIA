package io.github.albertosa23.heraldia.update;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.annotations.SerializedName;
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
 * {@code <world>/heraldia/update/plan.json}. Fases: {@link #PENDING} (se acaba de confirmar; al arrancar, antes
 * de cargar el mundo, se copia lo afectado si se pidió y se borran los chunks vírgenes), {@link #REGENERATED} (con el
 * servidor en marcha, se colocan las estructuras nuevas) y {@link #DONE} (queda el informe). Un plan de deshacer
 * ({@link #UNDO}) restaura la copia antes de cargar el mundo.
 */
public final class Plan {
	public static final String PENDING = "pendiente", REGENERATED = "regenerado", DONE = "hecho", UNDO = "deshacer";
	private static final Gson GSON = new GsonBuilder().setPrettyPrinting().disableHtmlEscaping().create();

	/** Un chunk a regenerar y su InhabitedTime al analizar (si ha subido al arrancar, ya no se borra). */
	public record Chunk(int cx, int cz, @SerializedName("habitado") long inhabited) {
	}

	/** Una estructura nueva que colocar: su id, su chunk de inicio y su caja al analizar {minX, minY, minZ, maxX, maxY, maxZ}. */
	public record Placement(@SerializedName("estructura") String structure, int cx, int cz, @SerializedName("caja") int[] box) {
	}

	public String id;
	@SerializedName("fecha")
	public String date;
	@SerializedName("fase")
	public String phase = PENDING;
	@SerializedName("copia")
	public boolean backup;
	@SerializedName("margen")
	public int margin;
	@SerializedName("regenerar")
	public List<Chunk> regenerate = new ArrayList<>();
	@SerializedName("colocar")
	public List<Placement> place = new ArrayList<>();
	// resultado
	@SerializedName("regenerados")
	public int regenerated;
	@SerializedName("omitidos")
	public int skipped;
	@SerializedName("colocadas")
	public int placed;
	@SerializedName("colocacionesOmitidas")
	public int skippedPlacements;
	@SerializedName("carpetaCopia")
	public String backupFolder;
	@SerializedName("notas")
	public List<String> notes = new ArrayList<>();

	/** Los ficheros de región que tocan los chunks a regenerar y las cajas de las estructuras a colocar. */
	public TreeSet<String> regions() {
		TreeSet<String> out = new TreeSet<>();
		regenerate.forEach(c -> out.add(Region.name(c.cx() >> 5, c.cz() >> 5)));
		for (Placement c : place) {
			for (int rx = Math.floorDiv(c.box()[0], 512); rx <= Math.floorDiv(c.box()[3], 512); rx++) {
				for (int rz = Math.floorDiv(c.box()[2], 512); rz <= Math.floorDiv(c.box()[5], 512); rz++) {
					out.add(Region.name(rx, rz));
				}
			}
		}
		return out;
	}

	public static Optional<Plan> read(Path file) {
		if (!Files.isRegularFile(file)) {
			return Optional.empty();
		}
		try {
			return Optional.ofNullable(GSON.fromJson(Files.readString(file, StandardCharsets.UTF_8), Plan.class));
		} catch (IOException | RuntimeException e) {
			return Optional.empty();
		}
	}

	public void save(Path file) throws IOException {
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
