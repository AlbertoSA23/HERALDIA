package io.github.albertosa23.heraldia.tesoro;

import com.mojang.serialization.Codec;
import com.mojang.serialization.MapCodec;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import net.minecraft.world.level.storage.loot.LootContext;
import net.minecraft.world.level.storage.loot.predicates.LootItemCondition;

/**
 * Condición {@code heraldia:tesoro_pista} del grupo que añade tools/gen/tesoro.con_pista a las tablas de cofre: el
 * fragmento sale con probabilidad tesoro.probabilidad % x {@code factor} (la misma cuenta que tesoro.probabilidad en el
 * generador) y nunca con tesoro.activado = false. Lee la configuración al tirar el botín (recargable sin reiniciar).
 */
public record PistaCondition(double factor) implements LootItemCondition {
	public static final MapCodec<PistaCondition> CODEC = Codec.DOUBLE.optionalFieldOf("factor", 1.0)
			.xmap(PistaCondition::new, PistaCondition::factor);
	public static final String ACTIVADO = "tesoro.activado", PROBABILIDAD = "tesoro.probabilidad", RADIO = "tesoro.radio_max";

	/** Probabilidad de sacar el fragmento con un porcentaje de la opción y el factor de la tabla, entre 0 y 1. */
	public static double probabilidad(double porcentaje, double factor) {
		return Math.max(0, Math.min(1, porcentaje / 100.0 * factor));
	}

	@Override
	public MapCodec<PistaCondition> codec() {
		return CODEC;
	}

	@Override
	public boolean test(LootContext context) {
		HeraldiaConfig cfg = HeraldiaConfig.get();
		return cfg.getBool(ACTIVADO) && context.getRandom().nextDouble() < probabilidad(cfg.getDouble(PROBABILIDAD), factor);
	}
}
