package io.github.albertosa23.heraldia.mixin;

import io.github.albertosa23.heraldia.comun.ZonaAjenas;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.config.UniqueSeparation;
import io.github.albertosa23.heraldia.unicas.atlantida.AtlantisAnchor;
import io.github.albertosa23.heraldia.unicas.isla.IslaZona;
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
 * corsario ({@link IslaZona}), que las de otros mods nazcan encima de una aldea o una única ({@link ZonaAjenas}) y que dos
 * estructuras únicas distintas salgan a menos de la distancia mínima ({@link UniqueSeparation}).
 */
@Mixin(ChunkGenerator.class)
abstract class ChunkGeneratorMixin {
	@Inject(method = "tryGenerateStructure", at = @At("HEAD"), cancellable = true)
	private void heraldia$villageRules(StructureSet.StructureSelectionEntry selected, StructureManager structureManager,
									   RegistryAccess registryAccess, RandomState randomState, StructureTemplateManager templateManager,
									   long seed, ChunkAccess centerChunk, ChunkPos sourceChunkPos, ResourceKey<Level> level,
									   Climate.Sampler climateSampler, CallbackInfoReturnable<Boolean> cir) {
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
		long isla = IslaZona.candidata(id, level, sep, seed, sourceChunkPos.x(), sourceChunkPos.z());
		if (isla != IslaZona.NINGUNA && IslaZona.sale(sep, isla, seed, sep.viability(registryAccess, (ChunkGenerator) (Object) this,
				((ChunkGenerator) (Object) this).getBiomeSource(), climateSampler, randomState, templateManager, seed, centerChunk, level))) {
			cir.setReturnValue(false); // un inicio ajeno junto a una isla que sale de verdad (raro: solo cerca de sus candidatas)
			return;
		}
		ZonaAjenas zona = ZonaAjenas.of(registryAccess);
		if (zona.activa(level) && ZonaAjenas.deOtroMod(id) && ZonaAjenas.visible(selected.structure().value().step())) {
			long[] cerca = zona.cercanas(sep, seed, sourceChunkPos.x(), sourceChunkPos.z());
			ChunkGenerator self = (ChunkGenerator) (Object) this;
			if (cerca != null && zona.ocupada(cerca, sep, seed,
					sep.viability(registryAccess, self, self.getBiomeSource(), climateSampler, randomState, templateManager, seed, centerChunk, level),
					zona.aldea(registryAccess, self, self.getBiomeSource(), climateSampler, randomState, templateManager, seed, centerChunk, level))) {
				cir.setReturnValue(false); // una estructura de otro mod junto a una aldea o una única de Heraldia que sale ahí
				return;
			}
		}
		if (UniqueSeparation.isUnique(id)) { // solo en los chunks candidatos de una estructura única: unos pocos por mundo
			int i = sep.indexOf(id);
			if (i >= 0 && sep.enabled() && sep.blocked(i, sourceChunkPos.x(), sourceChunkPos.z(), seed, sep.viability(registryAccess,
					(ChunkGenerator) (Object) this, ((ChunkGenerator) (Object) this).getBiomeSource(), climateSampler, randomState,
					templateManager, seed, centerChunk, level))) {
				cir.setReturnValue(false);
			}
		}
	}
}
