package io.github.albertosa23.heraldia.loot;

import com.mojang.serialization.Codec;
import com.mojang.serialization.DataResult;
import com.mojang.serialization.MapCodec;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import net.minecraft.world.level.storage.loot.LootContext;
import net.minecraft.world.level.storage.loot.predicates.LootItemCondition;

/**
 * Condición {@code heraldia:opcion}: se cumple si la opción sí/no {@code clave} de {@code config/heraldia.json} está
 * activada. La usan los tratos de los aldeanos ({@code merchant_predicate}) para que se puedan desactivar sin tocar los
 * datos. Una clave que no existe o que no es sí/no hace fallar la carga de los datos (con su error en el log).
 */
public record OptionCondition(String clave) implements LootItemCondition {
	public static final MapCodec<OptionCondition> CODEC = Codec.STRING.validate(OptionCondition::boolOption)
			.fieldOf("clave").xmap(OptionCondition::new, OptionCondition::clave);

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
		return HeraldiaConfig.get().getBool(clave);   // un mapa ya leído: no cuesta nada al sortear los tratos
	}
}
