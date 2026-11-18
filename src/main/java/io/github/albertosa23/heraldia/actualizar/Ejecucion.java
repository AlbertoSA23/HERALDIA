package io.github.albertosa23.heraldia.actualizar;

import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.comando.Textos;
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
public final class Ejecucion {
	private static final Logger LOGGER = LoggerFactory.getLogger(Heraldia.MOD_ID);
	static final List<String> CARPETAS = List.of("region", "entities", "poi");
	private static Plan enCurso;
	private static final Deque<Plan.Colocacion> COLA = new ArrayDeque<>();

	private Ejecucion() {
	}

	static Path plan(MinecraftServer server) {
		return Analisis.carpeta(server).resolve("plan.json");
	}

	static Path deshacer(MinecraftServer server) {
		return Analisis.carpeta(server).resolve("deshacer.json");
	}

	/** SERVER_STARTING: deshacer y la fase de ficheros del plan, con el mundo aún sin cargar. */
	static void alEmpezar(MinecraftServer server) {
		Path dir = Analisis.carpeta(server), ow = Analisis.overworld(server);
		boolean cargado = server.getAllLevels().iterator().hasNext();
		Optional<Plan> d = Plan.leer(deshacer(server));
		if (d.isPresent()) {
			if (cargado) {
				LOGGER.error("Heraldia: update undo: el mundo ya está cargado; no se restaura nada (vuelve a arrancar)");
			} else {
				restaurar(d.get(), dir, ow);
			}
		}
		Optional<Plan> op = Plan.leer(plan(server));
		if (op.isEmpty() || !Plan.PENDIENTE.equals(op.get().fase)) {
			return;
		}
		Plan p = op.get();
		if (cargado) {
			LOGGER.error("Heraldia: update apply: el mundo ya está cargado; no se borra nada");
			p.notas.add("world already loaded at start: nothing deleted / el mundo ya estaba cargado: no se borró nada");
			p.regenerar.clear();
		}
		try {
			if (p.copia) {
				Path copia = dir.resolve("copia-" + p.id);
				int n = copiar(p, ow, copia);
				p.carpetaCopia = copia.toString();
				LOGGER.info("Heraldia: update apply: copia de seguridad de {} ficheros en {}", n, copia);
			}
			borrar(p, ow);
			p.fase = Plan.REGENERADO;
			p.guardar(plan(server));
			LOGGER.info("Heraldia: update apply: {} chunks vírgenes borrados para regenerarse ({} se dejaron porque cambiaron)",
					p.regenerados, p.omitidos);
		} catch (IOException e) {
			LOGGER.error("Heraldia: update apply: falló la fase de ficheros; el plan queda pendiente", e);
		}
	}

	/** Copia los ficheros de las regiones del plan (región, entidades y PDI) a {@code destino}; devuelve cuántos. */
	static int copiar(Plan p, Path ow, Path destino) throws IOException {
		int n = 0;
		for (String carpeta : CARPETAS) {
			for (String nombre : p.regiones()) {
				Path f = ow.resolve(carpeta).resolve(nombre);
				if (Files.isRegularFile(f)) {
					Path d = destino.resolve(carpeta).resolve(nombre);
					Files.createDirectories(d.getParent());
					Files.copy(f, d, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.COPY_ATTRIBUTES);
					n++;
				}
			}
		}
		return n;
	}

	/** Borra los chunks del plan que siguen igual que al analizar (InhabitedTime sin subir). */
	static void borrar(Plan p, Path ow) throws IOException {
		Map<String, List<Integer>> porRegion = new LinkedHashMap<>();
		for (Plan.Chunk c : p.regenerar) {
			Path f = ow.resolve("region").resolve(Region.nombre(c.cx() >> 5, c.cz() >> 5));
			int idx = Region.indice(c.cx(), c.cz());
			Optional<CompoundTag> t = Files.isRegularFile(f) ? Region.leer(f, idx) : Optional.empty();
			if (t.isEmpty()) {
				continue;
			}
			long hab = t.get().getLongOr("InhabitedTime", 0);
			if (hab > c.habitado()) {
				p.omitidos++;
				continue;
			}
			porRegion.computeIfAbsent(Region.nombre(c.cx() >> 5, c.cz() >> 5), k -> new ArrayList<>()).add(idx);
		}
		for (Map.Entry<String, List<Integer>> e : porRegion.entrySet()) {
			p.regenerados += Region.borrar(ow.resolve("region").resolve(e.getKey()), e.getValue());
			Region.borrar(ow.resolve("entities").resolve(e.getKey()), e.getValue());
			Region.borrar(ow.resolve("poi").resolve(e.getKey()), e.getValue());
		}
	}

	/** Restaura una copia (deshacer): vuelve a poner sus ficheros en su sitio. */
	static void restaurar(Plan d, Path dir, Path ow) {
		Path copia = d.carpetaCopia == null ? null : Path.of(d.carpetaCopia);
		int n = 0;
		try {
			if (copia == null || !Files.isDirectory(copia)) {
				LOGGER.error("Heraldia: update undo: no está la copia {}", copia);
				return;
			}
			for (String carpeta : CARPETAS) {
				Path src = copia.resolve(carpeta);
				if (!Files.isDirectory(src)) {
					continue;
				}
				try (DirectoryStream<Path> ds = Files.newDirectoryStream(src, "r.*.mca")) {
					for (Path f : ds) {
						Path to = ow.resolve(carpeta).resolve(f.getFileName().toString());
						Files.createDirectories(to.getParent());
						Files.copy(f, to, StandardCopyOption.REPLACE_EXISTING);
						n++;
					}
				}
			}
			Files.move(dir.resolve("deshacer.json"), dir.resolve("deshecho-" + d.id + ".json"), StandardCopyOption.REPLACE_EXISTING);
			LOGGER.info("Heraldia: update undo: restaurados {} ficheros de la copia {}", n, copia);
		} catch (IOException e) {
			LOGGER.error("Heraldia: update undo: falló la restauración", e);
		}
	}

	/** SERVER_STARTED: pone en cola las estructuras del plan (una por tick) o, si no hay, cierra el plan. */
	static void alArrancar(MinecraftServer server) {
		Optional<Plan> op = Plan.leer(plan(server));
		if (op.isEmpty() || !Plan.REGENERADO.equals(op.get().fase)) {
			return;
		}
		enCurso = op.get();
		COLA.clear();
		COLA.addAll(enCurso.colocar);
		if (COLA.isEmpty()) {
			terminar(server);
		}
	}

	/** Cada tick, mientras haya cola: una estructura. */
	static void tick(MinecraftServer server) {
		if (enCurso == null) {
			return;
		}
		Plan.Colocacion c = COLA.poll();
		if (c != null) {
			try {
				if (colocar(server.overworld(), c)) {
					enCurso.colocadas++;
				} else {
					enCurso.colocacionesOmitidas++;
				}
			} catch (RuntimeException e) {
				enCurso.colocacionesOmitidas++;
				LOGGER.error("Heraldia: update apply: no se pudo colocar {} en {}, {}", c.estructura(), c.cx(), c.cz(), e);
			}
		}
		if (COLA.isEmpty()) {
			terminar(server);
		}
	}

	/**
	 * Coloca una estructura nueva en un chunk ya generado: la vuelve a calcular (si ya no sale igual, o ya hay una, no
	 * hace nada), la registra en su chunk de inicio y en los que toca, y pone sus piezas en los chunks ya generados (los
	 * que aún no lo están las pondrán al generarse).
	 */
	static boolean colocar(ServerLevel level, Plan.Colocacion c) {
		Identifier id = Identifier.tryParse(c.estructura());
		var reg = level.registryAccess().lookupOrThrow(Registries.STRUCTURE);
		Optional<Structure> st = id == null ? Optional.empty() : reg.getOptional(ResourceKey.create(Registries.STRUCTURE, id));
		if (st.isEmpty()) {
			return false;
		}
		ChunkPos pos = new ChunkPos(c.cx(), c.cz());
		ProtoChunk p = Analisis.generar(level, pos);
		StructureStart s = p.getStartForStructure(st.get());
		if (s == null || !s.isValid() || !Analisis.mismaPlanta(Analisis.caja(s), c.caja())) {
			LOGGER.info("Heraldia: update apply: {} ya no sale en {}, {}; no se coloca", c.estructura(), c.cx(), c.cz());
			return false;
		}
		ChunkAccess inicio = level.getChunk(c.cx(), c.cz());
		if (inicio.getStartForStructure(st.get()) != null) {
			return false;
		}
		inicio.setStartForStructure(st.get(), s);
		inicio.markUnsaved();
		BoundingBox bb = s.getBoundingBox();
		Path regiones = Analisis.overworld(level.getServer()).resolve("region");
		int x0 = SectionPos.blockToSectionCoord(bb.minX()), x1 = SectionPos.blockToSectionCoord(bb.maxX());
		int z0 = SectionPos.blockToSectionCoord(bb.minZ()), z1 = SectionPos.blockToSectionCoord(bb.maxZ());
		for (int cx = x0; cx <= x1; cx++) {
			for (int cz = z0; cz <= z1; cz++) {
				if (!generado(level, regiones, cx, cz)) {
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
		LOGGER.info("Heraldia: update apply: colocada {} en el chunk {}, {}", c.estructura(), c.cx(), c.cz());
		return true;
	}

	/** ¿Está el chunk generado? (cargado, o guardado en su región) */
	static boolean generado(ServerLevel level, Path regiones, int cx, int cz) {
		if (level.getChunkSource().getChunkNow(cx, cz) != null) {
			return true;
		}
		try {
			Path f = regiones.resolve(Region.nombre(cx >> 5, cz >> 5));
			return Files.isRegularFile(f) && Region.entrada(Region.cabecera(f), Region.indice(cx, cz)) != 0;
		} catch (IOException e) {
			return true;     // en la duda, como generado: se cargará
		}
	}

	private static void terminar(MinecraftServer server) {
		Plan p = enCurso;
		enCurso = null;
		if (p == null) {
			return;
		}
		p.fase = Plan.HECHO;
		Path dir = Analisis.carpeta(server);
		try {
			Path informe = dir.resolve("informe-" + p.id + ".txt");
			Files.writeString(informe, informe(p), StandardCharsets.UTF_8);
			p.guardar(dir.resolve("hecho-" + p.id + ".json"));
			Files.deleteIfExists(plan(server));
			LOGGER.info("Heraldia: update apply terminado: {} chunks regenerables, {} dejados, {} estructuras colocadas, {} omitidas; informe en {}",
					p.regenerados, p.omitidos, p.colocadas, p.colocacionesOmitidas, informe);
		} catch (IOException e) {
			LOGGER.error("Heraldia: update apply: no se pudo escribir el informe", e);
		}
		for (ServerPlayer op : server.getPlayerList().getPlayers()) {
			if (server.getPlayerList().isOp(op.nameAndId())) {
				op.sendSystemMessage(Textos.t(Textos.idioma(op), "heraldia.actualizar.terminado", p.regenerados, p.colocadas)
						.withStyle(ChatFormatting.GOLD));
			}
		}
	}

	static String informe(Plan p) {
		StringBuilder sb = new StringBuilder();
		sb.append("Heraldia /heraldia update apply — ").append(p.id).append(" (").append(p.fecha).append(")\n");
		sb.append("Backup / copia: ").append(p.copia ? p.carpetaCopia : "none / ninguna").append('\n');
		sb.append("Virgin chunks deleted to regenerate / chunks vírgenes borrados para regenerarse: ").append(p.regenerados).append('\n');
		sb.append("Kept because they changed since the analysis / dejados porque cambiaron: ").append(p.omitidos).append('\n');
		sb.append("New structures placed / estructuras nuevas colocadas: ").append(p.colocadas).append(" (skipped / omitidas: ")
				.append(p.colocacionesOmitidas).append(")\n");
		p.colocar.forEach(c -> sb.append("  ").append(c.estructura()).append(" @ chunk ").append(c.cx()).append(',').append(c.cz()).append('\n'));
		p.notas.forEach(n -> sb.append("Note / nota: ").append(n).append('\n'));
		if (p.copia) {
			sb.append("\nUndo / deshacer: /heraldia update undo (restores the backed-up region files; anything changed there since is lost / ")
					.append("restaura las regiones copiadas; se pierde lo cambiado en ellas desde entonces)\n");
		}
		return sb.toString();
	}

	/** El último plan hecho con copia (para deshacer), si hay. */
	static Optional<Plan> ultimoConCopia(MinecraftServer server) {
		Path dir = Analisis.carpeta(server);
		if (!Files.isDirectory(dir)) {
			return Optional.empty();
		}
		Plan mejor = null;
		try (DirectoryStream<Path> ds = Files.newDirectoryStream(dir, "hecho-*.json")) {
			for (Path f : ds) {
				Optional<Plan> p = Plan.leer(f);
				if (p.isPresent() && p.get().copia && p.get().carpetaCopia != null && (mejor == null || p.get().fecha.compareTo(mejor.fecha) > 0)) {
					mejor = p.get();
				}
			}
		} catch (IOException e) {
			return Optional.empty();
		}
		return Optional.ofNullable(mejor);
	}
}
