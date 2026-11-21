package io.github.albertosa23.heraldia.welcome;

import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.quests.Data;
import io.github.albertosa23.heraldia.quests.Quests;
import io.github.albertosa23.heraldia.quests.Reputation;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.IdentityHashMap;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import net.fabricmc.fabric.api.attachment.v1.AttachmentRegistry;
import net.fabricmc.fabric.api.attachment.v1.AttachmentType;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerChunkEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.fabricmc.fabric.api.networking.v1.ServerPlayConnectionEvents;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderSet;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.Identifier;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.tags.TagKey;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.BannerBlock;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.TrapDoorBlock;
import net.minecraft.world.level.block.WallBannerBlock;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.chunk.ChunkAccess;
import net.minecraft.world.level.chunk.LevelChunk;
import net.minecraft.world.level.chunk.status.ChunkStatus;
import net.minecraft.world.level.levelgen.structure.PoolElementStructurePiece;
import net.minecraft.world.level.levelgen.structure.Structure;
import net.minecraft.world.level.levelgen.structure.StructurePiece;
import net.minecraft.world.level.levelgen.structure.StructureStart;
import net.minecraft.world.level.levelgen.structure.pools.SinglePoolElement;
import net.minecraft.world.level.levelgen.structure.templatesystem.StructurePlaceSettings;
import net.minecraft.world.level.levelgen.structure.templatesystem.StructureTemplate;
import org.jspecify.annotations.Nullable;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Reputation visible in the village (option {@code reputacion.aldea_visible}, on by default): a Heraldia village that a
 * player has helped looks different, without opening anything. It shows the best reputation any player has with it
 * ({@link Look}): flowers on the fountain when someone is known there; banners of the village's colour at the square's
 * entrances, by the job board, at the wall gates and at the watchtowers when someone is a friend; more flowers, lanterns on
 * the gates' battlements and a carpet in front of the job board for a hero. When everyone who has dealt with it is in
 * negative reputation, the watchtowers close their shutters. Vanilla blocks only, no entity, no client code.
 * <ul>
 * <li><b>Where:</b> at fixed spots of the mod's own pieces ({@link Spots}), found from the village's saved structure start
 * (also villages generated before this version).</li>
 * <li><b>Never a player's block:</b> a decoration is only put up on air and on the template's own support block, and only
 * taken down while it is exactly what was put up and nothing rests on it; every block put up is recorded with its state
 * ({@link Shown}, attachment {@code heraldia:reputacion_visible} of the overworld). A spot where something else turns up is
 * forgotten and never decorated again ({@link Spots#decide}).</li>
 * <li><b>When:</b> nothing runs per tick and there is no tick handler. A player's reputation is mirrored into the record
 * when it is saved ({@link #reputationSaved}, from {@code Quests.save}) and on joining; a village whose look changes, and a
 * village whose chunk loads with something to do, is queued, and one task on the server's own queue (scheduled only when
 * something is queued) handles up to {@link #PER_RUN} villages and schedules itself again while any are left. A village
 * nobody has helped and with nothing put up is skipped on its chunk load without any work. Only spots in loaded chunks
 * are touched; the rest when their chunk loads.</li>
 * <li><b>Reversible:</b> with the option (or {@code reputacion.activado}) off, and after {@code /heraldia reload}, each village
 * takes down what this mod put up (at once in the loaded villages, the rest as they load), and puts up nothing more.</li>
 * </ul>
 */
public final class Welcome {
	private static final Logger LOGGER = LoggerFactory.getLogger(Heraldia.MOD_ID);
	public static final String OPTION = "reputacion.aldea_visible";
	/** Villages processed in one task at most (each one is a few dozen block reads). */
	static final int PER_RUN = 4;
	private static final TagKey<Structure> VILLAGES = TagKey.create(Registries.STRUCTURE, Heraldia.id("aldeas"));
	private static final String[] WOODS = {"oak", "spruce", "birch", "jungle", "acacia", "dark_oak", "mangrove", "cherry",
			"pale_oak", "bamboo", "crimson", "warped"};

	/** Villages waiting to be reconciled (keys of {@link Reputation#key}), in arrival order. */
	private static final Set<String> PENDING = new LinkedHashSet<>();
	/** Villages whose every spot is reconciled with this look (this session): their chunk loads do nothing. */
	private static final Map<String, Look> SETTLED = new HashMap<>();
	/** The spots of each village at their world position, worked out once per session. */
	private static final Map<String, List<Resolved>> LAYOUTS = new HashMap<>();
	/** Positions of each template's blocks of each kind (template support checks). */
	private static final Map<Identifier, Map<Block, Set<BlockPos>>> TEMPLATE_BLOCKS = new HashMap<>();
	private static @Nullable Set<Structure> villageStructures;
	private static @Nullable Boolean lastEnabled;
	/** A task to drain the queue is already on the server's queue. */
	private static boolean scheduled;

	private Welcome() {
	}

	/** The attachment, kept apart so the tests register nothing when the class loads. */
	static final class Type {
		static final AttachmentType<Shown> SHOWN = AttachmentRegistry.create(Heraldia.id("reputacion_visible"),
				b -> b.persistent(Shown.CODEC));

		private Type() {
		}
	}

	/** A spot of one village: world position, the block that goes there (null: no material), its support and the template's block there. */
	record Resolved(BlockPos pos, Spots.Spot spot, String style, net.minecraft.world.level.block.Rotation rotation, BlockPos support,
			@Nullable Identifier template) {
	}

	/** Each style's materials, read from its templates the first time something of that style is put up (this session). */
	private static final Map<String, Materials> MATERIALS = new HashMap<>();

	/** The block a spot gets, in its village's materials and rotated with its piece (null: that material does not exist). */
	private static @Nullable BlockState stateOf(ServerLevel level, Resolved r) {
		BlockState st = MATERIALS.computeIfAbsent(r.style(), style -> materials(level, style)).state(r.spot(), r.style());
		return st == null ? null : st.rotate(r.rotation());
	}

	/** One line in Heraldia.onInitialize. */
	public static void register() {
		Type.SHOWN.identifier();   // registers the attachment at startup: otherwise the saved record is dropped when the world loads
		ServerChunkEvents.CHUNK_LOAD.register(Welcome::onChunkLoad);
		// on the server's task queue, as Guide does: Carpet (fake players) loads the player's data after JOIN
		ServerPlayConnectionEvents.JOIN.register((handler, sender, server) -> server.schedule(server.wrapRunnable(() -> {
			if (!handler.player.hasDisconnected()) {
				reputationSaved(handler.player, Quests.data(handler.player));
			}
		})));
		ServerLifecycleEvents.SERVER_STARTED.register(server -> lastEnabled = enabled());   // what a later reload is compared with
		ServerLifecycleEvents.SERVER_STOPPED.register(server -> {
			PENDING.clear();
			SETTLED.clear();
			LAYOUTS.clear();
			MATERIALS.clear();
			TEMPLATE_BLOCKS.clear();
			villageStructures = null;
			lastEnabled = null;
			scheduled = false;
		});
	}

	static boolean enabled() {
		HeraldiaConfig cfg = HeraldiaConfig.get();
		return cfg.getBool(OPTION) && cfg.getBool(Quests.REPUTATION);
	}

	static Shown shown(MinecraftServer server) {
		return server.overworld().getAttachedOrElse(Type.SHOWN, Shown.EMPTY);
	}

	/** The look a village should have now. */
	static Look look(Shown shown, String key) {
		return Look.of(shown.village(key).points().values(), enabled());
	}

	/**
	 * A player's reputation data was saved (or they joined): their points are mirrored into the record and each village
	 * whose look changes because of it is queued. On the server thread; a map comparison when nothing changed.
	 */
	public static void reputationSaved(Player p, Data d) {
		if (!(p instanceof ServerPlayer sp) || sp.level().getServer() == null || d.reputation().isEmpty()) {
			return;
		}
		MinecraftServer server = sp.level().getServer();
		checkOption(server);
		Shown before = shown(server);
		List<String> changed = new ArrayList<>();
		Shown after = before.sync(sp.getUUID().toString(), d.reputation(), changed);
		if (changed.isEmpty()) {
			return;
		}
		server.overworld().setAttached(Type.SHOWN, after);
		for (String key : changed) {
			if (look(before, key) != look(after, key)) {
				SETTLED.remove(key);
				queue(server, key);
			}
		}
	}

	/** After {@code /heraldia reload} (ReloadCommand.apply): if the option or reputation was switched, every recorded village is looked at again now. */
	public static void reloaded(MinecraftServer server) {
		checkOption(server);
	}

	/** /heraldia reload may switch the option: every village with something recorded is looked at again. */
	private static void checkOption(MinecraftServer server) {
		boolean e = enabled();
		if (lastEnabled != null && e != lastEnabled) {
			SETTLED.clear();
			lastEnabled = e;
			shown(server).villages().keySet().forEach(k -> queue(server, k));
			LOGGER.info("Heraldia: village look: option {}: {} villages to look at again", e ? "on" : "off", PENDING.size());
		}
		lastEnabled = e;
	}

	/** Queues a village and, if none is on the way, schedules the task that drains the queue (on the server thread, next tick). */
	private static void queue(MinecraftServer server, String key) {
		PENDING.add(key);
		if (!scheduled) {
			scheduled = true;
			server.schedule(server.wrapRunnable(() -> {
				scheduled = false;
				run(server.overworld());
				if (!PENDING.isEmpty()) {
					queue(server, PENDING.iterator().next());
				}
			}));
		}
	}

	/** The structures of the {@code #heraldia:aldeas} tag (worked out once per session). */
	private static Set<Structure> villageStructures(ServerLevel level) {
		if (villageStructures == null) {
			Set<Structure> s = Collections.newSetFromMap(new IdentityHashMap<>());
			Optional<HolderSet.Named<Structure>> set = level.registryAccess().lookupOrThrow(Registries.STRUCTURE).get(VILLAGES);
			set.ifPresent(h -> h.forEach(holder -> s.add(holder.value())));
			villageStructures = s;
		}
		return villageStructures;
	}

	/** A chunk of a Heraldia village loads: the village is queued only if it has something to do. */
	private static void onChunkLoad(ServerLevel level, LevelChunk chunk, boolean generated) {
		if (level.dimension() != Level.OVERWORLD) {
			return;
		}
		Shown shown = level.getAttached(Type.SHOWN);
		if (shown == null || shown.villages().isEmpty()) {
			return;    // almost always: nobody has reputation anywhere and nothing is put up
		}
		Map<Structure, it.unimi.dsi.fastutil.longs.LongSet> refs = chunk.getAllReferences();
		if (refs.isEmpty()) {
			return;
		}
		checkOption(level.getServer());
		Set<Structure> villages = villageStructures(level);
		for (Map.Entry<Structure, it.unimi.dsi.fastutil.longs.LongSet> e : refs.entrySet()) {
			if (!villages.contains(e.getKey())) {
				continue;
			}
			for (long start : e.getValue()) {
				String key = Reputation.key(ChunkPos.getX(start), ChunkPos.getZ(start));
				Shown.Village v = shown.village(key);
				Look look = look(shown, key);
				if (SETTLED.get(key) == look || (look == Look.PLAIN && v.placed().isEmpty()) || !spotsIn(key, chunk.getPos())) {
					continue;
				}
				queue(level.getServer(), key);
			}
		}
	}

	/** Does the chunk hold a spot of that village? True while its layout is not known yet (it is worked out on its first pass). */
	private static boolean spotsIn(String key, ChunkPos chunk) {
		List<Resolved> layout = LAYOUTS.get(key);
		if (layout == null) {
			return true;
		}
		for (Resolved r : layout) {
			if (r.pos().getX() >> 4 == chunk.x() && r.pos().getZ() >> 4 == chunk.z()) {
				return true;
			}
		}
		return false;
	}

	/** Processes a few queued villages. */
	private static void run(ServerLevel level) {
		int n = 0;
		for (Iterator<String> it = PENDING.iterator(); it.hasNext() && n < PER_RUN; n++) {
			String key = it.next();
			it.remove();
			try {
				reconcile(level, key);
			} catch (RuntimeException ex) {
				LOGGER.warn("Heraldia: village look: {} could not be updated", key, ex);
			}
		}
	}

	/** The start of the Heraldia village of that key, only if its start chunk is in memory (never loads one), or null. */
	private static @Nullable StructureStart start(ServerLevel level, String key) {
		int[] c = Reputation.chunk(key);
		if (c == null) {
			return null;
		}
		ChunkAccess chunk = level.getChunkSource().getChunk(c[0], c[1], ChunkStatus.STRUCTURE_STARTS, false);
		if (chunk == null) {
			return null;    // when that chunk loads, its own reference queues the village again
		}
		Set<Structure> villages = villageStructures(level);
		for (Map.Entry<Structure, StructureStart> e : chunk.getAllStarts().entrySet()) {
			if (villages.contains(e.getKey()) && e.getValue().isValid()) {
				return e.getValue();
			}
		}
		return null;
	}

	/** Brings the village's spots in loaded chunks in line with its look (see {@link Spots#decide}). */
	static void reconcile(ServerLevel level, String key) {
		long t0 = System.nanoTime();
		StructureStart start = start(level, key);
		if (start == null) {
			return;
		}
		Shown shown = shown(level.getServer());
		Shown.Village v = shown.village(key);
		Look look = look(shown, key);
		List<Resolved> layout = LAYOUTS.computeIfAbsent(key, k -> layout(level, start));
		Map<Long, BlockState> added = new LinkedHashMap<>();
		List<Long> removed = new ArrayList<>(), declined = new ArrayList<>();
		boolean complete = true;
		for (Resolved r : layout) {
			LevelChunk chunk = level.getChunkSource().getChunkNow(r.pos().getX() >> 4, r.pos().getZ() >> 4);
			if (chunk == null) {
				complete = false;
				continue;
			}
			long lp = r.pos().asLong();
			BlockState placed = v.placedAt(lp);
			BlockState current = level.getBlockState(r.pos());
			boolean wanted = r.spot().shownIn(look);
			// the materials and the support are only looked at when something could really go up here
			BlockState state = wanted && placed == null && current.isAir() && !v.isDeclined(lp) ? stateOf(level, r) : null;
			boolean support = state != null && supported(level, r, state);
			boolean free = level.getBlockState(r.pos().above()).isAir();
			switch (Spots.decide(wanted, placed, current, current.isAir(), support, v.isDeclined(lp), free)) {
				case PLACE -> {
					level.setBlock(r.pos(), state, Block.UPDATE_ALL);
					added.put(lp, level.getBlockState(r.pos()));
				}
				case REMOVE -> {
					level.setBlock(r.pos(), Blocks.AIR.defaultBlockState(), Block.UPDATE_ALL);
					removed.add(lp);
				}
				case DECLINE -> declined.add(lp);
				case KEEP, NONE -> {
				}
			}
		}
		Shown.Village after = v.with(added, removed, declined);
		if (after != v) {
			level.setAttached(Type.SHOWN, shown.with(key, after));
		}
		if (complete) {
			SETTLED.put(key, look);
		} else {
			SETTLED.remove(key);
		}
		if (!added.isEmpty() || !removed.isEmpty() || !declined.isEmpty()) {
			LOGGER.info("Heraldia: village look: {} {}: placed {}, removed {}, left alone {} ({} spots, {} µs){}", key, look.id(),
					added.size(), removed.size(), declined.size(), layout.size(), (System.nanoTime() - t0) / 1000,
					complete ? "" : " (some chunks not loaded yet)");
		}
	}

	/** Is the spot's support in place: the template's own block (or, for the board, a sturdy top face), and would it stay? */
	private static boolean supported(ServerLevel level, Resolved r, BlockState state) {
		BlockState support = level.getBlockState(r.support());
		if (r.template() != null) {
			BlockPos local = new BlockPos(r.spot().sx(), r.spot().sy(), r.spot().sz());
			boolean own = templateBlocks(level, r.template(), support.getBlock()).contains(local);
			if (!own) {
				// the village's processor weathers a share of the stone as it generates: mossy or cracked, it is still the wall
				for (String fresh : Spots.fresh(BuiltInRegistries.BLOCK.getKey(support.getBlock()).toString())) {
					Optional<Block> b = BuiltInRegistries.BLOCK.getOptional(Identifier.parse(fresh));
					own |= b.isPresent() && templateBlocks(level, r.template(), b.get()).contains(local);
				}
			}
			if (!own) {
				return false;
			}
		} else if (!support.isFaceSturdy(level, r.support(), Direction.UP)) {
			return false;
		}
		return state.canSurvive(level, r.pos());
	}

	/** The local positions of a template's blocks of one kind (cached for the session). */
	private static Set<BlockPos> templateBlocks(ServerLevel level, Identifier template, Block block) {
		return TEMPLATE_BLOCKS.computeIfAbsent(template, t -> new HashMap<>()).computeIfAbsent(block, b -> {
			Set<BlockPos> s = new java.util.HashSet<>();
			level.getStructureTemplateManager().get(template).ifPresent(t -> {
				for (StructureTemplate.StructureBlockInfo info : t.filterBlocks(BlockPos.ZERO, new StructurePlaceSettings(), b, false)) {
					s.add(info.pos());
				}
			});
			return s;
		});
	}

	/** Every spot of the village's pieces at its world position (the block that goes there is worked out only when it goes up). */
	static List<Resolved> layout(ServerLevel level, StructureStart start) {
		Identifier id = level.registryAccess().lookupOrThrow(Registries.STRUCTURE).getKey(start.getStructure());
		String style = id == null ? "" : id.getPath();
		if (style.endsWith("_grande")) {
			style = style.substring(0, style.length() - "_grande".length());
		}
		List<Resolved> l = new ArrayList<>();
		for (StructurePiece piece : start.getPieces()) {
			if (!(piece instanceof PoolElementStructurePiece pe) || !(pe.getElement() instanceof SinglePoolElement e)) {
				continue;
			}
			Identifier template = e.getTemplateLocation();
			Spots.Piece kind = Spots.Piece.of(template.getPath());
			if (kind == null) {
				continue;
			}
			StructurePlaceSettings settings = new StructurePlaceSettings().setRotation(pe.getRotation());
			for (Spots.Spot s : Spots.of(kind)) {
				BlockPos pos = StructureTemplate.calculateRelativePosition(settings, new BlockPos(s.x(), s.y(), s.z())).offset(pe.getPosition());
				BlockPos support = StructureTemplate.calculateRelativePosition(settings, new BlockPos(s.sx(), s.sy(), s.sz())).offset(pe.getPosition());
				l.add(new Resolved(pos, s, style, pe.getRotation(), support, s.templateSupport() ? template : null));
			}
		}
		return List.copyOf(l);
	}

	/** The materials of a style, read from its own templates: the banner colour and lantern of its wall gate, the wood of its square's fences. */
	record Materials(String colour, Block lantern, String wood) {
		@Nullable BlockState state(Spots.Spot s, String style) {
			return switch (s.item()) {
				case WALL_BANNER -> block(colour + "_wall_banner").map(b -> b.defaultBlockState().setValue(WallBannerBlock.FACING, direction(s.dir()))).orElse(null);
				case BANNER -> block(colour + "_banner").map(b -> b.defaultBlockState().setValue(BannerBlock.ROTATION, s.dir())).orElse(null);
				case CARPET -> block(colour + "_carpet").map(Block::defaultBlockState).orElse(null);
				case POT -> block(Spots.flower(style, s.dir())).map(Block::defaultBlockState).orElse(null);
				case LANTERN -> lantern.defaultBlockState();
				case SHUTTER -> block(wood + "_trapdoor").map(b -> b.defaultBlockState().setValue(TrapDoorBlock.FACING, direction(s.dir()))
						.setValue(TrapDoorBlock.OPEN, true)).orElse(null);
			};
		}
	}

	static Direction direction(int dir) {
		return switch (dir) {
			case Spots.EAST -> Direction.EAST;
			case Spots.SOUTH -> Direction.SOUTH;
			case Spots.WEST -> Direction.WEST;
			default -> Direction.NORTH;
		};
	}

	private static Optional<Block> block(String path) {
		return BuiltInRegistries.BLOCK.getOptional(Identifier.withDefaultNamespace(path));
	}

	private static Materials materials(ServerLevel level, String style) {
		Identifier gate = Heraldia.id(style + "/terminators/gate"), plaza = Heraldia.id(style + "/plaza/std");
		String colour = "white";
		for (net.minecraft.world.item.DyeColor c : net.minecraft.world.item.DyeColor.values()) {
			Optional<Block> b = block(c.getSerializedName() + "_wall_banner");
			if (b.isPresent() && !templateBlocks(level, gate, b.get()).isEmpty()) {
				colour = c.getSerializedName();
				break;
			}
		}
		Block lantern = templateBlocks(level, gate, Blocks.SOUL_LANTERN).isEmpty() ? Blocks.LANTERN : Blocks.SOUL_LANTERN;
		String wood = "spruce";
		for (String w : WOODS) {
			Optional<Block> b = block(w + "_fence");
			if (b.isPresent() && !templateBlocks(level, plaza, b.get()).isEmpty()) {
				wood = w;
				break;
			}
		}
		return new Materials(colour, lantern, wood);
	}
}
