package io.github.albertosa23.heraldia.mixin;

import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.unicas.atlantida.AtlantisAnchor;
import net.minecraft.core.RegistryAccess;
import net.minecraft.resources.ResourceKey;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.StructureManager;
import net.minecraft.world.level.biome.Climate;
import net.minecraft.world.level.chunk.ChunkAccess;
import net.minecraft.world.level.chunk.ChunkGenerator;
import net.minecraft.world.level.levelgen.RandomState;
import net.minecraft.world.level.levelgen.structure.StructureSet;
import net.minecraft.world.level.levelgen.structure.templatesystem.StructureTemplateManager;
import net.minecraft.world.level.ChunkPos;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/**
 * Mixin (último recurso): un structure_set no tiene forma de saltarse entradas desactivadas ni de elegir el tamaño
 * según la configuración; al fallar aquí, el set prueba la siguiente estructura igual que cuando no vale el bioma.
 * También impide que otras estructuras (monumentos, naufragios, ruinas) nazcan dentro de la Atlántida.
 */
@Mixin(ChunkGenerator.class)
abstract class ChunkGeneratorMixin {
	@Inject(method = "tryGenerateStructure", at = @At("HEAD"), cancellable = true)
	private void heraldia$villageRules(StructureSet.StructureSelectionEntry selected, StructureManager structureManager,
									   RegistryAccess registryAccess, RandomState randomState, StructureTemplateManager templateManager,
									   long seed, ChunkAccess centerChunk, ChunkPos sourceChunkPos, ResourceKey<Level> level,
									   Climate.Sampler climateSampler, CallbackInfoReturnable<Boolean> cir) {
		selected.structure().unwrapKey().ifPresent(key -> {
			if (!HeraldiaConfig.get().villages().allows(key.identifier(), seed, sourceChunkPos.x(), sourceChunkPos.z())
					|| AtlantisAnchor.excludes(key.identifier(), level, seed, sourceChunkPos.x(), sourceChunkPos.z())) {
				cir.setReturnValue(false);
			}
		});
	}
}
