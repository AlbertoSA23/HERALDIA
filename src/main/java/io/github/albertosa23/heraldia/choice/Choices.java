package io.github.albertosa23.heraldia.choice;

import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.arguments.IntegerArgumentType;
import com.mojang.brigadier.arguments.StringArgumentType;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import it.unimi.dsi.fastutil.ints.Int2ObjectMaps;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.OptionalInt;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.Predicate;
import net.fabricmc.fabric.api.entity.FakePlayer;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.fabricmc.fabric.api.networking.v1.ServerPlayConnectionEvents;
import net.fabricmc.fabric.api.networking.v1.ServerPlayNetworking;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.SharedSuggestionProvider;
import net.minecraft.locale.Language;
import net.minecraft.network.HashedStack;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.contents.PlainTextContents;
import net.minecraft.network.chat.contents.TranslatableContents;
import net.minecraft.network.protocol.game.ServerboundContainerClickPacket;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.SimpleMenuProvider;
import net.minecraft.world.inventory.ContainerInput;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * The game side of a {@link Choice}: which presentation each player gets, what each one was offered, and the replies.
 * Used by the villager conversations (dialogue/Dialogue) and the arena bell's mode menu (arena/Game), so both look and
 * behave the same.
 * <ul>
 * <li>{@link #presentation}: the screen if the player's client registered this protocol's channel (Fabric's channel
 * registration: a real handshake, not a guess), otherwise the container menu; the chat only with
 * {@code dialogos.en_pantalla} off or for automation's fake players (Fabric's {@link FakePlayer}), which cannot see a
 * window. A caller whose {@link #show} returns false prints its old chat version instead.</li>
 * <li>Each player has at most one choice open ({@link Pending}); a new one replaces it under a new session number.</li>
 * <li>{@link #reply}: <b>the client is never trusted.</b> A reply counts only for the player's current session and an
 * option that is on screen in it, once (the choice is consumed before its handler runs), and only while the choice is
 * still valid (its {@code still} test: the villager alive and near, the player in the ring...). The handler then checks
 * its own rules again (a mode still enabled, the conversation still on...). Anything else is refused, logged and
 * changes nothing.</li>
 * <li>No per-tick work: everything happens on a click or a reply. What is pending lives in memory only and goes when the
 * player leaves or the server stops.</li>
 * </ul>
 */
public final class Choices {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	/** The server's option: false keeps the old chat buttons for everyone (dialogue and arena). */
	public static final String ON_SCREEN = "dialogos.en_pantalla";
	private static final Map<UUID, Pending> PENDING = new ConcurrentHashMap<>();
	private static final AtomicInteger SESSIONS = new AtomicInteger();

	private Choices() {
	}

	/**
	 * What happens when the player picks an option (on the server thread, after the reply was checked). It shows the next
	 * page with {@link #show}, opens another window, or does neither and the choice window closes; true if its answer
	 * comes later (the window then stays open, with nothing left to pick, until that answer shows or {@link #close}).
	 */
	@FunctionalInterface
	public interface Handler {
		boolean picked(ServerPlayer p, String id);
	}

	/** A choice on a player's screen: what was offered, how, what it is about (for the log) and what still holds. */
	record Pending(Choice.Offer offer, Choice.Prompt prompt, Choice.Presentation how, String what, Predicate<ServerPlayer> still,
			Handler handler) {
	}

	/** One line in Heraldia.onInitialize. */
	public static void register() {
		ChoicePayloads.register();
		ServerPlayNetworking.registerGlobalReceiver(ChoicePayloads.Pick.TYPE,
				(payload, ctx) -> reply(ctx.player(), payload.session(), payload.option(), "screen"));
		ServerPlayConnectionEvents.DISCONNECT.register((handler, server) -> PENDING.remove(handler.getPlayer().getUUID()));
		ServerLifecycleEvents.SERVER_STOPPED.register(server -> PENDING.clear());
	}

	/** How a choice reaches this player now (see the class comment). */
	public static Choice.Presentation presentation(ServerPlayer p) {
		return Choice.Presentation.of(HeraldiaConfig.get().getBool(ON_SCREEN), !(p instanceof FakePlayer),
				ServerPlayNetworking.canSend(p, ChoicePayloads.Open.TYPE));
	}

	/**
	 * Shows {@code prompt} to {@code p} in the middle of the screen (replacing any choice they had open). False if it
	 * goes to the chat instead (the option is off, or nothing could open): the caller then prints its chat version.
	 *
	 * @param what  what it is about, for the log ("dialogue", "arena")
	 * @param still while this holds, the choice stays open and its options can be picked
	 */
	public static boolean show(ServerPlayer p, String what, Choice.Prompt prompt, Predicate<ServerPlayer> still, Handler handler) {
		Choice.Presentation how = presentation(p);
		if (how == Choice.Presentation.CHAT) {
			PENDING.remove(p.getUUID());
			return false;
		}
		int session = SESSIONS.incrementAndGet();
		Pending pending = new Pending(new Choice.Offer(session, prompt.ids()), prompt, how, what, still, handler);
		PENDING.put(p.getUUID(), pending);
		if (how == Choice.Presentation.SCREEN) {
			ServerPlayNetworking.send(p, new ChoicePayloads.Open(session, prompt));
		} else if (p.containerMenu instanceof ChoiceMenu m && m.shownTitle().equals(prompt.title())) {
			m.fill(session, prompt);           // the next page of the same window: no flicker, the mouse stays put
		} else {
			OptionalInt id = p.openMenu(new SimpleMenuProvider((cid, inventory, player) -> ChoiceMenu.create(cid, inventory, p, session,
					prompt), prompt.title()));
			if (id.isEmpty()) {
				PENDING.remove(p.getUUID(), pending);
				LOGGER.info("Heraldia: choice: {} cannot open the {} menu: chat instead", p.getGameProfile().name(), what);
				return false;
			}
		}
		LOGGER.info("Heraldia: choice: {} sees {} as {} (session {}: {})", p.getGameProfile().name(), what,
				how.name().toLowerCase(Locale.ROOT), session, String.join(", ", prompt.ids()));
		return true;
	}

	/** Closes the player's choice, if any (its window closes on their client too). */
	public static void close(ServerPlayer p) {
		Pending pending = PENDING.remove(p.getUUID());
		if (pending != null) {
			dismiss(p, pending);
		}
	}

	private static void dismiss(ServerPlayer p, Pending pending) {
		if (pending.how() == Choice.Presentation.SCREEN) {
			ServerPlayNetworking.send(p, new ChoicePayloads.Close(pending.offer().session()));
		} else if (p.containerMenu instanceof ChoiceMenu m && m.session() == pending.offer().session()) {
			p.closeContainer();
		}
	}

	/**
	 * A reply from the client (the screen's payload, or a click in the menu): the option counts only if it is on offer
	 * in the player's current session and the choice is still valid; then the choice is consumed and its handler runs
	 * (which checks its own rules again). True if it was accepted.
	 */
	static boolean reply(ServerPlayer p, int session, String id, String from) {
		String name = p.getGameProfile().name();
		Pending pending = PENDING.get(p.getUUID());
		if (pending == null || !pending.offer().accepts(session, id)) {
			LOGGER.info("Heraldia: choice: refused from {} ({}): session {}, option '{}' was not on offer{}", name, from, session, id,
					pending == null ? " (no choice open)" : " (session " + pending.offer().session() + ": "
							+ String.join(", ", pending.offer().ids()) + ")");
			return false;
		}
		if (Choice.CLOSED.equals(id)) {
			PENDING.remove(p.getUUID(), pending);
			return true;
		}
		if (!pending.still().test(p)) {
			LOGGER.info("Heraldia: choice: refused from {} ({}): {} is no longer valid", name, from, pending.what());
			close(p);
			return false;
		}
		PENDING.remove(p.getUUID(), pending);          // one reply per page: a second click of the same page is refused
		LOGGER.info("Heraldia: choice: {} picks {} in {} (session {}, from the {})", name, id, pending.what(), session, from);
		boolean later = pending.handler().picked(p, id);
		if (PENDING.get(p.getUUID()) == null) {          // no next page (or another window): close, or wait for the answer
			if (later && !p.isRemoved()) {
				PENDING.put(p.getUUID(), new Pending(new Choice.Offer(session, List.of()), pending.prompt(), pending.how(), pending.what(),
						pending.still(), pending.handler()));
			} else {
				dismiss(p, pending);
			}
		}
		return true;
	}

	/** A click on an option in the menu: handled after the click packet (the handler may open another window). */
	static void menuPick(ServerPlayer p, int session, String id) {
		MinecraftServer server = p.level().getServer();
		server.schedule(server.wrapRunnable(() -> reply(p, session, id, "menu")));
	}

	/** The menu closed (the player closed it, walked away, or another window replaced it). */
	static void menuClosed(ServerPlayer p, int session) {
		Pending pending = PENDING.get(p.getUUID());
		if (pending != null && pending.offer().session() == session) {
			PENDING.remove(p.getUUID(), pending);
		}
	}

	/** For the menu's stillValid (vanilla closes the window when this turns false). */
	static boolean stillValid(ServerPlayer p, int session) {
		Pending pending = PENDING.get(p.getUUID());
		return pending == null || pending.offer().session() != session || pending.still().test(p);
	}

	// --- texts in the player's language ---

	/**
	 * A text component as a plain string in the language {@code texts} (the .jar's texts for the player, see
	 * command/Texts): translatable parts from {@code texts}, else their fallback, else the server's own language (the
	 * vanilla keys); arguments filled in the same way.
	 */
	public static String text(Component c, Map<String, String> texts) {
		StringBuilder out = new StringBuilder();
		append(out, c, texts, 0);
		return out.toString();
	}

	private static void append(StringBuilder out, Component c, Map<String, String> texts, int depth) {
		if (depth > 16) {
			return;
		}
		if (c.getContents() instanceof TranslatableContents t) {
			String pattern = texts.get(t.getKey());
			if (pattern == null) {
				pattern = t.getFallback() != null ? t.getFallback() : Language.getInstance().getOrDefault(t.getKey());
			}
			List<String> args = new ArrayList<>();
			for (Object a : t.getArgs()) {
				if (a instanceof Component ac) {
					StringBuilder s = new StringBuilder();
					append(s, ac, texts, depth + 1);
					args.add(s.toString());
				} else {
					args.add(String.valueOf(a));
				}
			}
			out.append(Choice.format(pattern, args));
		} else if (c.getContents() instanceof PlainTextContents p) {
			out.append(p.text());
		} else {
			c.getContents().visit(s -> {
				out.append(s);
				return java.util.Optional.empty();
			});
		}
		for (Component sibling : c.getSiblings()) {
			append(out, sibling, texts, depth + 1);
		}
	}

	// --- for the server tests and for checking by hand (operators): /heraldia choice [click | reply] ---

	/**
	 * /heraldia choice: the executing player's open choice (session, presentation, options). /heraldia choice click
	 * &lt;slot&gt; [&lt;input&gt; [&lt;button&gt;]]: a click in their open window exactly as a client sends it (a real
	 * container click packet, through the player's own connection handler: the same checks a vanilla client's click goes
	 * through). /heraldia choice reply &lt;session&gt; &lt;option&gt;: a reply exactly as the screen's payload brings it.
	 * The simulated players of the tests (Carpet) have no client to click with or to send payloads; with these, a test
	 * plays the vanilla client (menu) and a modified one (any reply it likes) and checks what the server accepts.
	 */
	public static LiteralArgumentBuilder<CommandSourceStack> node() {
		return Commands.literal("choice").requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))
				.executes(Choices::status)
				.then(Commands.literal("click").then(Commands.argument("slot", IntegerArgumentType.integer(-999, 127))
						.executes(ctx -> click(ctx, "pickup", 0))
						.then(Commands.argument("input", StringArgumentType.word())
								.suggests((ctx, b) -> SharedSuggestionProvider.suggest(inputs(), b))
								.executes(ctx -> click(ctx, StringArgumentType.getString(ctx, "input"), 0))
								.then(Commands.argument("button", IntegerArgumentType.integer(0, 40))
										.executes(ctx -> click(ctx, StringArgumentType.getString(ctx, "input"),
												IntegerArgumentType.getInteger(ctx, "button")))))))
				.then(Commands.literal("reply").then(Commands.argument("session", IntegerArgumentType.integer(0))
						.then(Commands.argument("option", StringArgumentType.word())
								.executes(ctx -> {
									ServerPlayer p = ctx.getSource().getPlayerOrException();
									boolean ok = reply(p, IntegerArgumentType.getInteger(ctx, "session"),
											StringArgumentType.getString(ctx, "option"), "command");
									ctx.getSource().sendSuccess(() -> Component.literal("choice reply " + (ok ? "accepted" : "refused")), false);
									return ok ? 1 : 0;
								}))));
	}

	private static List<String> inputs() {
		List<String> out = new ArrayList<>();
		for (ContainerInput i : ContainerInput.values()) {
			out.add(i.name().toLowerCase(Locale.ROOT));
		}
		return out;
	}

	private static int status(CommandContext<CommandSourceStack> ctx) throws CommandSyntaxException {
		ServerPlayer p = ctx.getSource().getPlayerOrException();
		Pending pending = PENDING.get(p.getUUID());
		String menu = p.containerMenu instanceof ChoiceMenu m ? "choice menu " + m.session() : p.containerMenu == p.inventoryMenu
				? "no window" : "another window";
		String line = pending == null ? "choice: none (" + menu + ", would show as " + presentation(p).name().toLowerCase(Locale.ROOT) + ")"
				: "choice: session " + pending.offer().session() + ", " + pending.what() + ", "
						+ pending.how().name().toLowerCase(Locale.ROOT) + " (" + menu + "): " + String.join(", ", pending.offer().ids());
		ctx.getSource().sendSuccess(() -> Component.literal(line), false);
		return pending == null ? 0 : pending.offer().session();
	}

	private static int click(CommandContext<CommandSourceStack> ctx, String input, int button) throws CommandSyntaxException {
		ServerPlayer p = ctx.getSource().getPlayerOrException();
		ContainerInput kind = null;
		for (ContainerInput i : ContainerInput.values()) {
			if (i.name().equalsIgnoreCase(input)) {
				kind = i;
			}
		}
		if (kind == null) {
			ctx.getSource().sendFailure(Component.literal("choice click: unknown input " + input + " (" + String.join(", ", inputs()) + ")"));
			return 0;
		}
		int slot = IntegerArgumentType.getInteger(ctx, "slot");
		var menu = p.containerMenu;
		// what a client that predicts nothing sends: no changed slots, nothing on the cursor (the server's resync answers)
		p.connection.handleContainerClick(new ServerboundContainerClickPacket(menu.containerId, menu.getStateId(), (short) slot,
				(byte) button, kind, Int2ObjectMaps.emptyMap(), HashedStack.EMPTY));
		String line = "choice click: slot " + slot + " " + kind.name().toLowerCase(Locale.ROOT) + " " + button + " in window "
				+ menu.containerId + (menu instanceof ChoiceMenu m ? " (choice menu " + m.session() + ")" : "");
		ctx.getSource().sendSuccess(() -> Component.literal(line), false);
		return 1;
	}
}
