package io.github.albertosa23.heraldia.mixin;

import io.github.albertosa23.heraldia.common.MediumStructures;
import io.github.albertosa23.heraldia.common.Profiler;
import io.github.albertosa23.heraldia.common.ForeignZone;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.config.UniqueSeparation;
import io.github.albertosa23.heraldia.coast.Coast;
import io.github.albertosa23.heraldia.mines.Mines;
import io.github.albertosa23.heraldia.uniques.atlantis.AtlantisAnchor;
import io.github.albertosa23.heraldia.uniques.island.IslandZone;
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

/** Mixin (last resort): /locate and the maps check here whether a structure would spawn; they must follow the same rules as generation. */
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
		long t0 = Profiler.start();
		try {
			heraldia$rules(pos, structure, cir);
		} finally {
			Profiler.end(Profiler.Segment.RULES_LOCATE, t0);
		}
	}

	private void heraldia$rules(ChunkPos pos, Structure structure, CallbackInfoReturnable<Boolean> cir) {
		Identifier id = registryAccess.lookupOrThrow(Registries.STRUCTURE).getKey(structure);
		if (id != null && (!HeraldiaConfig.get().villages().allows(id, seed, pos.x(), pos.z())
				|| AtlantisAnchor.excludes(id, dimension, seed, pos.x(), pos.z()))) {
			cir.setReturnValue(false);
			return;
		}
		if (id == null) {
			return;
		}
		UniqueSeparation sep = UniqueSeparation.of(registryAccess);
		long island = IslandZone.candidate(id, dimension, sep, seed, pos.x(), pos.z());
		if (island != IslandZone.NONE && IslandZone.outcome(sep, island, seed, sep.viability(registryAccess, chunkGenerator, biomeSource,
				climateSampler, randomState, structureTemplateManager, seed, heightAccessor, dimension))) {
			cir.setReturnValue(false); // like generation: nothing foreign inside the corsair's island
			return;
		}
		ForeignZone zone = ForeignZone.of(registryAccess);
		if (zone.active(dimension) && ForeignZone.fromOtherMod(id) && ForeignZone.visible(structure.step())) {
			long[] near = zone.nearby(sep, seed, pos.x(), pos.z());
			if (near != null && zone.occupied(near, sep, seed, sep.viability(registryAccess, chunkGenerator, biomeSource, climateSampler,
					randomState, structureTemplateManager, seed, heightAccessor, dimension), zone.village(registryAccess, chunkGenerator,
					biomeSource, climateSampler, randomState, structureTemplateManager, seed, heightAccessor, dimension))) {
				cir.setReturnValue(false); // like generation: no other mods' structures on top of a village or a unique
				return;
			}
		}
		if (UniqueSeparation.isUnique(id)) { // same separation as generation: /locate and the maps do not point at discarded ones
			int i = sep.indexOf(id);
			if (i >= 0 && sep.enabled() && sep.blocked(i, pos.x(), pos.z(), seed, sep.viability(registryAccess, chunkGenerator, biomeSource,
					climateSampler, randomState, structureTemplateManager, seed, heightAccessor, dimension))) {
				cir.setReturnValue(false);
			}
		}
		if (MediumStructures.isMedium(id) && MediumStructures.of(registryAccess).rejects(id, pos.x(), pos.z(), seed, registryAccess, chunkGenerator,
				biomeSource, climateSampler, randomState, structureTemplateManager, heightAccessor, dimension)) {
			cir.setReturnValue(false); // like generation: /locate does not point at a discarded medium
		}
	}

	/**
	 * The mine entrances (and the lighthouses and shipwrecks, with the same rule), at the end: their rule (villages, uniques,
	 * mediums and neighboring mines nearby) is much more expensive than checking whether the entrance itself wins (biome and
	 * hillside), and /locate only needs the rule where the entrance wins. Same result as checking it first (both conditions
	 * must hold), without paying for it in the candidates without biome or hillside.
	 */
	@Inject(method = "canCreateStructure", at = @At("RETURN"), cancellable = true)
	private void heraldia$minesRules(ChunkPos pos, Structure structure, CallbackInfoReturnable<Boolean> cir) {
		if (!cir.getReturnValueZ()) {
			return;
		}
		Identifier id = registryAccess.lookupOrThrow(Registries.STRUCTURE).getKey(structure);
		if (id == null || !Mines.isMine(id) && !Coast.isCoast(id)) {
			return;
		}
		long t0 = Profiler.start();
		try {
			if (Mines.isMine(id) ? Mines.of(registryAccess).rejects(id, pos.x(), pos.z(), seed, registryAccess, chunkGenerator, biomeSource,
					climateSampler, randomState, structureTemplateManager, heightAccessor, dimension)
					: Coast.of(registryAccess).rejects(id, pos.x(), pos.z(), seed, registryAccess, chunkGenerator, biomeSource,
					climateSampler, randomState, structureTemplateManager, heightAccessor, dimension)) {
				cir.setReturnValue(false); // nor a discarded mine entrance, lighthouse or shipwreck
			}
		} finally {
			Profiler.end(Profiler.Segment.RULES_LOCATE, t0);
		}
	}
}
