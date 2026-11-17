package io.github.albertosa23.heraldia.mixin;

import io.github.albertosa23.heraldia.mapas.MapasWeb;
import net.minecraft.advancements.AdvancementHolder;
import net.minecraft.server.PlayerAdvancements;
import net.minecraft.server.level.ServerPlayer;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/**
 * Mapas web: avisa cuando un jugador consigue un criterio de un logro (descubrir una estructura). Mixin porque ni Fabric
 * API ni los datos tienen un evento por criterio (la recompensa de un logro solo llega al terminarlo entero). Salida
 * temprana barata: nada si no hay mapas web o el logro no es de Heraldia.
 */
@Mixin(PlayerAdvancements.class)
abstract class PlayerAdvancementsMixin {
	@Shadow
	private ServerPlayer player;

	@Inject(method = "award", at = @At("RETURN"))
	private void heraldia$alConseguir(AdvancementHolder holder, String criterio, CallbackInfoReturnable<Boolean> cir) {
		if (cir.getReturnValueZ() && MapasWeb.enUso()) {
			MapasWeb.alConseguir(player, holder, criterio);
		}
	}
}
