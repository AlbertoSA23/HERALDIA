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
 * Mixin (último recurso): un structure_set no tiene forma de saltarse entradas desactivadas ni de elegir el tamaño
 * según la configuración; al fallar aquí, el set prueba la siguiente estructura igual que cuando no vale el bioma.
 * También impide que otras estructuras (monumentos, naufragios, ruinas) nazcan dentro de la Atlántida o de la isla del
 * corsario ({@link IslandZone}), que las de otros mods nazcan encima de una aldea o una única ({@link ForeignZone}), que dos
 * estructuras únicas distintas salgan a menos de la distancia mínima ({@link UniqueSeparation}) y que una mediana salga
 * junto a una aldea, una única u otra mediana ({@link MediumStructures}), ni una entrada a mina junto a ellas ({@link Mines}).
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
		// sin lambda que capture (ruta caliente de la generación): dos búsquedas en tablas hash y salida temprana
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
			cir.setReturnValue(false); // un inicio ajeno junto a una isla que sale de verdad (raro: solo cerca de sus candidatas)
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
				cir.setReturnValue(false); // una estructura de otro mod junto a una aldea o una única de Heraldia que sale ahí
				return;
			}
		}
		if (UniqueSeparation.isUnique(id)) { // solo en los chunks candidatos de una estructura única: unos pocos por mundo
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
		if (MediumStructures.isMedium(id)) { // solo en los chunks candidatos de una mediana: lejos de aldeas, únicas y otras medianas
			ChunkGenerator self = (ChunkGenerator) (Object) this;
			long tm = Profiler.start();
			boolean rejected = MediumStructures.of(registryAccess).rejects(id, sourceChunkPos.x(), sourceChunkPos.z(), seed, registryAccess, self,
					self.getBiomeSource(), climateSampler, randomState, templateManager, centerChunk, level);
			Profiler.end(Profiler.Segment.MEDIUMS, tm);
			if (rejected) {
				cir.setReturnValue(false);
			}
		}
		if (Mines.isMine(id)) { // solo en los chunks candidatos de una entrada a mina: cede a aldeas, únicas, medianas y vanilla
			ChunkGenerator self = (ChunkGenerator) (Object) this;
			long tm = Profiler.start();
			boolean rejected = Mines.of(registryAccess).rejects(id, sourceChunkPos.x(), sourceChunkPos.z(), seed, registryAccess, self,
					self.getBiomeSource(), climateSampler, randomState, templateManager, centerChunk, level);
			Profiler.end(Profiler.Segment.MINES, tm);
			if (rejected) {
				cir.setReturnValue(false);
			}
		}
		if (Coast.isCoast(id)) { // solo en los chunks candidatos de un faro o naufragio: cede a todo lo anterior y a las minas
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
