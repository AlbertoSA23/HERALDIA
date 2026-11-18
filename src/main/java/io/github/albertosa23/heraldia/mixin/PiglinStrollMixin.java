package io.github.albertosa23.heraldia.mixin;

import io.github.albertosa23.heraldia.common.Anchoring;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.ai.memory.MemoryModuleType;
import net.minecraft.world.entity.monster.piglin.AbstractPiglin;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/**
 * Mixin (last resort): piglins and piglin brutes have a brain instead of goals; their idle activity
 * ({@code RandomStroll}, {@code StrollToPoi}/{@code StrollAroundPoi} around their home, walking to another piglin) sets a
 * {@code WALK_TARGET} without looking at {@code noActionTime}, so {@link Anchoring} did not hold them: the renegades of
 * the piglin outpost left their post (2-9 out of 30 after 200 ticks). After every brain tick, an anchored piglin that has
 * not entered combat yet ({@code getTarget()} reads the brain's {@code ATTACK_TARGET}) forgets its walk target before
 * {@code MoveToTargetSink} (core activity, it runs first) can follow it next tick; seeing, getting angry and attacking are
 * untouched. Piglin and PiglinBrute call this method at the end of theirs, after {@code Brain.tick}.
 */
@Mixin(AbstractPiglin.class)
abstract class PiglinStrollMixin {
	@Inject(method = "customServerAiStep", at = @At("RETURN"))
	private void heraldia$still(ServerLevel level, CallbackInfo ci) {
		AbstractPiglin piglin = (AbstractPiglin) (Object) this;
		if (Anchoring.still(piglin)) {
			piglin.getBrain().eraseMemory(MemoryModuleType.WALK_TARGET);
		}
	}
}
