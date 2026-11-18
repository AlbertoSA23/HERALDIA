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
 * The work /heraldia update apply leaves for the next startup (T46), in
 * {@code <world>/heraldia/actualizar/plan.json}. Phases: {@link #PENDING} (just confirmed; at startup, before
 * loading the world, the affected files are copied if requested and the pristine chunks are deleted), {@link #REGENERATED} (with the
 * server running, the new structures are placed) and {@link #DONE} (the report remains). An undo plan
 * ({@link #UNDO}) restores the backup before loading the world. The JSON keys are the published Spanish ones ({@code SerializedName}).
 */
public final class Plan {
	public static final String PENDING = "pendiente", REGENERATED = "regenerado", DONE = "hecho", UNDO = "deshacer";
	private static final Gson GSON = new GsonBuilder().setPrettyPrinting().disableHtmlEscaping().create();

	/** A chunk to regenerate and its InhabitedTime at analysis time (if it has risen at startup, it is no longer deleted). */
	public record Chunk(int cx, int cz, @SerializedName("habitado") long inhabited) {
	}

	/** A new structure to place: its id, its start chunk and its box at analysis time {minX, minY, minZ, maxX, maxY, maxZ}. */
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
	// result
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

	/** The region files touched by the chunks to regenerate and the boxes of the structures to place. */
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
