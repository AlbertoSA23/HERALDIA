package io.github.albertosa23.heraldia.minas;

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
 * heraldia:minas_vanilla: la colocación de las minas abandonadas vanilla (structure_set minecraft:mineshafts, que el
 * datapack de Heraldia sustituye con los mismos valores de 26.3: random_spread de 1 chunk, sal 0, legacy_type_3 y
 * frecuencia 0,004) con la frecuencia multiplicada por minas.vanilla.multiplicador. Con 1 es idéntica a vanilla (el
 * mismo float). El sorteo de legacy_type_3 es «azar del chunk &lt; frecuencia» con un azar que solo depende de la
 * semilla y del chunk: con más frecuencia salen todas las de antes y algunas más, en los mismos sitios, y nada de
 * otras estructuras cambia (cada structure_set sortea con su sal). Los chunks ya generados guardan sus inicios: solo
 * los nuevos ven las minas de más. Hereda de random_spread para que /locate la recorra como a la vanilla.
 */
@SuppressWarnings("deprecation") // ExclusionZone, como en GridPlacement
public final class MinasVanillaPlacement extends RandomSpreadStructurePlacement {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	public static final MapCodec<MinasVanillaPlacement> CODEC = RecordCodecBuilder.mapCodec(i -> i.group(
			Vec3i.offsetCodec(16).optionalFieldOf("locate_offset", Vec3i.ZERO).forGetter(MinasVanillaPlacement::locateOffset),
			AbstractSpreadingStructurePlacement.FrequencyReductionMethod.CODEC.optionalFieldOf("frequency_reduction_method",
					AbstractSpreadingStructurePlacement.FrequencyReductionMethod.DEFAULT).forGetter(p -> p.metodo),
			Codec.floatRange(0.0F, 1.0F).fieldOf("frequency").forGetter(p -> p.base),
			Codec.INT.fieldOf("salt").forGetter(p -> p.sal),
			Codec.intRange(0, 4096).fieldOf("spacing").forGetter(RandomSpreadStructurePlacement::spacing),
			Codec.intRange(0, 4096).fieldOf("separation").forGetter(RandomSpreadStructurePlacement::separation),
			RandomSpreadType.CODEC.optionalFieldOf("spread_type", RandomSpreadType.LINEAR).forGetter(RandomSpreadStructurePlacement::spreadType)
	).apply(i, MinasVanillaPlacement::new));

	private final AbstractSpreadingStructurePlacement.FrequencyReductionMethod metodo;
	private final float base;
	private final int sal;

	private MinasVanillaPlacement(Vec3i offset, AbstractSpreadingStructurePlacement.FrequencyReductionMethod metodo, float base, int sal,
								  int spacing, int separation, RandomSpreadType tipo) {
		this(offset, metodo, base, sal, spacing, separation, tipo, HeraldiaConfig.get().getDouble(Minas.MULTIPLICADOR));
	}

	/** Pública para las pruebas: con el multiplicador dado. */
	public MinasVanillaPlacement(Vec3i offset, AbstractSpreadingStructurePlacement.FrequencyReductionMethod metodo, float base, int sal,
								 int spacing, int separation, RandomSpreadType tipo, double multiplicador) {
		super(offset, metodo, frecuencia(base, multiplicador), sal, Optional.empty(), spacing, separation, tipo);
		this.metodo = metodo;
		this.base = base;
		this.sal = sal;
		LOGGER.info("Heraldia: minas abandonadas vanilla: frecuencia {} (x{} sobre {})", frecuencia(base, multiplicador), multiplicador, base);
	}

	/** Frecuencia multiplicada (como mucho 1). Con 1 devuelve el mismo float: la colocación vanilla exacta. */
	public static float frecuencia(float base, double multiplicador) {
		return multiplicador == 1.0 ? base : (float) Math.min(1.0, base * multiplicador);
	}

	/** La frecuencia en uso (la de vanilla por el multiplicador). */
	public float frecuencia() {
		return frequency();
	}

	@Override
	@SuppressWarnings("unchecked")
	public MapCodec<RandomSpreadStructurePlacement> codec() {
		return (MapCodec<RandomSpreadStructurePlacement>) (MapCodec<?>) CODEC;
	}
}
