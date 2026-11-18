package io.github.albertosa23.heraldia.command;

import com.google.gson.JsonPrimitive;
import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.config.Profiles;
import java.util.ArrayList;
import java.util.List;
import net.minecraft.ChatFormatting;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.network.chat.Component;

/**
 * /heraldia profile (operators): the gameplay profile in use (the effective one and the one chosen in the file) and the values it
 * gives each of its options, marking those set by hand that override the profile. It only reads the configuration in use
 * (that of {@link HeraldiaConfig#get()}, also after a reload). New command: in English.
 */
public final class ProfileCommand {
	private ProfileCommand() {
	}

	/** /heraldia profile (hung by {@link HeraldiaCommands#tree}). */
	static LiteralArgumentBuilder<CommandSourceStack> node() {
		return Commands.literal("profile")
				.requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))
				.executes(ProfileCommand::show);
	}

	private static int show(CommandContext<CommandSourceStack> ctx) {
		List<Component> lines = lines(HeraldiaConfig.get());
		lines.forEach(l -> ctx.getSource().sendSuccess(() -> l, false));
		return lines.size();
	}

	/** The lines of the reply (public for the tests). */
	public static List<Component> lines(HeraldiaConfig cfg) {
		Profiles.Applied p = cfg.profile();
		List<Component> out = new ArrayList<>();
		out.add(Texts.t("heraldia.perfil.titulo", name(p.effective()), name(p.chosen())).withStyle(ChatFormatting.GOLD));
		for (String k : HeraldiaConfig.profiles().keys()) {
			JsonPrimitive v = cfg.values().get(k);
			JsonPrimitive[] d = p.differing().get(k);
			out.add(d != null ? Texts.t("heraldia.perfil.opcion.fijada", k, v.getAsString(), d[1].getAsString()).withStyle(ChatFormatting.YELLOW)
					: Texts.t("heraldia.perfil.opcion", k, v.getAsString()));
		}
		out.add(p.differing().isEmpty() ? Texts.t("heraldia.perfil.ninguna").withStyle(ChatFormatting.GRAY)
				: Texts.t("heraldia.perfil.personalizado").withStyle(ChatFormatting.GRAY));
		return out;
	}

	private static Component name(String profile) {
		return Texts.t("heraldia.config.perfil." + profile);
	}
}
