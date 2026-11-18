package io.github.albertosa23.heraldia.mixin;

import io.github.albertosa23.heraldia.common.Anchoring;
import net.minecraft.world.entity.PathfinderMob;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/**
 * Mixin (last resort): by day, a drowned out of the water heads to any water within 10 blocks
 * ({@code DrownedGoToWaterGoal}); the goal does not look at {@code noActionTime} and there is no way to remove it with data or
 * the API. An anchored drowned ({@link Anchoring}) that has not entered combat yet does not use it: the galleon's captain
 * used to leave his cabin this way. Early exit with the tag set.
 */
@Mixin(targets = "net.minecraft.world.entity.monster.zombie.Drowned$DrownedGoToWaterGoal")
abstract class DrownedWaterMixin {
	@Shadow
	@Final
	private PathfinderMob mob;

	@Inject(method = "canUse", at = @At("HEAD"), cancellable = true)
	private void heraldia$still(CallbackInfoReturnable<Boolean> cir) {
		if (Anchoring.still(mob)) {
			cir.setReturnValue(false);
		}
	}
}
