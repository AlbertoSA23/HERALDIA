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
 * Mixin (last resort: there is no event for the experience of a kill): arena mobs give
 * arena.experiencia_porcentaje % (15 by default) of the vanilla experience, already scaled by the game (enchantments).
 * Early exit with the tag set (almost always empty).
 */
@Mixin(LivingEntity.class)
abstract class ArenaExperienceMixin {
	@Inject(method = "getExperienceReward", at = @At("RETURN"), cancellable = true)
	private void heraldia$arena(ServerLevel level, Entity killer, CallbackInfoReturnable<Integer> cir) {
		LivingEntity self = (LivingEntity) (Object) this;
		if (!self.entityTags().isEmpty() && self.entityTags().contains(Arena.TAG)) {
			cir.setReturnValue(Arena.experience(cir.getReturnValueI(), level.getRandom().nextDouble()));
		}
	}
}
