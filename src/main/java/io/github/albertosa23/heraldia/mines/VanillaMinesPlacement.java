package io.github.albertosa23.heraldia.mines;

import com.mojang.serialization.Codec;
import com.mojang.serialization.MapCodec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import java.util.Optional;
import net.minecraft.core.Vec3i;
import net.minecraft.world.level.levelgen.structure.placement.AbstractSpreadingStructurePlacement;
import net.minecraft.world.level.levelgen.structure.placement.RandomSpreadStructurePlacement;
import net.minecraft.world.level.levelgen.structure.placement.RandomSpreadType;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * heraldia:minas_vanilla: the placement of the vanilla abandoned mineshafts (structure_set minecraft:mineshafts, which
 * Heraldia's datapack replaces with the same 26.3 values: random_spread of 1 chunk, salt 0, legacy_type_3 and
 * frequency 0.004) with the frequency multiplied by minas.vanilla.multiplicador. With 1 it is identical to vanilla (the
 * same float). The legacy_type_3 roll is "chunk random &lt; frequency" with a random that only depends on the
 * seed and the chunk: with more frequency all the earlier ones spawn plus some more, in the same places, and nothing of
 * other structures changes (each structure_set rolls with its salt). Already generated chunks keep their starts: only
 * new ones see the extra mineshafts. It extends random_spread so /locate walks it like the vanilla one.
 */
@SuppressWarnings("deprecation") // ExclusionZone, as in GridPlacement
public final class VanillaMinesPlacement extends RandomSpreadStructurePlacement {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	public static final MapCodec<VanillaMinesPlacement> CODEC = RecordCodecBuilder.mapCodec(i -> i.group(
			Vec3i.offsetCodec(16).optionalFieldOf("locate_offset", Vec3i.ZERO).forGetter(VanillaMinesPlacement::locateOffset),
			AbstractSpreadingStructurePlacement.FrequencyReductionMethod.CODEC.optionalFieldOf("frequency_reduction_method",
					AbstractSpreadingStructurePlacement.FrequencyReductionMethod.DEFAULT).forGetter(p -> p.method),
			Codec.floatRange(0.0F, 1.0F).fieldOf("frequency").forGetter(p -> p.base),
			Codec.INT.fieldOf("salt").forGetter(p -> p.salt),
			Codec.intRange(0, 4096).fieldOf("spacing").forGetter(RandomSpreadStructurePlacement::spacing),
			Codec.intRange(0, 4096).fieldOf("separation").forGetter(RandomSpreadStructurePlacement::separation),
			RandomSpreadType.CODEC.optionalFieldOf("spread_type", RandomSpreadType.LINEAR).forGetter(RandomSpreadStructurePlacement::spreadType)
	).apply(i, VanillaMinesPlacement::new));

	private final AbstractSpreadingStructurePlacement.FrequencyReductionMethod method;
	private final float base;
	private final int salt;

	private VanillaMinesPlacement(Vec3i offset, AbstractSpreadingStructurePlacement.FrequencyReductionMethod method, float base, int salt,
								  int spacing, int separation, RandomSpreadType type) {
		this(offset, method, base, salt, spacing, separation, type, HeraldiaConfig.get().getDouble(Mines.MULTIPLIER));
	}

	/** Public for the tests: with the given multiplier. */
	public VanillaMinesPlacement(Vec3i offset, AbstractSpreadingStructurePlacement.FrequencyReductionMethod method, float base, int salt,
								 int spacing, int separation, RandomSpreadType type, double multiplier) {
		super(offset, method, rate(base, multiplier), salt, Optional.empty(), spacing, separation, type);
		this.method = method;
		this.base = base;
		this.salt = salt;
		LOGGER.info("Heraldia: minas abandonadas vanilla: frecuencia {} (x{} sobre {})", rate(base, multiplier), multiplier, base);
	}

	/** Multiplied frequency (at most 1). With 1 it returns the same float: the exact vanilla placement. */
	public static float rate(float base, double multiplier) {
		return multiplier == 1.0 ? base : (float) Math.min(1.0, base * multiplier);
	}

	/** The frequency in use (vanilla's times the multiplier). */
	public float rate() {
		return frequency();
	}

	@Override
	@SuppressWarnings("unchecked")
	public MapCodec<RandomSpreadStructurePlacement> codec() {
		return (MapCodec<RandomSpreadStructurePlacement>) (MapCodec<?>) CODEC;
	}
}
