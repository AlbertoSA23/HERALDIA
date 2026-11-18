package io.github.albertosa23.heraldia.dialogue;

import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.command.Texts;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.mines.Mines;
import io.github.albertosa23.heraldia.quests.Generator;
import io.github.albertosa23.heraldia.quests.Objectives;
import io.github.albertosa23.heraldia.quests.Quests;
import io.github.albertosa23.heraldia.quests.Reputation;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ThreadLocalRandom;
import java.util.function.Consumer;
import net.fabricmc.fabric.api.attachment.v1.AttachmentRegistry;
import net.fabricmc.fabric.api.attachment.v1.AttachmentType;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.fabricmc.fabric.api.event.player.UseEntityCallback;
import net.fabricmc.fabric.api.networking.v1.ServerPlayConnectionEvents;
import net.minecraft.ChatFormatting;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.EntityArgument;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.ClickEvent;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.HoverEvent;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.resources.Identifier;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityTypes;
import net.minecraft.world.entity.npc.villager.Villager;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.SpawnEggItem;
import net.minecraft.world.level.biome.Biome;
import org.jspecify.annotations.Nullable;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Talking to the villagers (P9a): the part that touches the game. The pure logic is in {@link Gesture} (when a click
 * talks), {@link Context} and {@link Selector} (which line), {@link Hints} (the wayfarers and what they know),
 * {@link Memory} (what is kept) and {@link Lines} (the lines of each language).
 * <ul>
 * <li>A right click on a Heraldia villager inside a Heraldia village (see {@link Gesture}) shows, in chat, a greeting
 * and a line chosen by its profession, its village's land, the hour, the weather and the player's reputation, with
 * buttons (clickable text: vanilla clients too) to keep talking, ask for news, trade and say goodbye. Sneak + right
 * click, or any other villager, opens the trades as always.</li>
 * <li>Each villager rests {@code dialogos.espera_segundos} between conversations (it then says it is busy and offers its
 * trades). One villager in ten ({@code dialogos.viajeros_porcentaje}) is a wayfarer: asked for news by a player with
 * {@code dialogos.pista_reputacion} reputation with the village, it tells, once in its life, where a real structure lies
 * (direction and approximate distance, never coordinates).</li>
 * <li>No per-tick work: everything happens on a click or a button. The conversation in course (who is talking to which
 * villager) is kept in memory only, and dropped when the player leaves or the server stops.</li>
 * </ul>
 * Everything is read from the configuration on each use (reloads with /heraldia reload).
 */
public final class Dialogue {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	public static final String ENABLED = "dialogos.activado", WAIT = "dialogos.espera_segundos",
			WAYFARERS = "dialogos.viajeros_porcentaje", HINT_REPUTATION = "dialogos.pista_reputacion";
	/** The tag the generator puts on every Heraldia villager (core.villager, trades.VILLAGER_TAG). */
	static final String HERALDIA_VILLAGER = Heraldia.MOD_ID;
	/** Lines after the first one that "Keep talking" gives in one conversation. */
	static final int MORE = 2;
	/** A button only works this close to the villager, and for this long after the conversation started (5 min). */
	static final double RANGE = 8;
	static final long TTL = 20L * 60 * 5;
	static final String K = "heraldia.dialogos.";
	private static final Map<UUID, Talk> TALKS = new ConcurrentHashMap<>();

	private Dialogue() {
	}

	/** The conversation a player is having: with whom, how many more lines it has, whether they asked for news. */
	record Talk(UUID villager, int more, boolean asked, long started, int cx, int cz, String style, String family, String name) {
		Talk withMore(int n) {
			return new Talk(villager, n, asked, started, cx, cz, style, family, name);
		}

		Talk withAsked() {
			return new Talk(villager, more, true, started, cx, cz, style, family, name);
		}

		Quests.VillageView village() {
			return new Quests.VillageView(cx, cz, style, family, name);
		}
	}

	/** The attachments, kept apart so the tests register nothing when the class loads. */
	static final class Attachments {
		static final AttachmentType<Memory.Villager> VILLAGER = AttachmentRegistry.create(Heraldia.id("dialogo_aldeano"),
				b -> b.persistent(Memory.Villager.CODEC));
		static final AttachmentType<Memory.Player> PLAYER = AttachmentRegistry.create(Heraldia.id("dialogos"),
				b -> b.persistent(Memory.Player.CODEC).copyOnDeath());

		private Attachments() {
		}
	}

	/** One line in Heraldia.onInitialize. */
	public static void register() {
		Attachments.VILLAGER.identifier();
		Attachments.PLAYER.identifier();
		UseEntityCallback.EVENT.register((player, level, hand, entity, hit) -> {
			if (player instanceof ServerPlayer p && level instanceof ServerLevel sl && entity instanceof Villager v
					&& entity.getType() == EntityTypes.VILLAGER && click(p, sl, hand, v)) {
				return InteractionResult.SUCCESS;
			}
			return InteractionResult.PASS;
		});
		ServerPlayConnectionEvents.DISCONNECT.register((handler, server) -> TALKS.remove(handler.getPlayer().getUUID()));
		ServerLifecycleEvents.SERVER_STOPPED.register(server -> TALKS.clear());
	}

	static boolean enabled() {
		return HeraldiaConfig.get().getBool(ENABLED);
	}

	// --- the click ---

	static boolean itemWithUse(ItemStack s) {
		return s.is(Items.NAME_TAG) || s.is(Items.LEAD) || s.getItem() instanceof SpawnEggItem;
	}

	/** A right click on a villager: true if it opens a conversation (and the trades do not open). */
	static boolean click(ServerPlayer p, ServerLevel level, InteractionHand hand, Villager v) {
		Gesture.Click c = new Gesture.Click(enabled(), hand == InteractionHand.MAIN_HAND, p.isShiftKeyDown(), p.isSpectator(),
				v.entityTags().contains(HERALDIA_VILLAGER), v.entityTags().contains(Quests.BAILIFF), v.isBaby(), v.isSleeping(),
				v.isTrading(), itemWithUse(p.getMainHandItem()));
		if (!Gesture.mayTalk(c)) {
			return false;
		}
		Quests.VillageView a = Quests.villageView(level, v.blockPosition());
		if (a == null) {
			return false;
		}
		start(p, level, v, a);
		return true;
	}

	static void start(ServerPlayer p, ServerLevel level, Villager v, Quests.VillageView a) {
		long now = level.getGameTime();
		Memory.Villager mem = villager(v);
		long wait = HeraldiaConfig.get().getInt(WAIT) * 20L;
		Out o = new Out(p, Texts.language(p), Lines.of(Texts.code(p)), p::sendSystemMessage);
		v.getLookControl().setLookAt(p);
		Talk current = TALKS.get(p.getUUID());
		if (current != null && current.villager().equals(v.getUUID()) && current.more() > 0 && now - current.started() <= TTL
				&& now >= current.started()) {
			more(o, current, level, v, a);      // clicking again the villager you are talking to: it goes on
			return;
		}
		Talk t = new Talk(v.getUUID(), MORE, false, now, a.cx(), a.cz(), a.style(), a.family(), a.name());
		if (mem.resting(now, wait)) {
			say(o, v, a, o.one("busy"));
			TALKS.put(p.getUUID(), t.withMore(0).withAsked());
			buttons(o, false, false);
			o.gray("agacharse");
			LOGGER.info("Heraldia: diálogos: {} habla con un aldeano de {}: está ocupado ({} s)", p.getGameProfile().name(), a.name(),
					(mem.left(now, wait) + 19) / 20);
			return;
		}
		v.setAttached(Attachments.VILLAGER, mem.talks(now));
		v.playAmbientSound();
		Context ctx = context(p, level, v, a);
		say(o, v, a, o.one(ctx.greeting()));
		say(o, v, a, o.body(ctx));
		TALKS.put(p.getUUID(), t);
		buttons(o, true, true);
		LOGGER.info("Heraldia: diálogos: {} habla con un aldeano de {} ({}, {}, {}, {}, {})", p.getGameProfile().name(), a.name(),
				ctx.profession(), ctx.family(), ctx.moment(), ctx.weather(), ctx.tier().id());
	}

	static Context context(ServerPlayer p, ServerLevel level, Villager v, Quests.VillageView a) {
		String profession = v.getVillagerData().profession().unwrapKey().map(k -> k.identifier().getPath()).orElse("none");
		BlockPos pos = v.blockPosition();
		Biome.Precipitation pr = level.getBiome(pos).value().getPrecipitationAt(pos, level.getSeaLevel());
		String weather = Context.weather(level.isRaining() && pr != Biome.Precipitation.NONE, level.isThundering(),
				pr == Biome.Precipitation.SNOW);
		Reputation.Tier tier = HeraldiaConfig.get().getBool(Quests.REPUTATION) ? Reputation.tier(Quests.reputation(p, a.cx(), a.cz()))
				: Reputation.Tier.UNKNOWN;
		return new Context(profession, a.family(), Context.moment(level.getOverworldClockTime()), weather, tier);
	}

	// --- memory ---

	static Memory.Villager villager(Villager v) {
		Memory.Villager m = v.getAttached(Attachments.VILLAGER);
		return m == null ? Memory.Villager.EMPTY : m;
	}

	static List<String> recent(ServerPlayer p) {
		Memory.Player m = p.getAttached(Attachments.PLAYER);
		return m == null ? List.of() : m.recent();
	}

	static void heard(ServerPlayer p, Lines.Line line) {
		Memory.Player m = p.getAttached(Attachments.PLAYER);
		p.setAttached(Attachments.PLAYER, (m == null ? Memory.Player.EMPTY : m).heard(line.key()));
	}

	// --- texts ---

	/** A villager's line in chat: "Farmer: “...”", with the player's and the village's names for its slots. */
	static void say(Out o, Villager v, Quests.VillageView a, Lines.@Nullable Line line) {
		sayWith(o, v, line, o.p().getName(), Component.literal(a.name()));
	}

	static void sayWith(Out o, Villager v, Lines.@Nullable Line line, Object... args) {
		if (line == null) {
			return;
		}
		MutableComponent text = Component.translatableWithFallback(K + "frase." + line.key(), line.text(), args);
		o.out().accept(Texts.t(o.l(), K + "linea", v.getDisplayName(), text).withStyle(ChatFormatting.WHITE));
		heard(o.p(), line);
	}

	/** Where the texts go: the player's chat on a click; the command's source for the buttons (the console sees it too
	 *  with "execute as", as the job board does). */
	record Out(ServerPlayer p, Map<String, String> l, Lines lines, Consumer<Component> out) {
		Lines.@Nullable Line one(String pool) {
			return Selector.one(lines, pool, recent(p), ThreadLocalRandom.current());
		}

		Lines.@Nullable Line body(Context c) {
			return Selector.body(lines, c.pools(), recent(p), ThreadLocalRandom.current());
		}

		void gray(String key) {
			out.accept(Texts.t(l, K + key).withStyle(ChatFormatting.GRAY, ChatFormatting.ITALIC));
		}
	}

	static Component button(Map<String, String> l, String key, String order, ChatFormatting color) {
		return Texts.t(l, K + "boton." + key).withStyle(s -> s.withColor(color).withClickEvent(new ClickEvent.RunCommand(order))
				.withHoverEvent(new HoverEvent.ShowText(Component.literal(order))));
	}

	/** The answers: [Keep talking] [Any news?] [Trade] [Goodbye], only those that still make sense. */
	static void buttons(Out o, boolean more, boolean news) {
		Map<String, String> l = o.l();
		MutableComponent row = Component.empty();
		if (more) {
			row.append(button(l, "mas", "/heraldia talk more", ChatFormatting.AQUA)).append(" ");
		}
		if (news) {
			row.append(button(l, "rumores", "/heraldia talk rumor", ChatFormatting.LIGHT_PURPLE)).append(" ");
		}
		row.append(button(l, "tratar", "/heraldia talk trade", ChatFormatting.GREEN)).append(" ")
				.append(button(l, "adios", "/heraldia talk bye", ChatFormatting.GRAY));
		o.out().accept(row);
	}

	// --- the buttons: /heraldia talk [more | rumor | trade | bye] ---

	public static LiteralArgumentBuilder<CommandSourceStack> node() {
		return Commands.literal("talk")
				.executes(ctx -> answer(ctx, "more"))
				.then(Commands.literal("more").executes(ctx -> answer(ctx, "more")))
				.then(Commands.literal("rumor").executes(ctx -> answer(ctx, "rumor")))
				.then(Commands.literal("trade").executes(ctx -> answer(ctx, "trade")))
				.then(Commands.literal("bye").executes(ctx -> answer(ctx, "bye")))
				.then(Commands.literal("with").requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))
						.then(Commands.argument("villager", EntityArgument.entity()).executes(Dialogue::with)));
	}

	/**
	 * /heraldia talk with &lt;villager&gt; (operators): opens a conversation with that villager as a click would, whatever
	 * the hand, sneaking or the item held (to preview the lines, take screenshots, and for the server tests: a simulated
	 * Carpet player's click does not go through the network packet, so it trades as always).
	 */
	private static int with(CommandContext<CommandSourceStack> ctx) throws CommandSyntaxException {
		CommandSourceStack src = ctx.getSource();
		ServerPlayer p = src.getPlayerOrException();
		Map<String, String> l = Texts.language(p);
		if (!enabled()) {
			src.sendFailure(Texts.t(l, K + "desactivados"));
			return 0;
		}
		Entity e = EntityArgument.getEntity(ctx, "villager");
		Quests.VillageView a = e instanceof Villager v && e.getType() == EntityTypes.VILLAGER && v.entityTags().contains(HERALDIA_VILLAGER)
				&& !v.entityTags().contains(Quests.BAILIFF) && e.level() == p.level() ? Quests.villageView(p.level(), e.blockPosition()) : null;
		if (a == null) {
			src.sendFailure(Texts.t(l, K + "no_habla"));
			return 0;
		}
		start(p, p.level(), (Villager) e, a);
		return 1;
	}

	private static int answer(CommandContext<CommandSourceStack> ctx, String what) throws CommandSyntaxException {
		CommandSourceStack src = ctx.getSource();
		ServerPlayer p = src.getPlayerOrException();
		Map<String, String> l = Texts.language(p);
		if (!enabled()) {
			src.sendFailure(Texts.t(l, K + "desactivados"));
			return 0;
		}
		Talk t = TALKS.get(p.getUUID());
		if (t == null) {
			src.sendFailure(Texts.t(l, K + "sin_charla"));
			return 0;
		}
		ServerLevel level = p.level();
		Entity e = level.getEntity(t.villager());
		long now = level.getGameTime();
		if (!(e instanceof Villager v) || !v.isAlive() || v.distanceTo(p) > RANGE || now - t.started() > TTL || now < t.started()) {
			TALKS.remove(p.getUUID());
			src.sendFailure(Texts.t(l, K + "lejos"));
			return 0;
		}
		Out o = new Out(p, l, Lines.of(Texts.code(p)), c -> src.sendSuccess(() -> c, false));
		Quests.VillageView a = t.village();
		v.getLookControl().setLookAt(p);
		switch (what) {
			case "trade" -> {
				TALKS.remove(p.getUUID());
				v.mobInteract(p, InteractionHand.MAIN_HAND);
				LOGGER.info("Heraldia: diálogos: {} comercia con un aldeano de {}", p.getGameProfile().name(), a.name());
			}
			case "bye" -> {
				TALKS.remove(p.getUUID());
				say(o, v, a, o.one("farewell"));
			}
			case "rumor" -> {
				if (t.asked()) {
					say(o, v, a, o.one("busy"));
					buttons(o, false, false);
					return 1;
				}
				TALKS.put(p.getUUID(), t.withAsked());
				news(o, level, v, a, t.more() > 0);
			}
			default -> more(o, t, level, v, a);
		}
		return 1;
	}

	/** One more line ("Keep talking"); after the last one, the villager says goodbye. */
	static void more(Out o, Talk t, ServerLevel level, Villager v, Quests.VillageView a) {
		ServerPlayer p = o.p();
		if (t.more() <= 0) {
			TALKS.remove(p.getUUID());
			say(o, v, a, o.one("farewell"));
			return;
		}
		TALKS.put(p.getUUID(), t.withMore(t.more() - 1));
		say(o, v, a, o.body(context(p, level, v, a)));
		buttons(o, t.more() - 1 > 0, !t.asked());
	}

	// --- news and hints ---

	/** "Any news?": a rumour, or, from a wayfarer that trusts the player, the one place it knows (once in its life). */
	static void news(Out o, ServerLevel level, Villager v, Quests.VillageView a, boolean more) {
		HeraldiaConfig cfg = HeraldiaConfig.get();
		ServerPlayer p = o.p();
		String name = p.getGameProfile().name();
		if (!Hints.wayfarer(v.getUUID(), cfg.getInt(WAYFARERS))) {
			say(o, v, a, o.one("rumor"));
			buttons(o, more, false);
			return;
		}
		if (villager(v).hintTold()) {
			say(o, v, a, o.one("hint.told"));
			buttons(o, more, false);
			LOGGER.info("Heraldia: diálogos: un viajero de {} ya contó su pista ({} pregunta)", a.name(), name);
			return;
		}
		boolean rep = cfg.getBool(Quests.REPUTATION);
		int points = Quests.reputation(p, a.cx(), a.cz());
		if (!Hints.trusts(rep, points, cfg.getInt(HINT_REPUTATION))) {
			say(o, v, a, o.one("hint.withheld"));
			buttons(o, more, false);
			LOGGER.info("Heraldia: diálogos: un viajero de {} no se fía de {} (reputación {})", a.name(), name, points);
			return;
		}
		Quests.surroundings(level, a).thenAcceptAsync(c -> hint(o, v, a, c, more), level.getServer()).exceptionally(e -> {
			LOGGER.error("Heraldia: diálogos: pista de un aldeano de {}", a.name(), e);
			return null;
		});
	}

	static void hint(Out o, Villager v, Quests.VillageView a, Generator.Candidates c, boolean more) {
		ServerPlayer p = o.p();
		if (!v.isAlive() || p.isRemoved()) {
			return;
		}
		if (villager(v).hintTold()) {        // another player got it first while the search ran
			say(o, v, a, o.one("hint.told"));
			buttons(o, more, false);
			return;
		}
		Hints.Place place = Hints.choose(v.getUUID(), places(c));
		if (place == null) {
			say(o, v, a, o.one("hint.nothing"));
			buttons(o, more, false);
			LOGGER.info("Heraldia: diálogos: un viajero de {} no conoce nada cerca", a.name());
			return;
		}
		Map<String, String> l = o.l();
		int x = p.getBlockX(), z = p.getBlockZ();
		Component name = "unique".equals(place.kind()) ? Texts.t(l, "heraldia.unicas." + place.id() + ".nombre") : Quests.place(l, place.id());
		Component dir = Texts.t(l, "heraldia.info.dir." + Objectives.bearing(x, z, place.x(), place.z()));
		int distance = Objectives.approximate(x, z, place.x(), place.z());
		sayWith(o, v, o.one("hint." + place.kind()), name, dir, distance);
		o.gray("pista.mas");
		v.setAttached(Attachments.VILLAGER, villager(v).tellsHint());
		buttons(o, more, false);
		LOGGER.info("Heraldia: diálogos: un viajero de {} le cuenta a {} dónde está {} ({}, {}): {} a unos {} bloques",
				a.name(), p.getGameProfile().name(), place.id(), place.x(), place.z(), Objectives.bearing(x, z, place.x(), place.z()), distance);
	}

	/** The places around the village a wayfarer may know: the uniques with a guardian, the mediums and the mine entrances. */
	static List<Hints.Place> places(Generator.Candidates c) {
		List<Hints.Place> out = new ArrayList<>();
		for (Generator.Objective o : c.guardians()) {
			out.add(new Hints.Place("unique", o.id(), o.x(), o.z(), o.distance()));
		}
		for (Generator.Objective o : c.places()) {
			Identifier id = Identifier.tryParse(o.id());
			out.add(new Hints.Place(id != null && Mines.isMine(id) ? "mine" : "medium", o.id(), o.x(), o.z(), o.distance()));
		}
		return out;
	}
}
