package io.github.albertosa23.heraldia.command;

import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.tree.CommandNode;
import io.github.albertosa23.heraldia.arena.Arena;
import net.fabricmc.fabric.api.command.v2.CommandRegistrationCallback;
import net.minecraft.ChatFormatting;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.network.chat.ClickEvent;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.HoverEvent;
import net.minecraft.server.level.ServerPlayer;

/**
 * Todos los comandos del mod, bajo /heraldia y con nombres en inglés (los textos que ve el jugador siguen traducidos):
 * info [nearby [radius] | here], guide, key, arena, review, status, reload, update check, profile, webmap refresh, quest (encargos del tablón, T38), treasure give/info (T40), caravan (caravanas, T39, operadores) y wizard [reveal] (chozas de mago, T43, operadores); config (panel en diálogos), language (idioma de cada jugador) y update analyze/apply/undo/repair (actualizaciones seguras, T46). Los nombres antiguos en
 * español siguen funcionando como alias ocultos ({@link Alias}). Una línea en Heraldia.onInitialize.
 */
public final class HeraldiaCommands {
	private HeraldiaCommands() {
	}

	public static void register() {
		CommandRegistrationCallback.EVENT.register((dispatcher, access, environment) -> tree(dispatcher));
		ReviewCommand.registerEvents();
	}

	/** Registra /heraldia con todos sus subcomandos y sus alias antiguos; devuelve el nodo /heraldia. */
	public static CommandNode<CommandSourceStack> tree(CommandDispatcher<CommandSourceStack> dispatcher) {
		dispatcher.register(Commands.literal("heraldia")
				.then(InfoCommand.node())
				.then(Guide.node())
				.then(KeyCommand.node())
				.then(Arena.node())
				.then(ReviewCommand.node())
				.then(StatusCommand.node())
				.then(ReloadCommand.node())
				.then(VersionNotice.node())
				.then(ProfileCommand.node())
				.then(io.github.albertosa23.heraldia.maps.WebMaps.node())
				.then(io.github.albertosa23.heraldia.quests.Quests.node())
				.then(io.github.albertosa23.heraldia.treasure.Treasure.node())
				.then(io.github.albertosa23.heraldia.caravans.Caravans.node())
				.then(io.github.albertosa23.heraldia.huts.Wizards.node())
				.then(ConfigPanel.node())
				.then(Preferences.node())
				.then(io.github.albertosa23.heraldia.update.Updater.node()));
		CommandNode<CommandSourceStack> root = dispatcher.getRoot().getChild("heraldia");
		Alias.add(root, Alias.LEGACY, HeraldiaCommands::warn);
		return root;
	}

	/** Aviso de nombre antiguo: «/heraldia guia» está obsoleto, usa «/heraldia guide» (clicable), en el idioma del jugador. */
	public static void warn(CommandSourceStack src, String old, String fresh) {
		Component cmd = Component.literal(fresh).withStyle(s -> s.withColor(ChatFormatting.GREEN).withUnderlined(true)
				.withClickEvent(new ClickEvent.SuggestCommand(fresh.startsWith("/") ? fresh + " " : fresh))
				.withHoverEvent(new HoverEvent.ShowText(Component.literal(fresh))));
		ServerPlayer p = src.getPlayer();
		Component text = (p != null ? Texts.t(Texts.language(p), "heraldia.comando.obsoleto", old, cmd)
				: Texts.t("heraldia.comando.obsoleto", old, cmd)).withStyle(ChatFormatting.YELLOW);
		src.sendSystemMessage(text);
	}
}
