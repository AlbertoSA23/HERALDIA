package io.github.albertosa23.heraldia.mixin;

import io.github.albertosa23.heraldia.herald.HeraldHouse;
import net.minecraft.world.entity.monster.Enderman;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/**
 * Endermen do not pick up blocks in the Herald's House protected area (ArenaEndermanMixin only stops them from placing
 * the block they carry; the arena relies on materials an enderman cannot hold, the house has grass and flowers). Fabric
 * API has no event for it. The goal's tick is cancelled when the enderman stands within 3 blocks of the area (it reaches
 * 2 around itself): an early exit on one field, then integer comparisons.
 */
@Mixin(targets = "net.minecraft.world.entity.monster.Enderman$EndermanTakeBlockGoal")
abstract class HeraldEndermanMixin {
	@Shadow
	@Final
	private Enderman enderman;

	@Inject(method = "tick", at = @At("HEAD"), cancellable = true)
	private void heraldia$house(CallbackInfo ci) {
		if (HeraldHouse.endermanStays(enderman.level(), enderman.blockPosition())) {
			ci.cancel();
		}
	}
}
