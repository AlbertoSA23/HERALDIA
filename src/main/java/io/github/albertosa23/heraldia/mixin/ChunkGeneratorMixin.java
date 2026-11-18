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
import java.util.Optional;
import net.minecraft.core.RegistryAccess;
import net.minecraft.resources.Identifier;
import net.minecraft.resources.ResourceKey;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.StructureManager;
import net.minecraft.world.level.biome.Climate;
import net.minecraft.world.level.chunk.ChunkAccess;
import net.minecraft.world.level.chunk.ChunkGenerator;
import net.minecraft.world.level.levelgen.RandomState;
import net.minecraft.world.level.levelgen.structure.Structure;
import net.minecraft.world.level.levelgen.structure.StructureSet;
import net.minecraft.world.level.levelgen.structure.templatesystem.StructureTemplateManager;
import net.minecraft.world.level.ChunkPos;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/**
 * Mixin (last resort): a structure_set has no way of skipping disabled entries or choosing the size
 * by configuration; on failing here, the set tries the next structure just like when the biome does not match.
 * It also prevents other structures (monuments, shipwrecks, ruins) from being born inside Atlantis or the corsair's
 * island ({@link IslandZone}), other mods' structures from being born on top of a village or a unique ({@link ForeignZone}), two
 * different unique structures from spawning closer than the minimum distance ({@link UniqueSeparation}), a medium from spawning
 * next to a village, a unique or another medium ({@link MediumStructures}), and a mine entrance next to them ({@link Mines}).
 */
@Mixin(ChunkGenerator.class)
abstract class ChunkGeneratorMixin {
	@Inject(method = "tryGenerateStructure", at = @At("HEAD"), cancellable = true)
	private void heraldia$villageRules(StructureSet.StructureSelectionEntry selected, StructureManager structureManager,
									   RegistryAccess registryAccess, RandomState randomState, StructureTemplateManager templateManager,
									   long seed, ChunkAccess centerChunk, ChunkPos sourceChunkPos, ResourceKey<Level> level,
									   Climate.Sampler climateSampler, CallbackInfoReturnable<Boolean> cir) {
		long t0 = Profiler.start();
		try {
			heraldia$rules(selected, registryAccess, randomState, templateManager, seed, centerChunk, sourceChunkPos, level, climateSampler, cir);
		} finally {
			Profiler.end(Profiler.Segment.RULES, t0);
		}
	}

	private void heraldia$rules(StructureSet.StructureSelectionEntry selected, RegistryAccess registryAccess, RandomState randomState,
								 StructureTemplateManager templateManager, long seed, ChunkAccess centerChunk, ChunkPos sourceChunkPos,
								 ResourceKey<Level> level, Climate.Sampler climateSampler, CallbackInfoReturnable<Boolean> cir) {
		// no capturing lambda (hot generation path): two hash table lookups and an early exit
		Optional<ResourceKey<Structure>> key = selected.structure().unwrapKey();
		if (key.isEmpty()) {
			return;
		}
		Identifier id = key.get().identifier();
		if (!HeraldiaConfig.get().villages().allows(id, seed, sourceChunkPos.x(), sourceChunkPos.z())
				|| AtlantisAnchor.excludes(id, level, seed, sourceChunkPos.x(), sourceChunkPos.z())) {
			cir.setReturnValue(false);
			return;
		}
		UniqueSeparation sep = UniqueSeparation.of(registryAccess);
		long island = IslandZone.candidate(id, level, sep, seed, sourceChunkPos.x(), sourceChunkPos.z());
		if (island != IslandZone.NONE && IslandZone.outcome(sep, island, seed, sep.viability(registryAccess, (ChunkGenerator) (Object) this,
				((ChunkGenerator) (Object) this).getBiomeSource(), climateSampler, randomState, templateManager, seed, centerChunk, level))) {
			cir.setReturnValue(false); // a foreign start next to an island that really wins (rare: only near its candidates)
			return;
		}
		ForeignZone zone = ForeignZone.of(registryAccess);
		if (zone.active(level) && ForeignZone.fromOtherMod(id) && ForeignZone.visible(selected.structure().value().step())) {
			long tz = Profiler.start();
			long[] near = zone.nearby(sep, seed, sourceChunkPos.x(), sourceChunkPos.z());
			ChunkGenerator self = (ChunkGenerator) (Object) this;
			boolean occupied = near != null && zone.occupied(near, sep, seed,
					sep.viability(registryAccess, self, self.getBiomeSource(), climateSampler, randomState, templateManager, seed, centerChunk, level),
					zone.village(registryAccess, self, self.getBiomeSource(), climateSampler, randomState, templateManager, seed, centerChunk, level));
			Profiler.end(Profiler.Segment.FOREIGN_ZONE, tz);
			if (occupied) {
				cir.setReturnValue(false); // another mod's structure next to a Heraldia village or unique that wins there
				return;
			}
		}
		if (UniqueSeparation.isUnique(id)) { // only in the candidate chunks of a unique structure: a few per world
			int i = sep.indexOf(id);
			long ts = Profiler.start();
			boolean blocked = i >= 0 && sep.enabled() && sep.blocked(i, sourceChunkPos.x(), sourceChunkPos.z(), seed, sep.viability(registryAccess,
					(ChunkGenerator) (Object) this, ((ChunkGenerator) (Object) this).getBiomeSource(), climateSampler, randomState,
					templateManager, seed, centerChunk, level));
			Profiler.end(Profiler.Segment.UNIQUE_SEPARATION, ts);
			if (blocked) {
				cir.setReturnValue(false);
			}
		}
		if (MediumStructures.isMedium(id)) { // only in the candidate chunks of a medium: away from villages, uniques and other mediums
			ChunkGenerator self = (ChunkGenerator) (Object) this;
			long tm = Profiler.start();
			boolean rejected = MediumStructures.of(registryAccess).rejects(id, sourceChunkPos.x(), sourceChunkPos.z(), seed, registryAccess, self,
					self.getBiomeSource(), climateSampler, randomState, templateManager, centerChunk, level);
			Profiler.end(Profiler.Segment.MEDIUMS, tm);
			if (rejected) {
				cir.setReturnValue(false);
			}
		}
		if (Mines.isMine(id)) { // only in the candidate chunks of a mine entrance: yields to villages, uniques, mediums and vanilla
			ChunkGenerator self = (ChunkGenerator) (Object) this;
			long tm = Profiler.start();
			boolean rejected = Mines.of(registryAccess).rejects(id, sourceChunkPos.x(), sourceChunkPos.z(), seed, registryAccess, self,
					self.getBiomeSource(), climateSampler, randomState, templateManager, centerChunk, level);
			Profiler.end(Profiler.Segment.MINES, tm);
			if (rejected) {
				cir.setReturnValue(false);
			}
		}
		if (Coast.isCoast(id)) { // only in the candidate chunks of a lighthouse or shipwreck: yields to all of the above and to the mines
			ChunkGenerator self = (ChunkGenerator) (Object) this;
			long tc = Profiler.start();
			boolean rejected = Coast.of(registryAccess).rejects(id, sourceChunkPos.x(), sourceChunkPos.z(), seed, registryAccess, self,
					self.getBiomeSource(), climateSampler, randomState, templateManager, centerChunk, level);
			Profiler.end(Profiler.Segment.COAST, tc);
			if (rejected) {
				cir.setReturnValue(false);
			}
		}
	}
}
