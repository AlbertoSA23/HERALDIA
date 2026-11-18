package io.github.albertosa23.heraldia.treasure;

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
public record ClueCondition(double factor) implements LootItemCondition {
	public static final MapCodec<ClueCondition> CODEC = Codec.DOUBLE.optionalFieldOf("factor", 1.0)
			.xmap(ClueCondition::new, ClueCondition::factor);
	public static final String ENABLED = "tesoro.activado", PROBABILITY = "tesoro.probabilidad", RADIUS = "tesoro.radio_max";

	/** Probabilidad de sacar el fragmento con un porcentaje de la opción y el factor de la tabla, entre 0 y 1. */
	public static double probability(double percent, double factor) {
		return Math.max(0, Math.min(1, percent / 100.0 * factor));
	}

	@Override
	public MapCodec<ClueCondition> codec() {
		return CODEC;
	}

	@Override
	public boolean test(LootContext context) {
		HeraldiaConfig cfg = HeraldiaConfig.get();
		return cfg.getBool(ENABLED) && context.getRandom().nextDouble() < probability(cfg.getDouble(PROBABILITY), factor);
	}
}
