package io.github.albertosa23.heraldia.mixin;

import io.github.albertosa23.heraldia.herald.HeraldHouse;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.MobCategory;
import net.minecraft.world.level.NaturalSpawner;
import net.minecraft.world.level.StructureManager;
import net.minecraft.world.level.biome.MobSpawnSettings;
import net.minecraft.world.level.chunk.ChunkGenerator;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/**
 * No monster spawns naturally in the Herald's House protected area (the owner: respawn protection). Fabric API has no
 * event for natural spawning; this is the narrowest point (the position check of each spawn attempt), with an early
 * exit on the category and one field before any coordinate is compared.
 */
@Mixin(NaturalSpawner.class)
abstract class HeraldSpawnMixin {
	@Inject(method = "isValidSpawnPostitionForType", at = @At("HEAD"), cancellable = true)
	private static void heraldia$house(ServerLevel level, MobCategory category, StructureManager structures, ChunkGenerator generator,
			MobSpawnSettings.SpawnerData data, BlockPos.MutableBlockPos pos, double distance, CallbackInfoReturnable<Boolean> cir) {
		if (category == MobCategory.MONSTER && HeraldHouse.noSpawn(level, pos)) {
			cir.setReturnValue(false);
		}
	}
}
