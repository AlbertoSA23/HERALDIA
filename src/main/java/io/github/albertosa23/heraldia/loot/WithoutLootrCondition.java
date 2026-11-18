package io.github.albertosa23.heraldia.loot;

import com.mojang.serialization.MapCodec;
import net.fabricmc.loader.api.FabricLoader;
import net.minecraft.world.level.storage.loot.LootContext;
import net.minecraft.world.level.storage.loot.predicates.LootItemCondition;

/**
 * Loot condition {@code heraldia:sin_lootr}: passes only if Lootr is not loaded.
 * With Lootr each player opens their own loot, so the groups marked with it (the per-chest extra) are skipped.
 */
public record WithoutLootrCondition() implements LootItemCondition {
	public static final WithoutLootrCondition INSTANCE = new WithoutLootrCondition();
	public static final MapCodec<WithoutLootrCondition> CODEC = MapCodec.unit(INSTANCE);
	public static final boolean LOOTR_LOADED = FabricLoader.getInstance().isModLoaded("lootr");

	@Override
	public MapCodec<WithoutLootrCondition> codec() {
		return CODEC;
	}

	@Override
	public boolean test(LootContext context) {
		return !LOOTR_LOADED;
	}
}
