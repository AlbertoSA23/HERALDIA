package io.github.albertosa23.heraldia.mixin;

import io.github.albertosa23.heraldia.villages.Clearing;
import net.minecraft.world.level.StructureManager;
import net.minecraft.world.level.WorldGenLevel;
import net.minecraft.world.level.chunk.ChunkAccess;
import net.minecraft.world.level.chunk.ChunkGenerator;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/** While a chunk is decorated, the village pieces that reach it are known to {@link Clearing} (no trees on them). */
@Mixin(ChunkGenerator.class)
abstract class ChunkGeneratorClearingMixin {
	@Inject(method = "applyBiomeDecoration", at = @At("HEAD"))
	private void heraldia$clearingBegin(WorldGenLevel level, ChunkAccess chunk, StructureManager structures, CallbackInfo ci) {
		Clearing.begin(structures, chunk);
	}

	@Inject(method = "applyBiomeDecoration", at = @At("RETURN"))
	private void heraldia$clearingEnd(WorldGenLevel level, ChunkAccess chunk, StructureManager structures, CallbackInfo ci) {
		Clearing.end();
	}
}
