package io.github.albertosa23.heraldia.loot;

import com.mojang.serialization.Codec;
import com.mojang.serialization.DataResult;
import com.mojang.serialization.MapCodec;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import net.minecraft.world.level.storage.loot.LootContext;
import net.minecraft.world.level.storage.loot.predicates.LootItemCondition;

/**
 * Condition {@code heraldia:opcion}: passes if the yes/no option {@code key} of {@code config/heraldia.json} is
 * enabled. The villager trades use it ({@code merchant_predicate}) so they can be disabled without touching the
 * data. A key that does not exist or is not yes/no makes the data fail to load (with its error in the log).
 */
public record OptionCondition(String key) implements LootItemCondition {
	public static final MapCodec<OptionCondition> CODEC = Codec.STRING.validate(OptionCondition::boolOption)
			.fieldOf("clave").xmap(OptionCondition::new, OptionCondition::key);

	private static DataResult<String> boolOption(String key) {
		boolean ok = HeraldiaConfig.options().stream().anyMatch(o -> o.key().equals(key) && o.isBoolean());
		return ok ? DataResult.success(key) : DataResult.error(() -> "heraldia:opcion: no hay opción sí/no " + key);
	}

	@Override
	public MapCodec<OptionCondition> codec() {
		return CODEC;
	}

	@Override
	public boolean test(LootContext context) {
		return HeraldiaConfig.get().getBool(key);   // an already read map: costs nothing when the trades are rolled
	}
}
