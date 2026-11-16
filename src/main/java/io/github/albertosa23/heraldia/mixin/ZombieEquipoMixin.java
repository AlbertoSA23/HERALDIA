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
 * Mixin (último recurso): el {@code populateDefaultEquipmentSlots} de los zombis, que {@code finalizeSpawn} llama al
 * colocar los mobs de una plantilla, cambia el arma del NBT sin mirarla (zombi y husk: pala, lanza o espada de hierro el
 * 1-5 %; ahogado: tridente o caña el 10 %, y con tridente monta un nautilo zombi la mitad de las veces). Los mobs con la
 * etiqueta {@link Heraldia#ADULTO} conservan el equipo de su plantilla. Ahogado y piglin zombificado lo redefinen sin
 * llamar al del zombi: por eso van los tres.
 */
@Mixin({Zombie.class, Drowned.class, ZombifiedPiglin.class})
abstract class ZombieEquipoMixin {
	@Inject(method = "populateDefaultEquipmentSlots", at = @At("HEAD"), cancellable = true)
	private void heraldia$equipoDePlantilla(RandomSource random, DifficultyInstance difficulty, CallbackInfo ci) {
		if (((Entity) (Object) this).entityTags().contains(Heraldia.ADULTO)) {
			ci.cancel();
		}
	}
}
