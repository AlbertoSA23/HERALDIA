package io.github.albertosa23.heraldia.mixin;

import com.llamalad7.mixinextras.injector.wrapoperation.Operation;
import com.llamalad7.mixinextras.injector.wrapoperation.WrapOperation;
import com.mojang.brigadier.tree.CommandNode;
import io.github.albertosa23.heraldia.command.Alias;
import net.minecraft.commands.Commands;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;

/**
 * Mixin (last resort: the game sends the client every node the player can use, and no API allows running a
 * node without sending it): the old command aliases ({@link Alias.Hidden}) do not go into the tree the client receives,
 * so they do not show up in autocompletion, but the server still runs them. It only checks the node's type.
 */
@Mixin(Commands.class)
abstract class CommandsMixin {
	@WrapOperation(method = "fillUsableCommands", at = @At(value = "INVOKE",
			target = "Lcom/mojang/brigadier/tree/CommandNode;canUse(Ljava/lang/Object;)Z"))
	private static boolean heraldia$noAlias(CommandNode<?> node, Object source, Operation<Boolean> original) {
		return Alias.visible(node) && original.call(node, source);
	}
}
