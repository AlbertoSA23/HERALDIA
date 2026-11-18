package io.github.albertosa23.heraldia.mixin;

import com.llamalad7.mixinextras.injector.wrapoperation.Operation;
import com.llamalad7.mixinextras.injector.wrapoperation.WrapOperation;
import com.mojang.brigadier.tree.CommandNode;
import io.github.albertosa23.heraldia.command.Alias;
import net.minecraft.commands.Commands;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;

/**
 * Mixin (último recurso: el juego envía al cliente todo nodo que el jugador puede usar, y ninguna API deja ejecutar un
 * nodo sin enviarlo): los alias antiguos de los comandos ({@link Alias.Hidden}) no van en el árbol que recibe el cliente,
 * así que no salen en el autocompletado, pero el servidor los sigue ejecutando. Solo mira el tipo del nodo.
 */
@Mixin(Commands.class)
abstract class CommandsMixin {
	@WrapOperation(method = "fillUsableCommands", at = @At(value = "INVOKE",
			target = "Lcom/mojang/brigadier/tree/CommandNode;canUse(Ljava/lang/Object;)Z"))
	private static boolean heraldia$noAlias(CommandNode<?> node, Object source, Operation<Boolean> original) {
		return Alias.visible(node) && original.call(node, source);
	}
}
