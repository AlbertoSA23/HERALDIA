package io.github.albertosa23.heraldia.herald;

import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;
import io.github.albertosa23.heraldia.arena.Site;
import io.github.albertosa23.heraldia.command.Texts;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import java.util.Optional;
import java.util.concurrent.CompletableFuture;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.fabricmc.fabric.api.event.player.AttackEntityCallback;
import net.fabricmc.fabric.api.event.player.PlayerBlockBreakEvents;
import net.fabricmc.fabric.api.event.player.UseBlockCallback;
import net.fabricmc.fabric.api.event.player.UseEntityCallback;
import net.fabricmc.fabric.api.event.player.UseItemCallback;
import net.fabricmc.fabric.api.networking.v1.ServerPlayConnectionEvents;
import net.minecraft.ChatFormatting;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.core.BlockPos;
import net.minecraft.core.component.DataComponents;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.network.chat.ClickEvent;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.permissions.Permissions;
import net.minecraft.util.Util;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.decoration.ArmorStand;
import net.minecraft.world.entity.decoration.HangingEntity;
import net.minecraft.world.entity.monster.Enemy;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.BucketItem;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.SolidBucketItem;
import net.minecraft.world.item.component.WrittenBookContent;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.entity.LecternBlockEntity;
import net.minecraft.world.level.chunk.ChunkGenerator;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.level.levelgen.RandomState;
import net.minecraft.world.level.storage.LevelData;
import net.minecraft.world.phys.BlockHitResult;
import org.jspecify.annotations.Nullable;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * The Herald's House ("La Casa del Heraldo"): the walled town at the world spawn. One per world, in the overworld; it
 * builds itself at the spawn of a new world (casa_heraldo.generar_en_mundos_nuevos) and an operator places it in a world
 * that already exists (/heraldia herald place [here] and then confirm), the same mechanism as the arena (arena/Arena):
 * a persistent attachment with the origin and a "decided" flag, so a world is never decided twice.
 * <ul>
 * <li>Protection ({@link Grounds}): the footprint and {@link Grounds#RING} blocks around it, every height. No player
 * who is not an operator breaks, places or uses blocks there (doors, beds, the bell and the workstations' screens
 * excepted), empties buckets, lights the portal, hits a villager or an animal or touches item frames and armour
 * stands; a stall's tenant may do anything inside their own stall. Explosions, pistons, endermen and dispensers go
 * through the arena's mixins, which also ask {@link #isProtected(Level, BlockPos)}; trampling farmland and monsters
 * spawning, through HeraldFarmlandMixin and HeraldSpawnMixin. Every check is an early exit on one field and integer
 * comparisons.</li>
 * <li>The market ({@link Market}): stalls for rent, charged lazily.</li>
 * <li>Building it: {@link Building}, a chunk per tick.</li>
 * </ul>
 * No per-tick work when nothing is being built or proposed: one field check, plus the market's check once a minute.
 */
public final class HeraldHouse {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	/** Text key prefix. */
	static final String K = "heraldia.casa_heraldo.";
	/** Tag of the house's own entities (herald_house.HOUSE_TAG: villagers, the bailiff, horses and the golem). */
	static final String TAG = "heraldia_casa";
	/** A world is new if less than this time has passed when it first starts with the mod (as the arena). */
	static final long NEW_WORLD_TICKS = 1200;
	private static final int PROPOSAL_TICKS = 6000, PARTICLES_EVERY = 20;
	public static final String ENABLED = "casa_heraldo.activado", NEW_WORLDS = "casa_heraldo.generar_en_mundos_nuevos";

	private static @Nullable HousePlan plan;
	private static volatile @Nullable Grounds grounds;
	private static @Nullable ServerLevel houseLevel;
	private static boolean turnedOn;

	private record Proposal(Grounds g, long until, @Nullable ServerPlayer who) {
	}

	private static @Nullable Proposal proposal;

	private HeraldHouse() {
	}

	/** One line in Heraldia.onInitialize. */
	public static void register() {
		plan = HousePlan.fromJar();
		Saved.Type.HOUSE.identifier();       // the attachment, registered before the world loads (see LESSONS)
		ServerLifecycleEvents.SERVER_STARTED.register(HeraldHouse::onStart);
		ServerLifecycleEvents.SERVER_STOPPING.register(server -> {
			grounds = null;
			houseLevel = null;
			proposal = null;
		});
		ServerTickEvents.END_SERVER_TICK.register(HeraldHouse::tick);
		PlayerBlockBreakEvents.BEFORE.register((level, player, pos, state, be) -> !deniedBreak(level, pos, player));
		UseBlockCallback.EVENT.register(HeraldHouse::useBlock);
		UseItemCallback.EVENT.register(HeraldHouse::useItem);
		UseEntityCallback.EVENT.register((player, level, hand, entity, hit) -> touchEntity(player, level, entity, false));
		AttackEntityCallback.EVENT.register((player, level, hand, entity, hit) -> touchEntity(player, level, entity, true));
		ServerPlayConnectionEvents.JOIN.register((handler, sender, server) -> server.execute(() -> {
			if (grounds != null && !handler.player.hasDisconnected()) {
				Market.onJoin(handler.player);
			}
		}));
	}

	static HousePlan plan() {
		return plan;
	}

	static @Nullable Grounds grounds() {
		return grounds;
	}

	static @Nullable ServerLevel level() {
		return houseLevel;
	}

	static boolean isOperator(Player p) {
		return p instanceof ServerPlayer sp && sp.permissions().hasPermission(Permissions.COMMANDS_GAMEMASTER);
	}

	// --- protection (cheap early exits: one field, then integers) ---

	/** For the mixins (explosions, pistons, endermen, buckets from dispensers, trampling): is this block protected? */
	public static boolean isProtected(Level level, BlockPos pos) {
		Grounds g = grounds;
		return g != null && level == houseLevel && g.isProtected(pos.getX(), pos.getY(), pos.getZ(), false, 0);
	}

	/** Is there a house in this world? (early exit for the mixins) */
	public static boolean hasHouse(Level level) {
		return grounds != null && level == houseLevel;
	}

	/** For ArenaBucketMixin: emptying a bucket in the area is refused to dispensers and to players who are not operators. */
	public static boolean bucketDenied(Level level, BlockPos pos, @Nullable LivingEntity who) {
		Grounds g = grounds;
		return g != null && level == houseLevel && g.inArea(pos.getX(), pos.getZ()) && !(who instanceof Player p && isOperator(p));
	}

	/** For HeraldSpawnMixin: no monster spawns in the protected area. */
	public static boolean noSpawn(Level level, BlockPos pos) {
		Grounds g = grounds;
		return g != null && level == houseLevel && g.inArea(pos.getX(), pos.getZ());
	}

	/** For the arena's site search: does the house's protected area touch that chunk? */
	public static boolean overlapsChunk(int chunkX, int chunkZ) {
		Grounds g = grounds;
		return g != null && g.areaOverlaps(chunkX << 4, chunkZ << 4, (chunkX << 4) + 15, (chunkZ << 4) + 15);
	}

	private static boolean deniedBreak(Level level, BlockPos pos, Player p) {
		Grounds g = grounds;
		if (g == null || level != houseLevel || !g.inArea(pos.getX(), pos.getZ())) {
			return false;
		}
		if (g.isProtected(pos.getX(), pos.getY(), pos.getZ(), isOperator(p), Market.stallOf(p))) {
			deny(p, "prohibido");
			return true;
		}
		return false;
	}

	private static InteractionResult useBlock(Player player, Level level, InteractionHand hand, BlockHitResult hit) {
		Grounds g = grounds;
		if (g == null || level != houseLevel || !(player instanceof ServerPlayer p)) {
			return InteractionResult.PASS;
		}
		BlockPos pos = hit.getBlockPos();
		BlockPos beside = pos.relative(hit.getDirection());
		if (!g.inArea(pos.getX(), pos.getZ()) && !g.inArea(beside.getX(), beside.getZ())) {
			return InteractionResult.PASS;
		}
		ItemStack held = p.getItemInHand(hand);
		if (g.inPortal(pos.getX(), pos.getY(), pos.getZ()) || g.inPortal(beside.getX(), beside.getY(), beside.getZ())) {
			if (!isOperator(p)) {
				deny(p, "portal.prohibido");
				return InteractionResult.FAIL;
			}
			return InteractionResult.PASS;
		}
		int sign = g.signAt(pos.getX(), pos.getY(), pos.getZ());
		if (sign > 0) {
			if (hand == InteractionHand.MAIN_HAND) {
				Market.signClicked(p, sign);
			}
			return InteractionResult.FAIL;                  // the sign is never edited
		}
		int barrel = g.barrelAt(pos.getX(), pos.getY(), pos.getZ());
		if (barrel >= 0 && !p.isSecondaryUseActive()) {
			return isOperator(p) || Market.mayOpen(p, barrel) ? InteractionResult.PASS : InteractionResult.FAIL;
		}
		if (isOperator(p)) {
			return InteractionResult.PASS;
		}
		int own = Market.stallOf(p);
		if (own != 0 && (g.stallAt(pos.getX(), pos.getY(), pos.getZ()) == own
				|| g.stallAt(beside.getX(), beside.getY(), beside.getZ()) == own)) {
			return InteractionResult.PASS;                  // inside their own stall
		}
		String block = BuiltInRegistries.BLOCK.getKey(level.getBlockState(pos).getBlock()).getPath();
		boolean placing = p.isSecondaryUseActive() && !held.isEmpty();
		if (!placing && Grounds.usable(block)) {
			return InteractionResult.PASS;
		}
		if (!placing && block.equals("lectern") && level.getBlockEntity(pos) instanceof LecternBlockEntity lectern) {
			read(p, lectern.getBook());
			return InteractionResult.FAIL;
		}
		deny(p, "prohibido");
		return InteractionResult.FAIL;
	}

	private static InteractionResult useItem(Player player, Level level, InteractionHand hand) {
		Grounds g = grounds;
		if (g == null || level != houseLevel || !(player instanceof ServerPlayer p) || !g.inArea(p.getBlockX(), p.getBlockZ())
				|| isOperator(p)) {
			return InteractionResult.PASS;
		}
		ItemStack s = p.getItemInHand(hand);
		if (s.getItem() instanceof BucketItem || s.getItem() instanceof SolidBucketItem) {
			deny(p, "prohibido");
			return InteractionResult.FAIL;
		}
		return InteractionResult.PASS;
	}

	/** Hitting or using an entity: villagers trade and talk; animals, villagers and decorations cannot be hurt or changed. */
	private static InteractionResult touchEntity(Player player, Level level, Entity e, boolean attack) {
		Grounds g = grounds;
		if (g == null || level != houseLevel || !(player instanceof ServerPlayer p) || !g.inArea(e.getBlockX(), e.getBlockZ())
				|| isOperator(p) || e instanceof Enemy) {
			return InteractionResult.PASS;
		}
		if (e instanceof HangingEntity || e instanceof ArmorStand) {
			int own = Market.stallOf(p);
			if (own != 0 && g.stallAt(e.getBlockX(), e.getBlockY(), e.getBlockZ()) == own) {
				return InteractionResult.PASS;
			}
			deny(p, "prohibido");
			return InteractionResult.FAIL;
		}
		if (attack && refusesAttack(e)) {
			deny(p, "prohibido");
			return InteractionResult.FAIL;
		}
		return InteractionResult.PASS;
	}

	/** Hits refused in the area: any living thing that is not a monster or a player (villagers, the golem, the horses). */
	static boolean refusesAttack(Entity e) {
		return e instanceof LivingEntity && !(e instanceof Enemy) && !(e instanceof Player);
	}

	/** The job board's book, in chat (the lectern is not opened: its book could be taken). */
	private static void read(ServerPlayer p, ItemStack book) {
		WrittenBookContent c = book.get(DataComponents.WRITTEN_BOOK_CONTENT);
		if (c == null) {
			return;
		}
		p.sendSystemMessage(Texts.t(Texts.language(p), K + "tablon").withStyle(ChatFormatting.GOLD));
		c.pages().forEach(page -> p.sendSystemMessage(page.raw()));
	}

	static void deny(Player p, String key) {
		if (p instanceof ServerPlayer sp) {
			sp.sendOverlayMessage(Texts.t(Texts.language(sp), K + key).withStyle(ChatFormatting.RED));
			sp.inventoryMenu.sendAllDataToRemote();       // the client may have counted the item as used up
		}
	}

	// --- startup and tick ---

	private static void onStart(MinecraftServer server) {
		HeraldiaConfig cfg = HeraldiaConfig.get();
		turnedOn = cfg.getBool(ENABLED);
		ServerLevel ow = server.overworld();
		Saved s = saved(ow);
		if (!turnedOn) {
			LOGGER.info("Heraldia: herald's house: disabled ({} = false)", ENABLED);
			return;
		}
		s.origin().ifPresent(o -> load(ow, o));
		if (s.origin().isEmpty() && !s.decided()) {
			boolean fresh = ow.getGameTime() < NEW_WORLD_TICKS;
			ow.setAttached(Saved.Type.HOUSE, s.decide());
			if (fresh && cfg.getBool(NEW_WORLDS)) {
				LOGGER.info("Heraldia: herald's house: new world: looking for its site at spawn");
				search(server, null, true);
			} else if (fresh) {
				LOGGER.info("Heraldia: herald's house: new world, {} = false: none until an operator places it", NEW_WORLDS);
			} else {
				LOGGER.info("Heraldia: herald's house: existing world: none until an operator places it (/heraldia herald place)");
			}
		}
	}

	private static void load(ServerLevel ow, BlockPos o) {
		houseLevel = ow;
		grounds = new Grounds(o.getX(), o.getY(), o.getZ(), plan);
		LOGGER.info("Heraldia: herald's house: at {} {} {}", grounds.centerX(), grounds.groundY(), grounds.centerZ());
	}

	/** /heraldia reload: casa_heraldo.activado on or off (the market options are read on every use). */
	public static void reload(MinecraftServer server) {
		boolean before = turnedOn;
		turnedOn = HeraldiaConfig.get().getBool(ENABLED);
		ServerLevel ow = server.overworld();
		if (turnedOn && !before) {
			saved(ow).origin().ifPresent(o -> load(ow, o));
		} else if (!turnedOn && before) {
			grounds = null;
			houseLevel = null;
		}
		if (grounds != null) {
			Market.refreshSigns(ow);
		}
	}

	static Saved saved(ServerLevel level) {
		return Optional.ofNullable(level.getAttached(Saved.Type.HOUSE)).orElse(Saved.EMPTY);
	}

	static void save(ServerLevel level, Saved s) {
		level.setAttached(Saved.Type.HOUSE, s);
	}

	/** Called by {@link Building} when done: saved, protected and, in a new world, the spawn on the plaza. */
	static void placed(ServerLevel level, Grounds g, boolean newWorld) {
		save(level, saved(level).withOrigin(new BlockPos(g.ox(), g.oy(), g.oz())));
		houseLevel = level;
		grounds = g;
		if (newWorld) {
			int[] s = g.spawn();
			level.setRespawnData(LevelData.RespawnData.of(Level.OVERWORLD, new BlockPos(s[0], s[1], s[2]), 0f, 0f));
		}
		Market.refreshSigns(level);
	}

	private static void tick(MinecraftServer server) {
		Building.tick(server);
		if (grounds != null && server.getTickCount() % Market.CHECK_TICKS == 0) {
			Market.check(server);
		}
		Proposal pr = proposal;
		if (pr != null && server.getTickCount() % PARTICLES_EVERY == 0) {
			if (server.overworld().getGameTime() > pr.until()) {
				proposal = null;
			} else {
				particles(server.overworld(), pr.g());
			}
		}
	}

	/** Marks a proposed site: particle columns at the four corners of the footprint and of the protected ring. */
	private static void particles(ServerLevel level, Grounds g) {
		int r = Grounds.RING;
		int[][] cols = {{g.ox(), g.oz()}, {g.maxX(), g.oz()}, {g.ox(), g.maxZ()}, {g.maxX(), g.maxZ()},
				{g.ox() - r, g.oz() - r}, {g.maxX() + r, g.oz() - r}, {g.ox() - r, g.maxZ() + r}, {g.maxX() + r, g.maxZ() + r}};
		for (ServerPlayer p : level.players()) {
			if (!isOperator(p)) {
				continue;
			}
			for (int i = 0; i < cols.length; i++) {
				for (int y = 1; y <= 24; y += 2) {
					level.sendParticles(p, i < 4 ? ParticleTypes.END_ROD : ParticleTypes.HAPPY_VILLAGER, true, true,
							cols[i][0] + 0.5, g.groundY() + y, cols[i][1] + 0.5, 1, 0, 0, 0, 0);
				}
			}
		}
	}

	// --- site search ---

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
		};
		HousePlan pl = plan;
		int side = Math.max(pl.size()[0], pl.size()[2]);
		int low = pl.ground(), high = pl.size()[1] - pl.ground();
		long t0 = System.nanoTime();
		CompletableFuture.supplyAsync(() -> Siting.choose(spawn.getX(), spawn.getZ(), side, low, high, ow.getMinY(), ow.getMaxY(),
						heights, io.github.albertosa23.heraldia.arena.Arena::touches), Util.backgroundExecutor())
				.thenAcceptAsync(res -> {
					long ms = (System.nanoTime() - t0) / 1_000_000;
					if (res.isEmpty()) {
						LOGGER.info("Heraldia: herald's house: no site within {} blocks of spawn ({} ms)", Siting.RADIUS, ms);
						if (who != null) {
							who.sendSystemMessage(Texts.t(K + "sin_sitio", Siting.RADIUS).withStyle(ChatFormatting.RED));
						}
						return;
					}
					Siting.Choice c = res.get();
					Grounds g = Grounds.centered(c.x(), c.z(), c.ground(), pl);
					LOGGER.info("Heraldia: herald's house: site at {} {} {} ({} blocks from spawn, drop {}, {} water samples) in {} ms",
							c.x(), c.ground(), c.z(), c.distance(), c.drop(), c.water(), ms);
					if (placeAlone) {
						Building.start(ow, g, null, true);
						return;
					}
					propose(ow, g, who);
				}, server);
	}

	private static void propose(ServerLevel ow, Grounds g, @Nullable ServerPlayer who) {
		proposal = new Proposal(g, ow.getGameTime() + PROPOSAL_TICKS, who);
		if (who == null) {
			return;
		}
		String order = "/heraldia herald place confirm";
		who.sendSystemMessage(Texts.t(K + "propuesta", g.centerX(), g.groundY() + 1, g.centerZ(), Grounds.RING)
				.withStyle(ChatFormatting.GOLD));
		MutableComponent cmd = Component.literal(order).withStyle(s -> s.withColor(ChatFormatting.GREEN).withUnderlined(true)
				.withClickEvent(new ClickEvent.SuggestCommand(order)));
		who.sendSystemMessage(Texts.t(K + "propuesta.confirmar", cmd));
	}

	// --- commands ---

	/** /heraldia herald [place [here | confirm] | stall ...] (registered by command/HeraldiaCommands). */
	public static LiteralArgumentBuilder<CommandSourceStack> node() {
		return Commands.literal("herald")
				.executes(HeraldHouse::info)
				.then(Commands.literal("place").requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))
						.executes(ctx -> place(ctx, false))
						.then(Commands.literal("here").executes(ctx -> place(ctx, true)))
						.then(Commands.literal("confirm").executes(HeraldHouse::confirm)))
				.then(Market.node());
	}

	private static boolean check(CommandSourceStack src) {
		if (!turnedOn) {
			src.sendFailure(Texts.t(K + "desactivada"));
			return false;
		}
		if (Building.busy()) {
			src.sendFailure(Texts.t(K + "trabajando"));
			return false;
		}
		Grounds g = grounds;
		if (g != null) {
			src.sendFailure(Texts.t(K + "ya_existe", g.centerX(), g.groundY() + 1, g.centerZ()));
			return false;
		}
		return true;
	}

	private static int info(CommandContext<CommandSourceStack> ctx) {
		Grounds g = grounds;
		if (g == null) {
			ctx.getSource().sendFailure(Texts.t(turnedOn ? K + "no_existe" : K + "desactivada"));
			return 0;
		}
		int[] s = g.spawn();
		ctx.getSource().sendSuccess(() -> Texts.t(K + "info", s[0], s[1], s[2]).withStyle(ChatFormatting.GOLD), false);
		return 1;
	}

	private static int place(CommandContext<CommandSourceStack> ctx, boolean here) {
		CommandSourceStack src = ctx.getSource();
		if (!check(src)) {
			return 0;
		}
		if (here) {
			ServerPlayer p = src.getPlayer();
			if (p == null || p.level() != src.getServer().overworld()) {
				src.sendFailure(Texts.t(K + "sin_sitio", Siting.RADIUS));
				return 0;
			}
			Grounds g = Grounds.centered(p.getBlockX(), p.getBlockZ(), p.getBlockY() - 1, plan);
			if (io.github.albertosa23.heraldia.arena.Arena.touches(g.ox() - Grounds.RING, g.oz() - Grounds.RING,
					g.maxX() + Grounds.RING, g.maxZ() + Grounds.RING)) {
				src.sendFailure(Texts.t(K + "sin_sitio", Siting.RADIUS));
				return 0;
			}
			propose(src.getServer().overworld(), g, p);
			return 1;
		}
		src.sendSuccess(() -> Texts.t(K + "buscando"), false);
		search(src.getServer(), src.getPlayer(), false);
		return 1;
	}

	private static int confirm(CommandContext<CommandSourceStack> ctx) {
		CommandSourceStack src = ctx.getSource();
		if (!check(src)) {
			return 0;
		}
		Proposal pr = proposal;
		if (pr == null) {
			src.sendFailure(Texts.t(K + "sin_propuesta", "/heraldia herald place"));
			return 0;
		}
		proposal = null;
		Grounds g = pr.g();
		if (!Building.start(src.getServer().overworld(), g, src.getPlayer(), false)) {
			return 0;
		}
		src.sendSuccess(() -> Texts.t(K + "colocando", g.centerX(), g.groundY() + 1, g.centerZ()), true);
		return 1;
	}

	// --- the villagers' conversations (dialogue/Dialogue through quests/Quests.villageView) ---

	/** The house's chunk (x, z) if {@code pos} is in its footprint, for its villagers' conversations; else null. */
	public static int @Nullable [] villageAt(Level level, BlockPos pos) {
		Grounds g = grounds;
		if (g == null || level != houseLevel || !g.inColumns(pos.getX(), pos.getZ())) {
			return null;
		}
		return new int[] {g.centerX() >> 4, g.centerZ() >> 4};
	}

	/** The village style the house's villagers speak as. */
	public static String style() {
		return plan.style();
	}

	/** The house's name in a village view (dialogue/Dialogue replaces it with the translated name). */
	public static final String NAME = "La Casa del Heraldo";
}
