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
import net.minecraft.world.level.levelgen.structure.BoundingBox;
import net.minecraft.world.level.levelgen.structure.Structure;
import net.minecraft.world.level.levelgen.structure.StructureStart;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Lo que /heraldia update apply deja hecho al arrancar (T46). Con el servidor parado no se puede hacer nada, así que el
 * plan ({@link Plan}) espera al siguiente arranque, que el administrador hace a mano:
 * <ol>
 * <li>al empezar a arrancar, <em>antes de cargar el mundo</em> ({@code SERVER_STARTING}): si se pidió, copia los ficheros
 * de región, entidades y PDI afectados a {@code heraldia/actualizar/copia-<id>/}; luego borra de las regiones los chunks
 * vírgenes del plan que siguen igual (si su InhabitedTime ha subido, alguien ha pasado: se dejan), para que se
 * regeneren cuando alguien se acerque;</li>
 * <li>con el servidor en marcha ({@code SERVER_STARTED}): coloca las estructuras nuevas del plan, una por tick, si siguen
 * saliendo igual y no hay ya otra; las registra en su chunk de inicio (para /locate y los mapas) y en los que toca;</li>
 * <li>deja el informe en {@code heraldia/actualizar/informe-<id>.txt} y el plan como {@code hecho-<id>.json}.</li>
 * </ol>
 * Deshacer ({@code deshacer.json}) restaura la copia antes de cargar el mundo.
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

	/** SERVER_STARTING: deshacer y la fase de ficheros del plan, con el mundo aún sin cargar. */
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

	/** Copia los ficheros de las regiones del plan (región, entidades y PDI) a {@code destination}; devuelve cuántos. */
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
				}
			}
		}
		return n;
	}

	/** Borra los chunks del plan que siguen igual que al analizar (InhabitedTime sin subir). */
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

	/** Restaura una copia (deshacer): vuelve a poner sus ficheros en su sitio. */
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
			Files.move(dir.resolve("deshacer.json"), dir.resolve("deshecho-" + d.id + ".json"), StandardCopyOption.REPLACE_EXISTING);
			LOGGER.info("Heraldia: update undo: restaurados {} ficheros de la copia {}", n, backup);
		} catch (IOException e) {
			LOGGER.error("Heraldia: update undo: falló la restauración", e);
		}
	}

	/** SERVER_STARTED: pone en cola las estructuras del plan (una por tick) o, si no hay, cierra el plan. */
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

	/** Cada tick, mientras haya cola: una estructura. */
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
	 * Coloca una estructura nueva en un chunk ya generado: la vuelve a calcular (si ya no sale igual, o ya hay una, no
	 * hace nada), la registra en su chunk de inicio y en los que toca, y pone sus piezas en los chunks ya generados (los
	 * que aún no lo están las pondrán al generarse).
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
					continue;           // al generarse, sus referencias lo encuentran y pone las piezas
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

	/** ¿Está el chunk generado? (cargado, o guardado en su región) */
	static boolean generated(ServerLevel level, Path regions, int cx, int cz) {
		if (level.getChunkSource().getChunkNow(cx, cz) != null) {
			return true;
		}
		try {
			Path f = regions.resolve(Region.name(cx >> 5, cz >> 5));
			return Files.isRegularFile(f) && Region.entry(Region.header(f), Region.index(cx, cz)) != 0;
		} catch (IOException e) {
			return true;     // en la duda, como generado: se cargará
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

	/** El último plan hecho con copia (para deshacer), si hay. */
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
