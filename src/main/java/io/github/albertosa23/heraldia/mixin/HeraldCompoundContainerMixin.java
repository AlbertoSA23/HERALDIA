package io.github.albertosa23.heraldia.mixin;

import net.minecraft.world.CompoundContainer;
import net.minecraft.world.Container;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

/** The two halves of a double chest, for the Herald's House look-only check (where each half is). */
@Mixin(CompoundContainer.class)
public interface HeraldCompoundContainerMixin {
	@Accessor("container1")
	Container heraldia$first();

	@Accessor("container2")
	Container heraldia$second();
}
