package io.github.albertosa23.heraldia.dimensions;

import io.github.albertosa23.heraldia.Heraldia;
import java.util.Set;
import net.minecraft.core.Holder;
import net.minecraft.core.Registry;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.world.level.biome.Biome;
import net.minecraft.world.level.biome.BiomeSource;
import net.minecraft.world.level.levelgen.structure.Structure;
import net.minecraft.world.level.levelgen.structure.StructureType;

/**
 * Heraldia content in the Nether and the End: the structure type heraldia:dimension ({@link DimensionStructure}) and
 * {@link #possible}, the cheap filter that keeps out of the separation rules (uniques, mediums, village zone) the
 * structures that cannot spawn in the dimension being generated.
 */
public final class Dimensions {
	public static final StructureType<DimensionStructure> TYPE = () -> DimensionStructure.CODEC;

	private Dimensions() {
	}

	public static void register() {
		Registry.register(BuiltInRegistries.STRUCTURE_TYPE, Heraldia.id("dimension"), TYPE);
	}

	/**
	 * Can the structure spawn in the dimension of this biome source (some of its biomes are in it)? So a
	 * Nether unique is not compared with the overworld's, nor the other way round, without assembling its jigsaw in a terrain that
	 * is not its own. Only in the candidate chunks (a few per area): it walks the structure's biome tag.
	 */
	public static boolean possible(Structure s, BiomeSource source) {
		Set<Holder<Biome>> possible = source.possibleBiomes();
		for (Holder<Biome> b : s.biomes()) {
			if (possible.contains(b)) {
				return true;
			}
		}
		return false;
	}
}
