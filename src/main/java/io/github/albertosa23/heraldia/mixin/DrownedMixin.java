package io.github.albertosa23.heraldia.mixin;

import com.llamalad7.mixinextras.injector.ModifyExpressionValue;
import io.github.albertosa23.heraldia.Heraldia;
import net.minecraft.world.entity.monster.zombie.Drowned;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;

/**
 * Mixin (último recurso): {@code Drowned.finalizeSpawn} monta en un nautilo zombi (persistente) a la mitad de los ahogados
 * con tridente colocados por una estructura. Los de plantilla con la etiqueta {@link Heraldia#ADULTO} (los centinelas de
 * la Atlántida) se quedan como los diseñó la plantilla: la condición del jinete, que exige que no sea bebé, falla.
 */
@Mixin(Drowned.class)
abstract class DrownedMixin {
	@ModifyExpressionValue(method = "finalizeSpawn", at = @At(value = "INVOKE",
			target = "Lnet/minecraft/world/entity/monster/zombie/Drowned;isBaby()Z"))
	private boolean heraldia$sinNautilo(boolean baby) {
		return baby || ((Drowned) (Object) this).entityTags().contains(Heraldia.ADULTO);
	}
}
