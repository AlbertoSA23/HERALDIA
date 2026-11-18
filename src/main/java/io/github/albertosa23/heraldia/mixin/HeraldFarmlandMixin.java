package io.github.albertosa23.heraldia.mixin;

import io.github.albertosa23.heraldia.herald.HeraldHouse;
import net.minecraft.core.BlockPos;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.FarmlandBlock;
import net.minecraft.world.level.block.state.BlockState;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/**
 * The Herald's House farm is not trampled (by players or mobs): Fabric API has no event for it. Only the turning of
 * farmland into dirt is cancelled (the fall itself, and its damage, stay vanilla); early exit on one field.
 */
@Mixin(FarmlandBlock.class)
abstract class HeraldFarmlandMixin {
	@Inject(method = "turnToBaseBlock", at = @At("HEAD"), cancellable = true)
	private void heraldia$house(Entity entity, BlockState state, Level level, BlockPos pos, CallbackInfo ci) {
		if (HeraldHouse.isProtected(level, pos)) {
			ci.cancel();
		}
	}
}
