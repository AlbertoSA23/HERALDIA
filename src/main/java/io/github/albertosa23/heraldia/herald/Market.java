package io.github.albertosa23.heraldia.herald;

import com.mojang.brigadier.arguments.IntegerArgumentType;
import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import io.github.albertosa23.heraldia.command.Texts;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import net.minecraft.ChatFormatting;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.ClickEvent;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.Container;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.decoration.ArmorStand;
import net.minecraft.world.entity.decoration.GlowItemFrame;
import net.minecraft.world.entity.decoration.ItemFrame;
import net.minecraft.world.entity.decoration.painting.Painting;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.DyeColor;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.entity.SignBlockEntity;
import net.minecraft.world.level.block.entity.SignText;
import net.minecraft.world.level.block.entity.SignTextSlot;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.BedPart;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;
import net.minecraft.world.level.block.state.properties.DoubleBlockHalf;
import net.minecraft.world.level.block.state.properties.SlabType;
import net.minecraft.world.phys.AABB;
import org.jspecify.annotations.Nullable;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * The Herald's House market: stalls players rent with emeralds (off by default: casa_heraldo.mercado.*, read on every
 * use, so an operator changes prices in game with /heraldia config set). Claiming a free stall costs the entry fee and
 * the first period; the tenant pays ahead with /heraldia herald stall pay (up to {@link Rent#MAX_AHEAD} periods). Rent is
 * charged lazily: the state of a tenancy is computed from the world's game time when someone looks at it, when the
 * tenant joins and once a minute ({@link #CHECK_TICKS}, only while there are tenancies) — never a countdown per tick.
 * The tenant is warned a day before the rent is due and again in the grace; once the grace ends, the stall is
 * reclaimed: <b>no item is ever destroyed</b>. Everything in it (blocks the tenant placed, what their containers held,
 * item frames, armour stands, paintings and loose items) goes into a free return barrel of the market office, assigned
 * to them (only they and operators open it), and they are told where it is (now, or when they next join). If there is
 * not enough room in the barrels, nothing is touched: the stall stays closed until an operator empties one. With the
 * market turned off, nothing is charged or reclaimed (tenancies freeze).
 */
final class Market {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	static final int CHECK_TICKS = 1200;
	static final String ON = "casa_heraldo.mercado.activado", ENTRY = "casa_heraldo.mercado.entrada_esmeraldas",
			RENT = "casa_heraldo.mercado.alquiler_esmeraldas", PERIOD = "casa_heraldo.mercado.periodo_dias",
			GRACE = "casa_heraldo.mercado.gracia_dias";
	private static final int FLAGS = Block.UPDATE_CLIENTS | Block.UPDATE_KNOWN_SHAPE | Block.UPDATE_SUPPRESS_DROPS;
	private static final String K = HeraldHouse.K;

	private Market() {
	}

	static boolean on() {
		return HeraldiaConfig.get().getBool(ON);
	}

	static Rent.Terms terms() {
		HeraldiaConfig c = HeraldiaConfig.get();
		return new Rent.Terms(c.getInt(ENTRY), c.getInt(RENT), c.getInt(PERIOD), c.getInt(GRACE));
	}

	private static long now(ServerLevel level) {
		return level.getGameTime();
	}

	/** The stall this player rents and still holds (not expired), or 0. A handful of comparisons. */
	static int stallOf(Player p) {
		ServerLevel level = HeraldHouse.level();
		if (level == null) {
			return 0;
		}
		Optional<Saved.Tenancy> t = HeraldHouse.saved(level).tenancyOf(p.getUUID());
		if (t.isEmpty() || (on() && Rent.status(now(level), t.get().paidUntil(), terms()) == Rent.Status.EXPIRED)) {
			return 0;
		}
		return t.get().stall();
	}

	// --- what players see ---

	private static MutableComponent button(Map<String, String> l, String key, String cmd, Object... args) {
		return Texts.t(l, K + key, args).withStyle(s -> s.withColor(ChatFormatting.GREEN)
				.withClickEvent(new ClickEvent.RunCommand(cmd)));
	}

	/** A click on a stall's sign: its state, with the buttons that apply. */
	static void signClicked(ServerPlayer p, int n) {
		ServerLevel level = HeraldHouse.level();
		Map<String, String> l = Texts.language(p);
		if (level == null) {
			return;
		}
		if (!on()) {
			p.sendSystemMessage(Texts.t(l, K + "mercado.desactivado").withStyle(ChatFormatting.YELLOW));
			return;
		}
		p.sendSystemMessage(describe(level, n, p, l));
	}

	private static Component describe(ServerLevel level, int n, @Nullable ServerPlayer p, Map<String, String> l) {
		Rent.Terms t = terms();
		Optional<Saved.Tenancy> ten = HeraldHouse.saved(level).tenancy(n);
		long now = now(level);
		if (ten.isEmpty()) {
			return Texts.t(l, K + "mercado.libre", n, t.entry(), t.rent(), t.periodDays(),
					button(l, "mercado.alquilar", "/heraldia herald stall claim " + n)).withStyle(ChatFormatting.GOLD);
		}
		Saved.Tenancy x = ten.get();
		Rent.Status st = Rent.status(now, x.paidUntil(), t);
		if (st == Rent.Status.EXPIRED) {
			return Texts.t(l, K + "mercado.vencido", n).withStyle(ChatFormatting.YELLOW);
		}
		long days = Rent.daysLeft(now, st == Rent.Status.GRACE ? Rent.graceEnd(x.paidUntil(), t) : x.paidUntil());
		if (p != null && x.owner().equals(p.getUUID())) {
			return Texts.t(l, K + "mercado.tuyo", n, days, button(l, "mercado.pagar", "/heraldia herald stall pay " + n, t.rent()),
					button(l, "mercado.dejar", "/heraldia herald stall leave " + n)).withStyle(ChatFormatting.GOLD);
		}
		return Texts.t(l, K + "mercado.ocupado", n, x.name(), days).withStyle(ChatFormatting.GOLD);
	}

	/** The sign of each stall: its number and its tenant, "for rent" or "closed" (market off). Only loaded chunks. */
	static void refreshSigns(ServerLevel level) {
		Grounds g = HeraldHouse.grounds();
		if (g == null) {
			return;
		}
		Saved s = HeraldHouse.saved(level);
		Map<String, String> l = Texts.texts("es_es");
		for (HousePlan.Stall st : g.plan().stalls()) {
			int[] c = g.world(st.sign());
			BlockPos pos = new BlockPos(c[0], c[1], c[2]);
			if (!level.isLoaded(pos) || !(level.getBlockEntity(pos) instanceof SignBlockEntity sign)) {
				continue;
			}
			Component state = s.tenancy(st.id()).<Component>map(t -> Component.literal(t.name()))
					.orElseGet(() -> Texts.t(l, K + (on() ? "se_alquila" : "cerrado")));
			List<Component> lines = List.of(Texts.t(l, K + "puesto"), Component.literal("#" + st.id()), state, Component.empty());
			sign.setText(new SignText(lines, lines, DyeColor.BLACK, false), SignTextSlot.FRONT);
			sign.setWaxed(true);
			sign.setChanged();
			level.sendBlockUpdated(pos, sign.getBlockState(), sign.getBlockState(), Block.UPDATE_CLIENTS);
		}
	}

	/** May this player open that return barrel? Only the player it holds things for (operators are let through before). */
	static boolean mayOpen(ServerPlayer p, int barrel) {
		ServerLevel level = HeraldHouse.level();
		Optional<Saved.Return> r = level == null ? Optional.empty() : HeraldHouse.saved(level).returnAt(barrel);
		if (r.isPresent() && r.get().owner().equals(p.getUUID())) {
			return true;
		}
		HeraldHouse.deny(p, r.isPresent() ? "mercado.barril_ajeno" : "prohibido");
		return false;
	}

	// --- lazy rent: on joining and once a minute ---

	static void onJoin(ServerPlayer p) {
		ServerLevel level = HeraldHouse.level();
		Grounds g = HeraldHouse.grounds();
		if (level == null || g == null) {
			return;
		}
		Saved s = HeraldHouse.saved(level);
		Map<String, String> l = Texts.language(p);
		if (on()) {
			s.tenancyOf(p.getUUID()).ifPresent(t -> warn(p, l, t, Rent.status(now(level), t.paidUntil(), terms()), now(level)));
		}
		for (Saved.Return r : s.returns()) {
			if (r.owner().equals(p.getUUID())) {
				int[] c = g.world(g.plan().returns().get(r.barrel()));
				BlockPos pos = new BlockPos(c[0], c[1], c[2]);
				if (level.isLoaded(pos) && level.getBlockEntity(pos) instanceof Container box && box.isEmpty()) {
					s = s.withReturn(r.barrel(), null);      // already collected
					continue;
				}
				p.sendSystemMessage(Texts.t(l, K + "mercado.pendiente", c[0], c[1], c[2]).withStyle(ChatFormatting.YELLOW));
				if (!r.told()) {
					s = s.withReturn(r.barrel(), new Saved.Return(r.barrel(), r.owner(), r.name(), true));
				}
			}
		}
		HeraldHouse.save(level, s);
	}

	private static void warn(ServerPlayer p, Map<String, String> l, Saved.Tenancy t, Rent.Status st, long now) {
		Rent.Terms terms = terms();
		if (st == Rent.Status.DUE_SOON) {
			p.sendSystemMessage(Texts.t(l, K + "mercado.aviso", t.stall(), Rent.daysLeft(now, t.paidUntil()), t.stall())
					.withStyle(ChatFormatting.YELLOW));
		} else if (st == Rent.Status.GRACE) {
			p.sendSystemMessage(Texts.t(l, K + "mercado.gracia", t.stall(), Rent.daysLeft(now, Rent.graceEnd(t.paidUntil(), terms)),
					t.stall()).withStyle(ChatFormatting.RED));
		}
	}

	/** Once a minute, with the market on and at least one tenancy: warnings and reclaiming. A handful of entries. */
	static void check(MinecraftServer server) {
		ServerLevel level = HeraldHouse.level();
		Grounds g = HeraldHouse.grounds();
		if (level == null || g == null || !on()) {
			return;
		}
		Saved s = HeraldHouse.saved(level);
		if (s.tenancies().isEmpty()) {
			return;
		}
		long now = now(level);
		Rent.Terms terms = terms();
		for (Saved.Tenancy t : s.tenancies()) {
			Rent.Status st = Rent.status(now, t.paidUntil(), terms);
			int stage = st == Rent.Status.DUE_SOON ? 1 : st == Rent.Status.GRACE ? 2 : 0;
			if (st == Rent.Status.EXPIRED) {
				reclaim(level, g, t, "mercado.perdido");
				s = HeraldHouse.saved(level);
			} else if (stage > t.warned()) {
				ServerPlayer p = server.getPlayerList().getPlayer(t.owner());
				if (p != null) {
					warn(p, Texts.language(p), t, st, now);
					s = s.withTenancy(t.stall(), t.warn(stage));
					HeraldHouse.save(level, s);
				}
			}
		}
	}

	// --- reclaiming: nothing is destroyed ---

	/** Does this block count as an item of its own (the lower half of a door, the foot of a bed...)? */
	static int itemsOf(BlockState s) {
		if (s.hasProperty(BlockStateProperties.DOUBLE_BLOCK_HALF) && s.getValue(BlockStateProperties.DOUBLE_BLOCK_HALF) == DoubleBlockHalf.UPPER) {
			return 0;
		}
		if (s.hasProperty(BlockStateProperties.BED_PART) && s.getValue(BlockStateProperties.BED_PART) == BedPart.HEAD) {
			return 0;
		}
		if (s.hasProperty(BlockStateProperties.SLAB_TYPE) && s.getValue(BlockStateProperties.SLAB_TYPE) == SlabType.DOUBLE) {
			return 2;
		}
		return 1;
	}

	/** Merges equal stacks (up to their maximum size). */
	static List<ItemStack> merge(List<ItemStack> in) {
		List<ItemStack> out = new ArrayList<>();
		for (ItemStack s : in) {
			ItemStack rest = s.copy();
			for (ItemStack o : out) {
				if (rest.isEmpty()) {
					break;
				}
				if (ItemStack.isSameItemSameComponents(o, rest) && o.getCount() < o.getMaxStackSize()) {
					int k = Math.min(rest.getCount(), o.getMaxStackSize() - o.getCount());
					o.grow(k);
					rest.shrink(k);
				}
			}
			if (!rest.isEmpty()) {
				out.add(rest);
			}
		}
		return out;
	}

	/**
	 * Empties stall {@code t.stall()} into the return barrels and frees it. False (and nothing touched) if its chunks or
	 * the office's are not loaded or the free barrels have no room for everything.
	 */
	static boolean reclaim(ServerLevel level, Grounds g, Saved.Tenancy t, String key) {
		HousePlan.Stall st = g.plan().stall(t.stall());
		if (st == null) {
			return false;
		}
		int[] a = g.world(st.min()), b = g.world(st.max());
		BlockPos lo = new BlockPos(a[0], a[1], a[2]), hi = new BlockPos(b[0], b[1], b[2]);
		if (!level.isLoaded(lo) || !level.isLoaded(hi)) {
			return false;
		}
		// 1. look, without touching anything
		List<ItemStack> items = new ArrayList<>();
		List<BlockPos> blocks = new ArrayList<>();
		for (BlockPos pos : BlockPos.betweenClosed(lo, hi)) {
			BlockState s = level.getBlockState(pos);
			if (s.isAir()) {
				continue;
			}
			blocks.add(pos.immutable());
			BlockEntity be = level.getBlockEntity(pos);
			if (be instanceof Container c) {
				for (int i = 0; i < c.getContainerSize(); i++) {
					if (!c.getItem(i).isEmpty()) {
						items.add(c.getItem(i).copy());
					}
				}
			}
			Item it = s.getBlock().asItem();
			if (it != Items.AIR && itemsOf(s) > 0) {
				items.add(new ItemStack(it, itemsOf(s)));
			}
		}
		AABB box = new AABB(a[0], a[1], a[2], b[0] + 1, b[1] + 1, b[2] + 1);
		List<Entity> things = level.getEntities((Entity) null, box,
				e -> e instanceof ItemEntity || e instanceof ItemFrame || e instanceof ArmorStand || e instanceof Painting);
		for (Entity e : things) {
			if (e instanceof ItemEntity ie) {
				items.add(ie.getItem().copy());
			} else if (e instanceof ItemFrame f) {
				if (!f.getItem().isEmpty()) {
					items.add(f.getItem().copy());
				}
				items.add(new ItemStack(f instanceof GlowItemFrame ? Items.GLOW_ITEM_FRAME : Items.ITEM_FRAME));
			} else if (e instanceof ArmorStand as) {
				for (EquipmentSlot slot : EquipmentSlot.values()) {
					if (!as.getItemBySlot(slot).isEmpty()) {
						items.add(as.getItemBySlot(slot).copy());
					}
				}
				items.add(new ItemStack(Items.ARMOR_STAND));
			} else {
				items.add(new ItemStack(Items.PAINTING));
			}
		}
		items = merge(items);
		// 2. room in the return barrels
		Saved s = HeraldHouse.saved(level);
		List<Integer> free = new ArrayList<>();
		List<Container> barrels = new ArrayList<>();
		for (int i = 0; i < g.plan().returns().size(); i++) {
			int[] c = g.world(g.plan().returns().get(i));
			BlockPos pos = new BlockPos(c[0], c[1], c[2]);
			if (level.isLoaded(pos) && level.getBlockEntity(pos) instanceof Container c2 && c2.isEmpty()) {
				free.add(i);
				barrels.add(c2);
			}
		}
		int size = barrels.isEmpty() ? 27 : barrels.get(0).getContainerSize();
		int needed = (items.size() + size - 1) / size;
		if (needed > free.size()) {
			LOGGER.warn("Heraldia: herald's house: stall {} cannot be reclaimed: {} return barrels needed, {} free", t.stall(), needed,
					free.size());
			level.getServer().getPlayerList().getPlayers().stream().filter(HeraldHouse::isOperator).forEach(op ->
					op.sendSystemMessage(Texts.t(Texts.language(op), K + "mercado.devolucion_llena", t.stall()).withStyle(ChatFormatting.RED)));
			return false;
		}
		// 3. move everything
		for (BlockPos pos : blocks) {
			if (level.getBlockEntity(pos) instanceof Container c) {
				c.clearContent();
			}
		}
		for (BlockPos pos : blocks) {
			level.setBlock(pos, Blocks.AIR.defaultBlockState(), FLAGS);
		}
		for (Entity e : things) {
			e.discard();
		}
		int first = -1;
		for (int k = 0; k < needed; k++) {
			Container c = barrels.get(k);
			for (int i = 0; i < size && k * size + i < items.size(); i++) {
				c.setItem(i, items.get(k * size + i));
			}
			c.setChanged();
			s = s.withReturn(free.get(k), new Saved.Return(free.get(k), t.owner(), t.name(), false));
			if (first < 0) {
				first = free.get(k);
			}
		}
		// barrels emptied by their owner are free again
		for (Saved.Return r : List.copyOf(s.returns())) {
			if (free.contains(r.barrel()) && free.indexOf(r.barrel()) >= needed) {
				s = s.withReturn(r.barrel(), null);
			}
		}
		s = s.withTenancy(t.stall(), null);
		ServerPlayer p = level.getServer().getPlayerList().getPlayer(t.owner());
		if (p != null && first >= 0) {
			int[] c = g.world(g.plan().returns().get(first));
			p.sendSystemMessage(Texts.t(Texts.language(p), K + key, t.stall(), c[0], c[1], c[2]).withStyle(ChatFormatting.YELLOW));
			for (int k = 0; k < needed; k++) {
				Saved.Return r = s.returnAt(free.get(k)).orElseThrow();
				s = s.withReturn(r.barrel(), new Saved.Return(r.barrel(), r.owner(), r.name(), true));
			}
		}
		HeraldHouse.save(level, s);
		refreshSigns(level);
		LOGGER.info("Heraldia: herald's house: stall {} of {} reclaimed: {} stacks into {} return barrel(s)", t.stall(), t.name(),
				items.size(), needed);
		return true;
	}

	// --- emeralds ---

	static int emeralds(ServerPlayer p) {
		int n = 0;
		var inv = p.getInventory();
		for (int i = 0; i < inv.getContainerSize(); i++) {
			if (inv.getItem(i).is(Items.EMERALD)) {
				n += inv.getItem(i).getCount();
			}
		}
		return n;
	}

	private static void take(ServerPlayer p, int cost) {
		var inv = p.getInventory();
		for (int i = 0; i < inv.getContainerSize() && cost > 0; i++) {
			ItemStack s = inv.getItem(i);
			if (s.is(Items.EMERALD)) {
				int k = Math.min(cost, s.getCount());
				s.shrink(k);
				cost -= k;
			}
		}
		inv.setChanged();
	}

	private static boolean pay(ServerPlayer p, Map<String, String> l, int cost, CommandSourceStack src) {
		int held = emeralds(p);
		if (!Rent.affordable(held, cost)) {
			src.sendFailure(Texts.t(l, K + "mercado.sin_esmeraldas", cost, held));
			return false;
		}
		take(p, cost);
		return true;
	}

	// --- commands ---

	/** /heraldia herald stall [claim &lt;n&gt; | pay &lt;n&gt; [periods] | leave &lt;n&gt; | evict &lt;n&gt;]. */
	static LiteralArgumentBuilder<CommandSourceStack> node() {
		return Commands.literal("stall")
				.executes(Market::list)
				.then(Commands.literal("claim").then(Commands.argument("stall", IntegerArgumentType.integer(1)).executes(Market::claim)))
				.then(Commands.literal("pay").then(Commands.argument("stall", IntegerArgumentType.integer(1))
						.executes(ctx -> pay(ctx, 1))
						.then(Commands.argument("periods", IntegerArgumentType.integer(1, Rent.MAX_AHEAD))
								.executes(ctx -> pay(ctx, IntegerArgumentType.getInteger(ctx, "periods"))))))
				.then(Commands.literal("leave").then(Commands.argument("stall", IntegerArgumentType.integer(1))
						.executes(ctx -> leave(ctx, false))))
				.then(Commands.literal("evict").requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))
						.then(Commands.argument("stall", IntegerArgumentType.integer(1)).executes(ctx -> leave(ctx, true))));
	}

	private static @Nullable ServerLevel ready(CommandSourceStack src) {
		ServerLevel level = HeraldHouse.level();
		if (level == null || HeraldHouse.grounds() == null) {
			src.sendFailure(Texts.t(K + "no_existe"));
			return null;
		}
		if (!on()) {
			src.sendFailure(Texts.t(K + "mercado.desactivado"));
			return null;
		}
		return level;
	}

	private static int list(CommandContext<CommandSourceStack> ctx) {
		ServerLevel level = ready(ctx.getSource());
		if (level == null) {
			return 0;
		}
		Saved s = HeraldHouse.saved(level);
		long now = now(level);
		ctx.getSource().sendSuccess(() -> Texts.t(K + "mercado.lista").withStyle(ChatFormatting.GOLD), false);
		for (HousePlan.Stall st : HeraldHouse.grounds().plan().stalls()) {
			Optional<Saved.Tenancy> t = s.tenancy(st.id());
			ctx.getSource().sendSuccess(() -> t.isEmpty() ? Texts.t(K + "mercado.linea_libre", st.id())
					: Texts.t(K + "mercado.linea", st.id(), t.get().name(), Rent.daysLeft(now, t.get().paidUntil())), false);
		}
		return 1;
	}

	private static HousePlan.@Nullable Stall stall(CommandContext<CommandSourceStack> ctx) {
		int n = IntegerArgumentType.getInteger(ctx, "stall");
		HousePlan.Stall st = HeraldHouse.plan().stall(n);
		if (st == null) {
			ctx.getSource().sendFailure(Texts.t(K + "mercado.no_existe", n));
		}
		return st;
	}

	private static int claim(CommandContext<CommandSourceStack> ctx) throws CommandSyntaxException {
		CommandSourceStack src = ctx.getSource();
		ServerPlayer p = src.getPlayerOrException();
		ServerLevel level = ready(src);
		HousePlan.Stall st = stall(ctx);
		if (level == null || st == null) {
			return 0;
		}
		Map<String, String> l = Texts.language(p);
		Saved s = HeraldHouse.saved(level);
		Rent.Terms terms = terms();
		long now = now(level);
		Optional<Saved.Tenancy> mine = s.tenancyOf(p.getUUID());
		if (mine.isPresent() && Rent.status(now, mine.get().paidUntil(), terms) != Rent.Status.EXPIRED) {
			src.sendFailure(Texts.t(l, K + "mercado.ya_tienes", mine.get().stall()));
			return 0;
		}
		Optional<Saved.Tenancy> cur = s.tenancy(st.id());
		if (cur.isPresent()) {
			if (Rent.status(now, cur.get().paidUntil(), terms) != Rent.Status.EXPIRED
					|| !reclaim(level, HeraldHouse.grounds(), cur.get(), "mercado.perdido")) {
				src.sendFailure(describe(level, st.id(), p, l).copy());
				return 0;
			}
			s = HeraldHouse.saved(level);
		}
		if (mine.isPresent()) {               // their own expired one goes back first
			if (!reclaim(level, HeraldHouse.grounds(), mine.get(), "mercado.perdido")) {
				return 0;
			}
			s = HeraldHouse.saved(level);
		}
		int cost = Rent.claimCost(terms);
		if (!pay(p, l, cost, src)) {
			return 0;
		}
		long until = Rent.claimUntil(now, terms);
		HeraldHouse.save(level, s.withTenancy(st.id(), new Saved.Tenancy(st.id(), p.getUUID(), p.getGameProfile().name(), until, 0)));
		refreshSigns(level);
		src.sendSuccess(() -> Texts.t(l, K + "mercado.alquilado", st.id(), Rent.daysLeft(now, until), st.id())
				.withStyle(ChatFormatting.GREEN), false);
		LOGGER.info("Heraldia: herald's house: stall {} claimed by {} for {} emeralds", st.id(), p.getGameProfile().name(), cost);
		return 1;
	}

	private static int pay(CommandContext<CommandSourceStack> ctx, int periods) throws CommandSyntaxException {
		CommandSourceStack src = ctx.getSource();
		ServerPlayer p = src.getPlayerOrException();
		ServerLevel level = ready(src);
		HousePlan.Stall st = stall(ctx);
		if (level == null || st == null) {
			return 0;
		}
		Map<String, String> l = Texts.language(p);
		Saved s = HeraldHouse.saved(level);
		Optional<Saved.Tenancy> t = s.tenancy(st.id());
		if (t.isEmpty() || !t.get().owner().equals(p.getUUID())) {
			src.sendFailure(Texts.t(l, K + "mercado.no_es_tuyo"));
			return 0;
		}
		Rent.Terms terms = terms();
		long now = now(level);
		int max = Rent.payable(now, t.get().paidUntil(), terms);
		if (max <= 0 || periods > max) {
			src.sendFailure(max <= 0 && Rent.status(now, t.get().paidUntil(), terms) == Rent.Status.EXPIRED
					? describe(level, st.id(), p, l).copy() : Texts.t(l, K + "mercado.tope", Rent.MAX_AHEAD));
			return 0;
		}
		if (!pay(p, l, periods * terms.rent(), src)) {
			return 0;
		}
		long until = Rent.pay(t.get().paidUntil(), periods, terms);
		HeraldHouse.save(level, s.withTenancy(st.id(), t.get().paid(until)));
		src.sendSuccess(() -> Texts.t(l, K + "mercado.pagado", st.id(), Rent.daysLeft(now, until)).withStyle(ChatFormatting.GREEN), false);
		return 1;
	}

	private static int leave(CommandContext<CommandSourceStack> ctx, boolean evict) throws CommandSyntaxException {
		CommandSourceStack src = ctx.getSource();
		ServerLevel level = HeraldHouse.level();
		HousePlan.Stall st = stall(ctx);
		if (level == null || HeraldHouse.grounds() == null || st == null) {
			if (level == null) {
				src.sendFailure(Texts.t(K + "no_existe"));
			}
			return 0;
		}
		Optional<Saved.Tenancy> t = HeraldHouse.saved(level).tenancy(st.id());
		if (t.isEmpty() || (!evict && !t.get().owner().equals(src.getPlayerOrException().getUUID()))) {
			src.sendFailure(Texts.t(K + (t.isEmpty() ? "mercado.no_existe" : "mercado.no_es_tuyo"), st.id()));
			return 0;
		}
		if (!reclaim(level, HeraldHouse.grounds(), t.get(), evict ? "mercado.desalojado" : "mercado.dejado")) {
			src.sendFailure(Texts.t(K + "mercado.devolucion_llena", st.id()));
			return 0;
		}
		src.sendSuccess(() -> Texts.t(K + "mercado.linea_libre", st.id()), true);
		return 1;
	}
}
