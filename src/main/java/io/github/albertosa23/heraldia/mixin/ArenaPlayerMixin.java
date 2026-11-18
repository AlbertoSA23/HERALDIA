package io.github.albertosa23.heraldia.mixin;

import io.github.albertosa23.heraldia.arena.Arena;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.player.Player;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/**
 * Mixin (último recurso: la regla keepInventory es de todo el mundo y Fabric API no deja cancelar lo que suelta un
 * jugador al morir): quien cae en el ruedo durante una partida no suelta su inventario ni su experiencia; al reaparecer
 * se le devuelven (ServerPlayerEvents.COPY_FROM, arena/Juego). Salida temprana: sin partida no se mira nada más.
 */
@Mixin(Player.class)
abstract class ArenaPlayerMixin {
	@Inject(method = "dropEquipment", at = @At("HEAD"), cancellable = true)
	private void heraldia$keep(ServerLevel level, CallbackInfo ci) {
		if (Arena.keepsOnDeath((Player) (Object) this)) {
			ci.cancel();
		}
	}

	@Inject(method = "getBaseExperienceReward", at = @At("HEAD"), cancellable = true)
	private void heraldia$noExperience(ServerLevel level, CallbackInfoReturnable<Integer> cir) {
		if (Arena.keeping((Player) (Object) this)) {
			cir.setReturnValue(0);
		}
	}
}
