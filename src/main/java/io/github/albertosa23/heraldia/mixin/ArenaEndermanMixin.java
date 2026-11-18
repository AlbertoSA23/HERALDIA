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
 * Mixin (last resort: the mobGriefing rule is world-wide): an enderman does not drop the block it carries inside the
 * arena. That it picks up none of its blocks is ensured by design (its materials are not in {@code #enderman_holdable}; the
 * generator checks it). Early exit without an arena.
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
