package io.github.albertosa23.heraldia.uniques.atlantis;

import com.mojang.serialization.MapCodec;
import java.util.Optional;
import net.minecraft.core.Vec3i;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.chunk.ChunkGeneratorStructureState;
import net.minecraft.world.level.levelgen.structure.placement.AbstractSpreadingStructurePlacement;
import net.minecraft.world.level.levelgen.structure.placement.RandomSpreadStructurePlacement;
import net.minecraft.world.level.levelgen.structure.placement.RandomSpreadType;

/**
 * heraldia:mundial: exactly one structure per world, at the anchor {@link AtlantisAnchor} computes.
 * The structure chunks are the starts of the nine districts (anchor ± 16 chunks). It extends random_spread because
 * /locate and the maps only walk that type: getPotentialStructureChunk always returns the central district.
 */
public final class WorldPlacement extends RandomSpreadStructurePlacement {
	public static final MapCodec<WorldPlacement> CODEC = MapCodec.unit(WorldPlacement::new);

	private WorldPlacement() {
		super(Vec3i.ZERO, AbstractSpreadingStructurePlacement.FrequencyReductionMethod.DEFAULT, 1.0F, 0, Optional.empty(),
				4096, 0, RandomSpreadType.LINEAR);
	}

	@Override
	public ChunkPos getPotentialStructureChunk(long seed, int chunkX, int chunkZ) {
		ChunkPos anchor = AtlantisAnchor.get(seed);
		return anchor != null ? anchor : new ChunkPos(Integer.MAX_VALUE / 32, Integer.MAX_VALUE / 32);
	}

	@Override
	protected boolean isPlacementChunk(ChunkGeneratorStructureState state, int chunkX, int chunkZ) {
		return AtlantisAnchor.isDistrictStart(state.getLevelSeed(), chunkX, chunkZ);
	}

	/** /locate goes through here and not through isPlacementChunk. */
	@Override
	public boolean applyAdditionalChunkRestrictions(int chunkX, int chunkZ, long seed) {
		return AtlantisAnchor.isDistrictStart(seed, chunkX, chunkZ);
	}

	@Override
	@SuppressWarnings("unchecked")
	public MapCodec<RandomSpreadStructurePlacement> codec() {
		return (MapCodec<RandomSpreadStructurePlacement>) (MapCodec<?>) CODEC;
	}
}
