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
 * Mixin (último recurso): {@code Zombie.finalizeSpawn}, que las plantillas llaman al colocar sus mobs, sortea un bebé (5 %)
 * y un jinete de gallina sin mirar el {@code IsBaby} del NBT; los datos no pueden evitarlo. A los mobs de plantilla con la
 * etiqueta {@link Heraldia#ADULT} (zombi, husk, ahogado, zombi aldeano, piglin zombificado) les pasa un grupo «adulto, sin
 * jinete», como el juego hace en las conversiones. Solo en la colocación de estructuras (salida temprana con el motivo).
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
