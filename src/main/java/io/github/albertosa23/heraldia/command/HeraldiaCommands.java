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
 * All the mod's commands, under /heraldia and with English names (the texts the player sees are still translated):
 * info [nearby [radius] | here], guide, journal [section] (each player's journal of what they found and what is
 * missing), key, arena, review, status, reload, update check, profile, webmap refresh, quest
 * (board quests, T38), talk (villager conversations, P9a), treasure give/info (T40), caravan (caravans, T39, operators) and wizard [reveal] (wizard huts,
 * T43, operators); config (dialog panel), language (each player's language) and update analyze/apply/undo/repair (safe
 * updates, T46). The old Spanish names keep working as hidden aliases ({@link Alias}). One line in Heraldia.onInitialize.
 */
public final class HeraldiaCommands {
	private HeraldiaCommands() {
	}

	public static void register() {
		CommandRegistrationCallback.EVENT.register((dispatcher, access, environment) -> tree(dispatcher));
		ReviewCommand.registerEvents();
	}

	/** Registers /heraldia with all its subcommands and its old aliases; returns the /heraldia node. */
	public static CommandNode<CommandSourceStack> tree(CommandDispatcher<CommandSourceStack> dispatcher) {
		dispatcher.register(Commands.literal("heraldia")
				.then(InfoCommand.node())
				.then(Guide.node())
				.then(Journal.node())
				.then(KeyCommand.node())
				.then(Arena.node())
				.then(ReviewCommand.node())
				.then(StatusCommand.node())
				.then(ReloadCommand.node())
				.then(VersionNotice.node())
				.then(ProfileCommand.node())
				.then(io.github.albertosa23.heraldia.maps.WebMaps.node())
				.then(io.github.albertosa23.heraldia.quests.Quests.node())
				.then(io.github.albertosa23.heraldia.dialogue.Dialogue.node())
				.then(io.github.albertosa23.heraldia.treasure.Treasure.node())
				.then(io.github.albertosa23.heraldia.caravans.Caravans.node())
				.then(io.github.albertosa23.heraldia.huts.Wizards.node())
				.then(ConfigPanel.node())
				.then(Preferences.node())
				.then(io.github.albertosa23.heraldia.update.Updater.node())
				.then(io.github.albertosa23.heraldia.herald.HeraldHouse.node())
				.then(io.github.albertosa23.heraldia.events.VillageEvents.node()));
		CommandNode<CommandSourceStack> root = dispatcher.getRoot().getChild("heraldia");
		Alias.add(root, Alias.LEGACY, HeraldiaCommands::warn);
		return root;
	}

	/** Old-name notice: «/heraldia guia» is deprecated, use «/heraldia guide» (clickable), in the player's language. */
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
