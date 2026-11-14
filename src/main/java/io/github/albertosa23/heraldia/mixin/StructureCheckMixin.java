package io.github.albertosa23.heraldia.mixin;

import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.config.UniqueSeparation;
import io.github.albertosa23.heraldia.unicas.atlantida.AtlantisAnchor;
import net.minecraft.core.RegistryAccess;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.Identifier;
import net.minecraft.resources.ResourceKey;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.LevelHeightAccessor;
import net.minecraft.world.level.biome.BiomeSource;
import net.minecraft.world.level.biome.Climate;
import net.minecraft.world.level.chunk.ChunkGenerator;
import net.minecraft.world.level.levelgen.RandomState;
import net.minecraft.world.level.levelgen.structure.templatesystem.StructureTemplateManager;
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

	@Shadow
	@Final
	private ChunkGenerator chunkGenerator;

	@Shadow
	@Final
	private BiomeSource biomeSource;

	@Shadow
	@Final
	private Climate.Sampler climateSampler;

	@Shadow
	@Final
	private RandomState randomState;

	@Shadow
	@Final
	private StructureTemplateManager structureTemplateManager;

	@Shadow
	@Final
	private LevelHeightAccessor heightAccessor;

	@Inject(method = "canCreateStructure", at = @At("HEAD"), cancellable = true)
	private void heraldia$villageRules(ChunkPos pos, Structure structure, CallbackInfoReturnable<Boolean> cir) {
		Identifier id = registryAccess.lookupOrThrow(Registries.STRUCTURE).getKey(structure);
		if (id != null && (!HeraldiaConfig.get().villages().allows(id, seed, pos.x(), pos.z())
				|| AtlantisAnchor.excludes(id, dimension, seed, pos.x(), pos.z()))) {
			cir.setReturnValue(false);
			return;
		}
		if (id != null && UniqueSeparation.isUnique(id)) { // misma separación que la generación: /locate y los mapas no señalan descartadas
			UniqueSeparation sep = UniqueSeparation.of(registryAccess);
			int i = sep.indexOf(id);
			if (i >= 0 && sep.enabled() && sep.blocked(i, pos.x(), pos.z(), seed, sep.viability(registryAccess, chunkGenerator, biomeSource,
					climateSampler, randomState, structureTemplateManager, seed, heightAccessor, dimension))) {
				cir.setReturnValue(false);
			}
		}
	}
}
