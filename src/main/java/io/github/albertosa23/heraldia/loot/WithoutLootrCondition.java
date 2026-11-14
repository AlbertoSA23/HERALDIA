package io.github.albertosa23.heraldia.loot;

import com.mojang.serialization.MapCodec;
import net.fabricmc.loader.api.FabricLoader;
import net.minecraft.world.level.storage.loot.LootContext;
import net.minecraft.world.level.storage.loot.predicates.LootItemCondition;

/**
 * Condición de botín {@code heraldia:sin_lootr}: se cumple solo si Lootr no está cargado.
 * Con Lootr cada jugador abre su propio botín, así que los grupos marcados con ella (el extra por cofre) se omiten.
 */
public record WithoutLootrCondition() implements LootItemCondition {
	public static final WithoutLootrCondition INSTANCE = new WithoutLootrCondition();
	public static final MapCodec<WithoutLootrCondition> CODEC = MapCodec.unit(INSTANCE);
	private static final boolean LOOTR_LOADED = FabricLoader.getInstance().isModLoaded("lootr");

	@Override
	public MapCodec<WithoutLootrCondition> codec() {
		return CODEC;
	}

	@Override
	public boolean test(LootContext context) {
		return !LOOTR_LOADED;
	}
}
