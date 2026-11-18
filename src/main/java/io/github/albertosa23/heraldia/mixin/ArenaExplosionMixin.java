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
 * Mixin (last resort: Fabric API has no explosion event): the arena's blocks neither break nor burn
 * from any explosion (creepers, TNT, fireballs, wind charges). They are removed from the list that
 * {@code calculateExplodedPositions} returns (the same one block breaking and fire use); damage to entities does not
 * change. Early exit: without an arena, or in another world, nothing is walked; otherwise, one in-memory AABB check per block.
 */
@Mixin(ServerExplosion.class)
abstract class ArenaExplosionMixin {
	@Shadow
	@Final
	private ServerLevel level;

	@Inject(method = "calculateExplodedPositions", at = @At("RETURN"))
	private void heraldia$arena(CallbackInfoReturnable<List<BlockPos>> cir) {
		if (Arena.hasArena(level)) {
			cir.getReturnValue().removeIf(pos -> Arena.isProtected(level, pos));
		}
		if (io.github.albertosa23.heraldia.herald.HeraldHouse.hasHouse(level)) {
			cir.getReturnValue().removeIf(pos -> io.github.albertosa23.heraldia.herald.HeraldHouse.isProtected(level, pos));
		}
	}
}
