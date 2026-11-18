package io.github.albertosa23.heraldia.uniques.citadel;

import io.github.albertosa23.heraldia.Heraldia;
import net.minecraft.core.Registry;
import net.minecraft.core.registries.BuiltInRegistries;

/** Registration of the Dwarven Citadel: its structure type heraldia:ciudadela. */
public final class Citadel {
	private Citadel() {
	}

	public static void register() {
		Registry.register(BuiltInRegistries.STRUCTURE_TYPE, Heraldia.id("ciudadela"), CitadelStructure.TYPE);
	}
}
