package io.github.albertosa23.heraldia.mixin;

import io.github.albertosa23.heraldia.arena.Arena;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/**
 * Mixin (último recurso: la regla mobGriefing es de todo el mundo): un enderman no deja el bloque que lleva dentro de la
 * arena. Que no coja ninguno de ella lo asegura el diseño (sus materiales no están en {@code #enderman_holdable}; lo
 * comprueba el generador). Salida temprana sin arena.
 */
@Mixin(targets = "net.minecraft.world.entity.monster.Enderman$EndermanLeaveBlockGoal")
abstract class ArenaEndermanMixin {
	@Inject(method = "canPlaceBlock", at = @At("HEAD"), cancellable = true)
	private void heraldia$arena(Level level, BlockPos pos, BlockState carried, BlockState at, BlockState below, BlockPos belowPos,
			CallbackInfoReturnable<Boolean> cir) {
		if (Arena.isProtected(level, pos)) {
			cir.setReturnValue(false);
		}
	}
}
