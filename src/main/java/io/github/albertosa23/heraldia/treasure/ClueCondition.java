package io.github.albertosa23.heraldia.treasure;

import com.mojang.serialization.Codec;
import com.mojang.serialization.MapCodec;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import net.minecraft.world.level.storage.loot.LootContext;
import net.minecraft.world.level.storage.loot.predicates.LootItemCondition;

/**
 * Condition {@code heraldia:tesoro_pista} of the group tools/gen/treasure.with_hint adds to the chest tables: the
 * fragment drops with probability tesoro.probabilidad % x {@code factor} (the same computation as tesoro.probabilidad in the
 * generator) and never with tesoro.activado = false. It reads the configuration when the loot is rolled (reloadable without restarting).
 */
public record ClueCondition(double factor) implements LootItemCondition {
	public static final MapCodec<ClueCondition> CODEC = Codec.DOUBLE.optionalFieldOf("factor", 1.0)
			.xmap(ClueCondition::new, ClueCondition::factor);
	public static final String ENABLED = "tesoro.activado", PROBABILITY = "tesoro.probabilidad", RADIUS = "tesoro.radio_max";

	/** Probability of getting the fragment with the option's percentage and the table's factor, between 0 and 1. */
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
