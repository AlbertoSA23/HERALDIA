package io.github.albertosa23.heraldia.mixin;

import com.llamalad7.mixinextras.injector.ModifyExpressionValue;
import io.github.albertosa23.heraldia.Heraldia;
import net.minecraft.world.entity.monster.zombie.Drowned;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;

/**
 * Mixin (last resort): {@code Drowned.finalizeSpawn} puts half of the trident-wielding drowned placed by a structure
 * on a (persistent) zombie nautilus. Template ones with the {@link Heraldia#ADULT} tag (the Atlantis sentinels)
 * stay as the template designed them: the rider condition, which requires it not to be a baby, fails.
 */
@Mixin(Drowned.class)
abstract class DrownedMixin {
	@ModifyExpressionValue(method = "finalizeSpawn", at = @At(value = "INVOKE",
			target = "Lnet/minecraft/world/entity/monster/zombie/Drowned;isBaby()Z"))
	private boolean heraldia$noNautilus(boolean baby) {
		return baby || ((Drowned) (Object) this).entityTags().contains(Heraldia.ADULT);
	}
}
