package io.github.albertosa23.heraldia.mixin;

import io.github.albertosa23.heraldia.Heraldia;
import net.minecraft.util.RandomSource;
import net.minecraft.world.DifficultyInstance;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.monster.zombie.Drowned;
import net.minecraft.world.entity.monster.zombie.Zombie;
import net.minecraft.world.entity.monster.zombie.ZombifiedPiglin;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/**
 * Mixin (last resort): the zombies' {@code populateDefaultEquipmentSlots}, which {@code finalizeSpawn} calls when
 * a template's mobs are placed, changes the NBT weapon without looking at it (zombie and husk: iron shovel, spear or sword
 * 1-5 %; drowned: trident or fishing rod 10 %, and with a trident it rides a zombie nautilus half of the time). Mobs with the
 * {@link Heraldia#ADULT} tag keep their template's gear. Drowned and zombified piglin redefine it without
 * calling the zombie's: that is why all three are here.
 */
@Mixin({Zombie.class, Drowned.class, ZombifiedPiglin.class})
abstract class ZombieEquipmentMixin {
	@Inject(method = "populateDefaultEquipmentSlots", at = @At("HEAD"), cancellable = true)
	private void heraldia$templateEquipment(RandomSource random, DifficultyInstance difficulty, CallbackInfo ci) {
		if (((Entity) (Object) this).entityTags().contains(Heraldia.ADULT)) {
			ci.cancel();
		}
	}
}
