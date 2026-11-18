package io.github.albertosa23.heraldia.arena;

import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;
import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.command.Texts;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.CompletableFuture;
import net.fabricmc.fabric.api.entity.event.v1.ServerLivingEntityEvents;
import net.fabricmc.fabric.api.entity.event.v1.ServerPlayerEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerEntityEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.fabricmc.fabric.api.event.player.PlayerBlockBreakEvents;
import net.fabricmc.fabric.api.event.player.UseBlockCallback;
import net.fabricmc.fabric.api.event.player.UseItemCallback;
import net.fabricmc.fabric.api.loot.v3.LootTableEvents;
import net.minecraft.ChatFormatting;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.core.BlockPos;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.chat.ClickEvent;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.permissions.Permissions;
import net.minecraft.util.Util;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.BucketItem;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.chunk.ChunkGenerator;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.level.levelgen.RandomState;
import net.minecraft.world.level.storage.loot.parameters.LootContextParams;
import org.jspecify.annotations.Nullable;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Wave arena near spawn (T31). One per world, in the overworld; operators place it
 * (/heraldia arena place, with confirmation) or it generates on its own in a new world (arena.generar_en_mundos_nuevos).
 * <ul>
 * <li>Protection ({@link #isProtected}): the template's box, an integer AABB in memory ({@link Zone}). No
 * non-operator player can break, place or use blocks (except the bell), nor use buckets nearby; explosions, pistons
 * and endermen that drop blocks do not touch it (mixins with a cheap early exit); fire and endermen that pick up
 * blocks, by design (its materials neither burn nor can be picked up).</li>
 * <li>Matches: {@link Game} and {@link Match}.</li>
 * <li>Works (place, move, remove): {@link Works}, one chunk per tick.</li>
 * </ul>
 * No per-tick work without a match, work or proposal (three field checks).
 */
public final class Arena {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	/** Tag of the arena mobs. */
	public static final String TAG = "heraldia_arena";
	/** A world is new (the arena generates on its own) if less than this time has passed when it first starts with the mod. */
	static final long NEW_WORLD_TICKS = 1200;
	private static final int PROPOSAL_TICKS = 6000, PARTICLES_EVERY = 20;

	private static @Nullable Blueprint plan;
	private static volatile @Nullable Zone zone;
	private static @Nullable ServerLevel arenaLevel;
	private static @Nullable MinecraftServer arenaServer;
	private static boolean turnedOn;

	/** A proposed site awaiting confirmation (or placed on its own, in a new world). */
	private record Proposal(Zone zone, Site.Choice choice, long until, @Nullable ServerPlayer who) {
	}

	private static @Nullable Proposal proposal;

	private Arena() {
	}

	public static void register() {
		plan = Blueprint.fromJar();
		Saved.Type.ARENA.identifier();   // registers the attachments at startup
		Fame.registerAttachment();
		ServerLifecycleEvents.SERVER_STARTED.register(Arena::onStart);
		ServerLifecycleEvents.SERVER_STOPPING.register(server -> {
			Game.onStop();
			Fame.onStop();
			zone = null;
			arenaLevel = null;
			arenaServer = null;
			proposal = null;
		});
		// champion advancements of the weeks that closed without the player (on the server queue: Carpet loads the fake
		// player's data after JOIN; see command/Guide)
		net.fabricmc.fabric.api.networking.v1.ServerPlayConnectionEvents.JOIN.register((handler, sender, server) ->
				server.schedule(server.wrapRunnable(() -> {
					if (turnedOn && !handler.player.hasDisconnected()) {
						Fame.onJoin(handler.player);
					}
				})));
		ServerTickEvents.END_SERVER_TICK.register(Arena::tick);
		ServerEntityEvents.ENTITY_LOAD.register(Game::onLoad);
		ServerLivingEntityEvents.AFTER_DEATH.register((entity, source) -> Game.onDeath(entity));
		ServerPlayerEvents.COPY_FROM.register(Game::copy);
		ServerPlayerEvents.AFTER_RESPAWN.register((oldValue, newValue, alive) -> Game.respawn(newValue));
		PlayerBlockBreakEvents.BEFORE.register((level, player, pos, state, be) -> !isProtected(level, pos, player));
		UseBlockCallback.EVENT.register(Arena::useBlock);
		UseItemCallback.EVENT.register(Arena::useItem);
		LootTableEvents.MODIFY_DROPS.register((table, context, drops) -> {
			Entity e = context.getOptional(LootContextParams.THIS_ENTITY);
			if (e != null && !drops.isEmpty() && e.entityTags().contains(TAG)) {
				drops.clear();                       // arena mobs drop nothing
			}
		});
	}

	static Blueprint plan() {
		return plan;
	}

	static @Nullable Zone zone() {
		return zone;
	}

	static @Nullable ServerLevel arenaLevel() {
		return arenaLevel;
	}

	static @Nullable MinecraftServer arenaServer() {
		return arenaServer;
	}

	/** Arena enabled (arena.activado)? */
	public static boolean turnedOn() {
		return turnedOn;
	}

	static void setZone(@Nullable Zone z) {
		zone = z;
	}

	/** Saves the placed arena (or none) in the world and starts (or stops) protecting it. */
	static void save(ServerLevel level, @Nullable Zone z) {
		Saved g = Optional.ofNullable(level.getAttached(Saved.Type.ARENA)).orElse(Saved.EMPTY);
		level.setAttached(Saved.Type.ARENA, g.withOrigin(z == null ? null : new BlockPos(z.ox(), z.oy(), z.oz())));
		arenaLevel = level;
		zone = z;
		if (z != null) {
			Fame.signs(level.getServer());   // the hall of fame of the freshly placed arena
		}
		io.github.albertosa23.heraldia.maps.WebMaps.schedule();   // its marker on the web maps (if any)
	}

	// --- protection ---

	/** Is this block protected against whoever acts (null: explosion, piston, enderman)? Cheap early exit. */
	public static boolean isProtected(Level level, BlockPos pos, @Nullable Player who) {
		Zone z = zone;
		if (z == null || level != arenaLevel || !z.mentions(pos.getX(), pos.getY(), pos.getZ())) {
			return false;
		}
		return z.isProtected(pos.getX(), pos.getY(), pos.getZ(), who != null && isOperator(who));
	}

	public static boolean isProtected(Level level, BlockPos pos) {
		return isProtected(level, pos, null);
	}

	/**
	 * For ArenaBucketMixin: is emptying a bucket (of water, lava, powder snow...) at {@code pos} denied? Yes within
	 * {@link Zone#BUCKET_RADIUS} blocks of the arena if a dispenser empties it ({@code who} null) or a player who is not an
	 * operator (players are already stopped by {@link #useItem}; this covers dispensers stuck to the arena).
	 */
	public static boolean bucketDenied(Level level, BlockPos pos, @Nullable LivingEntity who) {
		Zone z = zone;
		if (z == null || level != arenaLevel) {
			return false;
		}
		return z.bucketDenied(pos.getX(), pos.getY(), pos.getZ(), who instanceof Player p && isOperator(p));
	}

	/** Is there an arena in this world? (early exit for the mixins) */
	public static boolean hasArena(Level level) {
		return zone != null && level == arenaLevel;
	}

	/** For ArenaPlayerMixin: does the player keep the inventory on death (falls in the ring during a match)? */
	public static boolean keepsOnDeath(Player p) {
		if (zone == null) {
			if (p.hasAttached(Saved.Type.KEEP)) {
				p.removeAttached(Saved.Type.KEEP);
			}
			return false;
		}
		return Game.keepsOnDeath(p);
	}

	/** For ArenaPlayerMixin: is the player keeping (drops no experience)? */
	public static boolean keeping(Player p) {
		return Game.keeping(p);
	}

	/** For ArenaExperienceMixin: experience of an arena mob (arena.experiencia_porcentaje % of vanilla). */
	public static int experience(int vanilla, double rng) {
		int r = Waves.experience(vanilla, Game.experiencePct(), rng);
		Game.addExperience(vanilla, r);
		return r;
	}

	static boolean isOperator(Player p) {
		return p instanceof ServerPlayer sp && sp.permissions().hasPermission(Permissions.COMMANDS_GAMEMASTER);
	}

	private static InteractionResult useBlock(Player player, Level level, net.minecraft.world.InteractionHand hand,
			net.minecraft.world.phys.BlockHitResult hit) {
		Zone z = zone;
		if (z == null || level != arenaLevel || !(player instanceof ServerPlayer p)) {
			return InteractionResult.PASS;
		}
		BlockPos pos = hit.getBlockPos();
		BlockPos beside = pos.relative(hit.getDirection());
		boolean inside = z.mentions(pos.getX(), pos.getY(), pos.getZ()) || z.mentions(beside.getX(), beside.getY(), beside.getZ());
		if (!inside) {
			return InteractionResult.PASS;
		}
		if (z.isBell(pos.getX(), pos.getY(), pos.getZ()) && !p.isSecondaryUseActive()) {
			if (turnedOn && hand == net.minecraft.world.InteractionHand.MAIN_HAND) {
				Game.bell(p, z);
			}
			return InteractionResult.PASS;          // and the bell rings (vanilla)
		}
		if (isOperator(p)) {
			return InteractionResult.PASS;
		}
		deny(p, "heraldia.arena.prohibido");
		return InteractionResult.FAIL;
	}

	private static InteractionResult useItem(Player player, Level level, net.minecraft.world.InteractionHand hand) {
		Zone z = zone;
		if (z == null || level != arenaLevel || !(player instanceof ServerPlayer p) || isOperator(p)) {
			return InteractionResult.PASS;
		}
		ItemStack s = p.getItemInHand(hand);
		if (s.getItem() instanceof BucketItem && z.near(p.getBlockX(), p.getBlockY(), p.getBlockZ(), Zone.BUCKET_RADIUS)) {
			deny(p, "heraldia.arena.prohibido");
			return InteractionResult.FAIL;
		}
		if (s.is(Items.ENDER_PEARL) && Game.match().state() != Match.State.FREE && z.inRing(p.getX(), p.getY(), p.getZ())) {
			deny(p, "heraldia.arena.perla");
			return InteractionResult.FAIL;
		}
		return InteractionResult.PASS;
	}

	private static void deny(ServerPlayer p, String key) {
		p.sendOverlayMessage(Texts.t(key).withStyle(ChatFormatting.RED));
		p.inventoryMenu.sendAllDataToRemote();      // the client may have counted the item as used up
		LOGGER.debug("Heraldia: arena: {} para {}", key, p.getGameProfile().name());
	}

	// --- startup and tick ---

	private static void onStart(MinecraftServer server) {
		HeraldiaConfig cfg = HeraldiaConfig.get();
		arenaServer = server;
		turnedOn = cfg.getBool("arena.activado");
		Game.configure(cfg);
		Fame.configure(cfg);
		ServerLevel ow = server.overworld();
		Saved g = Optional.ofNullable(ow.getAttached(Saved.Type.ARENA)).orElse(Saved.EMPTY);
		if (!turnedOn) {
			LOGGER.info("Heraldia: arena: desactivada (arena.activado = false)");
			return;
		}
		ArenaScoreboard.target(server);
		if (g.origin().isPresent()) {
			load(ow, g.origin().get());
		}
		Fame.onStart(server);          // record migration, week close and signs
		if (g.origin().isEmpty() && !g.decided()) {
			boolean newValue = ow.getGameTime() < NEW_WORLD_TICKS;
			ow.setAttached(Saved.Type.ARENA, g.decide());
			if (newValue && cfg.getBool("arena.generar_en_mundos_nuevos")) {
				LOGGER.info("Heraldia: arena: mundo nuevo: se busca sitio para la arena");
				search(server, null, true);
			} else {
				LOGGER.info("Heraldia: arena: mundo existente: sin arena hasta que un operador la coloque (/heraldia arena place)");
			}
		}
	}

	/** The arena saved in {@code o} comes into use (at startup or when enabled with /heraldia reload). */
	private static void load(ServerLevel ow, BlockPos o) {
		arenaLevel = ow;
		zone = new Zone(o.getX(), o.getY(), o.getZ(), plan);
		Game.gate(ow, zone, false);           // in case the server stopped in the middle of a match
		io.github.albertosa23.heraldia.maps.WebMaps.schedule();
		LOGGER.info("Heraldia: arena: en {} {} {}", zone.columnX(), zone.groundY(), zone.columnZ());
	}

	/**
	 * /heraldia reload: applies the arena.* options in use (increments, max alive, experience and arena.activado;
	 * arena.generar_en_mundos_nuevos only counts at startup). With a match running it changes nothing (its waves
	 * carry on with what they started with) and returns false: it applies with another reload once it ends.
	 */
	public static boolean reload(MinecraftServer server) {
		HeraldiaConfig cfg = HeraldiaConfig.get();
		Fame.configure(cfg);              // the week (day, hour, history) applies even during a match
		if (turnedOn) {
			Fame.reload(server);
		}
		if (Game.match().state() != Match.State.FREE) {
			return false;
		}
		boolean before = turnedOn;
		turnedOn = cfg.getBool("arena.activado");
		Game.configure(cfg);
		ServerLevel ow = server.overworld();
		if (turnedOn && !before) {
			ArenaScoreboard.target(server);
			Optional.ofNullable(ow.getAttached(Saved.Type.ARENA)).flatMap(Saved::origin).ifPresent(o -> load(ow, o));
			Fame.onStart(server);
		} else if (!turnedOn && before) {
			zone = null;                         // no matches or protection, as if it started disabled
			arenaLevel = null;
			LOGGER.info("Heraldia: arena: desactivada (arena.activado = false)");
		}
		return true;
	}

	/** Does the arena in use (its box and {@link Site#MARGIN}) touch the rectangle? For the Herald's House site search. */
	public static boolean touches(int minX, int minZ, int maxX, int maxZ) {
		Zone z = zone;
		return z != null && minX <= z.maxX() + Site.MARGIN && maxX >= z.minX() - Site.MARGIN
				&& minZ <= z.maxZ() + Site.MARGIN && maxZ >= z.minZ() - Site.MARGIN;
	}

	/** Center of the ring (the bell's column, at ground height) of the arena in use, or null if there is none. */
	public static @Nullable BlockPos center() {
		Zone z = zone;
		return z == null ? null : new BlockPos(z.columnX(), z.groundY(), z.columnZ());
	}

	/** Server record (waves cleared in a match), 0 if none or the arena is disabled (does not create the scoreboard). */
	public static int record(MinecraftServer server) {
		return turnedOn ? ArenaScoreboard.record(server) : 0;
	}

	private static void tick(MinecraftServer server) {
		Works.tick(server);
		Game.tick(server);
		if (turnedOn) {
			Fame.tick(server);               // one comparison per minute
		}
		Proposal pr = proposal;
		if (pr != null && server.getTickCount() % PARTICLES_EVERY == 0) {
			if (server.overworld().getGameTime() > pr.until()) {
				proposal = null;
			} else {
				particles(server.overworld(), pr);
			}
		}
	}

	/** Marks the proposed site: particle columns at the corners and the center, visible from afar. */
	private static void particles(ServerLevel level, Proposal pr) {
		Zone z = pr.zone();
		int[][] cols = {{z.minX(), z.minZ()}, {z.maxX(), z.minZ()}, {z.minX(), z.maxZ()}, {z.maxX(), z.maxZ()},
				{z.columnX(), z.columnZ()}};
		for (ServerPlayer p : level.players()) {
			if (!isOperator(p)) {
				continue;
			}
			for (int[] c : cols) {
				for (int y = 1; y <= 24; y += 2) {
					level.sendParticles(p, ParticleTypes.END_ROD, true, true, c[0] + 0.5, z.groundY() + y, c[1] + 0.5, 1, 0, 0, 0, 0);
				}
			}
		}
	}

	// --- site search ---

	/** Searches for a site off the server thread; once found, proposes it (or places it, in a new world). */
	private static void search(MinecraftServer server, @Nullable ServerPlayer who, boolean placeAlone) {
		ServerLevel ow = server.overworld();
		BlockPos spawn = ow.getRespawnData().pos();
		ChunkGenerator gen = ow.getChunkSource().getGenerator();
		RandomState rs = ow.getChunkSource().randomState();
		Site.Heights heights = new Site.Heights() {
			@Override
			public int surface(int x, int z) {
				return gen.getBaseHeight(x, z, Heightmap.Types.WORLD_SURFACE_WG, ow, rs);
			}

			@Override
			public int depth(int x, int z) {
				return gen.getBaseHeight(x, z, Heightmap.Types.OCEAN_FLOOR_WG, ow, rs);
			}

			@Override
			public boolean occupied(int chunkX, int chunkZ) {
				return Structures.occupied(ow, chunkX, chunkZ)
						|| io.github.albertosa23.heraldia.herald.HeraldHouse.overlapsChunk(chunkX, chunkZ);
			}
		};
		Blueprint pl = plan;
		int side = Math.max(pl.size()[0], pl.size()[2]);
		int low = pl.ground(), high = pl.size()[1] - pl.ground();
		long t0 = System.nanoTime();
		CompletableFuture.supplyAsync(() -> Site.choose(spawn.getX(), spawn.getZ(), side, low, high, ow.getMinY(), ow.getMaxY(), heights),
						Util.backgroundExecutor())
				.thenAcceptAsync(res -> {
					long ms = (System.nanoTime() - t0) / 1_000_000;
					if (res.isEmpty()) {
						LOGGER.info("Heraldia: arena: sin sitio llano a {}-{} bloques del spawn ({} ms)", Site.RADIUS_MIN, Site.RADIUS_MAX, ms);
						if (who != null) {
							who.sendSystemMessage(Texts.t("heraldia.arena.sin_sitio").withStyle(ChatFormatting.RED));
						}
						return;
					}
					Site.Choice e = res.get();
					Zone z = Zone.centered(e.x(), e.z(), e.ground(), pl);
					LOGGER.info("Heraldia: arena: sitio propuesto en {} {} {} (a {} bloques del spawn {} {}, desnivel {}) en {} ms",
							e.x(), e.ground(), e.z(), e.distance(), spawn.getX(), spawn.getZ(), e.drop(), ms);
					if (placeAlone) {
						Works.start(ow, null, z, null);
						return;
					}
					proposal = new Proposal(z, e, ow.getGameTime() + PROPOSAL_TICKS, who);
					if (who != null) {
						propose(who, e, zone != null);
					}
				}, server);
	}

	private static void propose(ServerPlayer p, Site.Choice e, boolean move) {
		String order = "/heraldia arena " + (move ? "move" : "place") + " confirm";
		p.sendSystemMessage(Texts.t("heraldia.arena.propuesta", e.x(), e.ground() + 1, e.z(), e.distance()).withStyle(ChatFormatting.GOLD));
		p.sendSystemMessage(Texts.t("heraldia.arena.copia").withStyle(ChatFormatting.YELLOW));
		MutableComponent cmd = Component.literal(order).withStyle(s -> s.withColor(ChatFormatting.GREEN).withUnderlined(true)
				.withClickEvent(new ClickEvent.SuggestCommand(order)));
		p.sendSystemMessage(Texts.t("heraldia.arena.propuesta.confirmar", cmd));
	}

	// --- commands ---

	/**
	 * /heraldia arena [leave | leaderboard [mode [week]] | place [confirm] | move [confirm] | remove [confirm] |
	 * start [coop | timeattack | survival] | stop | season [reset]] (registered by command/HeraldiaCommands). Anyone can use
	 * start from the ring (the buttons of the bell's mode menu); operators and the console, from anywhere.
	 */
	public static LiteralArgumentBuilder<CommandSourceStack> node() {
		return Commands.literal("arena")
				.executes(Arena::info)
				.then(Commands.literal("leave").executes(ctx -> {
					ServerPlayer p = ctx.getSource().getPlayerOrException();
					if (!Game.leave(p)) {
						ctx.getSource().sendFailure(Texts.t("heraldia.arena.salir.no"));
						return 0;
					}
					return 1;
				}))
				.then(Commands.literal("place").requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS)).executes(ctx -> proposeCmd(ctx, false))
						.then(Commands.literal("confirm").executes(ctx -> confirm(ctx, false))))
				.then(Commands.literal("move").requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS)).executes(ctx -> proposeCmd(ctx, true))
						.then(Commands.literal("confirm").executes(ctx -> confirm(ctx, true))))
				.then(Commands.literal("remove").requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS)).executes(Arena::clearNotice)
						.then(Commands.literal("confirm").executes(Arena::clear)))
				.then(Fame.leaderboard())
				.then(startNode())
				.then(Commands.literal("stop").requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS)).executes(ctx -> {
					if (Game.match().state() == Match.State.FREE) {
						ctx.getSource().sendFailure(Texts.t("heraldia.arena.info.libre"));
						return 0;
					}
					Game.finish(arenaLevel, zone, "parada por un operador");
					ctx.getSource().sendSuccess(() -> Texts.t("heraldia.arena.parada"), true);
					return 1;
				}))
				.then(Fame.season());
	}

	private static LiteralArgumentBuilder<CommandSourceStack> startNode() {
		LiteralArgumentBuilder<CommandSourceStack> n = Commands.literal("start").executes(ctx -> startCmd(ctx, null));
		for (Mode m : Mode.values()) {
			n.then(Commands.literal(m.id()).executes(ctx -> startCmd(ctx, m)));
		}
		return n;
	}

	private static boolean check(CommandSourceStack src, boolean free) {
		if (!turnedOn) {
			src.sendFailure(Texts.t("heraldia.arena.desactivada"));
			return false;
		}
		if (Works.occupied()) {
			src.sendFailure(Texts.t("heraldia.arena.trabajando"));
			return false;
		}
		if (free && Game.match().state() != Match.State.FREE) {
			src.sendFailure(Texts.t("heraldia.arena.ocupada"));
			return false;
		}
		return true;
	}

	private static int info(CommandContext<CommandSourceStack> ctx) {
		CommandSourceStack src = ctx.getSource();
		Zone z = zone;
		if (z == null) {
			src.sendFailure(Texts.t(turnedOn ? "heraldia.arena.no_existe" : "heraldia.arena.desactivada"));
			return 0;
		}
		src.sendSuccess(() -> Texts.t("heraldia.arena.info", z.columnX(), z.groundY() + 1, z.columnZ()).withStyle(ChatFormatting.GOLD), false);
		Match pa = Game.match();
		src.sendSuccess(() -> pa.state() == Match.State.FREE ? Texts.t("heraldia.arena.info.libre")
				: Texts.t("heraldia.arena.info.partida.modo", Texts.t(pa.mode().text()), Math.max(1, pa.wave()),
						pa.participants().size()), false);
		ServerPlayer p = src.getPlayer();
		MinecraftServer server = src.getServer();
		int own = p == null ? 0 : ArenaScoreboard.read(server, p.getScoreboardName());
		src.sendSuccess(() -> Texts.t("heraldia.arena.info.record", own, ArenaScoreboard.record(server)), false);
		return 1;
	}

	private static int proposeCmd(CommandContext<CommandSourceStack> ctx, boolean move) {
		CommandSourceStack src = ctx.getSource();
		if (!check(src, true)) {
			return 0;
		}
		Zone z = zone;
		if (!move && z != null) {
			src.sendFailure(Texts.t("heraldia.arena.ya_existe", z.columnX(), z.groundY() + 1, z.columnZ()));
			return 0;
		}
		if (move && z == null) {
			src.sendFailure(Texts.t("heraldia.arena.no_existe"));
			return 0;
		}
		search(src.getServer(), src.getPlayer(), false);
		return 1;
	}

	private static int confirm(CommandContext<CommandSourceStack> ctx, boolean move) {
		CommandSourceStack src = ctx.getSource();
		if (!check(src, true)) {
			return 0;
		}
		Proposal pr = proposal;
		String order = "/heraldia arena " + (move ? "move" : "place");
		if (pr == null) {
			src.sendFailure(Texts.t("heraldia.arena.sin_propuesta", order));
			return 0;
		}
		Zone old = zone;
		if (!move && old != null) {
			src.sendFailure(Texts.t("heraldia.arena.ya_existe", old.columnX(), old.groundY() + 1, old.columnZ()));
			return 0;
		}
		if (move && old == null) {
			src.sendFailure(Texts.t("heraldia.arena.no_existe"));
			return 0;
		}
		proposal = null;
		Zone z = pr.zone();
		if (!Works.start(src.getServer().overworld(), old, z, src.getPlayer())) {
			return 0;
		}
		src.sendSuccess(() -> Texts.t("heraldia.arena.colocando", z.columnX(), z.groundY() + 1, z.columnZ()), true);
		return 1;
	}

	private static int clearNotice(CommandContext<CommandSourceStack> ctx) {
		Zone z = zone;
		if (z == null) {
			ctx.getSource().sendFailure(Texts.t("heraldia.arena.no_existe"));
			return 0;
		}
		ctx.getSource().sendSuccess(() -> Texts.t("heraldia.arena.quitar.confirmar", z.columnX(), z.groundY() + 1, z.columnZ())
				.withStyle(ChatFormatting.YELLOW), false);
		return 1;
	}

	private static int clear(CommandContext<CommandSourceStack> ctx) {
		CommandSourceStack src = ctx.getSource();
		if (!check(src, true)) {
			return 0;
		}
		Zone z = zone;
		if (z == null) {
			src.sendFailure(Texts.t("heraldia.arena.no_existe"));
			return 0;
		}
		return Works.start(src.getServer().overworld(), z, null, src.getPlayer()) ? 1 : 0;
	}

	/**
	 * /heraldia arena start [mode]. An operator (or the console) starts it from anywhere (without a mode: the coop one, as
	 * always, or the first enabled mode). Any other player, only from the ring (they are the buttons of the bell's
	 * menu); without a mode, it shows them that menu.
	 */
	private static int startCmd(CommandContext<CommandSourceStack> ctx, @Nullable Mode mode) {
		CommandSourceStack src = ctx.getSource();
		Zone z = zone;
		if (!check(src, false) || z == null || arenaLevel == null) {
			if (z == null && turnedOn) {
				src.sendFailure(Texts.t("heraldia.arena.no_existe"));
			}
			return 0;
		}
		boolean op = Commands.hasPermission(Commands.LEVEL_GAMEMASTERS).test(src);
		ServerPlayer p = src.getPlayer();
		if (!op && (p == null || p.level() != arenaLevel || !p.isAlive() || p.isSpectator() || !z.inRing(p.getX(), p.getY(), p.getZ()))) {
			src.sendFailure(Texts.t("heraldia.arena.modo.ruedo"));
			return 0;
		}
		if (Game.match().state() != Match.State.FREE) {
			src.sendFailure(Texts.t("heraldia.arena.en_marcha"));
			return 0;
		}
		List<Mode> active = Game.modes();
		if (active.isEmpty()) {
			src.sendFailure(Texts.t("heraldia.arena.modo.ninguno"));
			return 0;
		}
		if (mode == null) {
			if (!op && active.size() > 1) {
				Game.menu(p);
				return 1;
			}
			mode = active.contains(Mode.COOP) ? Mode.COOP : active.get(0);
		}
		if (!Game.enabled(mode)) {
			src.sendFailure(Texts.t("heraldia.arena.modo.desactivado", Texts.t(mode.text())));
			return 0;
		}
		Mode m = mode;
		if (!Game.start(arenaLevel, z, src.getTextName(), m)) {
			src.sendFailure(Texts.t("heraldia.arena.en_marcha"));
			return 0;
		}
		src.sendSuccess(() -> Texts.t("heraldia.arena.cuenta.modo", Texts.t(m.text())), false);
		return 1;
	}

	/** For tests: the attachment's identifier. */
	static String attachment() {
		return Heraldia.id("arena").toString();
	}
}
