package io.github.albertosa23.heraldia.maps;

import com.google.gson.JsonObject;
import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.arena.Arena;
import io.github.albertosa23.heraldia.command.State;
import io.github.albertosa23.heraldia.command.StatusCommand;
import io.github.albertosa23.heraldia.command.Texts;
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
 * estructura que empiezan en él: los de Heraldia se apuntan en el {@link Ledger} (unas búsquedas en un mapa; casi
 * siempre vacío) y la arena, de {@link Arena#center()}.</li>
 * <li>Qué sale: {@link Markers} (opciones mapas_web.*; con solo_descubiertas, lo mismo que cuenta /heraldia status).</li>
 * <li>Cuándo: al arrancar (lee el registro y los logros de los jugadores fuera del hilo), cuando alguien consigue un logro de
 * Heraldia (PlayerAdvancementsMixin), cuando aparece una estructura nueva, tras /heraldia reload y con /heraldia webmap
 * refresh. Todo el trabajo va en un hilo propio, agrupado (una actualización cada {@value #WAIT_MS} ms como mucho).</li>
 * </ul>
 */
public final class WebMaps {
	private static final Logger LOGGER = LoggerFactory.getLogger(Heraldia.MOD_ID);
	public static final String ENABLED = "mapas_web.activado", ONLY_DISCOVERED = "mapas_web.solo_descubiertas",
			LANGUAGE = "mapas_web.idioma";
	/** id del mod → adaptador (por nombre: así su clase, y la API del mapa, solo se cargan si el mod está). */
	public static final Map<String, String> ADAPTERS = adapters();
	static final long WAIT_MS = 2000;

	private static List<String> present = List.of();
	private static volatile List<WebMap> maps = List.of();
	private static final Ledger LEDGER = new Ledger();
	/** Logros de todos los jugadores; solo se tocan desde el hilo de los mapas web. */
	private static State.Achievements advancements = new State.Achievements();
	private static @Nullable ScheduledExecutorService thread;
	private static final AtomicBoolean PENDING = new AtomicBoolean();
	/** Si un mapa aún no está listo, se reintenta (cada {@value #WAIT_MS} ms) hasta este número de veces. */
	static final int MAX_RETRIES = 60;
	private static final java.util.concurrent.atomic.AtomicInteger RETRIES = new java.util.concurrent.atomic.AtomicInteger();
	private static volatile @Nullable Path file;
	private static volatile Map<String, String> familyStyle = Map.of();
	private static volatile int last;

	private WebMaps() {
	}

	private static Map<String, String> adapters() {
		Map<String, String> m = new LinkedHashMap<>();
		m.put("bluemap", WebMaps.class.getPackageName() + ".bluemap.BlueMapAdapter");
		m.put("dynmap", WebMaps.class.getPackageName() + ".dynmap.DynmapAdapter");
		m.put("squaremap", WebMaps.class.getPackageName() + ".squaremap.SquaremapAdapter");
		return Map.copyOf(m);
	}

	/** Los mods de mapa que están cargados, en orden (lógica pura). */
	public static List<String> detected(Predicate<String> loaded) {
		return ADAPTERS.keySet().stream().sorted().filter(loaded).toList();
	}

	/** Una línea en Heraldia.onInitialize. Sin mapas web cargados no registra nada. */
	public static void register() {
		present = detected(FabricLoader.getInstance()::isModLoaded);
		if (present.isEmpty()) {
			return;
		}
		LOGGER.info("Heraldia: mapas web: {}", String.join(", ", present));
		ServerChunkEvents.CHUNK_LOAD.register(WebMaps::onChunkLoad);
		ServerLifecycleEvents.SERVER_STARTED.register(WebMaps::start);
		ServerLifecycleEvents.SERVER_STOPPING.register(server -> stop());
	}

	/** ¿Hay algún mapa web en uso? */
	public static boolean inUse() {
		return !maps.isEmpty();
	}

	// --- eventos ---

	private static void start(MinecraftServer server) {
		familyStyle = styles(HeraldiaConfig.get());
		Path root = server.getWorldPath(LevelResource.ROOT);
		file = root.resolve(Ledger.FILE);
		Context ctx = new Context(server.getWorldData().getLevelName(), server, server.overworld());
		List<WebMap> loadedMaps = new ArrayList<>();
		for (String mod : present) {
			try {
				loadedMaps.add((WebMap) Class.forName(ADAPTERS.get(mod)).getConstructor(Context.class).newInstance(ctx));
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
		thread = ex;
		maps = List.copyOf(loadedMaps);
		if (loadedMaps.isEmpty()) {
			return;
		}
		Path dir = server.getWorldPath(LevelResource.PLAYER_ADVANCEMENTS_DIR);
		ex.execute(() -> {
			int readCount = LEDGER.read(root.resolve(Ledger.FILE));
			State.Achievements l = new State.Achievements();
			StatusCommand.readFiles(dir, Set.of(), l);
			advancements = l;
			LOGGER.info("Heraldia: mapas web: {} estructuras conocidas ({} del fichero), logros de {} jugadores", LEDGER.size(),
					readCount, l.players());
			refresh();
		});
	}

	private static void stop() {
		ScheduledExecutorService ex = thread;
		thread = null;
		List<WebMap> ms = maps;
		maps = List.of();
		if (ex != null) {
			ex.shutdown();
			try {
				ex.awaitTermination(10, TimeUnit.SECONDS);
			} catch (InterruptedException e) {
				Thread.currentThread().interrupt();
			}
		}
		save();
		for (WebMap m : ms) {
			try {
				m.close();
			} catch (RuntimeException | LinkageError e) {
				LOGGER.warn("Heraldia: mapas web: {} al cerrar: {}", m.name(), String.valueOf(e));
			}
		}
		advancements = new State.Achievements();
	}

	/** Hilo del servidor: los inicios de estructura de Heraldia que empiezan en este chunk. Salida temprana barata. */
	private static void onChunkLoad(ServerLevel level, LevelChunk chunk, boolean generated) {
		if (maps.isEmpty() || level.dimension() != Level.OVERWORLD) {
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
			Site s = Site.of(id.getPath(), familyStyle, c.getX(), c.getY(), c.getZ());
			if (s != null && LEDGER.add(s)) {
				schedule();
			}
		}
	}

	/**
	 * Hilo del servidor (PlayerAdvancementsMixin): un jugador acaba de conseguir un criterio de un logro de Heraldia.
	 * Se suma a los logros conocidos y se actualizan los mapas (agrupado).
	 */
	public static void onAward(ServerPlayer player, AdvancementHolder holder, String criterion) {
		ScheduledExecutorService ex = thread;
		if (maps.isEmpty() || ex == null || !Heraldia.MOD_ID.equals(holder.id().getNamespace())) {
			return;
		}
		AdvancementProgress pr = player.getAdvancements().getOrStartProgress(holder);
		String id = holder.id().toString();
		boolean done = pr.isDone();
		ex.execute(() -> advancements.add(id, done, List.of(criterion)));
		schedule();
	}

	/** Pide una actualización de los mapas (se agrupan: como mucho una cada {@value #WAIT_MS} ms). */
	public static void schedule() {
		ScheduledExecutorService ex = thread;
		if (ex == null || maps.isEmpty() || !PENDING.compareAndSet(false, true)) {
			return;
		}
		try {
			ex.schedule(() -> {
				PENDING.set(false);
				refresh();
			}, WAIT_MS, TimeUnit.MILLISECONDS);
		} catch (RuntimeException e) {
			PENDING.set(false);   // parando
		}
	}

	// --- la actualización (hilo de los mapas web) ---

	/** Opciones en uso (lee la configuración cada vez: se recargan con /heraldia reload). */
	static Markers.Options options(HeraldiaConfig cfg) {
		Set<Layer> layers = EnumSet.noneOf(Layer.class);
		for (Layer c : Layer.values()) {
			if (!cfg.has(c.option()) || cfg.getBool(c.option())) {
				layers.add(c);
			}
		}
		return new Markers.Options(cfg.getBool(ENABLED), cfg.getBool(ONLY_DISCOVERED), layers);
	}

	/** Código de idioma de los textos de los mapas: el de mapas_web.idioma o, con «auto», el de la JVM. */
	static String language(String option, Locale jvm) {
		return "auto".equals(option) ? (jvm.getLanguage() + "_" + jvm.getCountry()).toLowerCase(Locale.ROOT) : option;
	}

	/** Recalcula y publica los marcadores; devuelve cuántos hay. */
	static int refresh() {
		List<WebMap> ms = maps;
		if (ms.isEmpty()) {
			return 0;
		}
		HeraldiaConfig cfg = HeraldiaConfig.get();
		Markers.Options o = options(cfg);
		Map<String, String> texts = Texts.texts(language(cfg.has(LANGUAGE) ? cfg.getString(LANGUAGE) : "auto", Locale.getDefault()));
		BlockPos a = Arena.center();
		int[] arena = a == null ? null : new int[]{a.getX(), a.getY(), a.getZ()};
		List<MapMarker> list = Markers.build(LEDGER.all(), arena, advancements, o, texts);
		Map<Layer, List<MapMarker>> byLayer = Markers.byLayer(list, o);
		Map<Layer, String> names = Markers.layerNames(texts);
		boolean ready = true;
		for (WebMap m : ms) {
			try {
				ready &= m.publish(names, byLayer);
			} catch (RuntimeException | LinkageError e) {
				LOGGER.warn("Heraldia: mapas web: {} no aceptó los marcadores: {}", m.name(), String.valueOf(e));
			}
		}
		if (!ready && RETRIES.getAndIncrement() < MAX_RETRIES) {
			schedule();        // algún mapa arranca después que el servidor: otra vez dentro de un rato
		} else if (ready) {
			RETRIES.set(0);
		}
		if (list.size() != last) {
			LOGGER.info("Heraldia: mapas web: {} marcadores ({} estructuras conocidas)", list.size(), LEDGER.size());
			last = list.size();
		}
		save();
		return list.size();
	}

	private static void save() {
		Path f = file;
		if (f == null) {
			return;
		}
		try {
			LEDGER.save(f);
		} catch (java.io.IOException e) {
			LOGGER.warn("Heraldia: mapas web: no se pudo guardar {}: {}", f, e.getMessage());
		}
	}

	static Map<String, String> styles(HeraldiaConfig cfg) {
		Map<String, String> out = new LinkedHashMap<>();
		JsonObject styles = cfg.schema().getAsJsonObject("aldeas").getAsJsonObject("estilos");
		styles.entrySet().forEach(e -> out.put(e.getKey(), e.getValue().getAsString()));
		return Map.copyOf(out);
	}

	// --- /heraldia webmap refresh ---

	public static LiteralArgumentBuilder<CommandSourceStack> node() {
		return Commands.literal("webmap")
				.requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))
				.then(Commands.literal("refresh").executes(ctx -> refreshByHand(ctx.getSource())));
	}

	/** Vuelve a leer los logros de todos los jugadores (los conectados, de memoria) y publica; contesta al acabar. */
	private static int refreshByHand(CommandSourceStack src) {
		ScheduledExecutorService ex = thread;
		if (maps.isEmpty() || ex == null) {
			src.sendFailure(Texts.t("heraldia.mapas_web.ninguno", String.join(", ", List.of("BlueMap", "Dynmap", "squaremap"))));
			return 0;
		}
		MinecraftServer server = src.getServer();
		State.Achievements l = new State.Achievements();
		Set<UUID> online = new HashSet<>();
		List<AdvancementHolder> own = server.getAdvancements().getAllAdvancements().stream()
				.filter(a -> Heraldia.MOD_ID.equals(a.id().getNamespace())).toList();
		for (ServerPlayer p : server.getPlayerList().getPlayers()) {
			online.add(p.getUUID());
			l.player();
			for (AdvancementHolder a : own) {
				AdvancementProgress pr = p.getAdvancements().getOrStartProgress(a);
				if (pr.hasProgress()) {
					l.add(a.id().toString(), pr.isDone(), pr.getCompletedCriteria());
				}
			}
		}
		Path dir = server.getWorldPath(LevelResource.PLAYER_ADVANCEMENTS_DIR);
		String names = String.join(", ", maps.stream().map(WebMap::name).toList());
		CompletableFuture.supplyAsync(() -> {
			StatusCommand.readFiles(dir, online, l);
			advancements = l;
			return refresh();
		}, ex).thenAcceptAsync(n -> src.sendSuccess(() -> Texts.t("heraldia.mapas_web.actualizado", n, names, LEDGER.size()), true),
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
	public record Context(String levelName, Executor serverThread, Object overworld) {
	}

	/** Para las pruebas: el registro en uso. */
	static Ledger ledger() {
		return LEDGER;
	}
}
