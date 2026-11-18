package io.github.albertosa23.heraldia.mixin;

import io.github.albertosa23.heraldia.arena.Arena;
import java.util.List;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.piston.PistonStructureResolver;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/**
 * Mixin (último recurso: no hay evento de pistones): un pistón no mueve, rompe ni empuja nada dentro de la arena (ni
 * mete su cabeza o un bloque en ella): {@code resolve} devuelve false y el pistón no se mueve, como ante obsidiana.
 * Salida temprana sin arena o en otro mundo.
 */
@Mixin(PistonStructureResolver.class)
abstract class ArenaPistonMixin {
	@Shadow
	@Final
	private Level level;

	@Shadow
	@Final
	private BlockPos startPos;

	@Shadow
	@Final
	private Direction pushDirection;

	@Shadow
	@Final
	private List<BlockPos> toPush;

	@Shadow
	@Final
	private List<BlockPos> toDestroy;

	@Inject(method = "resolve", at = @At("RETURN"), cancellable = true)
	private void heraldia$arena(CallbackInfoReturnable<Boolean> cir) {
		if (!cir.getReturnValueZ() || !Arena.hasArena(level)) {
			return;
		}
		boolean touches = Arena.isProtected(level, startPos);
		for (int i = 0; i < toPush.size() && !touches; i++) {
			touches = Arena.isProtected(level, toPush.get(i)) || Arena.isProtected(level, toPush.get(i).relative(pushDirection));
		}
		for (int i = 0; i < toDestroy.size() && !touches; i++) {
			touches = Arena.isProtected(level, toDestroy.get(i));
		}
		if (touches) {
			cir.setReturnValue(false);
		}
	}
}
