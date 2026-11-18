package io.github.albertosa23.heraldia.command;

import com.mojang.brigadier.arguments.StringArgumentType;
import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.serialization.Codec;
import io.github.albertosa23.heraldia.Heraldia;
import java.util.Collection;
import java.util.Map;
import java.util.Optional;
import net.fabricmc.fabric.api.attachment.v1.AttachmentRegistry;
import net.fabricmc.fabric.api.attachment.v1.AttachmentType;
import net.minecraft.ChatFormatting;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.SharedSuggestionProvider;
import net.minecraft.network.chat.ClickEvent;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.HoverEvent;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerPlayer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Minimal personal preferences of each player (T46): the language of Heraldia's texts. /heraldia language (for
 * everyone) shows the language in use and gives one button per language; /heraldia language &lt;code&gt; sets it and
 * /heraldia language auto goes back to the client's. It is saved with the player (Fabric API persistent attachment, also
 * after death) and overrides the client's language in {@link Texts#language(ServerPlayer)}. A client without the mod sees the
 * fallback texts, which are already in the chosen language; one with the mod translates the keys with its own language.
 */
public final class Preferences {
	private static final Logger LOGGER = LoggerFactory.getLogger(Heraldia.MOD_ID);
	/** Argument value that goes back to the client's language (in English: it is a literal that is typed). */
	public static final String AUTO = "auto";

	private Preferences() {
	}

	/** The attachment, kept apart so the tests register nothing when the class loads. */
	static final class Type {
		static final AttachmentType<String> LANGUAGE = AttachmentRegistry.create(Heraldia.id("idioma"),
				b -> b.persistent(Codec.STRING).copyOnDeath());

		private Type() {
		}
	}

	public static void register() {
		Type.LANGUAGE.identifier();
	}

	/** The language the player chose, if any (and the .jar has it). */
	public static Optional<String> language(ServerPlayer p) {
		String v = p.getAttached(Type.LANGUAGE);
		return v != null && Texts.languages().contains(v) ? Optional.of(v) : Optional.empty();
	}

	/**
	 * What is saved for what the player types (pure logic): {@link #AUTO} (or empty) clears the preference; a
	 * code from the .jar (in any letter case) is saved as is; anything else is invalid.
	 */
	static Optional<Optional<String>> choose(String text, Collection<String> available) {
		String t = text == null ? "" : text.strip().toLowerCase(java.util.Locale.ROOT);
		if (t.isEmpty() || AUTO.equals(t)) {
			return Optional.of(Optional.empty());
		}
		return available.contains(t) ? Optional.of(Optional.of(t)) : Optional.empty();
	}

	/** /heraldia language [auto|&lt;code&gt;] (hung by {@link HeraldiaCommands#tree}): for all players. */
	static LiteralArgumentBuilder<CommandSourceStack> node() {
		return Commands.literal("language")
				.executes(Preferences::show)
				.then(Commands.argument("language", StringArgumentType.word())
						.suggests((c, b) -> SharedSuggestionProvider.suggest(
								java.util.stream.Stream.concat(java.util.stream.Stream.of(AUTO), Texts.languages().stream()), b))
						.executes(c -> setLanguage(c, StringArgumentType.getString(c, "language"))));
	}

	private static int show(CommandContext<CommandSourceStack> ctx) {
		ServerPlayer p = ctx.getSource().getPlayer();
		if (p == null) {
			ctx.getSource().sendFailure(Texts.t("heraldia.idioma.solo_jugadores"));
			return 0;
		}
		Map<String, String> l = Texts.language(p);
		p.sendSystemMessage(Texts.t(l, language(p).isPresent() ? "heraldia.idioma.actual" : "heraldia.idioma.actual_cliente",
				name(l, Texts.code(p))).withStyle(ChatFormatting.GOLD));
		MutableComponent row = Component.empty();
		for (String c : Texts.languages()) {
			row.append(button(Component.literal("[" + name(l, c) + "]"), "/heraldia language " + c, c)).append(" ");
		}
		row.append(button(Texts.t(l, "heraldia.idioma.auto"), "/heraldia language " + AUTO, AUTO));
		p.sendSystemMessage(row);
		return 1;
	}

	private static int setLanguage(CommandContext<CommandSourceStack> ctx, String text) {
		ServerPlayer p = ctx.getSource().getPlayer();
		if (p == null) {
			ctx.getSource().sendFailure(Texts.t("heraldia.idioma.solo_jugadores"));
			return 0;
		}
		Optional<Optional<String>> choice = choose(text, Texts.languages());
		if (choice.isEmpty()) {
			ctx.getSource().sendFailure(Texts.t(Texts.language(p), "heraldia.idioma.no_existe", text, String.join(", ", Texts.languages())));
			return 0;
		}
		if (choice.get().isPresent()) {
			p.setAttached(Type.LANGUAGE, choice.get().get());
		} else {
			p.removeAttached(Type.LANGUAGE);
		}
		Map<String, String> l = Texts.language(p);
		p.sendSystemMessage(Texts.t(l, choice.get().isPresent() ? "heraldia.idioma.fijado" : "heraldia.idioma.automatico",
				name(l, Texts.code(p))).withStyle(ChatFormatting.GREEN));
		LOGGER.info("Heraldia: idioma de {}: {}", p.getGameProfile().name(), choice.get().orElse(AUTO));
		return 1;
	}

	/** Name of the language in itself ("Français"), the same in all languages (heraldia.idioma.nombre.&lt;code&gt;). */
	private static Component name(Map<String, String> l, String code) {
		return Texts.t(l, "heraldia.idioma.nombre." + code);
	}

	private static Component button(Component text, String cmd, String hover) {
		return text.copy().withStyle(s -> s.withColor(ChatFormatting.AQUA).withClickEvent(new ClickEvent.RunCommand(cmd))
				.withHoverEvent(new HoverEvent.ShowText(Component.literal(hover))));
	}
}
