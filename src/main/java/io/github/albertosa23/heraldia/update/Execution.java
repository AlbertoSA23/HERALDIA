package io.github.albertosa23.heraldia.update;

import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.command.Texts;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.DirectoryStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import net.minecraft.ChatFormatting;
import net.minecraft.core.SectionPos;
import net.minecraft.core.registries.Registries;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.resources.Identifier;
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.chunk.ChunkAccess;
import net.minecraft.world.level.chunk.ProtoChunk;
import net.minecraft.world.level.chunk.status.ChunkStatus;
import net.minecraft.world.level.levelgen.structure.BoundingBox;
import net.minecraft.world.level.levelgen.structure.Structure;
import net.minecraft.world.level.levelgen.structure.StructureStart;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * What /heraldia update apply gets done at startup (T46). With the server stopped nothing can be done, so the
 * plan ({@link Plan}) waits for the next startup, which the administrator does by hand:
 * <ol>
 * <li>when startup begins, <em>before loading the world</em> ({@code SERVER_STARTING}): if requested, copies the affected
 * region, entity and POI files to {@code heraldia/actualizar/copia-<id>/}; then deletes from the regions the plan's
 * pristine chunks that are unchanged (if their InhabitedTime has risen, someone has passed: they are left), so they
 * regenerate when someone comes near;</li>
 * <li>with the server running ({@code SERVER_STARTED}): places the plan's new structures, one per tick, if they still
 * spawn the same and there is not already another one; registers them in their start chunk (for /locate and the maps) and in those they touch;</li>
 * <li>leaves the report in {@code heraldia/actualizar/informe-<id>.txt} and the plan as {@code hecho-<id>.json}.</li>
 * </ol>
 * Undo ({@code deshacer.json}) restores the backup before loading the world.
 */
public final class Execution {
	private static final Logger LOGGER = LoggerFactory.getLogger(Heraldia.MOD_ID);
	static final List<String> FOLDERS = List.of("region", "entities", "poi");
	private static Plan inProgress;
	private static final Deque<Plan.Placement> QUEUE = new ArrayDeque<>();

	private Execution() {
	}

	static Path plan(MinecraftServer server) {
		return Analysis.folder(server).resolve("plan.json");
	}

	static Path undo(MinecraftServer server) {
		return Analysis.folder(server).resolve("deshacer.json");
	}

	/** SERVER_STARTING: undo and the plan's file phase, with the world not loaded yet. */
	static void onBegin(MinecraftServer server) {
		Path dir = Analysis.folder(server), ow = Analysis.overworld(server);
		boolean loaded = server.getAllLevels().iterator().hasNext();
		Optional<Plan> d = Plan.read(undo(server));
		if (d.isPresent()) {
			if (loaded) {
				LOGGER.error("Heraldia: update undo: el mundo ya está cargado; no se restaura nada (vuelve a arrancar)");
			} else {
				restore(d.get(), dir, ow);
			}
		}
		Optional<Plan> op = Plan.read(plan(server));
		if (op.isEmpty() || !Plan.PENDING.equals(op.get().phase)) {
			return;
		}
		Plan p = op.get();
		if (loaded) {
			LOGGER.error("Heraldia: update apply: el mundo ya está cargado; no se borra nada");
			p.notes.add("world already loaded at start: nothing deleted / el mundo ya estaba cargado: no se borró nada");
			p.regenerate.clear();
		}
		try {
			if (p.backup) {
				Path backup = dir.resolve("copia-" + p.id);
				int n = copy(p, ow, backup);
				p.backupFolder = backup.toString();
				LOGGER.info("Heraldia: update apply: copia de seguridad de {} ficheros en {}", n, backup);
			}
			delete(p, ow);
			p.phase = Plan.REGENERATED;
			p.save(plan(server));
			LOGGER.info("Heraldia: update apply: {} chunks vírgenes borrados para regenerarse ({} se dejaron porque cambiaron)",
					p.regenerated, p.skipped);
		} catch (IOException e) {
			LOGGER.error("Heraldia: update apply: falló la fase de ficheros; el plan queda pendiente", e);
		}
	}

	/**
	 * Copies the files of the plan's regions (region, entities and POI) to {@code destination}; returns how many. Those that
	 * do not exist yet go to {@link Plan#absent}: undo deletes them (apply can create them, e.g. the POI file of a region
	 * where a placed structure brings beds or workstations).
	 */
	static int copy(Plan p, Path ow, Path destination) throws IOException {
		int n = 0;
		for (String folder : FOLDERS) {
			for (String name : p.regions()) {
				Path f = ow.resolve(folder).resolve(name);
				if (Files.isRegularFile(f)) {
					Path d = destination.resolve(folder).resolve(name);
					Files.createDirectories(d.getParent());
					Files.copy(f, d, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.COPY_ATTRIBUTES);
					n++;
				} else {
					// it does not exist yet: placing a structure can create it (its POIs or mobs); undo deletes it
					p.absent.add(folder + "/" + name);
				}
			}
		}
		return n;
	}

	/** Deletes the plan's chunks that are the same as at analysis time (InhabitedTime has not risen). */
	static void delete(Plan p, Path ow) throws IOException {
		Map<String, List<Integer>> byRegion = new LinkedHashMap<>();
		for (Plan.Chunk c : p.regenerate) {
			Path f = ow.resolve("region").resolve(Region.name(c.cx() >> 5, c.cz() >> 5));
			int idx = Region.index(c.cx(), c.cz());
			Optional<CompoundTag> t = Files.isRegularFile(f) ? Region.read(f, idx) : Optional.empty();
			if (t.isEmpty()) {
				continue;
			}
			long inhabited = t.get().getLongOr("InhabitedTime", 0);
			if (inhabited > c.inhabited()) {
				p.skipped++;
				continue;
			}
			byRegion.computeIfAbsent(Region.name(c.cx() >> 5, c.cz() >> 5), k -> new ArrayList<>()).add(idx);
		}
		for (Map.Entry<String, List<Integer>> e : byRegion.entrySet()) {
			p.regenerated += Region.delete(ow.resolve("region").resolve(e.getKey()), e.getValue());
			Region.delete(ow.resolve("entities").resolve(e.getKey()), e.getValue());
			Region.delete(ow.resolve("poi").resolve(e.getKey()), e.getValue());
		}
	}

	/** Restores a backup (undo): puts its files back in place. */
	static void restore(Plan d, Path dir, Path ow) {
		Path backup = d.backupFolder == null ? null : Path.of(d.backupFolder);
		int n = 0;
		try {
			if (backup == null || !Files.isDirectory(backup)) {
				LOGGER.error("Heraldia: update undo: no está la copia {}", backup);
				return;
			}
			for (String folder : FOLDERS) {
				Path src = backup.resolve(folder);
				if (!Files.isDirectory(src)) {
					continue;
				}
				try (DirectoryStream<Path> ds = Files.newDirectoryStream(src, "r.*.mca")) {
					for (Path f : ds) {
						Path to = ow.resolve(folder).resolve(f.getFileName().toString());
						Files.createDirectories(to.getParent());
						Files.copy(f, to, StandardCopyOption.REPLACE_EXISTING);
						n++;
					}
				}
			}
			int deleted = 0;
			for (String rel : d.absent) {
				int slash = rel.indexOf('/');
				String folder = slash > 0 ? rel.substring(0, slash) : "", name = rel.substring(slash + 1);
				if (FOLDERS.contains(folder) && name.matches("r\\.-?\\d+\\.-?\\d+\\.mca") && Files.deleteIfExists(ow.resolve(folder).resolve(name))) {
					deleted++;
				}
			}
			if (deleted > 0) {
				LOGGER.info("Heraldia: update undo: borrados {} ficheros que no existían antes de apply", deleted);
			}
			Files.move(dir.resolve("deshacer.json"), dir.resolve("deshecho-" + d.id + ".json"), StandardCopyOption.REPLACE_EXISTING);
			LOGGER.info("Heraldia: update undo: restaurados {} ficheros de la copia {}", n, backup);
		} catch (IOException e) {
			LOGGER.error("Heraldia: update undo: falló la restauración", e);
		}
	}

	/** SERVER_STARTED: queues the plan's structures (one per tick) or, if there are none, closes the plan. */
	static void onStart(MinecraftServer server) {
		Optional<Plan> op = Plan.read(plan(server));
		if (op.isEmpty() || !Plan.REGENERATED.equals(op.get().phase)) {
			return;
		}
		inProgress = op.get();
		QUEUE.clear();
		QUEUE.addAll(inProgress.place);
		if (QUEUE.isEmpty()) {
			finish(server);
		}
	}

	/** Every tick, while there is a queue: one structure. */
	static void tick(MinecraftServer server) {
		if (inProgress == null) {
			return;
		}
		Plan.Placement c = QUEUE.poll();
		if (c != null) {
			try {
				if (place(server.overworld(), c)) {
					inProgress.placed++;
				} else {
					inProgress.skippedPlacements++;
				}
			} catch (RuntimeException e) {
				inProgress.skippedPlacements++;
				LOGGER.error("Heraldia: update apply: no se pudo colocar {} en {}, {}", c.structure(), c.cx(), c.cz(), e);
			}
		}
		if (QUEUE.isEmpty()) {
			finish(server);
		}
	}

	/**
	 * Places a new structure in an already generated chunk: computes it again (if it no longer spawns the same, or there already is one, it
	 * does nothing), registers it in its start chunk and in those it touches, and puts its pieces in the already generated chunks (those
	 * not generated yet will put them when they generate).
	 */
	static boolean place(ServerLevel level, Plan.Placement c) {
		Identifier id = Identifier.tryParse(c.structure());
		var reg = level.registryAccess().lookupOrThrow(Registries.STRUCTURE);
		Optional<Structure> st = id == null ? Optional.empty() : reg.getOptional(ResourceKey.create(Registries.STRUCTURE, id));
		if (st.isEmpty()) {
			return false;
		}
		ChunkPos pos = new ChunkPos(c.cx(), c.cz());
		ProtoChunk p = Analysis.generate(level, pos);
		StructureStart s = p.getStartForStructure(st.get());
		if (s == null || !s.isValid() || !Analysis.sameFootprint(Analysis.box(s), c.box())) {
			LOGGER.info("Heraldia: update apply: {} ya no sale en {}, {}; no se coloca", c.structure(), c.cx(), c.cz());
			return false;
		}
		ChunkAccess start = level.getChunk(c.cx(), c.cz());
		if (start.getStartForStructure(st.get()) != null) {
			return false;
		}
		start.setStartForStructure(st.get(), s);
		start.markUnsaved();
		BoundingBox bb = s.getBoundingBox();
		Path regions = Analysis.overworld(level.getServer()).resolve("region");
		int x0 = SectionPos.blockToSectionCoord(bb.minX()), x1 = SectionPos.blockToSectionCoord(bb.maxX());
		int z0 = SectionPos.blockToSectionCoord(bb.minZ()), z1 = SectionPos.blockToSectionCoord(bb.maxZ());
		for (int cx = x0; cx <= x1; cx++) {
			for (int cz = z0; cz <= z1; cz++) {
				if (!generated(level, regions, cx, cz)) {
					if (!pastReferences(level, cx, cz)) {
						continue;       // when it generates, its references find it and it places the pieces
					}
					// Loading the start chunk above can generate a neighbour that was deleted to regenerate (path A) as far as
					// the light steps, before the start was set: its references step has already run without it, so it would
					// never get its pieces. It is taken as generated (update_path_b.py: the box's last row, chunk 253, -247).
					LOGGER.info("Heraldia: update apply: chunk {}, {} of {} already past its references step; its reference is added",
							cx, cz, c.structure());
				}
				ChunkAccess ch = level.getChunk(cx, cz);
				ch.addReferenceForStructure(st.get(), pos.pack());
				ch.markUnsaved();
				ChunkPos cp = new ChunkPos(cx, cz);
				s.placeInChunk(level, level.structureManager(), level.getChunkSource().getGenerator(), level.getRandom(),
						new BoundingBox(cp.getMinBlockX(), level.getMinY(), cp.getMinBlockZ(), cp.getMaxBlockX(), level.getMaxY(), cp.getMaxBlockZ()), cp);
			}
		}
		LOGGER.info("Heraldia: update apply: colocada {} en el chunk {}, {}", c.structure(), c.cx(), c.cz());
		return true;
	}

	/** Is the chunk in memory, at whatever generation step, already past the one that records structure references? */
	static boolean pastReferences(ServerLevel level, int cx, int cz) {
		ChunkAccess ch = level.getChunkSource().getChunk(cx, cz, ChunkStatus.EMPTY, false);
		return ch != null && ch.getPersistedStatus().isOrAfter(ChunkStatus.STRUCTURE_REFERENCES);
	}

	/** Is the chunk generated? (loaded, or saved in its region) */
	static boolean generated(ServerLevel level, Path regions, int cx, int cz) {
		if (level.getChunkSource().getChunkNow(cx, cz) != null) {
			return true;
		}
		try {
			Path f = regions.resolve(Region.name(cx >> 5, cz >> 5));
			return Files.isRegularFile(f) && Region.entry(Region.header(f), Region.index(cx, cz)) != 0;
		} catch (IOException e) {
			return true;     // when in doubt, as generated: it will load
		}
	}

	private static void finish(MinecraftServer server) {
		Plan p = inProgress;
		inProgress = null;
		if (p == null) {
			return;
		}
		p.phase = Plan.DONE;
		Path dir = Analysis.folder(server);
		try {
			Path report = dir.resolve("informe-" + p.id + ".txt");
			Files.writeString(report, report(p), StandardCharsets.UTF_8);
			p.save(dir.resolve("hecho-" + p.id + ".json"));
			Files.deleteIfExists(plan(server));
			LOGGER.info("Heraldia: update apply terminado: {} chunks regenerables, {} dejados, {} estructuras colocadas, {} omitidas; informe en {}",
					p.regenerated, p.skipped, p.placed, p.skippedPlacements, report);
		} catch (IOException e) {
			LOGGER.error("Heraldia: update apply: no se pudo escribir el informe", e);
		}
		for (ServerPlayer op : server.getPlayerList().getPlayers()) {
			if (server.getPlayerList().isOp(op.nameAndId())) {
				op.sendSystemMessage(Texts.t(Texts.language(op), "heraldia.actualizar.terminado", p.regenerated, p.placed)
						.withStyle(ChatFormatting.GOLD));
			}
		}
	}

	static String report(Plan p) {
		StringBuilder sb = new StringBuilder();
		sb.append("Heraldia /heraldia update apply — ").append(p.id).append(" (").append(p.date).append(")\n");
		sb.append("Backup / copia: ").append(p.backup ? p.backupFolder : "none / ninguna").append('\n');
		sb.append("Virgin chunks deleted to regenerate / chunks vírgenes borrados para regenerarse: ").append(p.regenerated).append('\n');
		sb.append("Kept because they changed since the analysis / dejados porque cambiaron: ").append(p.skipped).append('\n');
		sb.append("New structures placed / estructuras nuevas colocadas: ").append(p.placed).append(" (skipped / omitidas: ")
				.append(p.skippedPlacements).append(")\n");
		p.place.forEach(c -> sb.append("  ").append(c.structure()).append(" @ chunk ").append(c.cx()).append(',').append(c.cz()).append('\n'));
		p.notes.forEach(n -> sb.append("Note / nota: ").append(n).append('\n'));
		if (p.backup) {
			sb.append("\nUndo / deshacer: /heraldia update undo (restores the backed-up region files; anything changed there since is lost / ")
					.append("restaura las regiones copiadas; se pierde lo cambiado en ellas desde entonces)\n");
		}
		return sb.toString();
	}

	/** The last plan done with a backup (for undo), if any. */
	static Optional<Plan> lastWithBackup(MinecraftServer server) {
		Path dir = Analysis.folder(server);
		if (!Files.isDirectory(dir)) {
			return Optional.empty();
		}
		Plan best = null;
		try (DirectoryStream<Path> ds = Files.newDirectoryStream(dir, "hecho-*.json")) {
			for (Path f : ds) {
				Optional<Plan> p = Plan.read(f);
				if (p.isPresent() && p.get().backup && p.get().backupFolder != null && (best == null || p.get().date.compareTo(best.date) > 0)) {
					best = p.get();
				}
			}
		} catch (IOException e) {
			return Optional.empty();
		}
		return Optional.ofNullable(best);
	}
}
