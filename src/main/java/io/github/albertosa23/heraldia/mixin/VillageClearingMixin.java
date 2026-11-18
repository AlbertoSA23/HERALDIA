package io.github.albertosa23.heraldia.mixin;

import io.github.albertosa23.heraldia.villages.Clearing;
import net.minecraft.core.BlockPos;
import net.minecraft.util.RandomSource;
import net.minecraft.world.level.WorldGenLevel;
import net.minecraft.world.level.chunk.ChunkGenerator;
import net.minecraft.world.level.levelgen.feature.BambooFeature;
import net.minecraft.world.level.levelgen.feature.FallenTreeFeature;
import net.minecraft.world.level.levelgen.feature.TreeFeature;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/** Trees, fallen trees and bamboo of world generation do not grow on a Heraldia village's pieces ({@link Clearing}). */
@Mixin({TreeFeature.class, FallenTreeFeature.class, BambooFeature.class})
abstract class VillageClearingMixin {
	@Inject(method = "place", at = @At("HEAD"), cancellable = true)
	private void heraldia$villageClearing(WorldGenLevel level, ChunkGenerator generator, RandomSource random, BlockPos origin,
										  CallbackInfoReturnable<Boolean> cir) {
		if (Clearing.cleared(origin)) {
			cir.setReturnValue(false);
		}
	}
}
