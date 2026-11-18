package io.github.albertosa23.heraldia.mixin;

import io.github.albertosa23.heraldia.common.Anchoring;
import net.minecraft.world.entity.monster.cubemob.AbstractCubeMob;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/**
 * Mixin (last resort): slimes and magma cubes do not walk with {@code RandomStrollGoal}; they hop forever with
 * {@code CubeMobKeepOnJumpingGoal} (it only asks that they are not riding) in the direction that
 * {@code CubeMobRandomDirectionGoal} turns them to every 2-5 s, and neither looks at {@code noActionTime}: the magma
 * altar's anchored cubes left their post (5-10 out of 30 more than a block away after 200 ticks). An anchored cube
 * ({@link Anchoring}) that has not entered combat yet does not hop (it may still turn in place); with a target or after
 * a hit, {@code Anchoring.still} is false and it hops at the player as always (the attack goal only aims, this goal
 * moves). Only this goal: a mixin with several string targets cannot have a remappable {@code @Shadow} (Mixin refuses
 * the whole configuration at startup).
 */
@Mixin(targets = "net.minecraft.world.entity.monster.cubemob.AbstractCubeMob$CubeMobKeepOnJumpingGoal")
abstract class CubeMobJumpMixin {
	@Shadow
	@Final
	private AbstractCubeMob cubeMob;

	@Inject(method = "canUse", at = @At("HEAD"), cancellable = true)
	private void heraldia$still(CallbackInfoReturnable<Boolean> cir) {
		if (Anchoring.still(cubeMob)) {
			cir.setReturnValue(false);
		}
	}
}
