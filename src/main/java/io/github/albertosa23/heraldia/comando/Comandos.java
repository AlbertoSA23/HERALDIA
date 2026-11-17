package io.github.albertosa23.heraldia.comando;

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
 * info [nearby [radius] | here], guide, key, arena, review, status, reload, update check y profile. Los nombres antiguos en
 * español siguen funcionando como alias ocultos ({@link Alias}). Una línea en Heraldia.onInitialize.
 */
public final class Comandos {
	private Comandos() {
	}

	public static void registrar() {
		CommandRegistrationCallback.EVENT.register((dispatcher, access, environment) -> arbol(dispatcher));
		RevisarCommand.registrarEventos();
	}

	/** Registra /heraldia con todos sus subcomandos y sus alias antiguos; devuelve el nodo /heraldia. */
	public static CommandNode<CommandSourceStack> arbol(CommandDispatcher<CommandSourceStack> dispatcher) {
		dispatcher.register(Commands.literal("heraldia")
				.then(InfoCommand.nodo())
				.then(Guia.nodo())
				.then(LlaveCommand.nodo())
				.then(Arena.nodo())
				.then(RevisarCommand.nodo())
				.then(EstadoCommand.nodo())
				.then(RecargarCommand.nodo())
				.then(AvisoVersion.nodo())
				.then(ProfileCommand.nodo()));
		CommandNode<CommandSourceStack> raiz = dispatcher.getRoot().getChild("heraldia");
		Alias.anadir(raiz, Alias.ANTIGUOS, Comandos::avisar);
		return raiz;
	}

	/** Aviso de nombre antiguo: «/heraldia guia» está obsoleto, usa «/heraldia guide» (clicable), en el idioma del jugador. */
	public static void avisar(CommandSourceStack src, String antigua, String nueva) {
		Component cmd = Component.literal(nueva).withStyle(s -> s.withColor(ChatFormatting.GREEN).withUnderlined(true)
				.withClickEvent(new ClickEvent.SuggestCommand(nueva.startsWith("/") ? nueva + " " : nueva))
				.withHoverEvent(new HoverEvent.ShowText(Component.literal(nueva))));
		ServerPlayer p = src.getPlayer();
		Component texto = (p != null ? Textos.t(Textos.idioma(p.clientInformation().language()), "heraldia.comando.obsoleto", antigua, cmd)
				: Textos.t("heraldia.comando.obsoleto", antigua, cmd)).withStyle(ChatFormatting.YELLOW);
		src.sendSystemMessage(texto);
	}
}
