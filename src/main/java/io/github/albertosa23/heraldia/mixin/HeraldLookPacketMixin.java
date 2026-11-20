package io.github.albertosa23.heraldia.mixin;

import com.llamalad7.mixinextras.injector.ModifyExpressionValue;
import io.github.albertosa23.heraldia.herald.HeraldHouse;
import net.minecraft.network.protocol.game.ServerboundPickItemFromBlockPacket;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.network.ServerGamePacketListenerImpl;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/**
 * Nothing leaves a look-only window (HeraldHouse.opened): every packet a client sends to change what an open window holds
 * is dropped, on the server thread, before vanilla touches the window, and the client is shown the truth again. They are
 * all the ways 26.3 has: the container click (every input: pickup with either button, quick move, swap with a hotbar
 * key or the offhand, clone, throw, quick craft or drag, pickup all or double click), the menu buttons, the recipe book's
 * placement (it would also move a furnace's items back to the player), the crafter's slot toggles and the bundle's
 * selected item. Creative mode's own slot packet only reaches the player's inventory, never an open container. And a
 * creative pick-block with data (Ctrl) of a protected block entity copies it without its contents. One field read per
 * packet: nothing per tick.
 */
@Mixin(ServerGamePacketListenerImpl.class)
abstract class HeraldLookPacketMixin {
	@Shadow
	public ServerPlayer player;

	@Inject(method = {"handleContainerClick", "handleContainerButtonClick", "handlePlaceRecipe", "handleContainerSlotStateChanged",
			"handleBundleItemSelectedPacket"}, at = @At(value = "INVOKE", shift = At.Shift.AFTER,
			target = "Lnet/minecraft/network/protocol/PacketUtils;ensureRunningOnSameThread(Lnet/minecraft/network/protocol/Packet;Lnet/minecraft/network/PacketListener;Lnet/minecraft/server/level/ServerLevel;)V"),
			cancellable = true)
	private void heraldia$lookOnly(CallbackInfo ci) {
		if (HeraldHouse.refused(player)) {
			ci.cancel();
		}
	}

	@ModifyExpressionValue(method = "handlePickItemFromBlock", at = @At(value = "INVOKE",
			target = "Lnet/minecraft/network/protocol/game/ServerboundPickItemFromBlockPacket;includeData()Z"))
	private boolean heraldia$noCopy(boolean includeData, ServerboundPickItemFromBlockPacket packet) {
		return includeData && !HeraldHouse.copyDenied(player, packet.pos());
	}
}
