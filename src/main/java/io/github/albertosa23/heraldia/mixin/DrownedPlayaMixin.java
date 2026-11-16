package io.github.albertosa23.heraldia.mixin;

import io.github.albertosa23.heraldia.comun.Anclaje;
import net.minecraft.world.entity.monster.zombie.Drowned;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/**
 * Mixin (último recurso): de noche, un ahogado en el agua cerca de la superficie sale a buscar la orilla
 * ({@code DrownedGoToBeachGoal}) sin mirar {@code noActionTime}. Un ahogado anclado ({@link Anclaje}) que
 * aún no ha entrado en combate no lo usa (es la pareja nocturna de {@link DrownedAguaMixin}).
 */
@Mixin(targets = "net.minecraft.world.entity.monster.zombie.Drowned$DrownedGoToBeachGoal")
abstract class DrownedPlayaMixin {
	@Shadow
	@Final
	private Drowned drowned;

	@Inject(method = "canUse", at = @At("HEAD"), cancellable = true)
	private void heraldia$quieto(CallbackInfoReturnable<Boolean> cir) {
		if (Anclaje.quieto(drowned)) {
			cir.setReturnValue(false);
		}
	}
}
