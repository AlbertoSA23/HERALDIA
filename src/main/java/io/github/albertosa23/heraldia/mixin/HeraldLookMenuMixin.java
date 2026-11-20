package io.github.albertosa23.heraldia.mixin;

import io.github.albertosa23.heraldia.herald.LookOnly;
import net.minecraft.world.inventory.AbstractContainerMenu;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Unique;

/** The look-only mark of a container window (one boolean per open window; see LookOnly). */
@Mixin(AbstractContainerMenu.class)
abstract class HeraldLookMenuMixin implements LookOnly {
	@Unique
	private boolean heraldia$lookOnly;

	@Override
	public boolean heraldia$lookOnly() {
		return heraldia$lookOnly;
	}

	@Override
	public void heraldia$markLookOnly() {
		heraldia$lookOnly = true;
	}
}
