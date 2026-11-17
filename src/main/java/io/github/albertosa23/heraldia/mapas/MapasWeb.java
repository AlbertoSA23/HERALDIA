package io.github.albertosa23.heraldia.mapas;

import com.google.gson.JsonObject;
import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.arena.Arena;
import io.github.albertosa23.heraldia.comando.Estado;
import io.github.albertosa23.heraldia.comando.EstadoCommand;
import io.github.albertosa23.heraldia.comando.Textos;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.EnumSet;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.Executor;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.ScheduledThreadPoolExecutor;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.function.Predicate;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerChunkEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.fabricmc.loader.api.FabricLoader;
import net.minecraft.advancements.AdvancementHolder;
import net.minecraft.advancements.AdvancementProgress;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Registry;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.Identifier;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.chunk.LevelChunk;
import net.minecraft.world.level.levelgen.structure.BoundingBox;
import net.minecraft.world.level.levelgen.structure.Structure;
import net.minecraft.world.level.levelgen.structure.StructureStart;
import net.minecraft.world.level.storage.LevelResource;
import org.jspecify.annotations.Nullable;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Marcadores de Heraldia en los mapas web del servidor (BlueMap, Dynmap y squaremap), dependencias opcionales: cada mapa
 * se detecta al iniciar con {@code FabricLoader.isModLoaded} y solo entonces se carga su adaptador (por nombre, en su
 * paquete); sin ninguno no se registra ningún evento y el mod no cambia nada.
 * <ul>
 * <li>De dónde salen: cada chunk del Overworld que se carga (evento de Fabric, en el hilo del servidor) trae los inicios de
 * estructura que empiezan en él: los de Heraldia se apuntan en el {@link Registro} (unas búsquedas en un mapa; casi
 * siempre vacío) y la arena, de {@link Arena#centro()}.</li>
 * <li>Qué sale: {@link Marcadores} (opciones mapas_web.*; con solo_descubiertas, lo mismo que cuenta /heraldia status).</li>
 * <li>Cuándo: al arrancar (lee el registro y los logros de los jugadores fuera del hilo), cuando alguien consigue un logro de
 * Heraldia (PlayerAdvancementsMixin), cuando aparece una estructura nueva, tras /heraldia reload y con /heraldia webmap
 * refresh. Todo el trabajo va en un hilo propio, agrupado (una actualización cada {@value #ESPERA_MS} ms como mucho).</li>
 * </ul>
 */
public final class MapasWeb {
	private static final Logger LOGGER = LoggerFactory.getLogger(Heraldia.MOD_ID);
	public static final String ACTIVADO = "mapas_web.activado", SOLO_DESCUBIERTAS = "mapas_web.solo_descubiertas",
			IDIOMA = "mapas_web.idioma";
	/** id del mod → adaptador (por nombre: así su clase, y la API del mapa, solo se cargan si el mod está). */
	public static final Map<String, String> ADAPTADORES = adaptadores();
	static final long ESPERA_MS = 2000;

	private static List<String> presentes = List.of();
	private static volatile List<MapaWeb> mapas = List.of();
	private static final Registro REGISTRO = new Registro();
	/** Logros de todos los jugadores; solo se tocan desde el hilo de los mapas web. */
	private static Estado.Logros logros = new Estado.Logros();
	private static @Nullable ScheduledExecutorService hilo;
	private static final AtomicBoolean PENDIENTE = new AtomicBoolean();
	/** Si un mapa aún no está listo, se reintenta (cada {@value #ESPERA_MS} ms) hasta este número de veces. */
	static final int REINTENTOS_MAX = 60;
	private static final java.util.concurrent.atomic.AtomicInteger REINTENTOS = new java.util.concurrent.atomic.AtomicInteger();
	private static volatile @Nullable Path fichero;
	private static volatile Map<String, String> estiloFamilia = Map.of();
	private static volatile int ultimos;

	private MapasWeb() {
	}

	private static Map<String, String> adaptadores() {
		Map<String, String> m = new LinkedHashMap<>();
		m.put("bluemap", MapasWeb.class.getPackageName() + ".bluemap.BlueMapAdaptador");
		m.put("dynmap", MapasWeb.class.getPackageName() + ".dynmap.DynmapAdaptador");
		m.put("squaremap", MapasWeb.class.getPackageName() + ".squaremap.SquaremapAdaptador");
		return Map.copyOf(m);
	}

	/** Los mods de mapa que están cargados, en orden (lógica pura). */
	public static List<String> detectados(Predicate<String> cargado) {
		return ADAPTADORES.keySet().stream().sorted().filter(cargado).toList();
	}

	/** Una línea en Heraldia.onInitialize. Sin mapas web cargados no registra nada. */
	public static void registrar() {
		presentes = detectados(FabricLoader.getInstance()::isModLoaded);
		if (presentes.isEmpty()) {
			return;
		}
		LOGGER.info("Heraldia: mapas web: {}", String.join(", ", presentes));
		ServerChunkEvents.CHUNK_LOAD.register(MapasWeb::alCargarChunk);
		ServerLifecycleEvents.SERVER_STARTED.register(MapasWeb::arrancar);
		ServerLifecycleEvents.SERVER_STOPPING.register(server -> parar());
	}

	/** ¿Hay algún mapa web en uso? */
	public static boolean enUso() {
		return !mapas.isEmpty();
	}

	// --- eventos ---

	private static void arrancar(MinecraftServer server) {
		estiloFamilia = estilos(HeraldiaConfig.get());
		Path raiz = server.getWorldPath(LevelResource.ROOT);
		fichero = raiz.resolve(Registro.FICHERO);
		Contexto ctx = new Contexto(server.getWorldData().getLevelName(), server, server.overworld());
		List<MapaWeb> cargados = new ArrayList<>();
		for (String mod : presentes) {
			try {
				cargados.add((MapaWeb) Class.forName(ADAPTADORES.get(mod)).getConstructor(Contexto.class).newInstance(ctx));
			} catch (ReflectiveOperationException | LinkageError | RuntimeException e) {
				LOGGER.warn("Heraldia: mapas web: no se pudo usar {} (¿otra versión de su API?): {}", mod, String.valueOf(e));
			}
		}
		ScheduledThreadPoolExecutor ex = new ScheduledThreadPoolExecutor(1, r -> {
			Thread t = new Thread(r, "Heraldia mapas web");
			t.setDaemon(true);
			t.setPriority(Thread.MIN_PRIORITY);
			return t;
		});
		ex.setRemoveOnCancelPolicy(true);
		hilo = ex;
		mapas = List.copyOf(cargados);
		if (cargados.isEmpty()) {
			return;
		}
		Path dir = server.getWorldPath(LevelResource.PLAYER_ADVANCEMENTS_DIR);
		ex.execute(() -> {
			int leidos = REGISTRO.leer(raiz.resolve(Registro.FICHERO));
			Estado.Logros l = new Estado.Logros();
			EstadoCommand.leerFicheros(dir, Set.of(), l);
			logros = l;
			LOGGER.info("Heraldia: mapas web: {} estructuras conocidas ({} del fichero), logros de {} jugadores", REGISTRO.tamano(),
					leidos, l.jugadores());
			refrescar();
		});
	}

	private static void parar() {
		ScheduledExecutorService ex = hilo;
		hilo = null;
		List<MapaWeb> ms = mapas;
		mapas = List.of();
		if (ex != null) {
			ex.shutdown();
			try {
				ex.awaitTermination(10, TimeUnit.SECONDS);
			} catch (InterruptedException e) {
				Thread.currentThread().interrupt();
			}
		}
		guardar();
		for (MapaWeb m : ms) {
			try {
				m.cerrar();
			} catch (RuntimeException | LinkageError e) {
				LOGGER.warn("Heraldia: mapas web: {} al cerrar: {}", m.nombre(), String.valueOf(e));
			}
		}
		logros = new Estado.Logros();
	}

	/** Hilo del servidor: los inicios de estructura de Heraldia que empiezan en este chunk. Salida temprana barata. */
	private static void alCargarChunk(ServerLevel level, LevelChunk chunk, boolean generado) {
		if (mapas.isEmpty() || level.dimension() != Level.OVERWORLD) {
			return;
		}
		Map<Structure, StructureStart> starts = chunk.getAllStarts();
		if (starts.isEmpty()) {
			return;
		}
		Registry<Structure> reg = null;
		for (Map.Entry<Structure, StructureStart> e : starts.entrySet()) {
			StructureStart st = e.getValue();
			if (st == null || !st.isValid()) {
				continue;
			}
			if (reg == null) {
				reg = level.registryAccess().lookupOrThrow(Registries.STRUCTURE);
			}
			Identifier id = reg.getKey(e.getKey());
			if (id == null || !Heraldia.MOD_ID.equals(id.getNamespace())) {
				continue;
			}
			BoundingBox bb = st.getBoundingBox();
			BlockPos c = bb.getCenter();
			Sitio s = Sitio.de(id.getPath(), estiloFamilia, c.getX(), c.getY(), c.getZ());
			if (s != null && REGISTRO.anadir(s)) {
				programar();
			}
		}
	}

	/**
	 * Hilo del servidor (PlayerAdvancementsMixin): un jugador acaba de conseguir un criterio de un logro de Heraldia.
	 * Se suma a los logros conocidos y se actualizan los mapas (agrupado).
	 */
	public static void alConseguir(ServerPlayer player, AdvancementHolder holder, String criterio) {
		ScheduledExecutorService ex = hilo;
		if (mapas.isEmpty() || ex == null || !Heraldia.MOD_ID.equals(holder.id().getNamespace())) {
			return;
		}
		AdvancementProgress pr = player.getAdvancements().getOrStartProgress(holder);
		String id = holder.id().toString();
		boolean hecho = pr.isDone();
		ex.execute(() -> logros.sumar(id, hecho, List.of(criterio)));
		programar();
	}

	/** Pide una actualización de los mapas (se agrupan: como mucho una cada {@value #ESPERA_MS} ms). */
	public static void programar() {
		ScheduledExecutorService ex = hilo;
		if (ex == null || mapas.isEmpty() || !PENDIENTE.compareAndSet(false, true)) {
			return;
		}
		try {
			ex.schedule(() -> {
				PENDIENTE.set(false);
				refrescar();
			}, ESPERA_MS, TimeUnit.MILLISECONDS);
		} catch (RuntimeException e) {
			PENDIENTE.set(false);   // parando
		}
	}

	// --- la actualización (hilo de los mapas web) ---

	/** Opciones en uso (lee la configuración cada vez: se recargan con /heraldia reload). */
	static Marcadores.Opciones opciones(HeraldiaConfig cfg) {
		Set<Capa> capas = EnumSet.noneOf(Capa.class);
		for (Capa c : Capa.values()) {
			if (!cfg.has(c.opcion()) || cfg.getBool(c.opcion())) {
				capas.add(c);
			}
		}
		return new Marcadores.Opciones(cfg.getBool(ACTIVADO), cfg.getBool(SOLO_DESCUBIERTAS), capas);
	}

	/** Código de idioma de los textos de los mapas: el de mapas_web.idioma o, con «auto», el de la JVM. */
	static String idioma(String opcion, Locale jvm) {
		return "auto".equals(opcion) ? (jvm.getLanguage() + "_" + jvm.getCountry()).toLowerCase(Locale.ROOT) : opcion;
	}

	/** Recalcula y publica los marcadores; devuelve cuántos hay. */
	static int refrescar() {
		List<MapaWeb> ms = mapas;
		if (ms.isEmpty()) {
			return 0;
		}
		HeraldiaConfig cfg = HeraldiaConfig.get();
		Marcadores.Opciones o = opciones(cfg);
		Map<String, String> textos = Textos.textos(idioma(cfg.has(IDIOMA) ? cfg.getString(IDIOMA) : "auto", Locale.getDefault()));
		BlockPos a = Arena.centro();
		int[] arena = a == null ? null : new int[]{a.getX(), a.getY(), a.getZ()};
		List<Marcador> lista = Marcadores.construir(REGISTRO.todos(), arena, logros, o, textos);
		Map<Capa, List<Marcador>> porCapa = Marcadores.porCapa(lista, o);
		Map<Capa, String> nombres = Marcadores.nombresCapas(textos);
		boolean listos = true;
		for (MapaWeb m : ms) {
			try {
				listos &= m.publicar(nombres, porCapa);
			} catch (RuntimeException | LinkageError e) {
				LOGGER.warn("Heraldia: mapas web: {} no aceptó los marcadores: {}", m.nombre(), String.valueOf(e));
			}
		}
		if (!listos && REINTENTOS.getAndIncrement() < REINTENTOS_MAX) {
			programar();        // algún mapa arranca después que el servidor: otra vez dentro de un rato
		} else if (listos) {
			REINTENTOS.set(0);
		}
		if (lista.size() != ultimos) {
			LOGGER.info("Heraldia: mapas web: {} marcadores ({} estructuras conocidas)", lista.size(), REGISTRO.tamano());
			ultimos = lista.size();
		}
		guardar();
		return lista.size();
	}

	private static void guardar() {
		Path f = fichero;
		if (f == null) {
			return;
		}
		try {
			REGISTRO.guardar(f);
		} catch (java.io.IOException e) {
			LOGGER.warn("Heraldia: mapas web: no se pudo guardar {}: {}", f, e.getMessage());
		}
	}

	static Map<String, String> estilos(HeraldiaConfig cfg) {
		Map<String, String> out = new LinkedHashMap<>();
		JsonObject styles = cfg.schema().getAsJsonObject("aldeas").getAsJsonObject("estilos");
		styles.entrySet().forEach(e -> out.put(e.getKey(), e.getValue().getAsString()));
		return Map.copyOf(out);
	}

	// --- /heraldia webmap refresh ---

	public static LiteralArgumentBuilder<CommandSourceStack> nodo() {
		return Commands.literal("webmap")
				.requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))
				.then(Commands.literal("refresh").executes(ctx -> refrescarAMano(ctx.getSource())));
	}

	/** Vuelve a leer los logros de todos los jugadores (los conectados, de memoria) y publica; contesta al acabar. */
	private static int refrescarAMano(CommandSourceStack src) {
		ScheduledExecutorService ex = hilo;
		if (mapas.isEmpty() || ex == null) {
			src.sendFailure(Textos.t("heraldia.mapas_web.ninguno", String.join(", ", List.of("BlueMap", "Dynmap", "squaremap"))));
			return 0;
		}
		MinecraftServer server = src.getServer();
		Estado.Logros l = new Estado.Logros();
		Set<UUID> conectados = new HashSet<>();
		List<AdvancementHolder> propios = server.getAdvancements().getAllAdvancements().stream()
				.filter(a -> Heraldia.MOD_ID.equals(a.id().getNamespace())).toList();
		for (ServerPlayer p : server.getPlayerList().getPlayers()) {
			conectados.add(p.getUUID());
			l.jugador();
			for (AdvancementHolder a : propios) {
				AdvancementProgress pr = p.getAdvancements().getOrStartProgress(a);
				if (pr.hasProgress()) {
					l.sumar(a.id().toString(), pr.isDone(), pr.getCompletedCriteria());
				}
			}
		}
		Path dir = server.getWorldPath(LevelResource.PLAYER_ADVANCEMENTS_DIR);
		String nombres = String.join(", ", mapas.stream().map(MapaWeb::nombre).toList());
		CompletableFuture.supplyAsync(() -> {
			EstadoCommand.leerFicheros(dir, conectados, l);
			logros = l;
			return refrescar();
		}, ex).thenAcceptAsync(n -> src.sendSuccess(() -> Textos.t("heraldia.mapas_web.actualizado", n, nombres, REGISTRO.tamano()), true),
				server).exceptionally(e -> {
			LOGGER.error("Heraldia: /heraldia webmap refresh falló", e);
			return null;
		});
		return 1;
	}

	/**
	 * Lo que reciben los adaptadores: el nombre del nivel (Dynmap nombra así el Overworld), el hilo del servidor y el
	 * Overworld (BlueMap lo acepta para encontrar su mundo).
	 */
	public record Contexto(String nombreNivel, Executor hiloServidor, Object overworld) {
	}

	/** Para las pruebas: el registro en uso. */
	static Registro registro() {
		return REGISTRO;
	}
}
