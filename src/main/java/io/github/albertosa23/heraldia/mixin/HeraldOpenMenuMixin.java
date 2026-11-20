package io.github.albertosa23.heraldia.mixin;

import io.github.albertosa23.heraldia.herald.HeraldHouse;
import java.util.OptionalInt;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.Container;
import net.minecraft.world.MenuProvider;
import net.minecraft.world.entity.animal.equine.AbstractHorse;
import net.minecraft.world.entity.animal.nautilus.AbstractNautilus;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/**
 * Every window a player opens (a container block, a chest minecart...) goes past the Herald's House once, after vanilla
 * made it (the loot table already rolled): it marks it look-only if it shows a protected container. A mount's inventory
 * (a horse, a donkey, a nautilus) opens by its own way and is marked by where the animal is. Only when a window opens,
 * never per tick; early exit on one field.
 */
@Mixin(ServerPlayer.class)
abstract class HeraldOpenMenuMixin {
	@Inject(method = "openMenu", at = @At("RETURN"))
	private void heraldia$look(MenuProvider provider, CallbackInfoReturnable<OptionalInt> cir) {
		if (cir.getReturnValue().isPresent()) {
			ServerPlayer self = (ServerPlayer) (Object) this;
			HeraldHouse.opened(self, self.containerMenu);
		}
	}

	@Inject(method = "openHorseInventory", at = @At("RETURN"))
	private void heraldia$lookHorse(AbstractHorse horse, Container inventory, CallbackInfo ci) {
		HeraldHouse.openedMount((ServerPlayer) (Object) this, horse);
	}

	@Inject(method = "openNautilusInventory", at = @At("RETURN"))
	private void heraldia$lookNautilus(AbstractNautilus nautilus, Container inventory, CallbackInfo ci) {
		HeraldHouse.openedMount((ServerPlayer) (Object) this, nautilus);
	}
}
