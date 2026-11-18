package io.github.albertosa23.heraldia.mixin;

import com.mojang.datafixers.util.Pair;
import io.github.albertosa23.heraldia.mines.ParallelLocate;
import java.util.Set;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Holder;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.LevelReader;
import net.minecraft.world.level.StructureManager;
import net.minecraft.world.level.chunk.ChunkGenerator;
import net.minecraft.world.level.levelgen.structure.Structure;
import net.minecraft.world.level.levelgen.structure.placement.RandomSpreadStructurePlacement;
import net.minecraft.world.level.levelgen.structure.placement.StructurePlacement;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/**
 * Mixin (último recurso): /locate de las entradas a mina en paralelo ({@link ParallelLocate}). Solo adelanta en otros
 * hilos las alturas que el hilo del servidor va a pedir; lo que decide qué estructura sale y dónde sigue siendo vanilla.
 * Salida temprana barata para cualquier otra rejilla (una comprobación de tipo).
 */
@Mixin(ChunkGenerator.class)
abstract class ChunkGeneratorLocateMixin {
	@Inject(method = "getNearestGeneratedStructure(Ljava/util/Set;Lnet/minecraft/world/level/LevelReader;Lnet/minecraft/world/level/StructureManager;IIIZJLnet/minecraft/world/level/levelgen/structure/placement/RandomSpreadStructurePlacement;)Lcom/mojang/datafixers/util/Pair;",
			at = @At("HEAD"))
	private static void heraldia$ring(Set<Holder<Structure>> structures, LevelReader level, StructureManager manager, int x, int z,
										int r, boolean skipKnown, long seed, RandomSpreadStructurePlacement placement,
										CallbackInfoReturnable<Pair<BlockPos, Holder<Structure>>> cir) {
		ParallelLocate.start(structures, level, x, z, r, seed, placement);
	}

	@Inject(method = "getNearestGeneratedStructure(Ljava/util/Set;Lnet/minecraft/world/level/LevelReader;Lnet/minecraft/world/level/StructureManager;IIIZJLnet/minecraft/world/level/levelgen/structure/placement/RandomSpreadStructurePlacement;)Lcom/mojang/datafixers/util/Pair;",
			at = @At("RETURN"))
	private static void heraldia$endRing(Set<Holder<Structure>> structures, LevelReader level, StructureManager manager, int x, int z,
										   int r, boolean skipKnown, long seed, RandomSpreadStructurePlacement placement,
										   CallbackInfoReturnable<Pair<BlockPos, Holder<Structure>>> cir) {
		ParallelLocate.finish();
	}

	@Inject(method = "getStructureGeneratingAt", at = @At("HEAD"))
	private static void heraldia$cell(Set<Holder<Structure>> structures, LevelReader level, StructureManager manager, boolean skipKnown,
										 StructurePlacement placement, ChunkPos pos, CallbackInfoReturnable<Pair<BlockPos, Holder<Structure>>> cir) {
		ParallelLocate.await(pos);
	}
}
