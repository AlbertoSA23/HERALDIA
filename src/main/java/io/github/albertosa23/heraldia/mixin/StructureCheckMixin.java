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
			cir.setReturnValue(false); // como la generación: nada ajeno dentro de la isla del corsario
			return;
		}
		ForeignZone zone = ForeignZone.of(registryAccess);
		if (zone.active(dimension) && ForeignZone.fromOtherMod(id) && ForeignZone.visible(structure.step())) {
			long[] near = zone.nearby(sep, seed, pos.x(), pos.z());
			if (near != null && zone.occupied(near, sep, seed, sep.viability(registryAccess, chunkGenerator, biomeSource, climateSampler,
					randomState, structureTemplateManager, seed, heightAccessor, dimension), zone.village(registryAccess, chunkGenerator,
					biomeSource, climateSampler, randomState, structureTemplateManager, seed, heightAccessor, dimension))) {
				cir.setReturnValue(false); // como la generación: nada de otros mods encima de una aldea o una única
				return;
			}
		}
		if (UniqueSeparation.isUnique(id)) { // misma separación que la generación: /locate y los mapas no señalan descartadas
			int i = sep.indexOf(id);
			if (i >= 0 && sep.enabled() && sep.blocked(i, pos.x(), pos.z(), seed, sep.viability(registryAccess, chunkGenerator, biomeSource,
					climateSampler, randomState, structureTemplateManager, seed, heightAccessor, dimension))) {
				cir.setReturnValue(false);
			}
		}
		if (MediumStructures.isMedium(id) && MediumStructures.of(registryAccess).rejects(id, pos.x(), pos.z(), seed, registryAccess, chunkGenerator,
				biomeSource, climateSampler, randomState, structureTemplateManager, heightAccessor, dimension)) {
			cir.setReturnValue(false); // como la generación: /locate no señala una mediana descartada
		}
	}

	/**
	 * Las entradas a mina (y los faros y naufragios, con la misma regla), al final: su regla (aldeas, únicas, medianas y minas vecinas cerca) es mucho más cara que ver
	 * si la propia entrada sale (bioma y ladera), y /locate solo necesita la regla donde la entrada sale. Mismo resultado
	 * que mirarla antes (las dos condiciones tienen que cumplirse), sin pagarla en los candidatos sin bioma ni ladera.
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
				cir.setReturnValue(false); // ni una entrada a mina, faro o naufragio descartados
			}
		} finally {
			Profiler.end(Profiler.Segment.RULES_LOCATE, t0);
		}
	}
}
