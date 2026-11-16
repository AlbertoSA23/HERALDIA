package io.github.albertosa23.heraldia.mixin;

import io.github.albertosa23.heraldia.arena.Arena;
import java.util.List;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.ServerExplosion;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/**
 * Mixin (último recurso: Fabric API no tiene un evento de explosión): los bloques de la arena no se rompen ni arden
 * por ninguna explosión (creepers, TNT, bolas de fuego, cargas de viento). Se quitan de la lista que devuelve
 * {@code calculateExplodedPositions} (la misma que usan la rotura de bloques y el fuego); el daño a las entidades no
 * cambia. Salida temprana: sin arena, o en otro mundo, no se recorre nada; si no, una AABB en memoria por bloque.
 */
@Mixin(ServerExplosion.class)
abstract class ArenaExplosionMixin {
	@Shadow
	@Final
	private ServerLevel level;

	@Inject(method = "calculateExplodedPositions", at = @At("RETURN"))
	private void heraldia$arena(CallbackInfoReturnable<List<BlockPos>> cir) {
		if (Arena.hayArena(level)) {
			cir.getReturnValue().removeIf(pos -> Arena.protegido(level, pos));
		}
	}
}
