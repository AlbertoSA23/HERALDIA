package io.github.albertosa23.heraldia.actualizar;

import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.actualizar.Detector.Construccion;
import io.github.albertosa23.heraldia.actualizar.Detector.Motivo;
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
 * <li>lee cada chunk guardado de las regiones ({@link Region}, {@link ResumenChunk});</li>
 * <li>compara la cima de unas columnas de los chunks por donde ha pasado algún jugador con la de la regeneración con la
 * misma semilla ({@code getBaseHeight} del generador, que es puro), sin contar las cimas naturales;</li>
 * <li>lee las camas, puntos de reaparición y últimas posiciones de los jugadores que no están conectados;</li>
 * <li>clasifica ({@link Detector}) con el margen de actualizar.margen_bloques;</li>
 * <li>en los chunks vírgenes y en los normales que alguna rejilla tiene por candidatos, calcula qué inicios de estructura
 * saldrían hoy en un chunk vacío con el generador del mundo ({@code createStructures} sobre un {@link ProtoChunk}: con
 * las mismas reglas que la generación) y los compara con los guardados: de ahí salen qué chunks vírgenes se pueden borrar
 * sin cortar estructuras (vía A) y qué estructuras nuevas de Heraldia caben en sitios seguros (vía B);</li>
 * <li>escribe el informe, el mapa en texto y en imagen en {@code <mundo>/heraldia/actualizar/}.</li>
 * </ol>
 * No cambia nada del mundo.
 */
public final class Analisis {
	private static final Logger LOGGER = LoggerFactory.getLogger(Heraldia.MOD_ID);
	/** Diferencia de altura (bloques) con la regeneración a partir de la cual una columna cuenta como distinta. */
	static final int TOLERANCIA = 4;
	/** Mods de protección conocidos: si hay alguno, sus reclamaciones no se pueden leer y apply no se ejecuta. */
	static final List<String> PROTECCION = List.of("flan", "goml", "ftbchunks", "openpartiesandclaims", "cadmus", "fabricclaims",
			"claimpoints", "griefdefender");
	private static final DateTimeFormatter FECHA = DateTimeFormatter.ofPattern("yyyyMMdd-HHmmss", Locale.ROOT);

	/** Lo que sale del análisis. */
	public record Informe(String id, String fecha, int chunks, Detector.Resultado resultado, Set<Long> regenerar,
						  List<Plan.Colocacion> colocar, int virgenesCortadas, int colocacionesInseguras, List<String> protecciones,
						  int margen, String mapaTexto, Path carpeta, Path fichero, Path mapaTxt, Path mapaPng, Map<Long, Long> habitado) {
		/** El plan que dejaría apply. */
		public Plan plan(boolean copia) {
			Plan p = new Plan();
			p.id = id;
			p.fecha = fecha;
			p.copia = copia;
			p.margen = margen;
			regenerar.stream().sorted().forEach(k -> p.regenerar.add(new Plan.Chunk(ResumenChunk.cx(k), ResumenChunk.cz(k),
					habitado.getOrDefault(k, 0L))));
			p.colocar.addAll(colocar);
			return p;
		}
	}

	/** Lo apuntado en el hilo del servidor antes de empezar. */
	record Inicio(Path mundo, Path overworld, int minY, List<Construccion> extra, ServerLevel level) {
	}

	private Analisis() {
	}

	/** La carpeta de /heraldia update dentro del mundo. */
	public static Path carpeta(MinecraftServer server) {
		return server.getWorldPath(LevelResource.ROOT).resolve("heraldia").resolve("actualizar");
	}

	/** La carpeta del mundo principal (con region/, entities/ y poi/). */
	public static Path overworld(MinecraftServer server) {
		return DimensionType.getStorageFolder(Level.OVERWORLD, server.getWorldPath(LevelResource.ROOT));
	}

	/** Mods de protección cargados (con reclamaciones que no se pueden leer). */
	public static List<String> protecciones() {
		return PROTECCION.stream().filter(FabricLoader.getInstance()::isModLoaded).toList();
	}

	/**
	 * Empieza el análisis: en el hilo del servidor guarda el mundo y apunta el spawn y los jugadores; el resto, en un hilo
	 * propio. {@code progreso} recibe mensajes de avance (desde ese hilo).
	 */
	public static CompletableFuture<Informe> empezar(MinecraftServer server, Consumer<String> progreso) {
		server.saveEverything(true, true, true);
		ServerLevel ow = server.overworld();
		List<Construccion> extra = new ArrayList<>();
		BlockPos spawn = ow.getRespawnData().pos();
		extra.add(Construccion.punto(spawn.getX(), spawn.getZ(), Motivo.SPAWN));
		for (ServerPlayer p : server.getPlayerList().getPlayers()) {
			if (p.level() == ow) {
				extra.add(Construccion.punto(p.getBlockX(), p.getBlockZ(), Motivo.JUGADOR));
			}
			ServerPlayer.RespawnConfig rc = p.getRespawnConfig();
			if (rc != null && rc.respawnData().dimension() == Level.OVERWORLD) {
				BlockPos r = rc.respawnData().pos();
				extra.add(Construccion.punto(r.getX(), r.getZ(), Motivo.REAPARICION));
			}
		}
		Inicio ini = new Inicio(server.getWorldPath(LevelResource.ROOT), overworld(server), ow.getMinY(), extra, ow);
		int margen = HeraldiaConfig.get().has("actualizar.margen_bloques") ? HeraldiaConfig.get().getInt("actualizar.margen_bloques") : 50;
		List<String> prot = protecciones();
		Path dir = carpeta(server);
		CompletableFuture<Informe> f = new CompletableFuture<>();
		Thread t = new Thread(() -> {
			try {
				f.complete(analizar(ini, margen, prot, dir, progreso));
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

	static Informe analizar(Inicio ini, int margen, List<String> prot, Path dir, Consumer<String> progreso) throws IOException {
		long t0 = System.nanoTime();
		String fecha = LocalDateTime.now().format(FECHA);
		String id = Long.toHexString(Double.doubleToLongBits(Math.random()) ^ System.nanoTime()).substring(0, 6);
		// 1) los chunks guardados
		Map<Long, ResumenChunk> chunks = leerChunks(ini.overworld().resolve("region"), ini.minY(), progreso);
		progreso.accept(chunks.size() + " chunks");
		// 2) la regeneración
		Map<Long, List<int[]>> piezas = Detector.piezasPorChunk(chunks.values());
		Map<Long, List<int[]>> dif = diferencias(ini.level(), chunks.values(), piezas);
		// 3) los jugadores desconectados
		List<Construccion> extra = new ArrayList<>(ini.extra());
		extra.addAll(jugadoresGuardados(ini.mundo().resolve("players").resolve("data")));
		// 4) clasificar
		Detector.Parametros par = Detector.Parametros.porDefecto(margen);
		Detector.Resultado r = Detector.clasificar(chunks.values(), dif, extra, par);
		// 5) estructuras: qué saldría hoy en cada chunk
		Set<Long> virgenes = new HashSet<>(), generados = chunks.keySet();
		r.clases().forEach((k, c) -> {
			if (c == Detector.Clase.VIRGEN) {
				virgenes.add(k);
			}
		});
		Map<Long, List<int[]>> requisitos = new HashMap<>();
		Map<Long, List<Nuevo>> nuevos = new LinkedHashMap<>();
		Hoy hoy = new Hoy(ini.level());
		int n = 0;
		for (ResumenChunk c : chunks.values()) {
			Detector.Clase cl = r.clases().get(c.clave());
			if (cl != Detector.Clase.VIRGEN && cl != Detector.Clase.NORMAL || !hoy.candidato(c.cx(), c.cz())) {
				if (cl == Detector.Clase.VIRGEN && !c.inicios().isEmpty()) {
					requisitos.put(c.clave(), cajasDeInicios(c.inicios()));   // hoy no sale nada ahí: lo guardado cambiaría
				}
				continue;
			}
			Map<String, int[]> salen = hoy.inicios(c.cx(), c.cz());
			Map<String, int[]> guardados = new LinkedHashMap<>();
			c.inicios().forEach((sid, cajas) -> guardados.put(sid, union(cajas)));
			List<int[]> cambian = new ArrayList<>();
			for (Map.Entry<String, int[]> e : salen.entrySet()) {
				int[] g = guardados.get(e.getKey());
				if (g == null || !mismaPlanta(g, e.getValue())) {
					cambian.add(e.getValue());
					if (g == null && e.getKey().startsWith(Heraldia.MOD_ID + ":")) {
						nuevos.computeIfAbsent(c.clave(), k -> new ArrayList<>()).add(new Nuevo(e.getKey(), e.getValue()));
					}
				}
			}
			guardados.forEach((sid, g) -> {
				if (!mismaPlanta(g, salen.get(sid))) {
					cambian.add(g);
				}
			});
			if (cl == Detector.Clase.VIRGEN && !cambian.isEmpty()) {
				requisitos.put(c.clave(), cambian);
			}
			if (++n % 2000 == 0) {
				progreso.accept(n + " chunks con estructuras revisados");
			}
		}
		Set<Long> regenerar = Detector.regenerables(virgenes, generados, requisitos);
		Map<Long, Long> habitados = new HashMap<>();
		regenerar.forEach(k -> habitados.put(k, chunks.get(k).habitado()));
		// 6) vía B: estructuras nuevas de Heraldia en sitios seguros
		List<Plan.Colocacion> colocar = new ArrayList<>();
		List<int[]> elegidas = new ArrayList<>();
		int inseguras = 0;
		for (Map.Entry<Long, List<Nuevo>> e : nuevos.entrySet()) {
			for (Nuevo nv : e.getValue()) {
				if (Detector.colocable(nv.caja(), e.getKey(), r, regenerar, piezas, elegidas)) {
					elegidas.add(nv.caja());
					colocar.add(new Plan.Colocacion(nv.id(), ResumenChunk.cx(e.getKey()), ResumenChunk.cz(e.getKey()), nv.caja()));
				} else {
					inseguras++;
				}
			}
		}
		// 7) informe y mapas
		Set<Long> conEstructura = new HashSet<>();
		colocar.forEach(c -> conEstructura.add(ResumenChunk.clave(c.cx(), c.cz())));
		BlockPos sp = BlockPos.ZERO;
		for (Construccion c : ini.extra()) {
			if (c.motivo() == Motivo.SPAWN) {
				sp = new BlockPos(c.minX(), 0, c.minZ());
			}
		}
		int[] spawn = {sp.getX() >> 4, sp.getZ() >> 4};
		String mapa = Mapa.texto(r.clases(), regenerar, conEstructura, spawn);
		Files.createDirectories(dir);
		Path fichero = dir.resolve("analisis-" + fecha + ".txt"), mtxt = dir.resolve("mapa-" + fecha + ".txt"),
				mpng = dir.resolve("mapa-" + fecha + ".png");
		Informe inf = new Informe(id, fecha, chunks.size(), r, regenerar, List.copyOf(colocar), virgenes.size() - regenerar.size(),
				inseguras, prot, margen, mapa, dir, fichero, mtxt, mpng, habitados);
		Files.writeString(mtxt, mapa, StandardCharsets.UTF_8);
		ImageIO.write(Mapa.imagen(r.clases(), regenerar, conEstructura, spawn, 1024, 4), "png", mpng.toFile());
		Files.writeString(fichero, textoInforme(inf, (System.nanoTime() - t0) / 1_000_000), StandardCharsets.UTF_8);
		LOGGER.info("Heraldia: update analyze: {} chunks, {} construcciones, {} protegidos, {} vírgenes ({} se regenerarían), "
						+ "{} estructuras nuevas que colocar ({} sin sitio seguro), margen {} bloques, {} ms; informe en {}",
				chunks.size(), r.construcciones().size(), r.cuenta(Detector.Clase.PROTEGIDO) + r.cuenta(Detector.Clase.CONSTRUCCION),
				virgenes.size(), regenerar.size(), colocar.size(), inseguras, margen, (System.nanoTime() - t0) / 1_000_000, fichero);
		return inf;
	}

	record Nuevo(String id, int[] caja) {
	}

	/** El informe en texto (en inglés y español: es para el administrador, en la consola o el fichero). */
	static String textoInforme(Informe i, long ms) {
		Detector.Resultado r = i.resultado();
		StringBuilder sb = new StringBuilder();
		sb.append("Heraldia /heraldia update analyze — ").append(i.fecha()).append(" (id ").append(i.id()).append(")\n");
		sb.append("Chunks: ").append(i.chunks()).append(", ").append(ms).append(" ms. Margin / margen: ").append(i.margen()).append(" blocks\n\n");
		sb.append("Builds / construcciones detectadas: ").append(r.construcciones().size()).append(' ').append(r.porMotivo()).append('\n');
		sb.append("  chunks with a build / con construcción: ").append(r.cuenta(Detector.Clase.CONSTRUCCION)).append('\n');
		sb.append("  protected (margin) / protegidos (margen): ").append(r.cuenta(Detector.Clase.PROTEGIDO)).append('\n');
		sb.append("Virgin / vírgenes: ").append(r.cuenta(Detector.Clase.VIRGEN)).append(", to regenerate / a regenerar: ")
				.append(i.regenerar().size()).append(" (kept to avoid cut structures / se conservan para no cortar estructuras: ")
				.append(i.virgenesCortadas()).append(")\n");
		sb.append("Generated, neither / generados, ni lo uno ni lo otro: ").append(r.cuenta(Detector.Clase.NORMAL))
				.append("; incomplete / incompletos: ").append(r.cuenta(Detector.Clase.INCOMPLETO)).append('\n');
		sb.append("New Heraldia structures to place / estructuras nuevas que colocar: ").append(i.colocar().size())
				.append(" (no safe spot / sin sitio seguro: ").append(i.colocacionesInseguras()).append(")\n");
		for (Plan.Colocacion c : i.colocar()) {
			sb.append("  ").append(c.estructura()).append(" @ chunk ").append(c.cx()).append(',').append(c.cz()).append(" (block ")
					.append(c.cx() * 16).append(", ").append(c.cz() * 16).append(")\n");
		}
		if (!i.protecciones().isEmpty()) {
			sb.append("\n!! Protection mods / mods de protección: ").append(i.protecciones())
					.append(" — their claims cannot be read: apply is refused / no se pueden leer sus reclamaciones: apply no se ejecuta\n");
		}
		sb.append("\nNothing has been changed / no se ha cambiado nada. Map / mapa: ").append(i.mapaTxt().getFileName()).append(", ")
				.append(i.mapaPng().getFileName()).append("\n\n").append(i.mapaTexto());
		return sb.toString();
	}

	/** Lee el resumen de cada chunk guardado en las regiones del mundo principal. */
	static Map<Long, ResumenChunk> leerChunks(Path region, int minY, Consumer<String> progreso) throws IOException {
		Map<Long, ResumenChunk> out = new LinkedHashMap<>();
		if (!Files.isDirectory(region)) {
			return out;
		}
		List<Path> ficheros = new ArrayList<>();
		try (DirectoryStream<Path> ds = Files.newDirectoryStream(region, "r.*.mca")) {
			ds.forEach(ficheros::add);
		}
		ficheros.sort(null);
		int i = 0;
		for (Path f : ficheros) {
			if (Region.coordenadas(f).isEmpty()) {
				continue;
			}
			for (int idx : Region.presentes(Region.cabecera(f))) {
				try {
					Optional<CompoundTag> nbt = Region.leer(f, idx);
					nbt.ifPresent(t -> {
						ResumenChunk rc = ResumenChunk.de(t, minY);
						out.put(rc.clave(), rc);
					});
				} catch (IOException | RuntimeException e) {
					LOGGER.warn("Heraldia: update analyze: no se pudo leer un chunk de {} ({}); se da por construcción", f.getFileName(), e.getMessage());
					int[] rr = Region.coordenadas(f).get();
					int cx = rr[0] * 32 + idx % 32, cz = rr[1] * 32 + idx / 32;
					// un chunk ilegible no se toca: se marca como muy habitado (construcción)
					out.put(ResumenChunk.clave(cx, cz), new ResumenChunk(cx, cz, true, Long.MAX_VALUE, minY, new int[0], Map.of(),
							new int[0], new String[0]));
				}
			}
			if (++i % 16 == 0) {
				progreso.accept(i + "/" + ficheros.size() + " regiones");
			}
		}
		return out;
	}

	/**
	 * Columnas {x, z} cuya cima no coincide con la de la regeneración con la misma semilla, por chunk, en los chunks por
	 * donde ha pasado algún jugador (InhabitedTime mayor que 0) y fuera de las piezas de estructuras. La regeneración es
	 * la altura del terreno base del generador ({@code OCEAN_FLOOR_WG}): árboles, nieve, fluidos y plantas no cuentan.
	 */
	static Map<Long, List<int[]>> diferencias(ServerLevel level, Iterable<ResumenChunk> chunks, Map<Long, List<int[]>> piezas) {
		Map<Long, List<int[]>> out = new HashMap<>();
		ChunkGenerator gen = level.getChunkSource().getGenerator();
		RandomState rs = level.getChunkSource().randomState();
		for (ResumenChunk c : chunks) {
			if (c.habitado() <= 0 || c.cimas().length == 0) {
				continue;
			}
			List<int[]> d = new ArrayList<>();
			for (int i = 0; i < ResumenChunk.MUESTRA.length; i++) {
				int y = c.cimas()[i];
				String b = c.bloquesCima()[i];
				if (y == Integer.MIN_VALUE || b == null || BloquesJugador.cimaNatural(b)) {
					continue;
				}
				int x = c.cx() * 16 + ResumenChunk.MUESTRA[i][0], z = c.cz() * 16 + ResumenChunk.MUESTRA[i][1];
				boolean enEstructura = false;
				for (int[] bb : piezas.getOrDefault(c.clave(), List.of())) {
					if (x >= bb[0] && x <= bb[3] && z >= bb[2] && z <= bb[5]) {
						enEstructura = true;
						break;
					}
				}
				if (enEstructura) {
					continue;
				}
				int base = gen.getBaseHeight(x, z, Heightmap.Types.OCEAN_FLOOR_WG, level, rs) - 1;
				if (Math.abs(y - base) > TOLERANCIA) {
					d.add(new int[] {x, z});
				}
			}
			if (!d.isEmpty()) {
				out.put(c.clave(), d);
			}
		}
		return out;
	}

	/** Posición, cama y punto de reaparición (en el mundo principal) de los jugadores guardados en players/data. */
	static List<Construccion> jugadoresGuardados(Path dir) {
		List<Construccion> out = new ArrayList<>();
		if (!Files.isDirectory(dir)) {
			return out;
		}
		try (DirectoryStream<Path> ds = Files.newDirectoryStream(dir, "*.dat")) {
			for (Path f : ds) {
				try {
					CompoundTag t = NbtIo.readCompressed(f, NbtAccounter.unlimitedHeap());
					out.addAll(deJugador(t));
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
	static List<Construccion> deJugador(CompoundTag t) {
		List<Construccion> out = new ArrayList<>();
		String dim = t.getStringOr("Dimension", "minecraft:overworld");
		var pos = t.getListOrEmpty("Pos");
		if ("minecraft:overworld".equals(dim) && pos.size() == 3) {
			out.add(Construccion.punto((int) Math.floor(pos.getDoubleOr(0, 0)), (int) Math.floor(pos.getDoubleOr(2, 0)), Motivo.JUGADOR));
		}
		CompoundTag r = t.getCompoundOrEmpty("respawn");
		int[] p = r.getIntArray("pos").orElse(null);
		if (p != null && p.length == 3 && "minecraft:overworld".equals(r.getStringOr("dimension", "minecraft:overworld"))) {
			out.add(Construccion.punto(p[0], p[2], Motivo.REAPARICION));
		}
		return out;
	}

	/**
	 * ¿La misma caja en planta? (la altura no cuenta: algunas piezas vanilla, como naufragios o ruinas, se bajan al
	 * suelo al colocarse y guardan otra y)
	 */
	static boolean mismaPlanta(int[] a, int[] b) {
		return b != null && a[0] == b[0] && a[2] == b[2] && a[3] == b[3] && a[5] == b[5];
	}

	static List<int[]> cajasDeInicios(Map<String, List<int[]>> inicios) {
		List<int[]> out = new ArrayList<>();
		inicios.values().forEach(c -> out.add(union(c)));
		return out;
	}

	/** La caja que envuelve varias. */
	static int[] union(List<int[]> cajas) {
		int[] u = {Integer.MAX_VALUE, Integer.MAX_VALUE, Integer.MAX_VALUE, Integer.MIN_VALUE, Integer.MIN_VALUE, Integer.MIN_VALUE};
		for (int[] b : cajas) {
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
	static final class Hoy {
		private final ServerLevel level;
		private final List<Holder<StructureSet>> sets;

		Hoy(ServerLevel level) {
			this.level = level;
			this.sets = level.getChunkSource().getGeneratorState().possibleStructureSets();
		}

		boolean candidato(int cx, int cz) {
			var state = level.getChunkSource().getGeneratorState();
			for (Holder<StructureSet> s : sets) {
				if (s.value().placement().isStructureChunk(state, cx, cz)) {
					return true;
				}
			}
			return false;
		}

		/** id de la estructura → caja de sus piezas, de cada inicio que sale hoy en el chunk. */
		Map<String, int[]> inicios(int cx, int cz) {
			ProtoChunk p = generar(level, new ChunkPos(cx, cz));
			Map<String, int[]> out = new LinkedHashMap<>();
			var reg = level.registryAccess().lookupOrThrow(Registries.STRUCTURE);
			for (Map.Entry<Structure, StructureStart> e : p.getAllStarts().entrySet()) {
				if (!e.getValue().isValid()) {
					continue;
				}
				Identifier id = reg.getKey(e.getKey());
				if (id != null) {
					out.put(id.toString(), caja(e.getValue()));
				}
			}
			return out;
		}
	}

	/** Un ProtoChunk vacío con los inicios de estructura que le daría hoy la generación. */
	static ProtoChunk generar(ServerLevel level, ChunkPos pos) {
		ProtoChunk p = new ProtoChunk(pos, UpgradeData.EMPTY, level, level.palettedContainerFactory(), null);
		level.getChunkSource().getGenerator().createStructures(level.registryAccess(), level.getChunkSource().getGeneratorState(),
				level.structureManager(), p, level.getServer().getStructureTemplateManager(), level.dimension());
		return p;
	}

	/** La caja de las piezas de un inicio, {minX, minY, minZ, maxX, maxY, maxZ}. */
	static int[] caja(StructureStart s) {
		List<int[]> cajas = new ArrayList<>();
		for (StructurePiece piece : s.getPieces()) {
			BoundingBox b = piece.getBoundingBox();
			cajas.add(new int[] {b.minX(), b.minY(), b.minZ(), b.maxX(), b.maxY(), b.maxZ()});
		}
		return cajas.isEmpty() ? new int[] {0, 0, 0, -1, -1, -1} : union(cajas);
	}
}
