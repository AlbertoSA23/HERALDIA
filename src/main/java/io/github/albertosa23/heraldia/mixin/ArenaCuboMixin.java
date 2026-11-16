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
 * Mixin (último recurso: Fabric API no tiene evento para lo que vacía un dispensador): un dispensador junto a la arena
 * no vacía en ella cubos de agua, lava ni nieve polvo ({@code emptyContents} devuelve false y el dispensador suelta el
 * cubo como objeto, como cuando no puede vaciarlo). Los jugadores ya los para {@code Arena.usarObjeto}. Salida
 * temprana sin arena o en otro mundo.
 */
@Mixin({BucketItem.class, SolidBucketItem.class})
abstract class ArenaCuboMixin {
	@Inject(method = "emptyContents", at = @At("HEAD"), cancellable = true)
	private void heraldia$arena(@Nullable LivingEntity user, Level level, BlockPos pos, @Nullable BlockHitResult hit,
			CallbackInfoReturnable<Boolean> cir) {
		if (Arena.cuboNegado(level, pos, user)) {
			cir.setReturnValue(false);
		}
	}
}
