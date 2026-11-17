package io.github.albertosa23.heraldia.comando;

import com.google.gson.JsonPrimitive;
import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.context.CommandContext;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.config.Perfiles;
import java.util.ArrayList;
import java.util.List;
import net.fabricmc.fabric.api.command.v2.CommandRegistrationCallback;
import net.minecraft.ChatFormatting;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.network.chat.Component;

/**
 * /heraldia profile (operadores): el perfil de juego en uso (el efectivo y el elegido en el fichero) y los valores que da
 * a cada una de sus opciones, marcando las fijadas a mano que mandan sobre el perfil. Solo lee la configuración en uso
 * (la de {@link HeraldiaConfig#get()}, también tras una recarga). Comando nuevo: en inglés.
 */
public final class ProfileCommand {
	private ProfileCommand() {
	}

	public static void register() {
		CommandRegistrationCallback.EVENT.register((dispatcher, access, environment) -> build(dispatcher));
	}

	private static void build(CommandDispatcher<CommandSourceStack> dispatcher) {
		dispatcher.register(Commands.literal("heraldia")
				.then(Commands.literal("profile")
						.requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))
						.executes(ProfileCommand::show)));
	}

	private static int show(CommandContext<CommandSourceStack> ctx) {
		List<Component> lines = lines(HeraldiaConfig.get());
		lines.forEach(l -> ctx.getSource().sendSuccess(() -> l, false));
		return lines.size();
	}

	/** Las líneas de la respuesta (pública para las pruebas). */
	public static List<Component> lines(HeraldiaConfig cfg) {
		Perfiles.Aplicado p = cfg.profile();
		List<Component> out = new ArrayList<>();
		out.add(Textos.t("heraldia.perfil.titulo", nombre(p.efectivo()), nombre(p.elegido())).withStyle(ChatFormatting.GOLD));
		for (String k : HeraldiaConfig.profiles().claves()) {
			JsonPrimitive v = cfg.values().get(k);
			JsonPrimitive[] d = p.difieren().get(k);
			out.add(d != null ? Textos.t("heraldia.perfil.opcion.fijada", k, v.getAsString(), d[1].getAsString()).withStyle(ChatFormatting.YELLOW)
					: Textos.t("heraldia.perfil.opcion", k, v.getAsString()));
		}
		out.add(p.difieren().isEmpty() ? Textos.t("heraldia.perfil.ninguna").withStyle(ChatFormatting.GRAY)
				: Textos.t("heraldia.perfil.personalizado").withStyle(ChatFormatting.GRAY));
		return out;
	}

	private static Component nombre(String perfil) {
		return Textos.t("heraldia.config.perfil." + perfil);
	}
}
