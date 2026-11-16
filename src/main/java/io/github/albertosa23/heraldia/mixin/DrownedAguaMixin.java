package io.github.albertosa23.heraldia.mixin;

import io.github.albertosa23.heraldia.comun.Anclaje;
import net.minecraft.world.entity.PathfinderMob;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/**
 * Mixin (último recurso): de día, un ahogado fuera del agua va hacia el agua que haya a 10 bloques
 * ({@code DrownedGoToWaterGoal}); el objetivo no mira {@code noActionTime} y no hay forma de quitárselo con datos ni con
 * la API. Un ahogado anclado ({@link Anclaje}) que aún no ha entrado en combate no lo usa: el capitán del galeón salía
 * así de su camarote. Salida temprana con el conjunto de etiquetas.
 */
@Mixin(targets = "net.minecraft.world.entity.monster.zombie.Drowned$DrownedGoToWaterGoal")
abstract class DrownedAguaMixin {
	@Shadow
	@Final
	private PathfinderMob mob;

	@Inject(method = "canUse", at = @At("HEAD"), cancellable = true)
	private void heraldia$quieto(CallbackInfoReturnable<Boolean> cir) {
		if (Anclaje.quieto(mob)) {
			cir.setReturnValue(false);
		}
	}
}
