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
 * Mixin (último recurso): de noche, un ahogado en el agua cerca de la superficie sale a buscar la orilla
 * ({@code DrownedGoToBeachGoal}) sin mirar {@code noActionTime}. Un ahogado anclado ({@link Anchoring}) que
 * aún no ha entrado en combate no lo usa (es la pareja nocturna de {@link DrownedWaterMixin}).
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
