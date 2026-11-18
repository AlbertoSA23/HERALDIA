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
 * Mixin (last resort: the keepInventory rule is world-wide and Fabric API does not allow cancelling what a player
 * drops on death): whoever falls in the ring during a match drops neither their inventory nor their experience; on respawn
 * they get them back (ServerPlayerEvents.COPY_FROM, arena/Game). Early exit: without a match nothing else is checked.
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
