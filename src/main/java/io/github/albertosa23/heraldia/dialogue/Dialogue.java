package io.github.albertosa23.heraldia.dialogue;

import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.choice.Choice;
import io.github.albertosa23.heraldia.choice.Choices;
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
 * <li>A right click on a Heraldia villager inside a Heraldia village (see {@link Gesture}) shows a greeting and a line
 * chosen by its profession, its village's land, the hour, the weather and the player's reputation, with answers to keep
 * talking, ask for news, trade and say goodbye. They show in the middle of the screen ({@link Choices}: the mod's
 * screen with Heraldia on the client, a container menu with a vanilla client); with {@code dialogos.en_pantalla} off,
 * or if no window can open, in the chat as before (clickable text that runs /heraldia talk). Sneak + right click, or any
 * other villager, opens the trades as always.</li>
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
		Out o = Choices.presentation(p) == Choice.Presentation.CHAT ? Out.chat(p, v, p::sendSystemMessage) : Out.screen(p, v);
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
			o.gray("agacharse");
			buttons(o, false, false);
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

	/** A villager's line: in chat "Farmer: “...”"; on screen the line alone (the name is the window's title). The player's
	 *  and the village's names fill its slots. */
	static void say(Out o, Villager v, Quests.VillageView a, Lines.@Nullable Line line) {
		sayWith(o, v, line, o.p().getName(), io.github.albertosa23.heraldia.herald.HeraldHouse.NAME.equals(a.name())
				? Texts.t(o.l(), "heraldia.casa_heraldo.nombre") : Component.literal(a.name()));
	}

	static void sayWith(Out o, Villager v, Lines.@Nullable Line line, Object... args) {
		if (line == null) {
			return;
		}
		MutableComponent text = Component.translatableWithFallback(K + "frase." + line.key(), line.text(), args);
		o.line(Texts.t(o.l(), K + "linea", v.getDisplayName(), text).withStyle(ChatFormatting.WHITE),
				new Choice.Line(Choices.text(text, o.l()), Choice.WHITE, false));
		heard(o.p(), line);
	}

	/**
	 * Where a conversation goes: the chat (on a click with the option off, and for the /heraldia talk commands: the
	 * command's source, so the console sees it too with "execute as", as the job board does) or a page of a choice window
	 * ({@code chat} null), which {@link #buttons} or {@link #end} then shows.
	 */
	static final class Out {
		private final ServerPlayer p;
		private final Villager v;
		private final Map<String, String> l;
		private final Lines lines;
		private final @Nullable Consumer<Component> chat;
		/** The page in course (screen), with its chat version in case no window can open. */
		private final List<Choice.Line> page = new ArrayList<>();
		private final List<Component> chatPage = new ArrayList<>();

		private Out(ServerPlayer p, Villager v, @Nullable Consumer<Component> chat) {
			this.p = p;
			this.v = v;
			this.l = Texts.language(p);
			this.lines = Lines.of(Texts.code(p));
			this.chat = chat;
		}

		static Out chat(ServerPlayer p, Villager v, Consumer<Component> out) {
			return new Out(p, v, out);
		}

		static Out screen(ServerPlayer p, Villager v) {
			return new Out(p, v, null);
		}

		ServerPlayer p() {
			return p;
		}

		Map<String, String> l() {
			return l;
		}

		boolean onScreen() {
			return chat == null;
		}

		void line(Component inChat, Choice.Line onScreen) {
			if (chat != null) {
				chat.accept(inChat);
			} else {
				page.add(onScreen);
				chatPage.add(inChat);
			}
		}

		Lines.@Nullable Line one(String pool) {
			return Selector.one(lines, pool, recent(p), ThreadLocalRandom.current());
		}

		Lines.@Nullable Line body(Context c) {
			return Selector.body(lines, c.pools(), recent(p), ThreadLocalRandom.current());
		}

		void gray(String key) {
			MutableComponent text = Texts.t(l, K + key);
			line(text.copy().withStyle(ChatFormatting.GRAY, ChatFormatting.ITALIC), new Choice.Line(Choices.text(text, l), Choice.GRAY, true));
		}

		/** Shows the page with these options; false if it had to go to the chat (then printed there). */
		boolean show(List<Choice.Option> options) {
			Choice.Prompt prompt = new Choice.Prompt(v.getDisplayName(), page.size() > Choice.MAX_LINES
					? page.subList(page.size() - Choice.MAX_LINES, page.size()) : page, options);
			boolean shown = Choices.show(p, "dialogue", prompt, pl -> near(pl, v), Dialogue::picked);
			if (!shown) {
				chatPage.forEach(p::sendSystemMessage);
			}
			page.clear();
			chatPage.clear();
			return shown;
		}
	}

	static Component button(Map<String, String> l, String key, String order, ChatFormatting color) {
		return Texts.t(l, K + "boton." + key).withStyle(s -> s.withColor(color).withClickEvent(new ClickEvent.RunCommand(order))
				.withHoverEvent(new HoverEvent.ShowText(Component.literal(order))));
	}

	static Choice.Option option(Map<String, String> l, String id, String key, int color) {
		return new Choice.Option(id, Choice.unbracket(Choices.text(Texts.t(l, K + "boton." + key), l)), color, "");
	}

	/** The answers: [Keep talking] [Any news?] [Trade] [Goodbye], only those that still make sense. */
	static void buttons(Out o, boolean more, boolean news) {
		Map<String, String> l = o.l();
		if (o.onScreen()) {
			List<Choice.Option> options = new ArrayList<>();
			if (more) {
				options.add(option(l, "more", "mas", Choice.AQUA));
			}
			if (news) {
				options.add(option(l, "rumor", "rumores", Choice.PURPLE));
			}
			options.add(option(l, "trade", "tratar", Choice.GREEN));
			options.add(option(l, "bye", "adios", Choice.GRAY));
			if (o.show(options)) {
				return;
			}
		}
		MutableComponent row = Component.empty();
		if (more) {
			row.append(button(l, "mas", "/heraldia talk more", ChatFormatting.AQUA)).append(" ");
		}
		if (news) {
			row.append(button(l, "rumores", "/heraldia talk rumor", ChatFormatting.LIGHT_PURPLE)).append(" ");
		}
		row.append(button(l, "tratar", "/heraldia talk trade", ChatFormatting.GREEN)).append(" ")
				.append(button(l, "adios", "/heraldia talk bye", ChatFormatting.GRAY));
		if (o.onScreen()) {
			o.p().sendSystemMessage(row);
		} else {
			o.chat.accept(row);
		}
	}

	/** The conversation is over (the villager said goodbye): on screen, its last line with only [Close]. */
	static void end(Out o) {
		if (o.onScreen()) {
			o.show(List.of(option(o.l(), "close", "cerrar", Choice.GRAY)));
		}
	}

	/** While this holds, the conversation's window stays open and its answers can be picked. */
	static boolean near(ServerPlayer p, Villager v) {
		return enabled() && v.isAlive() && v.level() == p.level() && v.distanceTo(p) <= RANGE;
	}

	/** An answer picked in the window (already checked against what was on offer, see Choices#reply). */
	static boolean picked(ServerPlayer p, String id) {
		if ("close".equals(id)) {
			return false;
		}
		return answer(p, id, v -> Out.screen(p, v), c -> p.sendOverlayMessage(c.copy().withStyle(ChatFormatting.RED))) == LATER;
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
		if (e instanceof Villager g && io.github.albertosa23.heraldia.herald.SpawnRoads.isGuide(g) && e.level() == p.level()) {
			return io.github.albertosa23.heraldia.herald.SpawnRoads.talk(p, g) ? 1 : 0;   // the Herald's House road guide
		}
		Quests.VillageView a = e instanceof Villager v && e.getType() == EntityTypes.VILLAGER && v.entityTags().contains(HERALDIA_VILLAGER)
				&& !v.entityTags().contains(Quests.BAILIFF) && e.level() == p.level() ? Quests.villageView(p.level(), e.blockPosition()) : null;
		if (a == null) {
			src.sendFailure(Texts.t(l, K + "no_habla"));
			return 0;
		}
		start(p, p.level(), (Villager) e, a);
		return 1;
	}

	/** /heraldia talk more | rumor | trade | bye: the chat's buttons, answered in the chat (any choice window closes). */
	private static int answer(CommandContext<CommandSourceStack> ctx, String what) throws CommandSyntaxException {
		CommandSourceStack src = ctx.getSource();
		ServerPlayer p = src.getPlayerOrException();
		Choices.close(p);
		return answer(p, what, v -> Out.chat(p, v, c -> src.sendSuccess(() -> c, false)), src::sendFailure) == FAILED ? 0 : 1;
	}

	static final int FAILED = 0, DONE = 1, LATER = 2;

	/**
	 * An answer (from the chat's buttons or the window): checks again that the conversation is on, the villager alive and
	 * near and the time not over, then answers. {@link #LATER} when the answer comes later (a wayfarer's hint, after the
	 * search).
	 */
	static int answer(ServerPlayer p, String what, java.util.function.Function<Villager, Out> out, Consumer<Component> fail) {
		Map<String, String> l = Texts.language(p);
		if (!enabled()) {
			fail.accept(Texts.t(l, K + "desactivados"));
			return FAILED;
		}
		Talk t = TALKS.get(p.getUUID());
		if (t == null) {
			fail.accept(Texts.t(l, K + "sin_charla"));
			return FAILED;
		}
		ServerLevel level = p.level();
		Entity e = level.getEntity(t.villager());
		long now = level.getGameTime();
		if (!(e instanceof Villager v) || !v.isAlive() || v.distanceTo(p) > RANGE || now - t.started() > TTL || now < t.started()) {
			TALKS.remove(p.getUUID());
			fail.accept(Texts.t(l, K + "lejos"));
			return FAILED;
		}
		Out o = out.apply(v);
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
				end(o);
			}
			case "rumor" -> {
				if (t.asked()) {
					say(o, v, a, o.one("busy"));
					buttons(o, false, false);
					return DONE;
				}
				TALKS.put(p.getUUID(), t.withAsked());
				return news(o, level, v, a, t.more() > 0) ? LATER : DONE;
			}
			default -> more(o, t, level, v, a);
		}
		return DONE;
	}

	/** One more line ("Keep talking"); after the last one, the villager says goodbye. */
	static void more(Out o, Talk t, ServerLevel level, Villager v, Quests.VillageView a) {
		ServerPlayer p = o.p();
		if (t.more() <= 0) {
			TALKS.remove(p.getUUID());
			say(o, v, a, o.one("farewell"));
			end(o);
			return;
		}
		TALKS.put(p.getUUID(), t.withMore(t.more() - 1));
		say(o, v, a, o.body(context(p, level, v, a)));
		buttons(o, t.more() - 1 > 0, !t.asked());
	}

	// --- news and hints ---

	/** "Any news?": a rumour, or, from a wayfarer that trusts the player, the one place it knows (once in its life). True
	 *  if the answer comes later (the search for the place runs off the server thread). */
	static boolean news(Out o, ServerLevel level, Villager v, Quests.VillageView a, boolean more) {
		HeraldiaConfig cfg = HeraldiaConfig.get();
		ServerPlayer p = o.p();
		String name = p.getGameProfile().name();
		if (!Hints.wayfarer(v.getUUID(), cfg.getInt(WAYFARERS))) {
			say(o, v, a, o.one("rumor"));
			buttons(o, more, false);
			return false;
		}
		if (villager(v).hintTold()) {
			say(o, v, a, o.one("hint.told"));
			buttons(o, more, false);
			LOGGER.info("Heraldia: diálogos: un viajero de {} ya contó su pista ({} pregunta)", a.name(), name);
			return false;
		}
		boolean rep = cfg.getBool(Quests.REPUTATION);
		int points = Quests.reputation(p, a.cx(), a.cz());
		if (!Hints.trusts(rep, points, cfg.getInt(HINT_REPUTATION))) {
			say(o, v, a, o.one("hint.withheld"));
			buttons(o, more, false);
			LOGGER.info("Heraldia: diálogos: un viajero de {} no se fía de {} (reputación {})", a.name(), name, points);
			return false;
		}
		Quests.surroundings(level, a).thenAcceptAsync(c -> hint(o, v, a, c, more), level.getServer()).exceptionally(e -> {
			LOGGER.error("Heraldia: diálogos: pista de un aldeano de {}", a.name(), e);
			return null;
		});
		return true;
	}

	static void hint(Out o, Villager v, Quests.VillageView a, Generator.Candidates c, boolean more) {
		ServerPlayer p = o.p();
		if (!v.isAlive() || p.isRemoved()) {
			if (o.onScreen() && !p.isRemoved()) {
				Choices.close(p);        // the window waited for this answer
			}
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
