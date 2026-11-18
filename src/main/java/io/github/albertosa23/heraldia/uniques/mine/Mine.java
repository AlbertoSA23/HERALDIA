package io.github.albertosa23.heraldia.uniques.mine;

import io.github.albertosa23.heraldia.Heraldia;
import net.minecraft.core.Registry;
import net.minecraft.core.registries.BuiltInRegistries;

/** Registration of the Lost Mine: its structure type heraldia:mina. */
public final class Mine {
	private Mine() {
	}

	public static void register() {
		Registry.register(BuiltInRegistries.STRUCTURE_TYPE, Heraldia.id("mina"), MineStructure.TYPE);
	}
}
