package io.github.albertosa23.heraldia.events;

import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.command.Texts;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.dialogue.Lines;
import io.github.albertosa23.heraldia.quests.Quests;
import io.github.albertosa23.heraldia.quests.Reputation;
import it.unimi.dsi.fastutil.ints.IntList;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ThreadLocalRandom;
import net.fabricmc.fabric.api.attachment.v1.AttachmentRegistry;
import net.fabricmc.fabric.api.attachment.v1.AttachmentType;
import net.fabricmc.fabric.api.entity.event.v1.ServerLivingEntityEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerChunkEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerEntityEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.fabricmc.fabric.api.event.player.PlayerBlockBreakEvents;
import net.fabricmc.fabric.api.event.player.UseEntityCallback;
import net.minecraft.ChatFormatting;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.EntityArgument;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.Holder;
import net.minecraft.core.HolderSet;
import net.minecraft.core.component.DataComponents;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.network.protocol.game.ClientboundSoundPacket;
import net.minecraft.resources.Identifier;
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.tags.ItemTags;
import net.minecraft.tags.TagKey;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntitySpawnReason;
import net.minecraft.world.entity.EntityTypes;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.npc.villager.Villager;
import net.minecraft.world.entity.npc.villager.VillagerData;
import net.minecraft.world.entity.npc.villager.VillagerProfession;
import net.minecraft.world.entity.npc.villager.VillagerType;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.entity.projectile.FireworkRocketEntity;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.component.FireworkExplosion;
import net.minecraft.world.item.component.Fireworks;
import net.minecraft.world.item.trading.ItemCost;
import net.minecraft.world.item.trading.MerchantOffer;
import net.minecraft.world.item.trading.MerchantOffers;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.RotatedPillarBlock;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;
import net.minecraft.world.level.block.state.properties.Property;
import net.minecraft.world.level.chunk.LevelChunk;
import net.minecraft.world.level.levelgen.structure.BoundingBox;
import net.minecraft.world.level.levelgen.structure.PoolElementStructurePiece;
import net.minecraft.world.level.levelgen.structure.Structure;
import net.minecraft.world.level.levelgen.structure.StructurePiece;
import net.minecraft.world.level.levelgen.structure.StructureStart;
import net.minecraft.world.level.levelgen.structure.pools.SinglePoolElement;
import net.minecraft.world.phys.AABB;
import org.jspecify.annotations.Nullable;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Things happen in the villages (option {@code eventos.activado}, on by default; off in the light profile): now and then,
 * when a player is in a Heraldia village, its square holds a market day, a wedding, a funeral or a festival
 * ({@link Kind}) for a few minutes, and then everything goes. This class is the part that touches the game; where things
 * go is {@link Layout}, when things happen is {@link Rules}, what is saved is {@link Record}.
 * <ul>
 * <li><b>When:</b> a draw every 30 s ({@link Rules#DRAW_TICKS}) with players in the overworld: for each village one of
 * them is in (and at least {@link Rules#MIN_DISTANCE} blocks from its square, so it is not laid out in their face), with
 * {@code eventos.frecuencia} % and the village rested {@code eventos.espera_minutos} since its last one, an event that
 * fits the hour and the weather starts. One per village, {@code eventos.max_activos} on the server.</li>
 * <li><b>What:</b> vanilla blocks laid out in one bay of the square (two for the market) and up to
 * {@link Rules#MAX_ENTITIES} entities: villagers without AI (they stand, turn, dance and speak; no brain, no
 * pathfinding, no beds or job sites taken) and a few fireworks. The figures speak through the villagers' line system
 * (pools {@code event.<kind>.*}); the market's traders and the festival's host trade; the couple and the widow take
 * gifts; the band takes requests. Taking part gives a little reputation with the village, once per event.</li>
 * <li><b>Never a player's block:</b> a prop is only put up on air, on a solid floor, in a cell the plan has checked is
 * free (no entity, not the job board's, not a spot of the reputation decorations), and recorded first
 * ({@link Record}); at the end only what is still exactly what was put up, with nothing on top, is taken down. The props
 * cannot be broken by survival players while the event runs.</li>
 * <li><b>Nothing stays:</b> when an event ends its figures are removed (and any entity with its tag in its area); if
 * the server stops, every event ends first; an event entity that loads with no event running is removed
 * ({@code ENTITY_LOAD}); a recorded block whose chunk was not loaded is taken down when it loads.</li>
 * <li><b>Cost:</b> with no event running, the tick handler is a modulo; the draw, a structure lookup per player every
 * 30 s. A running event is updated once a second; a festival plays its tune every {@link Rules#MUSIC_TICKS} ticks.</li>
 * </ul>
 * The {@code eventos.*} options are read on each use: they reload with /heraldia reload (turned off, the running events end).
 */
public final class VillageEvents {
	private static final Logger LOGGER = LoggerFactory.getLogger(Heraldia.MOD_ID);
	public static final String ENABLED = "eventos.activado", FREQUENCY = "eventos.frecuencia", WAIT = "eventos.espera_minutos",
			MAX_ACTIVE = "eventos.max_activos";
	static final String K = "heraldia.eventos.";
	private static final TagKey<Structure> VILLAGES = TagKey.create(Registries.STRUCTURE, Heraldia.id("aldeas"));

	/** The running events, by village key ({@link Reputation#key}). */
	private static final Map<String, Event> ACTIVE = new LinkedHashMap<>();
	/** Entity → its event: tagged entities missing from here are leftovers. */
	private static final Map<UUID, Event> BY_ENTITY = new HashMap<>();
	/** Positions of the props of running events (they cannot be broken). */
	private static final Map<Long, Event> PROPS = new HashMap<>();
	/** Recorded blocks of no running event, by chunk: taken down when their chunk is loaded. */
	private static final Map<Long, List<Record.Placed>> PENDING = new HashMap<>();
	private static @Nullable HolderSet<Structure> villages;
	private static int counter, started, finished;

	private VillageEvents() {
	}

	/** The attachment, kept apart so the tests register nothing when the class loads. */
	static final class Type {
		static final AttachmentType<Record> RECORD = AttachmentRegistry.create(Heraldia.id("eventos_aldea"),
				b -> b.persistent(Record.CODEC));

		private Type() {
		}
	}

	/** A running event (server thread only). */
	static final class Event {
		final int id;
		final Kind kind;
		final ServerLevel level;
		final String key, name;
		final int cx, cz;
		/** World position of the square's cell (0, 0) at floor height. */
		final int x0, y0, z0;
		final long start;
		final Layout.Plan plan;
		final Map<UUID, Layout.Figure> figures = new LinkedHashMap<>();
		final List<Record.Placed> placed = new ArrayList<>();
		final AABB area;
		final Set<UUID> greeted = new HashSet<>(), rewarded = new HashSet<>();
		/** Traders: the uses of their offers last seen, and who last opened their trades. */
		final Map<UUID, Integer> uses = new HashMap<>();
		final Map<UUID, UUID> lastTrader = new HashMap<>();
		int idle, tune, note;
		boolean bob;
		final Set<String> said = new HashSet<>();

		Event(int id, Kind kind, ServerLevel level, String key, String name, int cx, int cz, int x0, int y0, int z0, Layout.Plan plan) {
			this.id = id;
			this.kind = kind;
			this.level = level;
			this.key = key;
			this.name = name;
			this.cx = cx;
			this.cz = cz;
			this.x0 = x0;
			this.y0 = y0;
			this.z0 = z0;
			this.plan = plan;
			this.start = level.getGameTime();
			this.area = new AABB(x0 - 2, y0 - 2, z0 - 2, x0 + Layout.N + 2, y0 + 8, z0 + Layout.N + 2);
		}

		BlockPos at(int x, int y, int z) {
			return new BlockPos(x0 + x, y0 + y, z0 + z);
		}

		BlockPos centre() {
			return at(Layout.C, 1, Layout.C);
		}

		/** Middle of the bays used: where it is seen from, and where it is heard. */
		double[] focus() {
			double x = 0, z = 0;
			int n = 0;
			for (Layout.Figure f : plan.figures()) {
				x += f.x();
				z += f.z();
				n++;
			}
			return n == 0 ? new double[] {x0 + Layout.C + 0.5, z0 + Layout.C + 0.5} : new double[] {x0 + x / n + 0.5, z0 + z / n + 0.5};
		}

		long elapsed() {
			return level.getGameTime() - start;
		}
	}

	/** One line in Heraldia.onInitialize. */
	public static void register() {
		Type.RECORD.identifier();       // registered at startup: otherwise the saved record is dropped when the world loads
		ServerLifecycleEvents.SERVER_STARTED.register(VillageEvents::started);
		ServerTickEvents.END_SERVER_TICK.register(VillageEvents::tick);
		ServerEntityEvents.ENTITY_LOAD.register(VillageEvents::onLoad);
		ServerChunkEvents.CHUNK_LOAD.register((level, chunk, generated) -> {
			if (!PENDING.isEmpty() && level.dimension() == Level.OVERWORLD && PENDING.containsKey(chunk.getPos().pack())) {
				long c = chunk.getPos().pack();
				level.getServer().execute(() -> cleanPending(level, c));
			}
		});
		UseEntityCallback.EVENT.register((player, level, hand, entity, hit) -> {
			if (!ACTIVE.isEmpty() && player instanceof ServerPlayer p && hand == InteractionHand.MAIN_HAND
					&& entity.entityTags().contains(Rules.TAG) && BY_ENTITY.containsKey(entity.getUUID())) {
				return click(p, entity) ? InteractionResult.SUCCESS : InteractionResult.PASS;
			}
			return InteractionResult.PASS;
		});
		PlayerBlockBreakEvents.BEFORE.register((level, player, pos, state, be) -> PROPS.isEmpty() || player.isCreative()
				|| !PROPS.containsKey(pos.asLong()));
		ServerLivingEntityEvents.ALLOW_DAMAGE.register((entity, source, amount) -> {
			if (ACTIVE.isEmpty() || !entity.entityTags().contains(Rules.TAG)) {
				return true;
			}
			Event e = BY_ENTITY.get(entity.getUUID());
			if (e != null && source.getEntity() instanceof ServerPlayer p) {
				LOGGER.info("Heraldia: events: {} hurts a figure of the {} in {}: everyone scatters", p.getGameProfile().name(), e.kind.id, e.name);
				Quests.addReputation(p, e.cx, e.cz, Reputation.attack(false, false), "spoils the " + e.kind.id);
				e.level.getServer().execute(() -> finish(e, Rules.End.SCATTERED));
			}
			return false;       // no figure is hurt, killed, burnt or turned by anything: nothing to drop or convert
		});
		ServerLifecycleEvents.SERVER_STOPPING.register(server -> {
			for (Event e : new ArrayList<>(ACTIVE.values())) {
				finish(e, Rules.End.CLEANUP);
			}
		});
		ServerLifecycleEvents.SERVER_STOPPED.register(server -> {
			ACTIVE.clear();
			BY_ENTITY.clear();
			PROPS.clear();
			PENDING.clear();
			LATER.clear();
			villages = null;
			counter = started = finished = 0;
		});
	}

	static HeraldiaConfig cfg() {
		return HeraldiaConfig.get();
	}

	static Record record(MinecraftServer server) {
		return server.overworld().getAttachedOrElse(Type.RECORD, Record.EMPTY);
	}

	static void save(MinecraftServer server, Record r) {
		server.overworld().setAttached(Type.RECORD, r);
	}

	/** At startup: the villages' tag and, from the record, what a previous run left up (a crash: taken down as it loads). */
	private static void started(MinecraftServer server) {
		villages = server.registryAccess().lookupOrThrow(Registries.STRUCTURE).get(VILLAGES).map(h -> (HolderSet<Structure>) h)
				.orElse(HolderSet.empty());
		Record r = record(server);
		for (Record.Placed p : r.placed()) {
			BlockPos pos = BlockPos.of(p.pos());
			PENDING.computeIfAbsent(ChunkPos.pack(pos.getX() >> 4, pos.getZ() >> 4), c -> new ArrayList<>()).add(p);
		}
		if (!PENDING.isEmpty()) {
			LOGGER.info("Heraldia: events: {} blocks of an earlier run still up: taken down as their chunks load", r.placed().size());
			ServerLevel level = server.overworld();
			for (Long c : new ArrayList<>(PENDING.keySet())) {
				cleanPending(level, c);
			}
		}
	}

	// --- leftovers ---

	private static void onLoad(Entity e, ServerLevel level) {
		if (Rules.orphan(e.entityTags(), e.getUUID(), BY_ENTITY.keySet())) {
			LOGGER.info("Heraldia: events: removed an entity of an event that is no longer running ({} at {} {} {})",
					BuiltInRegistries.ENTITY_TYPE.getKey(e.getType()).getPath(), e.getBlockX(), e.getBlockY(), e.getBlockZ());
			e.discard();
		}
	}

	/** The recorded blocks of a chunk that no running event owns: taken down if loaded, and forgotten. */
	private static void cleanPending(ServerLevel level, long chunk) {
		List<Record.Placed> list = PENDING.get(chunk);
		if (list == null || level.getChunkSource().getChunkNow(ChunkPos.getX(chunk), ChunkPos.getZ(chunk)) == null) {
			return;
		}
		PENDING.remove(chunk);
		List<Long> gone = new ArrayList<>();
		int removed = takeDown(level, list.reversed(), gone);
		save(level.getServer(), record(level.getServer()).without(gone));
		LOGGER.info("Heraldia: events: chunk {} {}: {} leftover blocks taken down, {} left alone (no longer ours)", ChunkPos.getX(chunk),
				ChunkPos.getZ(chunk), removed, gone.size() - removed);
	}

	/**
	 * Takes down, in this order, every block that is loaded and still exactly what was put up with nothing on top; adds to
	 * {@code gone} every position it is done with (taken down, or no longer ours: left as it is). Returns how many it took down.
	 */
	static int takeDown(ServerLevel level, List<Record.Placed> blocks, List<Long> gone) {
		int n = 0;
		for (Record.Placed p : blocks) {
			BlockPos pos = BlockPos.of(p.pos());
			if (level.getChunkSource().getChunkNow(pos.getX() >> 4, pos.getZ() >> 4) == null) {
				continue;                       // not loaded: stays in the record for later
			}
			// the blocks come top first, so whatever of ours stood on this one is already gone
			BlockState now = level.getBlockState(pos), above = level.getBlockState(pos.above());
			if (Rules.removable(same(p.state(), now), above.isAir())) {
				level.setBlock(pos, Blocks.AIR.defaultBlockState(), Block.UPDATE_ALL);
				n++;
			} else {
				LOGGER.info("Heraldia: events: left alone at {} {} {}: put up {}, now {}, above {}", pos.getX(), pos.getY(), pos.getZ(),
						p.state(), now, above);
			}
			gone.add(p.pos());
		}
		return n;
	}

	/**
	 * Is the block there still the one that was put up? The same block with the same state, except for what a player or
	 * the weather may switch without making it theirs: a lantern or a campfire put out or lit, a waterlogged one.
	 */
	static boolean same(BlockState placed, BlockState now) {
		if (placed.getBlock() != now.getBlock()) {
			return false;
		}
		for (Property<?> p : placed.getProperties()) {
			if (p == BlockStateProperties.LIT || p == BlockStateProperties.SIGNAL_FIRE || p == BlockStateProperties.WATERLOGGED) {
				continue;
			}
			if (!placed.getValue(p).equals(now.getValue(p))) {
				return false;
			}
		}
		return true;
	}

	// --- every tick: a modulo; with events running, their update ---

	private static void tick(MinecraftServer server) {
		int t = server.getTickCount();
		if (!ACTIVE.isEmpty()) {
			if (!LATER.isEmpty()) {
				playLater(server);
			}
			if (t % Rules.MUSIC_TICKS == 0) {
				for (Event e : ACTIVE.values()) {
					if (e.kind == Kind.FESTIVAL) {
						music(e);
					}
				}
			}
			if (t % Rules.UPDATE_TICKS == 0) {
				boolean on = cfg().getBool(ENABLED);
				for (Event e : new ArrayList<>(ACTIVE.values())) {
					update(e, on);
				}
			}
		}
		if (t % Rules.DRAW_TICKS == Rules.DRAW_OFFSET) {
			draw(server);
		}
	}

	private static void draw(MinecraftServer server) {
		HeraldiaConfig cfg = cfg();
		ServerLevel level = server.overworld();
		if (!cfg.getBool(ENABLED) || villages == null || ACTIVE.size() >= cfg.getInt(MAX_ACTIVE) || cfg.getInt(FREQUENCY) <= 0
				|| level.players().isEmpty()) {
			return;
		}
		Map<String, ServerPlayer> near = new LinkedHashMap<>();
		Map<String, Site> sites = new LinkedHashMap<>();
		for (ServerPlayer p : level.players()) {
			if (p.isSpectator() || !p.isAlive()) {
				continue;
			}
			Site s = siteAt(level, p.blockPosition());
			if (s != null && !sites.containsKey(s.key())) {
				sites.put(s.key(), s);
				near.put(s.key(), p);
			}
		}
		Record r = record(server);
		long now = level.getGameTime();
		for (Map.Entry<String, Site> v : sites.entrySet()) {
			String key = v.getKey();
			if (ACTIVE.containsKey(key)) {
				continue;
			}
			Record.Village last = r.village(key);
			if (!Rules.starts(true, ACTIVE.size(), cfg.getInt(MAX_ACTIVE), cfg.getInt(FREQUENCY), now, last == null ? -1 : last.ended(),
					cfg.getInt(WAIT), level.getRandom().nextDouble())) {
				continue;
			}
			Kind kind = Kind.pick(Kind.possible(level.getOverworldClockTime(), level.isRaining(), last == null ? null : Kind.byId(last.kind())),
					level.getRandom().nextDouble());
			if (kind != null) {
				String why = start(level, v.getValue(), kind, near.get(key), false);
				if (why != null) {
					LOGGER.debug("Heraldia: events: no {} in {}: {}", kind.id, key, why);
				}
			}
		}
	}

	// --- start ---

	/** The square of a village: its box and the job board's (null if the square is not there: a skipped event). */
	record Square(BoundingBox box, List<BoundingBox> boards) {
	}

	/** Where an event can happen: a Heraldia village (its square) or the Herald's House plaza; keyed like the reputation. */
	record Site(String key, int cx, int cz, @Nullable Square square) {
	}

	/** The site at {@code pos}: the Herald's House plaza (version 2 on) or the Heraldia village there; null if none. */
	static @Nullable Site siteAt(ServerLevel level, BlockPos pos) {
		int[] h = io.github.albertosa23.heraldia.herald.HeraldHouse.eventSquare(level, pos);
		if (h != null) {
			BoundingBox box = new BoundingBox(h[0], h[1], h[2], h[0] + h[3] - 1, h[1] + 8, h[2] + h[3] - 1);
			return new Site(Reputation.key(h[4], h[5]), h[4], h[5], h[3] == Layout.N ? new Square(box, List.of()) : null);
		}
		if (villages == null) {
			return null;
		}
		StructureStart s = level.structureManager().getStructureAt(pos, villages);
		if (!s.isValid()) {
			return null;
		}
		ChunkPos c = s.getChunkPos();
		return new Site(Reputation.key(c.x(), c.z()), c.x(), c.z(), square(s));
	}

	static @Nullable Square square(StructureStart start) {
		BoundingBox plaza = null;
		List<BoundingBox> boards = new ArrayList<>();
		for (StructurePiece piece : start.getPieces()) {
			if (!(piece instanceof PoolElementStructurePiece pe) || !(pe.getElement() instanceof SinglePoolElement e)) {
				continue;
			}
			String path = e.getTemplateLocation().getPath();
			if (plaza == null && (path.endsWith("/plaza/std") || path.endsWith("/plaza/grande"))) {
				plaza = piece.getBoundingBox();
			} else if (path.endsWith("/tablon")) {
				boards.add(piece.getBoundingBox());
			}
		}
		if (plaza == null || plaza.getXSpan() != Layout.N || plaza.getZSpan() != Layout.N) {
			return null;
		}
		return new Square(plaza, boards);
	}

	/**
	 * Starts an event of {@code kind} in that village; null if it started, otherwise why not (a text for the command).
	 * {@code forced}: by an operator (ignores the frequency, the hour and the village's wait, never the caps or the room).
	 */
	static @Nullable String start(ServerLevel level, Site site, Kind kind, @Nullable ServerPlayer near, boolean forced) {
		HeraldiaConfig cfg = cfg();
		String key = site.key();
		Square sq = site.square();
		if (sq == null) {
			return "sin_plaza";
		}
		if (ACTIVE.containsKey(key)) {
			return "ya_hay";
		}
		if (ACTIVE.size() >= cfg.getInt(MAX_ACTIVE)) {
			return "limite";
		}
		BoundingBox b = sq.box();
		int x0 = b.minX(), y0 = b.minY(), z0 = b.minZ();
		// the whole square loaded with entities (never loads a chunk)
		for (int x : new int[] {b.minX(), b.maxX()}) {
			for (int z : new int[] {b.minZ(), b.maxZ()}) {
				if (!level.isPositionEntityTicking(new BlockPos(x, y0, z))) {
					return "sin_cargar";
				}
			}
		}
		BlockPos centre = new BlockPos(x0 + Layout.C, y0 + 1, z0 + Layout.C);
		if (!forced && near != null && Math.hypot(near.getX() - centre.getX(), near.getZ() - centre.getZ()) < Rules.MIN_DISTANCE) {
			return "cerca";
		}
		Layout.Plan plan = Layout.plan(kind, ground(level, x0, y0, z0, sq.boards()),
				near == null ? List.of(0, 1, 2, 3) : Layout.facing(near.getX() - x0, near.getZ() - z0));
		if (plan == null || !enough(kind, plan)) {
			return "no_cabe";
		}
		Quests.VillageView view = Quests.villageView(level, centre);
		String name = view != null ? view.name() : key;
		Event e = new Event(++counter, kind, level, key, name, site.cx(), site.cz(), x0, y0, z0, plan);
		// record first, then place: a crash in between leaves nothing that is not taken down at the next start
		List<Record.Placed> blocks = new ArrayList<>();
		for (Layout.Placed p : plan.props()) {
			BlockPos pos = e.at(p.x(), p.y(), p.z());
			BlockState st = state(p);
			if (level.getBlockState(pos).isAir() && st.canSurvive(level, pos)) {
				blocks.add(new Record.Placed(pos.asLong(), st));
			}
		}
		save(level.getServer(), record(level.getServer()).with(blocks));
		for (Record.Placed p : blocks) {
			BlockPos pos = BlockPos.of(p.pos());
			level.setBlock(pos, p.state(), Block.UPDATE_ALL);
			BlockState now = level.getBlockState(pos);
			e.placed.add(new Record.Placed(p.pos(), now));
			PROPS.put(p.pos(), e);
		}
		if (!e.placed.equals(blocks)) {      // a block that settled into another state as it was placed: record that one
			List<Long> all = new ArrayList<>();
			for (Record.Placed p : blocks) {
				all.add(p.pos());
			}
			save(level.getServer(), record(level.getServer()).without(all).with(e.placed));
		}
		ACTIVE.put(key, e);
		int spawned = 0;
		for (Layout.Figure f : plan.figures()) {
			spawned += figure(e, f) ? 1 : 0;
		}
		started++;
		if (Rules.fireworks(kind)) {
			fireworks(e, Rules.START_FIREWORKS);
		}
		BlockPos first = e.placed.isEmpty() ? BlockPos.ZERO : BlockPos.of(e.placed.getLast().pos());
		LOGGER.info("Heraldia: events: event {} starts: {} in {} ({}), square at {} {} {}, bays {}, {} figures and {} blocks (the top one {} at {} {} {})",
				e.id, kind.id, name, key, x0, y0, z0, plan.bays(), spawned, e.placed.size(),
				e.placed.isEmpty() ? "-" : BuiltInRegistries.BLOCK.getKey(e.placed.getLast().state().getBlock()), first.getX(), first.getY(), first.getZ());
		announce(e);
		return null;
	}

	/** Has the plan what makes the event read as what it is (at least one trader at the market, the couple...)? */
	static boolean enough(Kind kind, Layout.Plan plan) {
		return switch (kind) {
			case MARKET -> plan.count(Layout.Role.MERCHANT) >= 1;
			case WEDDING -> plan.count(Layout.Role.BRIDE) == 1 && plan.count(Layout.Role.GROOM) == 1 && plan.count(Layout.Role.CLERIC) == 1;
			case FUNERAL -> plan.count(Layout.Role.CLERIC) == 1 && plan.count(Layout.Role.WIDOW) == 1;
			case FESTIVAL -> plan.count(Layout.Role.MUSICIAN) >= 1 && plan.count(Layout.Role.DANCER) >= 3;
		};
	}

	/** The square as it is now, for {@link Layout#plan} (block reads of loaded chunks and one entity lookup). */
	static Layout.Ground ground(ServerLevel level, int x0, int y0, int z0, List<BoundingBox> boards) {
		List<AABB> entities = new ArrayList<>();
		for (Entity en : level.getEntities((Entity) null, new AABB(x0, y0, z0, x0 + Layout.N, y0 + 6, z0 + Layout.N), VillageEvents::stays)) {
			entities.add(en.getBoundingBox());
		}
		return new Layout.Ground() {
			@Override
			public boolean air(int x, int y, int z) {
				return level.getBlockState(new BlockPos(x0 + x, y0 + y, z0 + z)).isAir();
			}

			@Override
			public boolean floor(int x, int z) {
				BlockPos p = new BlockPos(x0 + x, y0, z0 + z);
				BlockState s = level.getBlockState(p);
				return !s.isAir() && s.getFluidState().isEmpty() && !s.getCollisionShape(level, p).isEmpty();
			}

			@Override
			public boolean occupied(int x, int y, int z) {
				AABB cell = new AABB(x0 + x, y0 + y, z0 + z, x0 + x + 1, y0 + y + 1, z0 + z + 1);
				for (AABB a : entities) {
					if (a.intersects(cell)) {
						return true;
					}
				}
				return false;
			}

			@Override
			public boolean reserved(int x, int z) {
				for (BoundingBox b : boards) {
					if (x0 + x >= b.minX() - 2 && x0 + x <= b.maxX() + 2 && z0 + z >= b.minZ() - 2 && z0 + z <= b.maxZ() + 2) {
						return true;
					}
				}
				return false;
			}
		};
	}

	/**
	 * Does this entity keep a cell taken? Players, mobs without AI (the board's bailiff) and the still things (armor
	 * stands, item frames, the square's marker) do; a villager, a golem or a cat walking across the square does not (it
	 * walks on, or a figure without AI standing there nudges it aside), nor an item or a projectile.
	 */
	static boolean stays(Entity en) {
		if (en instanceof Player) {
			return true;
		}
		if (en instanceof net.minecraft.world.entity.Mob m) {
			return m.isNoAi();
		}
		return !(en instanceof net.minecraft.world.entity.LivingEntity) && !(en instanceof net.minecraft.world.entity.item.ItemEntity)
				&& !(en instanceof net.minecraft.world.entity.ExperienceOrb) && !(en instanceof net.minecraft.world.entity.projectile.Projectile);
	}

	/** The block of a prop (vanilla only). */
	static BlockState state(Layout.Placed p) {
		return switch (p.prop()) {
			case POST_OAK -> Blocks.STRIPPED_OAK_LOG.defaultBlockState();
			case POST_BIRCH -> Blocks.STRIPPED_BIRCH_LOG.defaultBlockState();
			case AWNING_RED, WOOL_RED -> Blocks.WOOL.red().defaultBlockState();
			case AWNING_WHITE, WOOL_WHITE -> Blocks.WOOL.white().defaultBlockState();
			case WOOL_PINK -> Blocks.WOOL.pink().defaultBlockState();
			case WOOL_YELLOW -> Blocks.WOOL.yellow().defaultBlockState();
			case CARPET_WHITE -> Blocks.CARPET.white().defaultBlockState();
			case LANTERN -> Blocks.LANTERN.defaultBlockState();
			case SOUL_LANTERN -> Blocks.SOUL_LANTERN.defaultBlockState();
			case BIER -> Blocks.STRIPPED_DARK_OAK_LOG.defaultBlockState()
					.setValue(RotatedPillarBlock.AXIS, p.alongX() ? Direction.Axis.X : Direction.Axis.Z);
			case PALL -> Blocks.CARPET.black().defaultBlockState();
			case CAMPFIRE -> Blocks.CAMPFIRE.defaultBlockState();
			case GOODS -> switch (Math.floorMod(p.variant(), 4)) {
				case 1 -> Blocks.MELON.defaultBlockState();
				case 2 -> Blocks.WOOL.white().defaultBlockState();
				case 3 -> Blocks.DRIED_KELP_BLOCK.defaultBlockState();
				default -> Blocks.HAY_BLOCK.defaultBlockState();
			};
		};
	}

	// --- figures ---

	private static <T> Holder<T> holder(ServerLevel level, ResourceKey<net.minecraft.core.Registry<T>> reg, ResourceKey<T> key) {
		return level.registryAccess().lookupOrThrow(reg).getOrThrow(key);
	}

	static float yaw(double fx, double fz, double tx, double tz) {
		return (float) Math.toDegrees(Math.atan2(-(tx - fx), tz - fz));
	}

	/** Spawns one figure: a villager without AI, of the village's biome, looking at what it attends to. */
	private static boolean figure(Event e, Layout.Figure f) {
		ServerLevel level = e.level;
		Villager v = EntityTypes.VILLAGER.create(level, EntitySpawnReason.EVENT);
		if (v == null) {
			return false;
		}
		BlockPos at = e.at(f.x(), 1, f.z());
		float yaw = yaw(at.getX() + 0.5, at.getZ() + 0.5, e.x0 + f.tx() + 0.5, e.z0 + f.tz() + 0.5);
		v.snapTo(at.getX() + 0.5, at.getY(), at.getZ() + 0.5, yaw, 0f);
		v.setYHeadRot(yaw);
		v.setYBodyRot(yaw);
		v.setNoAi(true);
		v.setPersistenceRequired();
		v.addTag(Rules.TAG);
		v.addTag(Rules.TAG + "." + f.role().name().toLowerCase(java.util.Locale.ROOT));
		ResourceKey<VillagerType> type = VillagerType.byBiome(level.getBiome(at));
		v.setVillagerData(new VillagerData(holder(level, Registries.VILLAGER_TYPE, type),
				holder(level, Registries.VILLAGER_PROFESSION, profession(f)), 1));
		String named = switch (f.role()) {
			case MERCHANT, CLERIC, BRIDE, GROOM, WIDOW, MUSICIAN, HOST -> f.role().name().toLowerCase(java.util.Locale.ROOT);
			default -> null;
		};
		if (named != null) {
			v.setCustomName(Texts.t(K + "figura." + named));
			v.setCustomNameVisible(true);      // the names read from afar: "Bride", "Cleric", "Market trader"...
			v.addTag(Rules.FIGURE);
		}
		if (f.role() == Layout.Role.CHILD) {
			v.setAge(-24000);
		}
		Item held = held(f, ThreadLocalRandom.current().nextInt(4));
		if (held != null) {
			v.setItemSlot(EquipmentSlot.MAINHAND, new ItemStack(held));
			v.setDropChance(EquipmentSlot.MAINHAND, 0f);
		}
		MerchantOffers offers = new MerchantOffers();
		for (Trade t : trades(f)) {
			offers.add(new MerchantOffer(new ItemCost(t.cost(), t.count()), new ItemStack(t.result(), t.amount()), t.uses(), 0, 0.05f));
		}
		v.setOffers(offers);
		BY_ENTITY.put(v.getUUID(), e);
		if (!level.addFreshEntity(v)) {
			BY_ENTITY.remove(v.getUUID());
			return false;
		}
		e.figures.put(v.getUUID(), f);
		return true;
	}

	/** Who is who: the traders by what their stall sells, the cleric in robes, the rest in the village's plain clothes. */
	static ResourceKey<VillagerProfession> profession(Layout.Figure f) {
		return switch (f.role()) {
			case MERCHANT -> switch (Math.floorMod(f.variant(), 4)) {
				case 2 -> VillagerProfession.SHEPHERD;
				case 3 -> VillagerProfession.FISHERMAN;
				default -> VillagerProfession.FARMER;
			};
			case CLERIC -> VillagerProfession.CLERIC;
			case HOST -> VillagerProfession.BUTCHER;
			case MUSICIAN -> VillagerProfession.LIBRARIAN;
			default -> VillagerProfession.NONE;
		};
	}

	/** What a figure holds in its crossed arms (null: nothing). */
	static @Nullable Item held(Layout.Figure f, int r) {
		return switch (f.role()) {
			case BRIDE -> Items.ALLIUM;
			case GUEST -> r == 0 ? Items.POPPY : r == 1 ? Items.DANDELION : null;
			case MOURNER -> r < 2 ? Items.DYED_CANDLE.white() : null;
			case WIDOW -> Items.WITHER_ROSE;
			case MUSICIAN -> switch (Math.floorMod(f.x() + f.z(), 3)) {
				case 0 -> Items.GOAT_HORN;
				case 1 -> Items.NOTE_BLOCK;
				default -> Items.BELL;
			};
			case SHOPPER -> r < 2 ? Items.EMERALD : null;
			case HOST -> Items.CAKE;
			case MERCHANT -> switch (Math.floorMod(f.variant(), 4)) {
				case 1 -> Items.MELON_SLICE;
				case 2 -> Items.WOOL.white();
				case 3 -> Items.COD;
				default -> Items.BREAD;
			};
			default -> null;
		};
	}

	/** A trade: {@code count} × cost for {@code amount} × result, {@code uses} times. */
	record Trade(Item cost, int count, Item result, int amount, int uses) {
	}

	/** The traders' offers (modest: the village's produce, festival food and fireworks); none for the other figures. */
	static List<Trade> trades(Layout.Figure f) {
		return switch (f.role()) {
			case MERCHANT -> switch (Math.floorMod(f.variant(), 4)) {
				case 1 -> List.of(new Trade(Items.EMERALD, 1, Items.MELON_SLICE, 8, 12), new Trade(Items.EMERALD, 1, Items.APPLE, 4, 12),
						new Trade(Items.EMERALD, 1, Items.SWEET_BERRIES, 10, 12), new Trade(Items.MELON, 4, Items.EMERALD, 1, 8));
				case 2 -> List.of(new Trade(Items.EMERALD, 1, Items.WOOL.white(), 2, 12), new Trade(Items.EMERALD, 2, Items.BED.red(), 1, 6),
						new Trade(Items.EMERALD, 1, Items.CARPET.yellow(), 4, 12), new Trade(Items.WOOL.white(), 18, Items.EMERALD, 1, 8));
				case 3 -> List.of(new Trade(Items.EMERALD, 1, Items.COOKED_COD, 6, 12), new Trade(Items.EMERALD, 1, Items.COOKED_SALMON, 4, 12),
						new Trade(Items.EMERALD, 1, Items.DRIED_KELP, 12, 12), new Trade(Items.STRING, 20, Items.EMERALD, 1, 8));
				default -> List.of(new Trade(Items.EMERALD, 1, Items.BREAD, 6, 12), new Trade(Items.EMERALD, 1, Items.PUMPKIN_PIE, 4, 12),
						new Trade(Items.EMERALD, 2, Items.CAKE, 1, 6), new Trade(Items.WHEAT, 20, Items.EMERALD, 1, 8));
			};
			case HOST -> List.of(new Trade(Items.EMERALD, 1, Items.COOKIE, 8, 12), new Trade(Items.EMERALD, 2, Items.CAKE, 1, 6),
					new Trade(Items.EMERALD, 1, Items.HONEY_BOTTLE, 2, 12), new Trade(Items.EMERALD, 1, Items.FIREWORK_ROCKET, 3, 12));
			default -> List.of();
		};
	}

	// --- once a second ---

	private static void update(Event e, boolean enabled) {
		if (!ACTIVE.containsValue(e)) {
			return;
		}
		ServerLevel level = e.level;
		double[] focus = e.focus();
		List<ServerPlayer> near = near(level, focus[0], focus[1], Rules.KEEP_RADIUS);
		e.idle = near.isEmpty() ? e.idle + 1 : 0;
		boolean loaded = level.isPositionEntityTicking(e.centre());
		Rules.End end = Rules.end(e.elapsed(), e.kind, e.idle, loaded, enabled);
		if (end != null) {
			finish(e, end);
			return;
		}
		int second = (int) (e.elapsed() / 20);
		for (Rules.Step s : Rules.steps(e.kind)) {
			if (s.second() == second) {
				beat(e, s.beat(), s.pool(), s.line());
			}
		}
		for (Rules.Repeat r : Rules.repeats(e.kind)) {
			if (Rules.due(r, second)) {
				beat(e, r.beat(), r.pool(), "");
			}
		}
		// the figures look at a player close to them, or back at what they attend to
		for (Map.Entry<UUID, Layout.Figure> f : e.figures.entrySet()) {
			if (!(level.getEntity(f.getKey()) instanceof Villager v)) {
				continue;
			}
			Layout.Figure fig = f.getValue();
			if (fig.role() == Layout.Role.DANCER) {
				continue;
			}
			ServerPlayer close = null;
			double best = 5 * 5;
			for (ServerPlayer p : near) {
				double d = p.distanceToSqr(v);
				if (d < best) {
					best = d;
					close = p;
				}
			}
			float yaw = close != null ? yaw(v.getX(), v.getZ(), close.getX(), close.getZ())
					: yaw(v.getX(), v.getZ(), e.x0 + fig.tx() + 0.5, e.z0 + fig.tz() + 0.5);
			v.setYRot(yaw);
			v.setYHeadRot(yaw);
			v.setYBodyRot(yaw);
			if (v.getTradingPlayer() instanceof ServerPlayer tp) {
				e.lastTrader.put(v.getUUID(), tp.getUUID());
			}
			purchases(e, v);
		}
		if (e.kind == Kind.WEDDING && second > 88 && second % 3 == 0) {
			for (Map.Entry<UUID, Layout.Figure> f : e.figures.entrySet()) {
				if ((f.getValue().role() == Layout.Role.BRIDE || f.getValue().role() == Layout.Role.GROOM) && level.getEntity(f.getKey()) instanceof Villager v) {
					level.broadcastEntityEvent(v, (byte) 12);     // hearts
				}
			}
		}
		greet(e, near);
	}

	/** A trader whose offers were used since the last look: whoever last opened its trades gets the reputation (once). */
	private static void purchases(Event e, Villager v) {
		Layout.Role r = e.figures.get(v.getUUID()).role();
		if (r != Layout.Role.MERCHANT && r != Layout.Role.HOST) {
			return;
		}
		int uses = 0;
		for (MerchantOffer o : v.getOffers()) {
			uses += o.getUses();
		}
		Integer before = e.uses.put(v.getUUID(), uses);
		UUID who = e.lastTrader.get(v.getUUID());
		if (before != null && uses > before && who != null && e.rewarded.add(who)
				&& e.level.getServer().getPlayerList().getPlayer(who) instanceof ServerPlayer p) {
			Quests.addReputation(p, e.cx, e.cz, Rules.PURCHASE_REPUTATION, "buys at the " + e.kind.id);
			LOGGER.info("Heraldia: events: {} buys at the {} in {}", p.getGameProfile().name(), e.kind.id, e.name);
		}
	}

	/** Players within {@link Rules#GREET_RADIUS} of the event's main figure for the first time get a word from it. */
	private static void greet(Event e, List<ServerPlayer> near) {
		for (ServerPlayer p : near) {
			if (e.greeted.contains(p.getUUID()) || p.isSpectator()) {
				continue;
			}
			Villager host = closest(e, p, mainRoles(e.kind));
			if (host != null && host.distanceTo(p) <= Rules.GREET_RADIUS) {
				e.greeted.add(p.getUUID());
				say(e, host, p, "greet", "");
			}
		}
	}

	static Set<Layout.Role> mainRoles(Kind k) {
		return switch (k) {
			case MARKET -> Set.of(Layout.Role.MERCHANT);
			case WEDDING -> Set.of(Layout.Role.BRIDE, Layout.Role.GROOM);
			case FUNERAL -> Set.of(Layout.Role.WIDOW);
			case FESTIVAL -> Set.of(Layout.Role.HOST, Layout.Role.MUSICIAN);
		};
	}

	private static @Nullable Villager closest(Event e, Entity to, Set<Layout.Role> roles) {
		Villager best = null;
		double d = Double.MAX_VALUE;
		for (Map.Entry<UUID, Layout.Figure> f : e.figures.entrySet()) {
			if (roles.contains(f.getValue().role()) && e.level.getEntity(f.getKey()) instanceof Villager v) {
				double dd = v.distanceToSqr(to);
				if (dd < d) {
					d = dd;
					best = v;
				}
			}
		}
		return best;
	}

	private static @Nullable Villager anyOf(Event e, Layout.Role... roles) {
		List<Villager> l = new ArrayList<>();
		for (Map.Entry<UUID, Layout.Figure> f : e.figures.entrySet()) {
			for (Layout.Role r : roles) {
				if (f.getValue().role() == r && e.level.getEntity(f.getKey()) instanceof Villager v) {
					l.add(v);
				}
			}
		}
		return l.isEmpty() ? null : l.get(ThreadLocalRandom.current().nextInt(l.size()));
	}

	private static void beat(Event e, Rules.Beat beat, String pool, String line) {
		switch (beat) {
			case SPEAK -> {
				Villager who = switch (e.kind) {
					case WEDDING, FUNERAL -> anyOf(e, Layout.Role.CLERIC);
					case MARKET -> anyOf(e, Layout.Role.MERCHANT);
					case FESTIVAL -> anyOf(e, Layout.Role.HOST, Layout.Role.MUSICIAN);
				};
				if (who != null) {
					double[] f = e.focus();
					for (ServerPlayer p : near(e.level, f[0], f[1], Rules.HEAR_RADIUS)) {
						say(e, who, p, pool, line);
					}
				}
			}
			case BELL -> bell(e, e.kind == Kind.FUNERAL ? 1 : 3, e.kind == Kind.FUNERAL ? 0.6f : 1.0f);
			case VOWS -> {
				bell(e, 3, 1.2f);
				fireworks(e, Rules.END_FIREWORKS);
				for (Map.Entry<UUID, Layout.Figure> f : e.figures.entrySet()) {
					if (e.level.getEntity(f.getKey()) instanceof Villager v) {
						e.level.broadcastEntityEvent(v, f.getValue().role() == Layout.Role.BRIDE || f.getValue().role() == Layout.Role.GROOM
								? (byte) 12 : (byte) 14);
					}
				}
				LOGGER.info("Heraldia: events: event {}: the couple say yes in {}", e.id, e.name);
			}
		}
	}

	// --- what is said ---

	/** A figure's line to one player, in their language, through the villagers' line system ("Bride: “...”"). */
	static void say(Event e, Villager who, ServerPlayer p, String pool, String id) {
		Lines lines = Lines.of(Texts.code(p));
		String full = "event." + e.kind.id + "." + pool;
		List<Lines.Line> options = lines.pool(full);
		if (options.isEmpty()) {
			return;
		}
		Lines.Line line = null;
		if (!id.isEmpty()) {
			for (Lines.Line l : options) {
				if (l.id().equals(id)) {
					line = l;
				}
			}
		}
		if (line == null) {
			List<Lines.Line> fresh = new ArrayList<>();
			for (Lines.Line l : options) {
				if (!e.said.contains(l.key())) {
					fresh.add(l);
				}
			}
			List<Lines.Line> from = fresh.isEmpty() ? options : fresh;
			line = from.get(ThreadLocalRandom.current().nextInt(from.size()));
		}
		e.said.add(line.key());
		Map<String, String> l = Texts.language(p);
		MutableComponent text = Component.translatableWithFallback("heraldia.dialogos.frase." + line.key(), line.text(), p.getName(),
				Component.literal(e.name));
		p.sendSystemMessage(Texts.t(l, "heraldia.dialogos.linea", who.getDisplayName(), text).withStyle(ChatFormatting.WHITE));
		LOGGER.info("Heraldia: events: event {}: {} says {} to {}", e.id, e.figures.get(who.getUUID()).role().name().toLowerCase(java.util.Locale.ROOT),
				line.key(), p.getGameProfile().name());
	}

	private static void announce(Event e) {
		double[] f = e.focus();
		for (ServerPlayer p : near(e.level, f[0], f[1], Rules.ANNOUNCE_RADIUS)) {
			Map<String, String> l = Texts.language(p);
			p.sendSystemMessage(Texts.t(l, K + e.kind.id + ".anuncio", e.name).withStyle(ChatFormatting.GOLD));
		}
	}

	static List<ServerPlayer> near(ServerLevel level, double x, double z, double radius) {
		List<ServerPlayer> out = new ArrayList<>();
		for (ServerPlayer p : level.players()) {
			if (p.isAlive() && !p.isSpectator() && Math.hypot(p.getX() - x, p.getZ() - z) <= radius) {
				out.add(p);
			}
		}
		return out;
	}

	// --- sounds and sights ---

	private static void sound(ServerPlayer p, Holder<SoundEvent> s, double x, double y, double z, float volume, float pitch) {
		p.connection.send(new ClientboundSoundPacket(s, SoundSource.RECORDS, x, y, z, volume, pitch, p.getRandom().nextLong()));
	}

	/** The square's bell, {@code strikes} times 15 ticks apart, heard {@link Rules#SOUND_RADIUS} blocks away. */
	private static void bell(Event e, int strikes, float pitch) {
		Holder<SoundEvent> bell = BuiltInRegistries.SOUND_EVENT.wrapAsHolder(SoundEvents.BELL_BLOCK);
		BlockPos c = e.centre();
		long now = e.level.getGameTime();
		for (ServerPlayer p : near(e.level, c.getX(), c.getZ(), Rules.SOUND_RADIUS)) {
			for (int i = 0; i < strikes; i++) {
				Later l = new Later(p.getUUID(), bell, c, pitch, now + i * 15L);
				if (i == 0) {
					ring(p, l);
				} else {
					LATER.add(l);
				}
			}
		}
	}

	/** A strike still to sound (the wedding's peal): played from the tick handler, only while there are any. */
	private record Later(UUID player, Holder<SoundEvent> sound, BlockPos at, float pitch, long when) {
	}

	private static final List<Later> LATER = new ArrayList<>();

	private static void ring(ServerPlayer p, Later l) {
		p.connection.send(new ClientboundSoundPacket(l.sound(), SoundSource.BLOCKS, l.at().getX() + 0.5, l.at().getY() + 3,
				l.at().getZ() + 0.5, (float) (Rules.SOUND_RADIUS / 16), l.pitch(), p.getRandom().nextLong()));
	}

	private static void playLater(MinecraftServer server) {
		long now = server.overworld().getGameTime();
		for (java.util.Iterator<Later> it = LATER.iterator(); it.hasNext(); ) {
			Later l = it.next();
			if (now >= l.when() || l.when() - now > 100) {
				it.remove();
				ServerPlayer p = server.getPlayerList().getPlayer(l.player());
				if (p != null) {
					ring(p, l);
				}
			}
		}
	}

	/** The festival's band: one step of the tune, the bass, notes over the musicians and the dancers' hop. */
	private static void music(Event e) {
		int[] tune = Rules.TUNES.get(Math.floorMod(e.tune, Rules.TUNES.size()));
		int step = e.note++ % tune.length;
		double[] f = e.focus();
		List<ServerPlayer> players = near(e.level, f[0], f[1], Rules.MUSIC_RADIUS);
		if (!players.isEmpty()) {
			for (ServerPlayer p : players) {
				if (tune[step] >= 0) {
					sound(p, SoundEvents.NOTE_BLOCK_FLUTE, f[0], e.y0 + 2, f[1], 3f, Rules.pitch(tune[step]));
				}
				int bass = Rules.bass(step);
				if (bass >= 0) {
					sound(p, SoundEvents.NOTE_BLOCK_BASS, f[0], e.y0 + 2, f[1], 3f, Rules.pitch(bass + 6));
				}
			}
		}
		if (step % 2 == 0) {
			e.bob = !e.bob;
			for (Map.Entry<UUID, Layout.Figure> en : e.figures.entrySet()) {
				if (!(e.level.getEntity(en.getKey()) instanceof Villager v)) {
					continue;
				}
				Layout.Figure fig = en.getValue();
				if (fig.role() == Layout.Role.DANCER) {
					float yaw = v.getYRot() + 45f;
					v.setPos(e.x0 + fig.x() + 0.5, e.y0 + 1 + (e.bob ? 0.35 : 0), e.z0 + fig.z() + 0.5);
					v.setYRot(yaw);
					v.setYHeadRot(yaw);
					v.setYBodyRot(yaw);
				} else if (fig.role() == Layout.Role.MUSICIAN && tune[step] >= 0) {
					e.level.sendParticles(ParticleTypes.NOTE, v.getX(), v.getY() + 2.3, v.getZ(), 0, tune[step] / 24.0, 0, 0, 1);
				}
			}
		}
	}

	/** Fireworks over the event (vanilla rockets: they burst and vanish on their own in a second or two). */
	private static void fireworks(Event e, int n) {
		double[] f = e.focus();
		int[][] colours = {{0xFFFFFF, 0xF38BAA}, {0xF9801D, 0xFED83D}, {0x3AB3DA, 0xFFFFFF}};
		for (int i = 0; i < n; i++) {
			int[] c = colours[(e.id + i) % colours.length];
			FireworkExplosion ex = new FireworkExplosion(i % 2 == 0 ? FireworkExplosion.Shape.LARGE_BALL : FireworkExplosion.Shape.STAR,
					IntList.of(c), IntList.of(), true, i == 1);
			ItemStack rocket = new ItemStack(Items.FIREWORK_ROCKET);
			rocket.set(DataComponents.FIREWORKS, new Fireworks(1 + (i % 2), List.of(ex)));
			double ox = (i - (n - 1) / 2.0) * 2.5;
			FireworkRocketEntity r = new FireworkRocketEntity(e.level, f[0] + ox, e.y0 + 2, f[1], rocket);
			e.level.addFreshEntity(r);
		}
	}

	// --- the end ---

	/** Ends an event: its figures leave (and any entity with its tag in its area), its blocks are taken down where they are still ours. */
	static void finish(Event e, Rules.End end) {
		if (ACTIVE.get(e.key) != e) {
			return;
		}
		ACTIVE.remove(e.key);
		ServerLevel level = e.level;
		double[] f = e.focus();
		if (end == Rules.End.DONE || end == Rules.End.SCATTERED) {
			for (ServerPlayer p : near(level, f[0], f[1], Rules.HEAR_RADIUS)) {
				p.sendSystemMessage(Texts.t(Texts.language(p), K + e.kind.id + (end == Rules.End.DONE ? ".fin" : ".dispersa"), e.name)
						.withStyle(end == Rules.End.DONE ? ChatFormatting.GRAY : ChatFormatting.RED));
			}
			if (end == Rules.End.DONE && Rules.fireworks(e.kind) && e.kind == Kind.FESTIVAL) {
				fireworks(e, Rules.END_FIREWORKS);
			}
		}
		int removed = 0;
		for (UUID u : e.figures.keySet()) {
			BY_ENTITY.remove(u);
			Entity en = level.getEntity(u);
			if (en != null && !en.isRemoved()) {
				level.sendParticles(ParticleTypes.POOF, en.getX(), en.getY() + 1, en.getZ(), 4, 0.3, 0.4, 0.3, 0.01);
				en.discard();
				removed++;
			}
		}
		// anything else with the event tag in its square (a figure some other mod converted, say): it goes too
		for (Entity en : level.getEntities((Entity) null, e.area, x -> x.entityTags().contains(Rules.TAG) && !BY_ENTITY.containsKey(x.getUUID()))) {
			en.discard();
			removed++;
		}
		for (Record.Placed p : e.placed) {
			PROPS.remove(p.pos());
		}
		List<Long> gone = new ArrayList<>();
		int blocks = takeDown(level, e.placed.reversed(), gone);
		Record r = record(level.getServer()).without(gone).ended(e.key, level.getGameTime(), e.kind.id);
		save(level.getServer(), r);
		// what could not be reached (an unloaded chunk) waits for its chunk
		Set<Long> done = new HashSet<>(gone);
		for (Record.Placed p : e.placed) {
			if (!done.contains(p.pos())) {
				BlockPos pos = BlockPos.of(p.pos());
				PENDING.computeIfAbsent(ChunkPos.pack(pos.getX() >> 4, pos.getZ() >> 4), c -> new ArrayList<>()).add(p);
			}
		}
		finished++;
		LOGGER.info("Heraldia: events: event {} ends: {} in {}, {} ({} entities removed, {} blocks taken down, {} left alone, {} waiting for their chunk, {} s)",
				e.id, e.kind.id, e.name, end.id, removed, blocks, gone.size() - blocks, e.placed.size() - gone.size(), e.elapsed() / 20);
	}

	// --- taking part ---

	/** A right click on a figure: true if handled here (otherwise the vanilla interaction goes on: the traders' trades). */
	static boolean click(ServerPlayer p, Entity entity) {
		Event e = BY_ENTITY.get(entity.getUUID());
		Layout.Figure f = e == null ? null : e.figures.get(entity.getUUID());
		if (e == null || f == null || !(entity instanceof Villager v) || p.isSpectator()) {
			return false;
		}
		ItemStack hand = p.getMainHandItem();
		switch (f.role()) {
			case MERCHANT, HOST -> {
				e.lastTrader.put(v.getUUID(), p.getUUID());
				return false;           // the trades open as always
			}
			case BRIDE, GROOM, WIDOW -> {
				boolean wedding = e.kind == Kind.WEDDING;
				if (gift(hand, wedding)) {
					String given = BuiltInRegistries.ITEM.getKey(hand.getItem()).getPath();
					if (!p.isCreative()) {
						hand.shrink(1);
					}
					say(e, v, p, "thanks", "");
					e.level.broadcastEntityEvent(v, wedding ? (byte) 12 : (byte) 14);
					if (e.rewarded.add(p.getUUID())) {
						Quests.addReputation(p, e.cx, e.cz, Rules.GIFT_REPUTATION, wedding ? "gives a wedding gift" : "pays respects at the funeral");
					}
					LOGGER.info("Heraldia: events: {} gives {} at the {} in {}", p.getGameProfile().name(), given, e.kind.id, e.name);
				} else {
					say(e, v, p, "ask", "");
					p.sendSystemMessage(Texts.t(Texts.language(p), K + e.kind.id + ".regalo").withStyle(ChatFormatting.GRAY, ChatFormatting.ITALIC));
				}
				return true;
			}
			case MUSICIAN -> {
				e.tune++;
				e.note = 0;
				say(e, v, p, "song", "");
				if (e.rewarded.add(p.getUUID())) {
					Quests.addReputation(p, e.cx, e.cz, Rules.SONG_REPUTATION, "asks the band for a song");
				}
				LOGGER.info("Heraldia: events: {} asks the band in {} for a song (tune {})", p.getGameProfile().name(), e.name,
						Math.floorMod(e.tune, Rules.TUNES.size()));
				return true;
			}
			default -> {
				say(e, v, p, "guest", "");
				return true;
			}
		}
	}

	/** The vanilla tag of the small flowers (the game has it as data, without a constant in 26.3). */
	private static final TagKey<Item> SMALL_FLOWERS = TagKey.create(Registries.ITEM, Identifier.withDefaultNamespace("small_flowers"));

	/** A gift the couple or the bereaved accept: flowers (and for the couple a cake, an emerald, gold...), candles at a funeral. */
	static boolean gift(ItemStack s, boolean wedding) {
		if (s.isEmpty()) {
			return false;
		}
		if (s.is(SMALL_FLOWERS) || s.is(Items.EMERALD)) {
			return true;
		}
		return wedding ? s.is(Items.CAKE) || s.is(Items.GOLD_INGOT) || s.is(Items.DIAMOND) || s.is(Items.HONEY_BOTTLE) || s.is(Items.COOKIE)
				: s.is(ItemTags.CANDLES);
	}

	// --- /heraldia event (operators) ---

	public static LiteralArgumentBuilder<CommandSourceStack> node() {
		LiteralArgumentBuilder<CommandSourceStack> startNode = Commands.literal("start");
		for (Kind k : Kind.values()) {
			startNode.then(Commands.literal(k.id).executes(ctx -> startCommand(ctx, k)));
		}
		return Commands.literal("event").requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))
				.executes(VillageEvents::list)
				.then(Commands.literal("list").executes(VillageEvents::list))
				.then(startNode)
				.then(Commands.literal("stop").executes(ctx -> stop(ctx, false))
						.then(Commands.literal("all").executes(ctx -> stop(ctx, true))))
				.then(Commands.literal("with").then(Commands.argument("entity", EntityArgument.entity()).executes(VillageEvents::with)));
	}

	private static Map<String, String> language(CommandSourceStack src) {
		ServerPlayer p = src.getPlayer();
		return p == null ? Texts.language("es_es") : Texts.language(p);
	}

	private static @Nullable Site villageHere(CommandSourceStack src) {
		ServerLevel level = src.getLevel();
		if (level.dimension() != Level.OVERWORLD) {
			return null;
		}
		return siteAt(level, BlockPos.containing(src.getPosition()));
	}

	private static int startCommand(CommandContext<CommandSourceStack> ctx, Kind kind) {
		CommandSourceStack src = ctx.getSource();
		Map<String, String> l = language(src);
		if (!cfg().getBool(ENABLED)) {
			src.sendFailure(Texts.t(l, K + "desactivados"));
			return 0;
		}
		Site s = villageHere(src);
		if (s == null) {
			src.sendFailure(Texts.t(l, K + "sin_aldea"));
			return 0;
		}
		String why = start(src.getLevel(), s, kind, src.getPlayer(), true);
		if (why != null) {
			src.sendFailure(Texts.t(l, K + why, Texts.t(l, K + kind.id + ".nombre"), ACTIVE.size(), cfg().getInt(MAX_ACTIVE)));
			LOGGER.info("Heraldia: events: {} not started: {}", kind.id, why);
			return 0;
		}
		Event e = ACTIVE.get(s.key());
		src.sendSuccess(() -> Texts.t(l, K + "creado", Texts.t(l, K + kind.id + ".nombre"), e.name, e.figures.size(), e.placed.size()), true);
		return 1;
	}

	private static int stop(CommandContext<CommandSourceStack> ctx, boolean all) {
		CommandSourceStack src = ctx.getSource();
		Map<String, String> l = language(src);
		List<Event> which = new ArrayList<>();
		if (all) {
			which.addAll(ACTIVE.values());
		} else {
			Site s = villageHere(src);
			Event e = s == null ? null : ACTIVE.get(s.key());
			if (e != null) {
				which.add(e);
			}
		}
		for (Event e : which) {
			finish(e, Rules.End.CLEANUP);
		}
		int n = which.size();
		src.sendSuccess(() -> Texts.t(l, K + "parados", n), true);
		return n;
	}

	private static int list(CommandContext<CommandSourceStack> ctx) {
		CommandSourceStack src = ctx.getSource();
		Map<String, String> l = language(src);
		if (ACTIVE.isEmpty()) {
			src.sendSuccess(() -> Texts.t(l, K + "lista.ninguno"), false);
			return 0;
		}
		src.sendSuccess(() -> Texts.t(l, K + "lista.titulo", ACTIVE.size(), cfg().getInt(MAX_ACTIVE), started, finished), false);
		for (Event e : ACTIVE.values()) {
			int alive = 0;
			for (UUID u : e.figures.keySet()) {
				alive += e.level.getEntity(u) != null ? 1 : 0;
			}
			int a = alive;
			BlockPos c = e.centre();
			src.sendSuccess(() -> Texts.t(l, K + "lista.linea", Texts.t(l, K + e.kind.id + ".nombre"), e.name, e.elapsed() / 20, e.kind.seconds,
					a, e.placed.size(), c.getX(), c.getY(), c.getZ()), false);
		}
		return ACTIVE.size();
	}

	/** /heraldia event with &lt;entity&gt;: the operator's click on that figure (server tests: a simulated player's click does not reach the callback). */
	private static int with(CommandContext<CommandSourceStack> ctx) throws CommandSyntaxException {
		CommandSourceStack src = ctx.getSource();
		ServerPlayer p = src.getPlayerOrException();
		Entity en = EntityArgument.getEntity(ctx, "entity");
		Map<String, String> l = language(src);
		if (!BY_ENTITY.containsKey(en.getUUID())) {
			src.sendFailure(Texts.t(l, K + "no_figura"));
			return 0;
		}
		if (!click(p, en) && en instanceof Villager v) {
			v.mobInteract(p, InteractionHand.MAIN_HAND);      // a trader: its trades, as a click would
		}
		return 1;
	}

	// --- for the server tests and /heraldia status ---

	static int running() {
		return ACTIVE.size();
	}

	static Optional<Event> any() {
		return ACTIVE.values().stream().findFirst();
	}
}
