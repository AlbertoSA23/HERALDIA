package io.github.albertosa23.heraldia.mixin;

import io.github.albertosa23.heraldia.comun.Medianas;
import io.github.albertosa23.heraldia.comun.Perfil;
import io.github.albertosa23.heraldia.comun.ZonaAjenas;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.config.UniqueSeparation;
import io.github.albertosa23.heraldia.costa.Costa;
import io.github.albertosa23.heraldia.minas.Minas;
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
 * corsario ({@link IslaZona}), que las de otros mods nazcan encima de una aldea o una única ({@link ZonaAjenas}), que dos
 * estructuras únicas distintas salgan a menos de la distancia mínima ({@link UniqueSeparation}) y que una mediana salga
 * junto a una aldea, una única u otra mediana ({@link Medianas}), ni una entrada a mina junto a ellas ({@link Minas}).
 */
@Mixin(ChunkGenerator.class)
abstract class ChunkGeneratorMixin {
	@Inject(method = "tryGenerateStructure", at = @At("HEAD"), cancellable = true)
	private void heraldia$villageRules(StructureSet.StructureSelectionEntry selected, StructureManager structureManager,
									   RegistryAccess registryAccess, RandomState randomState, StructureTemplateManager templateManager,
									   long seed, ChunkAccess centerChunk, ChunkPos sourceChunkPos, ResourceKey<Level> level,
									   Climate.Sampler climateSampler, CallbackInfoReturnable<Boolean> cir) {
		long t0 = Perfil.inicio();
		try {
			heraldia$reglas(selected, registryAccess, randomState, templateManager, seed, centerChunk, sourceChunkPos, level, climateSampler, cir);
		} finally {
			Perfil.fin(Perfil.Tramo.REGLAS, t0);
		}
	}

	private void heraldia$reglas(StructureSet.StructureSelectionEntry selected, RegistryAccess registryAccess, RandomState randomState,
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
		long isla = IslaZona.candidata(id, level, sep, seed, sourceChunkPos.x(), sourceChunkPos.z());
		if (isla != IslaZona.NINGUNA && IslaZona.sale(sep, isla, seed, sep.viability(registryAccess, (ChunkGenerator) (Object) this,
				((ChunkGenerator) (Object) this).getBiomeSource(), climateSampler, randomState, templateManager, seed, centerChunk, level))) {
			cir.setReturnValue(false); // un inicio ajeno junto a una isla que sale de verdad (raro: solo cerca de sus candidatas)
			return;
		}
		ZonaAjenas zona = ZonaAjenas.of(registryAccess);
		if (zona.activa(level) && ZonaAjenas.deOtroMod(id) && ZonaAjenas.visible(selected.structure().value().step())) {
			long tz = Perfil.inicio();
			long[] cerca = zona.cercanas(sep, seed, sourceChunkPos.x(), sourceChunkPos.z());
			ChunkGenerator self = (ChunkGenerator) (Object) this;
			boolean ocupada = cerca != null && zona.ocupada(cerca, sep, seed,
					sep.viability(registryAccess, self, self.getBiomeSource(), climateSampler, randomState, templateManager, seed, centerChunk, level),
					zona.aldea(registryAccess, self, self.getBiomeSource(), climateSampler, randomState, templateManager, seed, centerChunk, level));
			Perfil.fin(Perfil.Tramo.ZONA_AJENAS, tz);
			if (ocupada) {
				cir.setReturnValue(false); // una estructura de otro mod junto a una aldea o una única de Heraldia que sale ahí
				return;
			}
		}
		if (UniqueSeparation.isUnique(id)) { // solo en los chunks candidatos de una estructura única: unos pocos por mundo
			int i = sep.indexOf(id);
			long ts = Perfil.inicio();
			boolean bloqueada = i >= 0 && sep.enabled() && sep.blocked(i, sourceChunkPos.x(), sourceChunkPos.z(), seed, sep.viability(registryAccess,
					(ChunkGenerator) (Object) this, ((ChunkGenerator) (Object) this).getBiomeSource(), climateSampler, randomState,
					templateManager, seed, centerChunk, level));
			Perfil.fin(Perfil.Tramo.SEPARACION_UNICAS, ts);
			if (bloqueada) {
				cir.setReturnValue(false);
			}
		}
		if (Medianas.esMediana(id)) { // solo en los chunks candidatos de una mediana: lejos de aldeas, únicas y otras medianas
			ChunkGenerator self = (ChunkGenerator) (Object) this;
			long tm = Perfil.inicio();
			boolean rechazada = Medianas.of(registryAccess).rechaza(id, sourceChunkPos.x(), sourceChunkPos.z(), seed, registryAccess, self,
					self.getBiomeSource(), climateSampler, randomState, templateManager, centerChunk, level);
			Perfil.fin(Perfil.Tramo.MEDIANAS, tm);
			if (rechazada) {
				cir.setReturnValue(false);
			}
		}
		if (Minas.esMina(id)) { // solo en los chunks candidatos de una entrada a mina: cede a aldeas, únicas, medianas y vanilla
			ChunkGenerator self = (ChunkGenerator) (Object) this;
			long tm = Perfil.inicio();
			boolean rechazada = Minas.of(registryAccess).rechaza(id, sourceChunkPos.x(), sourceChunkPos.z(), seed, registryAccess, self,
					self.getBiomeSource(), climateSampler, randomState, templateManager, centerChunk, level);
			Perfil.fin(Perfil.Tramo.MINAS, tm);
			if (rechazada) {
				cir.setReturnValue(false);
			}
		}
		if (Costa.esCosta(id)) { // solo en los chunks candidatos de un faro o naufragio: cede a todo lo anterior y a las minas
			ChunkGenerator self = (ChunkGenerator) (Object) this;
			long tc = Perfil.inicio();
			boolean rechazada = Costa.of(registryAccess).rechaza(id, sourceChunkPos.x(), sourceChunkPos.z(), seed, registryAccess, self,
					self.getBiomeSource(), climateSampler, randomState, templateManager, centerChunk, level);
			Perfil.fin(Perfil.Tramo.COSTA, tc);
			if (rechazada) {
				cir.setReturnValue(false);
			}
		}
	}
}
