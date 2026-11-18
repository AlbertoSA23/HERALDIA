package io.github.albertosa23.heraldia.mixin;

import io.github.albertosa23.heraldia.Heraldia;
import net.minecraft.world.DifficultyInstance;
import net.minecraft.world.entity.EntitySpawnReason;
import net.minecraft.world.entity.SpawnGroupData;
import net.minecraft.world.entity.monster.zombie.Zombie;
import net.minecraft.world.level.ServerLevelAccessor;
import org.jspecify.annotations.Nullable;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.ModifyVariable;

/**
 * Mixin (last resort): {@code Zombie.finalizeSpawn}, which templates call when placing their mobs, rolls a baby (5 %)
 * and a chicken jockey without looking at the NBT's {@code IsBaby}; the data cannot prevent it. Template mobs with the
 * {@link Heraldia#ADULT} tag (zombie, husk, drowned, zombie villager, zombified piglin) get an "adult, no
 * jockey" group, as the game does on conversions. Only during structure placement (early exit by the spawn reason).
 */
@Mixin(Zombie.class)
abstract class ZombieMixin {
	@ModifyVariable(method = "finalizeSpawn", at = @At("HEAD"), argsOnly = true)
	private @Nullable SpawnGroupData heraldia$adult(@Nullable SpawnGroupData groupData, ServerLevelAccessor level,
			DifficultyInstance difficulty, EntitySpawnReason spawnReason) {
		if (spawnReason != EntitySpawnReason.STRUCTURE || groupData != null
				|| !((Zombie) (Object) this).entityTags().contains(Heraldia.ADULT)) {
			return groupData;
		}
		return new Zombie.ZombieGroupData(false, false);
	}
}
