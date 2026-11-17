package io.github.albertosa23.heraldia.mixin;

import io.github.albertosa23.heraldia.encargos.Encargos;
import net.minecraft.world.entity.npc.villager.Villager;
import net.minecraft.world.entity.player.Player;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/**
 * Mixin (último recurso: no hay evento al calcular los precios de un aldeano): al final de
 * {@code Villager.updateSpecialPrices}, que vanilla llama al abrir los tratos (tras sumar los cotilleos y Héroe de la
 * aldea, y antes de enviar las ofertas), la rebaja por la reputación del jugador con la aldea (T38). Vanilla la
 * deshace al cerrar los tratos ({@code resetSpecialPrices}), así que no se guarda en el aldeano. Salida temprana sin
 * datos de reputación.
 */
@Mixin(Villager.class)
abstract class VillagerPreciosMixin {
	@Inject(method = "updateSpecialPrices", at = @At("TAIL"))
	private void heraldia$reputacion(Player player, CallbackInfo ci) {
		Encargos.precios((Villager) (Object) this, player);
	}
}
