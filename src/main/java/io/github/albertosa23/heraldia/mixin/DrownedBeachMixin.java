package io.github.albertosa23.heraldia.mixin;

import io.github.albertosa23.heraldia.common.Anchoring;
import net.minecraft.world.entity.monster.zombie.Drowned;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/**
 * Mixin (last resort): at night, a drowned in the water near the surface goes looking for the shore
 * ({@code DrownedGoToBeachGoal}) without looking at {@code noActionTime}. An anchored drowned ({@link Anchoring}) that
 * has not entered combat yet does not use it (it is the night-time partner of {@link DrownedWaterMixin}).
 */
@Mixin(targets = "net.minecraft.world.entity.monster.zombie.Drowned$DrownedGoToBeachGoal")
abstract class DrownedBeachMixin {
	@Shadow
	@Final
	private Drowned drowned;

	@Inject(method = "canUse", at = @At("HEAD"), cancellable = true)
	private void heraldia$still(CallbackInfoReturnable<Boolean> cir) {
		if (Anchoring.still(drowned)) {
			cir.setReturnValue(false);
		}
	}
}
