package io.github.albertosa23.heraldia.update;

import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.update.Detector.Build;
import io.github.albertosa23.heraldia.update.Detector.Reason;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.DirectoryStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.concurrent.CompletableFuture;
import java.util.function.Consumer;
import javax.imageio.ImageIO;
import net.fabricmc.loader.api.FabricLoader;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Holder;
import net.minecraft.core.registries.Registries;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.NbtAccounter;
import net.minecraft.nbt.NbtIo;
import net.minecraft.resources.Identifier;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.chunk.ChunkGenerator;
import net.minecraft.world.level.chunk.ProtoChunk;
import net.minecraft.world.level.chunk.UpgradeData;
import net.minecraft.world.level.dimension.DimensionType;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.level.levelgen.RandomState;
import net.minecraft.world.level.levelgen.structure.BoundingBox;
import net.minecraft.world.level.levelgen.structure.Structure;
import net.minecraft.world.level.levelgen.structure.StructurePiece;
import net.minecraft.world.level.levelgen.structure.StructureSet;
import net.minecraft.world.level.levelgen.structure.StructureStart;
import net.minecraft.world.level.storage.LevelResource;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * El análisis de /heraldia update analyze y apply (T46), en el mundo principal. En el hilo del servidor solo se guarda
 * el mundo y se apuntan el spawn y los jugadores conectados; lo demás va en un hilo propio, sin tocar el mundo cargado:
 * <ol>
 * <li>lee cada chunk guardado de las regiones ({@link Region}, {@link ChunkSummary});</li>
 * <li>compara la cima de unas columnas de los chunks por donde ha pasado algún jugador con la de la regeneración con la
 * misma semilla ({@code getBaseHeight} del generador, que es puro), sin contar las cimas naturales;</li>
 * <li>lee las camas, puntos de reaparición y últimas posiciones de los jugadores que no están conectados;</li>
 * <li>clasifica ({@link Detector}) con el margen de actualizar.margen_bloques;</li>
 * <li>en los chunks vírgenes y en los normales que alguna rejilla tiene por candidatos, calcula qué inicios de estructura
 * saldrían hoy en un chunk vacío con el generador del mundo ({@code createStructures} sobre un {@link ProtoChunk}: con
 * las mismas reglas que la generación) y los compara con los guardados: de ahí salen qué chunks vírgenes se pueden borrar
 * sin cortar estructuras (vía A) y qué estructuras nuevas de Heraldia caben en sitios seguros (vía B);</li>
 * <li>escribe el informe, el mapa en texto y en imagen en {@code <world>/heraldia/actualizar/}.</li>
 * </ol>
 * No cambia nada del mundo.
 */
public final class Analysis {
	private static final Logger LOGGER = LoggerFactory.getLogger(Heraldia.MOD_ID);
	/** Diferencia de altura (bloques) con la regeneración a partir de la cual una columna cuenta como distinta. */
	static final int TOLERANCE = 4;
	/** Mods de protección conocidos: si hay alguno, sus reclamaciones no se pueden leer y apply no se ejecuta. */
	static final List<String> PROTECTION = List.of("flan", "goml", "ftbchunks", "openpartiesandclaims", "cadmus", "fabricclaims",
			"claimpoints", "griefdefender");
	private static final DateTimeFormatter DATE = DateTimeFormatter.ofPattern("yyyyMMdd-HHmmss", Locale.ROOT);

	/** Lo que sale del análisis. */
	public record Report(String id, String date, int chunks, Detector.Result result, Set<Long> regenerate,
						  List<Plan.Placement> place, int cutPristine, int unsafePlacements, List<String> protections,
						  int margin, String textMap, Path folder, Path file, Path mapTxt, Path mapPng, Map<Long, Long> inhabited) {
		/** El plan que dejaría apply. */
		public Plan plan(boolean backup) {
			Plan p = new Plan();
			p.id = id;
			p.date = date;
			p.backup = backup;
			p.margin = margin;
			regenerate.stream().sorted().forEach(k -> p.regenerate.add(new Plan.Chunk(ChunkSummary.cx(k), ChunkSummary.cz(k),
					inhabited.getOrDefault(k, 0L))));
			p.place.addAll(place);
			return p;
		}
	}

	/** Lo apuntado en el hilo del servidor antes de empezar. */
	record Start(Path world, Path overworld, int minY, List<Build> extra, ServerLevel level) {
	}

	private Analysis() {
	}

	/** La carpeta de /heraldia update dentro del mundo. */
	public static Path folder(MinecraftServer server) {
		return server.getWorldPath(LevelResource.ROOT).resolve("heraldia").resolve("actualizar");
	}

	/** La carpeta del mundo principal (con region/, entities/ y poi/). */
	public static Path overworld(MinecraftServer server) {
		return DimensionType.getStorageFolder(Level.OVERWORLD, server.getWorldPath(LevelResource.ROOT));
	}

	/** Mods de protección cargados (con reclamaciones que no se pueden leer). */
	public static List<String> protections() {
		return PROTECTION.stream().filter(FabricLoader.getInstance()::isModLoaded).toList();
	}

	/**
	 * Empieza el análisis: en el hilo del servidor guarda el mundo y apunta el spawn y los jugadores; el resto, en un hilo
	 * propio. {@code progress} recibe mensajes de avance (desde ese hilo).
	 */
	public static CompletableFuture<Report> start(MinecraftServer server, Consumer<String> progress) {
		server.saveEverything(true, true, true);
		ServerLevel ow = server.overworld();
		List<Build> extra = new ArrayList<>();
		BlockPos spawn = ow.getRespawnData().pos();
		extra.add(Build.point(spawn.getX(), spawn.getZ(), Reason.SPAWN));
		for (ServerPlayer p : server.getPlayerList().getPlayers()) {
			if (p.level() == ow) {
				extra.add(Build.point(p.getBlockX(), p.getBlockZ(), Reason.PLAYER));
			}
			ServerPlayer.RespawnConfig rc = p.getRespawnConfig();
			if (rc != null && rc.respawnData().dimension() == Level.OVERWORLD) {
				BlockPos r = rc.respawnData().pos();
				extra.add(Build.point(r.getX(), r.getZ(), Reason.RESPAWN));
			}
		}
		Start ini = new Start(server.getWorldPath(LevelResource.ROOT), overworld(server), ow.getMinY(), extra, ow);
		int margin = HeraldiaConfig.get().has("actualizar.margen_bloques") ? HeraldiaConfig.get().getInt("actualizar.margen_bloques") : 50;
		List<String> prot = protections();
		Path dir = folder(server);
		CompletableFuture<Report> f = new CompletableFuture<>();
		Thread t = new Thread(() -> {
			try {
				f.complete(analyze(ini, margin, prot, dir, progress));
			} catch (Throwable e) {
				LOGGER.error("Heraldia: update analyze falló", e);
				f.completeExceptionally(e);
			}
		}, "Heraldia update analyze");
		t.setDaemon(true);
		t.setPriority(Thread.MIN_PRIORITY);
		t.start();
		return f;
	}

	static Report analyze(Start ini, int margin, List<String> prot, Path dir, Consumer<String> progress) throws IOException {
		long t0 = System.nanoTime();
		String date = LocalDateTime.now().format(DATE);
		String id = Long.toHexString(Double.doubleToLongBits(Math.random()) ^ System.nanoTime()).substring(0, 6);
		// 1) los chunks guardados
		Map<Long, ChunkSummary> chunks = readChunks(ini.overworld().resolve("region"), ini.minY(), progress);
		progress.accept(chunks.size() + " chunks");
		// 2) la regeneración
		Map<Long, List<int[]>> pieces = Detector.piecesByChunk(chunks.values());
		Map<Long, List<int[]>> dif = differences(ini.level(), chunks.values(), pieces);
		// 3) los jugadores desconectados
		List<Build> extra = new ArrayList<>(ini.extra());
		extra.addAll(savedPlayers(ini.world().resolve("players").resolve("data")));
		// 4) clasificar
		Detector.Parameters par = Detector.Parameters.defaults(margin);
		Detector.Result r = Detector.classify(chunks.values(), dif, extra, par);
		// 5) estructuras: qué saldría hoy en cada chunk
		Set<Long> pristine = new HashSet<>(), generated = chunks.keySet();
		r.classes().forEach((k, c) -> {
			if (c == Detector.Kind.PRISTINE) {
				pristine.add(k);
			}
		});
		Map<Long, List<int[]>> requirements = new HashMap<>();
		Map<Long, List<New>> fresh = new LinkedHashMap<>();
		Today today = new Today(ini.level());
		int n = 0;
		for (ChunkSummary c : chunks.values()) {
			Detector.Kind cl = r.classes().get(c.key());
			if (cl != Detector.Kind.PRISTINE && cl != Detector.Kind.NORMAL || !today.candidate(c.cx(), c.cz())) {
				if (cl == Detector.Kind.PRISTINE && !c.structureStarts().isEmpty()) {
					requirements.put(c.key(), startBoxes(c.structureStarts()));   // hoy no sale nada ahí: lo guardado cambiaría
				}
				continue;
			}
			Map<String, int[]> exits = today.structureStarts(c.cx(), c.cz());
			Map<String, int[]> saved = new LinkedHashMap<>();
			c.structureStarts().forEach((sid, boxes) -> saved.put(sid, union(boxes)));
			List<int[]> change = new ArrayList<>();
			for (Map.Entry<String, int[]> e : exits.entrySet()) {
				int[] g = saved.get(e.getKey());
				if (g == null || !sameFootprint(g, e.getValue())) {
					change.add(e.getValue());
					if (g == null && e.getKey().startsWith(Heraldia.MOD_ID + ":")) {
						fresh.computeIfAbsent(c.key(), k -> new ArrayList<>()).add(new New(e.getKey(), e.getValue()));
					}
				}
			}
			saved.forEach((sid, g) -> {
				if (!sameFootprint(g, exits.get(sid))) {
					change.add(g);
				}
			});
			if (cl == Detector.Kind.PRISTINE && !change.isEmpty()) {
				requirements.put(c.key(), change);
			}
			if (++n % 2000 == 0) {
				progress.accept(n + " chunks con estructuras revisados");
			}
		}
		Set<Long> regenerate = Detector.regenerable(pristine, generated, requirements);
		Map<Long, Long> inhabitedCount = new HashMap<>();
		regenerate.forEach(k -> inhabitedCount.put(k, chunks.get(k).inhabited()));
		// 6) vía B: estructuras nuevas de Heraldia en sitios seguros
		List<Plan.Placement> place = new ArrayList<>();
		List<int[]> chosen = new ArrayList<>();
		int unsafe = 0;
		for (Map.Entry<Long, List<New>> e : fresh.entrySet()) {
			for (New nv : e.getValue()) {
				if (Detector.placeable(nv.box(), e.getKey(), r, regenerate, pieces, chosen)) {
					chosen.add(nv.box());
					place.add(new Plan.Placement(nv.id(), ChunkSummary.cx(e.getKey()), ChunkSummary.cz(e.getKey()), nv.box()));
				} else {
					unsafe++;
				}
			}
		}
		// 7) informe y mapas
		Set<Long> withStructure = new HashSet<>();
		place.forEach(c -> withStructure.add(ChunkSummary.key(c.cx(), c.cz())));
		BlockPos sp = BlockPos.ZERO;
		for (Build c : ini.extra()) {
			if (c.reason() == Reason.SPAWN) {
				sp = new BlockPos(c.minX(), 0, c.minZ());
			}
		}
		int[] spawn = {sp.getX() >> 4, sp.getZ() >> 4};
		String map = RegionMap.text(r.classes(), regenerate, withStructure, spawn);
		Files.createDirectories(dir);
		Path file = dir.resolve("analisis-" + date + ".txt"), mtxt = dir.resolve("mapa-" + date + ".txt"),
				mpng = dir.resolve("mapa-" + date + ".png");
		Report inf = new Report(id, date, chunks.size(), r, regenerate, List.copyOf(place), pristine.size() - regenerate.size(),
				unsafe, prot, margin, map, dir, file, mtxt, mpng, inhabitedCount);
		Files.writeString(mtxt, map, StandardCharsets.UTF_8);
		ImageIO.write(RegionMap.image(r.classes(), regenerate, withStructure, spawn, 1024, 4), "png", mpng.toFile());
		Files.writeString(file, reportText(inf, (System.nanoTime() - t0) / 1_000_000), StandardCharsets.UTF_8);
		LOGGER.info("Heraldia: update analyze: {} chunks, {} construcciones, {} protegidos, {} vírgenes ({} se regenerarían), "
						+ "{} estructuras nuevas que colocar ({} sin sitio seguro), margen {} bloques, {} ms; informe en {}",
				chunks.size(), r.builds().size(), r.tally(Detector.Kind.PROTECTED) + r.tally(Detector.Kind.BUILD),
				pristine.size(), regenerate.size(), place.size(), unsafe, margin, (System.nanoTime() - t0) / 1_000_000, file);
		return inf;
	}

	record New(String id, int[] box) {
	}

	/** El informe en texto (en inglés y español: es para el administrador, en la consola o el fichero). */
	static String reportText(Report i, long ms) {
		Detector.Result r = i.result();
		StringBuilder sb = new StringBuilder();
		sb.append("Heraldia /heraldia update analyze — ").append(i.date()).append(" (id ").append(i.id()).append(")\n");
		sb.append("Chunks: ").append(i.chunks()).append(", ").append(ms).append(" ms. Margin / margen: ").append(i.margin()).append(" blocks\n\n");
		sb.append("Builds / construcciones detectadas: ").append(r.builds().size()).append(' ').append(r.byReason()).append('\n');
		sb.append("  chunks with a build / con construcción: ").append(r.tally(Detector.Kind.BUILD)).append('\n');
		sb.append("  protected (margin) / protegidos (margen): ").append(r.tally(Detector.Kind.PROTECTED)).append('\n');
		sb.append("Virgin / vírgenes: ").append(r.tally(Detector.Kind.PRISTINE)).append(", to regenerate / a regenerar: ")
				.append(i.regenerate().size()).append(" (kept to avoid cut structures / se conservan para no cortar estructuras: ")
				.append(i.cutPristine()).append(")\n");
		sb.append("Generated, neither / generados, ni lo uno ni lo otro: ").append(r.tally(Detector.Kind.NORMAL))
				.append("; incomplete / incompletos: ").append(r.tally(Detector.Kind.INCOMPLETE)).append('\n');
		sb.append("New Heraldia structures to place / estructuras nuevas que colocar: ").append(i.place().size())
				.append(" (no safe spot / sin sitio seguro: ").append(i.unsafePlacements()).append(")\n");
		for (Plan.Placement c : i.place()) {
			sb.append("  ").append(c.structure()).append(" @ chunk ").append(c.cx()).append(',').append(c.cz()).append(" (block ")
					.append(c.cx() * 16).append(", ").append(c.cz() * 16).append(")\n");
		}
		if (!i.protections().isEmpty()) {
			sb.append("\n!! Protection mods / mods de protección: ").append(i.protections())
					.append(" — their claims cannot be read: apply is refused / no se pueden leer sus reclamaciones: apply no se ejecuta\n");
		}
		sb.append("\nNothing has been changed / no se ha cambiado nada. Map / mapa: ").append(i.mapTxt().getFileName()).append(", ")
				.append(i.mapPng().getFileName()).append("\n\n").append(i.textMap());
		return sb.toString();
	}

	/** Lee el resumen de cada chunk guardado en las regiones del mundo principal. */
	static Map<Long, ChunkSummary> readChunks(Path region, int minY, Consumer<String> progress) throws IOException {
		Map<Long, ChunkSummary> out = new LinkedHashMap<>();
		if (!Files.isDirectory(region)) {
			return out;
		}
		List<Path> files = new ArrayList<>();
		try (DirectoryStream<Path> ds = Files.newDirectoryStream(region, "r.*.mca")) {
			ds.forEach(files::add);
		}
		files.sort(null);
		int i = 0;
		for (Path f : files) {
			if (Region.coordinatesOf(f).isEmpty()) {
				continue;
			}
			for (int idx : Region.present(Region.header(f))) {
				try {
					Optional<CompoundTag> nbt = Region.read(f, idx);
					nbt.ifPresent(t -> {
						ChunkSummary rc = ChunkSummary.of(t, minY);
						out.put(rc.key(), rc);
					});
				} catch (IOException | RuntimeException e) {
					LOGGER.warn("Heraldia: update analyze: no se pudo leer un chunk de {} ({}); se da por construcción", f.getFileName(), e.getMessage());
					int[] rr = Region.coordinatesOf(f).get();
					int cx = rr[0] * 32 + idx % 32, cz = rr[1] * 32 + idx / 32;
					// un chunk ilegible no se toca: se marca como muy habitado (construcción)
					out.put(ChunkSummary.key(cx, cz), new ChunkSummary(cx, cz, true, Long.MAX_VALUE, minY, new int[0], Map.of(),
							new int[0], new String[0]));
				}
			}
			if (++i % 16 == 0) {
				progress.accept(i + "/" + files.size() + " regiones");
			}
		}
		return out;
	}

	/**
	 * Columnas {x, z} cuya cima no coincide con la de la regeneración con la misma semilla, por chunk, en los chunks por
	 * donde ha pasado algún jugador (InhabitedTime mayor que 0) y fuera de las piezas de estructuras. La regeneración es
	 * la altura del terreno base del generador ({@code OCEAN_FLOOR_WG}): árboles, nieve, fluidos y plantas no cuentan.
	 */
	static Map<Long, List<int[]>> differences(ServerLevel level, Iterable<ChunkSummary> chunks, Map<Long, List<int[]>> pieces) {
		Map<Long, List<int[]>> out = new HashMap<>();
		ChunkGenerator gen = level.getChunkSource().getGenerator();
		RandomState rs = level.getChunkSource().randomState();
		for (ChunkSummary c : chunks) {
			if (c.inhabited() <= 0 || c.tops().length == 0) {
				continue;
			}
			List<int[]> d = new ArrayList<>();
			for (int i = 0; i < ChunkSummary.SAMPLE.length; i++) {
				int y = c.tops()[i];
				String b = c.topBlocks()[i];
				if (y == Integer.MIN_VALUE || b == null || PlayerBlocks.naturalTop(b)) {
					continue;
				}
				int x = c.cx() * 16 + ChunkSummary.SAMPLE[i][0], z = c.cz() * 16 + ChunkSummary.SAMPLE[i][1];
				boolean inStructure = false;
				for (int[] bb : pieces.getOrDefault(c.key(), List.of())) {
					if (x >= bb[0] && x <= bb[3] && z >= bb[2] && z <= bb[5]) {
						inStructure = true;
						break;
					}
				}
				if (inStructure) {
					continue;
				}
				int base = gen.getBaseHeight(x, z, Heightmap.Types.OCEAN_FLOOR_WG, level, rs) - 1;
				if (Math.abs(y - base) > TOLERANCE) {
					d.add(new int[] {x, z});
				}
			}
			if (!d.isEmpty()) {
				out.put(c.key(), d);
			}
		}
		return out;
	}

	/** Posición, cama y punto de reaparición (en el mundo principal) de los jugadores guardados en players/data. */
	static List<Build> savedPlayers(Path dir) {
		List<Build> out = new ArrayList<>();
		if (!Files.isDirectory(dir)) {
			return out;
		}
		try (DirectoryStream<Path> ds = Files.newDirectoryStream(dir, "*.dat")) {
			for (Path f : ds) {
				try {
					CompoundTag t = NbtIo.readCompressed(f, NbtAccounter.unlimitedHeap());
					out.addAll(playerSource(t));
				} catch (IOException | RuntimeException e) {
					LOGGER.warn("Heraldia: update analyze: no se pudo leer {} ({})", f.getFileName(), e.getMessage());
				}
			}
		} catch (IOException e) {
			LOGGER.warn("Heraldia: update analyze: no se pudo leer {} ({})", dir, e.getMessage());
		}
		return out;
	}

	/** De los datos de un jugador: su última posición (si estaba en el mundo principal) y su punto de reaparición. */
	static List<Build> playerSource(CompoundTag t) {
		List<Build> out = new ArrayList<>();
		String dim = t.getStringOr("Dimension", "minecraft:overworld");
		var pos = t.getListOrEmpty("Pos");
		if ("minecraft:overworld".equals(dim) && pos.size() == 3) {
			out.add(Build.point((int) Math.floor(pos.getDoubleOr(0, 0)), (int) Math.floor(pos.getDoubleOr(2, 0)), Reason.PLAYER));
		}
		CompoundTag r = t.getCompoundOrEmpty("respawn");
		int[] p = r.getIntArray("pos").orElse(null);
		if (p != null && p.length == 3 && "minecraft:overworld".equals(r.getStringOr("dimension", "minecraft:overworld"))) {
			out.add(Build.point(p[0], p[2], Reason.RESPAWN));
		}
		return out;
	}

	/**
	 * ¿La misma caja en planta? (la altura no cuenta: algunas piezas vanilla, como naufragios o ruinas, se bajan al
	 * suelo al colocarse y guardan otra y)
	 */
	static boolean sameFootprint(int[] a, int[] b) {
		return b != null && a[0] == b[0] && a[2] == b[2] && a[3] == b[3] && a[5] == b[5];
	}

	static List<int[]> startBoxes(Map<String, List<int[]>> structureStarts) {
		List<int[]> out = new ArrayList<>();
		structureStarts.values().forEach(c -> out.add(union(c)));
		return out;
	}

	/** La caja que envuelve varias. */
	static int[] union(List<int[]> boxes) {
		int[] u = {Integer.MAX_VALUE, Integer.MAX_VALUE, Integer.MAX_VALUE, Integer.MIN_VALUE, Integer.MIN_VALUE, Integer.MIN_VALUE};
		for (int[] b : boxes) {
			for (int i = 0; i < 3; i++) {
				u[i] = Math.min(u[i], b[i]);
				u[i + 3] = Math.max(u[i + 3], b[i + 3]);
			}
		}
		return u;
	}

	/**
	 * Lo que saldría hoy en un chunk vacío con el generador del mundo: {@code createStructures} sobre un ProtoChunk nuevo,
	 * con las reglas de colocación de siempre (también las de Heraldia, en sus mixins). Solo en los chunks donde alguna
	 * rejilla tiene candidata (la comprobación es barata).
	 */
	static final class Today {
		private final ServerLevel level;
		private final List<Holder<StructureSet>> sets;

		Today(ServerLevel level) {
			this.level = level;
			this.sets = level.getChunkSource().getGeneratorState().possibleStructureSets();
		}

		boolean candidate(int cx, int cz) {
			var state = level.getChunkSource().getGeneratorState();
			for (Holder<StructureSet> s : sets) {
				if (s.value().placement().isStructureChunk(state, cx, cz)) {
					return true;
				}
			}
			return false;
		}

		/** id de la estructura → caja de sus piezas, de cada inicio que sale hoy en el chunk. */
		Map<String, int[]> structureStarts(int cx, int cz) {
			ProtoChunk p = generate(level, new ChunkPos(cx, cz));
			Map<String, int[]> out = new LinkedHashMap<>();
			var reg = level.registryAccess().lookupOrThrow(Registries.STRUCTURE);
			for (Map.Entry<Structure, StructureStart> e : p.getAllStarts().entrySet()) {
				if (!e.getValue().isValid()) {
					continue;
				}
				Identifier id = reg.getKey(e.getKey());
				if (id != null) {
					out.put(id.toString(), box(e.getValue()));
				}
			}
			return out;
		}
	}

	/** Un ProtoChunk vacío con los inicios de estructura que le daría hoy la generación. */
	static ProtoChunk generate(ServerLevel level, ChunkPos pos) {
		ProtoChunk p = new ProtoChunk(pos, UpgradeData.EMPTY, level, level.palettedContainerFactory(), null);
		level.getChunkSource().getGenerator().createStructures(level.registryAccess(), level.getChunkSource().getGeneratorState(),
				level.structureManager(), p, level.getServer().getStructureTemplateManager(), level.dimension());
		return p;
	}

	/** La caja de las piezas de un inicio, {minX, minY, minZ, maxX, maxY, maxZ}. */
	static int[] box(StructureStart s) {
		List<int[]> boxes = new ArrayList<>();
		for (StructurePiece piece : s.getPieces()) {
			BoundingBox b = piece.getBoundingBox();
			boxes.add(new int[] {b.minX(), b.minY(), b.minZ(), b.maxX(), b.maxY(), b.maxZ()});
		}
		return boxes.isEmpty() ? new int[] {0, 0, 0, -1, -1, -1} : union(boxes);
	}
}
