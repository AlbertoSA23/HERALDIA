package io.github.albertosa23.heraldia.mixin;

import io.github.albertosa23.heraldia.arena.Arena;
import net.minecraft.core.BlockPos;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.item.BucketItem;
import net.minecraft.world.item.SolidBucketItem;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.BlockHitResult;
import org.jspecify.annotations.Nullable;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/**
 * Mixin (last resort: Fabric API has no event for what a dispenser empties): a dispenser next to the arena
 * does not empty water, lava or powder snow buckets into it ({@code emptyContents} returns false and the dispenser drops the
 * bucket as an item, like when it cannot empty it). Players are already stopped by {@code Arena.useItem}. Early
 * exit without an arena or in another world.
 */
@Mixin({BucketItem.class, SolidBucketItem.class})
abstract class ArenaBucketMixin {
	@Inject(method = "emptyContents", at = @At("HEAD"), cancellable = true)
	private void heraldia$arena(@Nullable LivingEntity user, Level level, BlockPos pos, @Nullable BlockHitResult hit,
			CallbackInfoReturnable<Boolean> cir) {
		if (Arena.bucketDenied(level, pos, user)) {
			cir.setReturnValue(false);
		}
	}
}
