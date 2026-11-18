package io.github.albertosa23.heraldia.common;

import net.minecraft.core.Holder;
import net.minecraft.core.HolderSet;
import net.minecraft.core.registries.Registries;
import net.minecraft.world.level.biome.Biome;
import net.minecraft.world.level.biome.Biomes;
import net.minecraft.world.level.block.Rotation;
import net.minecraft.world.level.levelgen.LegacyRandomSource;
import net.minecraft.world.level.levelgen.WorldgenRandom;
import net.minecraft.world.level.levelgen.structure.Structure;

/** Utilities for the own structure types placed relative to the terrain or water (lighthouse, galleon, villages). */
public final class Generation {
	private Generation() {
	}

	/** /place structure passes a biome predicate that accepts everything; normal generation, only the structure's. */
	public static boolean forced(Structure.GenerationContext ctx, HolderSet<Biome> biomes) {
		return ctx.registryAccess().lookupOrThrow(Registries.BIOME).get(Biomes.THE_VOID)
				.map(v -> !biomes.contains(v) && ctx.validBiome().test(v)).orElse(false);
	}

	/** The cell's random; with k = 0, the same as the freshly created context's (setLargeFeatureSeed of the seed). */
	public static WorldgenRandom rng(Structure.GenerationContext c, long k) {
		WorldgenRandom random = new WorldgenRandom(new LegacyRandomSource(0L));
		random.setLargeFeatureSeed(c.seed() + k * 0x9E3779B97F4A7C15L, c.chunkPos().x(), c.chunkPos().z());
		return random;
	}

	/**
	 * Copy of the context whose random gives the requested rotation as its first roll (JigsawPlacement rolls the rotation first). With the
	 * natural rotation it returns the context itself: the rest of the assembly does not change.
	 */
	public static Structure.GenerationContext withRotation(Structure.GenerationContext c, Rotation rotation) {
		for (long k = 0; ; k++) {
			if (Rotation.getRandom(rng(c, k)) == rotation) {
				return k == 0 ? c : new Structure.GenerationContext(c.registryAccess(), c.chunkGenerator(), c.biomeSource(),
						c.climateSampler(), c.biomeResolver(), c.randomState(), c.structureTemplateManager(), rng(c, k), c.seed(),
						c.chunkPos(), c.heightAccessor(), c.validBiome());
			}
		}
	}

	/** The structure's biome at a point (quarter-chunk resolution, cheap: does not evaluate the terrain). */
	public static boolean biome(Structure.GenerationContext c, HolderSet<Biome> biomes, int x, int y, int z) {
		Holder<Biome> b = c.biomeResolver().getNoiseBiome(net.minecraft.core.QuartPos.fromBlock(x), net.minecraft.core.QuartPos.fromBlock(y),
				net.minecraft.core.QuartPos.fromBlock(z));
		return biomes.contains(b);
	}
}
