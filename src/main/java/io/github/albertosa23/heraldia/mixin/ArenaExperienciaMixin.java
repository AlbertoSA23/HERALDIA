package io.github.albertosa23.heraldia.mixin;

import io.github.albertosa23.heraldia.arena.Arena;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/**
 * Mixin (último recurso: no hay evento para la experiencia de una muerte): los mobs de la arena dan el
 * arena.experiencia_porcentaje % (15 por defecto) de la experiencia vanilla, ya escalada por el juego (encantamientos).
 * Salida temprana con el conjunto de etiquetas (casi siempre vacío).
 */
@Mixin(LivingEntity.class)
abstract class ArenaExperienciaMixin {
	@Inject(method = "getExperienceReward", at = @At("RETURN"), cancellable = true)
	private void heraldia$arena(ServerLevel level, Entity killer, CallbackInfoReturnable<Integer> cir) {
		LivingEntity self = (LivingEntity) (Object) this;
		if (!self.entityTags().isEmpty() && self.entityTags().contains(Arena.TAG)) {
			cir.setReturnValue(Arena.experiencia(cir.getReturnValueI(), level.getRandom().nextDouble()));
		}
	}
}
