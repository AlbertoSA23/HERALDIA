package io.github.albertosa23.heraldia.unicas.atlantida;

import com.mojang.serialization.MapCodec;
import java.util.Optional;
import net.minecraft.core.Vec3i;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.chunk.ChunkGeneratorStructureState;
import net.minecraft.world.level.levelgen.structure.placement.AbstractSpreadingStructurePlacement;
import net.minecraft.world.level.levelgen.structure.placement.RandomSpreadStructurePlacement;
import net.minecraft.world.level.levelgen.structure.placement.RandomSpreadType;

/**
 * heraldia:mundial: exactamente una estructura por mundo, en el ancla que calcula {@link AtlantisAnchor}.
 * Son chunks de estructura los inicios de los nueve distritos (ancla ± 16 chunks). Hereda de random_spread porque
 * /locate y los mapas solo recorren ese tipo: getPotentialStructureChunk devuelve siempre el distrito central.
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

	/** /locate pasa por aquí y no por isPlacementChunk. */
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
