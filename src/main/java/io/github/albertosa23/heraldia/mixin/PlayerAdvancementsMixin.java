package io.github.albertosa23.heraldia.mixin;

import io.github.albertosa23.heraldia.maps.WebMaps;
import net.minecraft.advancements.AdvancementHolder;
import net.minecraft.server.PlayerAdvancements;
import net.minecraft.server.level.ServerPlayer;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/**
 * Web maps: notifies when a player earns a criterion of an advancement (discovering a structure). A mixin because neither Fabric
 * API nor the data have a per-criterion event (an advancement's reward only arrives when it is fully finished). Cheap early
 * exit: nothing if there are no web maps or the advancement is not Heraldia's.
 */
@Mixin(PlayerAdvancements.class)
abstract class PlayerAdvancementsMixin {
	@Shadow
	private ServerPlayer player;

	@Inject(method = "award", at = @At("RETURN"))
	private void heraldia$onAward(AdvancementHolder holder, String criterion, CallbackInfoReturnable<Boolean> cir) {
		if (cir.getReturnValueZ() && WebMaps.inUse()) {
			WebMaps.onAward(player, holder, criterion);
		}
	}
}
