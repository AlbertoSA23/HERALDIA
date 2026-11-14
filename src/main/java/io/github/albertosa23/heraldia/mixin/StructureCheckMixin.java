package io.github.albertosa23.heraldia.mixin;

import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.unicas.atlantida.AtlantisAnchor;
import net.minecraft.core.RegistryAccess;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.Identifier;
import net.minecraft.resources.ResourceKey;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.levelgen.structure.Structure;
import net.minecraft.world.level.levelgen.structure.StructureCheck;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/** Mixin (último recurso): /locate y los mapas comprueban aquí si una estructura saldría; deben seguir las mismas reglas que la generación. */
@Mixin(StructureCheck.class)
abstract class StructureCheckMixin {
	@Shadow
	@Final
	private RegistryAccess registryAccess;

	@Shadow
	@Final
	private long seed;

	@Shadow
	@Final
	private ResourceKey<Level> dimension;

	@Inject(method = "canCreateStructure", at = @At("HEAD"), cancellable = true)
	private void heraldia$villageRules(ChunkPos pos, Structure structure, CallbackInfoReturnable<Boolean> cir) {
		Identifier id = registryAccess.lookupOrThrow(Registries.STRUCTURE).getKey(structure);
		if (id != null && (!HeraldiaConfig.get().villages().allows(id, seed, pos.x(), pos.z())
				|| AtlantisAnchor.excludes(id, dimension, seed, pos.x(), pos.z()))) {
			cir.setReturnValue(false);
		}
	}
}
