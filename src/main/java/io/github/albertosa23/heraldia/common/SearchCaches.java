package io.github.albertosa23.heraldia.common;

import com.mojang.serialization.JsonOps;
import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.config.ProfileAdvice;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.DigestInputStream;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.stream.Stream;
import net.fabricmc.fabric.api.attachment.v1.AttachmentRegistry;
import net.fabricmc.fabric.api.attachment.v1.AttachmentType;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.fabricmc.loader.api.FabricLoader;
import net.fabricmc.loader.api.ModContainer;
import net.minecraft.core.Holder;
import net.minecraft.core.Registry;
import net.minecraft.core.RegistryAccess;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.Identifier;
import net.minecraft.resources.RegistryOps;
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.util.Util;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.levelgen.structure.Structure;
import net.minecraft.world.level.levelgen.structure.StructureSet;
import net.minecraft.world.level.storage.LevelResource;
import org.jspecify.annotations.Nullable;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * The world's search memory ({@link SearchCache}) in the game: one per server, saved in the main world (attachment
 * heraldia:busquedas) and used by /locate, the treasure maps (cartographers and chests), the Chronicle folios and
 * /heraldia info nearby, which all ask the same expensive question about the same cells (would this structure start
 * here? the biome, the terrain of the hillside or the shore and Heraldia's placement rules). Measured with the same
 * world: the mines' /locate from (8000, -8000) took 1.1 s again after every restart; with this memory, what was already
 * asked is answered without computing it (see docs/CONFIGURATION.md, "Search memory").
 * <p>When the server starts, the stamp (what decides the answers: seed, the generation options in use, the same ones as the
 * seam record heraldia:generacion_mundo, mods and their versions, datapacks, the .jar's content and the structures and
 * structure_sets registered) is computed on another thread; until it is ready nothing is served or stored (the searches
 * compute everything, as before). A saved memory with another stamp is discarded and the log says so. It is written
 * with the world (BEFORE_SAVE), only if something changed. Only Heraldia's structures.
 */
public final class SearchCaches {
	private static final Logger LOGGER = LoggerFactory.getLogger(Heraldia.MOD_ID);
	/** Kinds of answer (part of the key): a structure's prediction, a structure_set's (packed) and info's first viable. */
	public static final String PREDICTION = "p", SET_PREDICTION = "s", FIRST_VIABLE = "v";
	private static volatile @Nullable SearchCache actual;
	/** Heraldia structure → its structure_set and place in it (sets of at most SearchCache.SLOTS structures). */
	private static volatile Map<Identifier, Slot> slots = Map.of();

	/** Where a structure's prediction goes: packed with those of its structure_set, which share the candidate chunk. */
	record Slot(Identifier set, int index) {
	}
	private static volatile @Nullable CompletableFuture<String> jarHash;

	private SearchCaches() {
	}

	/** The attachment, apart so the tests register nothing when the class loads. */
	static final class Type {
		static final AttachmentType<SearchCache.Saved> SAVED = AttachmentRegistry.create(Heraldia.id("busquedas"),
				b -> b.persistent(SearchCache.Saved.CODEC));

		private Type() {
		}
	}

	public static void register() {
		Type.SAVED.identifier();
		// the .jar's hash (about 13 MB) on another thread from the start: it does not depend on the world
		jarHash = CompletableFuture.supplyAsync(SearchCaches::ownJarHash, Util.backgroundExecutor());
		ServerLifecycleEvents.SERVER_STARTED.register(SearchCaches::onStart);
		ServerLifecycleEvents.BEFORE_SAVE.register((server, flush, force) -> save(server));
		ServerLifecycleEvents.SERVER_STOPPED.register(server -> {
			SearchCache c = actual;
			actual = null;
			if (c != null && c.counts()[0] + c.counts()[1] > 0) {
				LOGGER.info("Heraldia: búsquedas: {} respuestas servidas de la memoria y {} calculadas en esta sesión; {} guardadas",
						c.counts()[0], c.counts()[1], c.size());
			}
		});
	}

	private static void onStart(MinecraftServer server) {
		actual = null;
		slots = Map.of();
		ServerLevel ow = server.overworld();
		SearchCache.Saved saved = ow.getAttached(Type.SAVED);
		RegistryAccess access = server.registryAccess();
		List<String> fixed = fixedParts(server);
		CompletableFuture<String> jar = jarHash;
		record Ready(String stamp, Map<Identifier, Slot> slots) {
		}
		CompletableFuture.supplyAsync(() -> {
			List<String> parts = new ArrayList<>(fixed);
			parts.add("jar=" + (jar == null ? "?" : jar.join()));
			parts.add("registros=" + registries(access));
			return new Ready(SearchCache.stamp(parts), slots(access));
		}, Util.backgroundExecutor()).thenAcceptAsync(ready -> {
			String stamp = ready.stamp();
			if (server.overworld() != ow || !server.isRunning()) {
				return;                                    // another world or stopping: this one is no longer used
			}
			SearchCache c = SearchCache.load(saved, stamp);
			if (saved != null && !SearchCache.compatible(saved, stamp)) {
				LOGGER.info("Heraldia: búsquedas: la memoria guardada ({} respuestas) es de otra configuración, mods o versión: se descarta",
						saved.size());
				c.forget();                                // the next save overwrites the old one
			} else {
				LOGGER.info("Heraldia: búsquedas: {} respuestas guardadas en la memoria", c.size());
			}
			slots = ready.slots();
			actual = c;
		}, server).exceptionally(e -> {
			LOGGER.warn("Heraldia: búsquedas: sin memoria en esta sesión ({})", e.toString());
			return null;
		});
	}

	/** On every save of the world, if something changed. */
	private static void save(MinecraftServer server) {
		SearchCache c = actual;
		if (c != null && c.dirty()) {
			server.overworld().setAttached(Type.SAVED, c.save());
		}
	}

	/** The parts of the stamp that are read on the server thread (cheap). */
	private static List<String> fixedParts(MinecraftServer server) {
		List<String> parts = new ArrayList<>();
		parts.add("formato=" + SearchCache.FORMAT);
		parts.add("semilla=" + server.overworld().getSeed());
		parts.addAll(optionParts(HeraldiaConfig.get()));
		FabricLoader.getInstance().getAllMods().stream()
				.map(m -> m.getMetadata().getId() + "@" + m.getMetadata().getVersion().getFriendlyString()).sorted()
				.forEach(m -> parts.add("mod " + m));
		server.getPackRepository().getSelectedIds().forEach(p -> parts.add("pack " + p));
		parts.add("datapacks=" + datapacksFolder(server.getWorldPath(LevelResource.DATAPACK_DIR)));
		return parts;
	}

	/**
	 * The generation options of the stamp: the same ones as the seam record (attachment heraldia:generacion_mundo), with
	 * their values in use, so one that changes, also because its default changed (a value not written in the file), changes
	 * the stamp. Public for the tests.
	 */
	public static List<String> optionParts(HeraldiaConfig cfg) {
		List<String> parts = new ArrayList<>();
		ProfileAdvice.fingerprint(cfg.values(), HeraldiaConfig.profiles().generation()).forEach((k, v) -> parts.add("opcion " + k + "=" + v));
		return parts;
	}

	/** The world's datapacks folder: every file with its size and date (an edited datapack keeps its name). */
	static String datapacksFolder(Path dir) {
		if (!Files.isDirectory(dir)) {
			return "";
		}
		StringBuilder sb = new StringBuilder();
		try (Stream<Path> s = Files.walk(dir)) {
			s.filter(Files::isRegularFile).sorted(Comparator.comparing(Path::toString)).forEach(p -> {
				try {
					sb.append(dir.relativize(p)).append(':').append(Files.size(p)).append(':').append(Files.getLastModifiedTime(p).toMillis()).append(';');
				} catch (IOException e) {
					sb.append(p.getFileName()).append(":?;");
				}
			});
		} catch (IOException e) {
			return "?";
		}
		return sb.toString();
	}

	/**
	 * The structures and structure_sets registered, as data (another datapack or mod that changes a grid, a structure or the
	 * biomes of its tag changes this), with each structure's biomes resolved.
	 */
	private static String registries(RegistryAccess access) {
		RegistryOps<com.google.gson.JsonElement> ops = access.createSerializationContext(JsonOps.INSTANCE);
		StringBuilder sb = new StringBuilder();
		Registry<StructureSet> sets = access.lookupOrThrow(Registries.STRUCTURE_SET);
		sets.keySet().stream().sorted(Comparator.comparing(Identifier::toString)).forEach(id -> sb.append(id).append('=')
				.append(encode(StructureSet.DIRECT_CODEC, ops, sets.getValue(id))).append('\n'));
		Registry<Structure> structures = access.lookupOrThrow(Registries.STRUCTURE);
		structures.keySet().stream().sorted(Comparator.comparing(Identifier::toString)).forEach(id -> {
			Structure st = structures.getValue(id);
			sb.append(id).append('=').append(encode(Structure.DIRECT_CODEC, ops, st)).append(" biomas=");
			st.biomes().stream().map(h -> h.unwrapKey().map(k -> k.identifier().toString()).orElse("?")).sorted().forEach(b -> sb.append(b).append(','));
			sb.append('\n');
		});
		return SearchCache.stamp(List.of(sb.toString()));
	}

	/**
	 * The slot of each Heraldia structure in its structure_set (the first one that has it), for the sets of at most
	 * {@link SearchCache#SLOTS} structures; the order is the registry's, which is in the stamp.
	 */
	static Map<Identifier, Slot> slots(RegistryAccess access) {
		Map<Identifier, Slot> out = new HashMap<>();
		Registry<StructureSet> sets = access.lookupOrThrow(Registries.STRUCTURE_SET);
		sets.keySet().stream().sorted(Comparator.comparing(Identifier::toString)).forEach(id -> {
			StructureSet set = sets.getValue(id);
			if (set == null || set.structures().size() > SearchCache.SLOTS) {
				return;
			}
			for (int i = 0; i < set.structures().size(); i++) {
				Identifier st = set.structures().get(i).structure().unwrapKey().map(ResourceKey::identifier).orElse(null);
				if (kept(st)) {
					out.putIfAbsent(st, new Slot(id, i));
				}
			}
		});
		return Map.copyOf(out);
	}

	private static <T> String encode(com.mojang.serialization.Codec<T> codec, RegistryOps<com.google.gson.JsonElement> ops, @Nullable T value) {
		if (value == null) {
			return "null";
		}
		try {
			return codec.encodeStart(ops, value).result().map(Object::toString).orElse(value.getClass().getName());
		} catch (RuntimeException e) {
			return value.getClass().getName();                // a mod's structure that does not encode: at least its type
		}
	}

	/** SHA-256 of Heraldia's .jar (of its files if it is a folder, in development: then its version). */
	private static String ownJarHash() {
		ModContainer mod = FabricLoader.getInstance().getModContainer(Heraldia.MOD_ID).orElse(null);
		if (mod == null) {
			return "?";
		}
		StringBuilder sb = new StringBuilder();
		for (Path p : mod.getOrigin().getPaths()) {
			if (!Files.isRegularFile(p)) {
				sb.append(mod.getMetadata().getVersion().getFriendlyString()).append(';');
				continue;
			}
			try (InputStream in = new DigestInputStream(Files.newInputStream(p), MessageDigest.getInstance("SHA-256"))) {
				in.transferTo(java.io.OutputStream.nullOutputStream());
				sb.append(HexFormat.of().formatHex(((DigestInputStream) in).getMessageDigest().digest())).append(';');
			} catch (IOException | java.security.NoSuchAlgorithmException e) {
				sb.append("?;");
			}
		}
		return sb.toString();
	}

	// --- what the searches use ---

	/** Key of an answer: dimension, kind and Heraldia structure. */
	static String key(ResourceKey<Level> dimension, String kind, Identifier structure) {
		return dimension.identifier() + "|" + kind + "|" + structure;
	}

	/** Key prefix of the grids' biome candidates (config/GridPlacement: one per cell, the overworld's). */
	public static final String GRID = "rejilla|";

	/** The stored answer for a raw key (the grids'), or {@link SearchCache#MISSING}. */
	public static int get(String key, int x, int z) {
		SearchCache c = actual;
		return c == null ? SearchCache.MISSING : c.get(key, x, z);
	}

	/** Stores an answer for a raw key (nothing without memory yet). */
	public static void put(String key, int x, int z, int value) {
		SearchCache c = actual;
		if (c != null) {
			c.put(key, x, z, value);
		}
	}

	/** Is this one of the structures whose answers are kept? (Only Heraldia's.) */
	public static boolean kept(@Nullable Identifier structure) {
		return structure != null && Heraldia.MOD_ID.equals(structure.getNamespace());
	}

	/** The stored answer, or {@link SearchCache#MISSING} (also without memory yet or for a structure not kept). */
	public static int get(ResourceKey<Level> dimension, String kind, @Nullable Identifier structure, int chunkX, int chunkZ) {
		SearchCache c = actual;
		return c == null || !kept(structure) ? SearchCache.MISSING : c.get(key(dimension, kind, structure), chunkX, chunkZ);
	}

	/** Stores an answer (nothing without memory yet or for a structure not kept). */
	public static void put(ResourceKey<Level> dimension, String kind, @Nullable Identifier structure, int chunkX, int chunkZ, int value) {
		SearchCache c = actual;
		if (c != null && kept(structure)) {
			c.put(key(dimension, kind, structure), chunkX, chunkZ, value);
		}
	}

	/** The stored prediction of a structure in that chunk (1 yes, 0 no) or {@link SearchCache#MISSING}. */
	public static int prediction(ResourceKey<Level> dimension, @Nullable Identifier structure, int chunkX, int chunkZ) {
		SearchCache c = actual;
		if (c == null || !kept(structure)) {
			return SearchCache.MISSING;
		}
		Slot sl = slots.get(structure);
		return sl == null ? c.get(key(dimension, PREDICTION, structure), chunkX, chunkZ)
				: c.getSlot(key(dimension, SET_PREDICTION, sl.set()), chunkX, chunkZ, sl.index());
	}

	/** Stores the prediction of a structure in that chunk. */
	public static void prediction(ResourceKey<Level> dimension, @Nullable Identifier structure, int chunkX, int chunkZ, boolean value) {
		SearchCache c = actual;
		if (c == null || !kept(structure)) {
			return;
		}
		Slot sl = slots.get(structure);
		if (sl == null) {
			c.put(key(dimension, PREDICTION, structure), chunkX, chunkZ, value ? 1 : 0);
		} else {
			c.putSlot(key(dimension, SET_PREDICTION, sl.set()), chunkX, chunkZ, sl.index(), value);
		}
	}

	/** The same as {@link #prediction(ResourceKey, Identifier, int, int)} without counting it as used (to skip precomputing it). */
	public static int peekPrediction(ResourceKey<Level> dimension, Holder<Structure> structure, int chunkX, int chunkZ) {
		SearchCache c = actual;
		Identifier id = structure.unwrapKey().map(ResourceKey::identifier).orElse(null);
		if (c == null || !kept(id)) {
			return SearchCache.MISSING;
		}
		Slot sl = slots.get(id);
		return sl == null ? c.peek(key(dimension, PREDICTION, id), chunkX, chunkZ)
				: c.peekSlot(key(dimension, SET_PREDICTION, sl.set()), chunkX, chunkZ, sl.index());
	}
}
