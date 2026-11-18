package io.github.albertosa23.heraldia.mixin;

import io.github.albertosa23.heraldia.quests.Quests;
import net.minecraft.world.entity.npc.villager.Villager;
import net.minecraft.world.entity.player.Player;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/**
 * Mixin (last resort: there is no event when a villager's prices are computed): at the end of
 * {@code Villager.updateSpecialPrices}, which vanilla calls when the trades open (after adding gossip and Hero of the
 * Village, and before sending the offers), the discount for the player's reputation with the village (T38). Vanilla
 * undoes it when the trades close ({@code resetSpecialPrices}), so it is not saved on the villager. Early exit without
 * reputation data.
 */
@Mixin(Villager.class)
abstract class VillagerPricesMixin {
	@Inject(method = "updateSpecialPrices", at = @At("TAIL"))
	private void heraldia$reputation(Player player, CallbackInfo ci) {
		Quests.prices((Villager) (Object) this, player);
	}
}
