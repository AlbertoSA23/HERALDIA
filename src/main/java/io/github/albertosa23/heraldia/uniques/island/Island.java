package io.github.albertosa23.heraldia.uniques.island;

import io.github.albertosa23.heraldia.Heraldia;
import net.minecraft.core.Registry;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.world.level.levelgen.structure.StructureType;

/** Registration of the corsair's island: its structure type looks for open sea with a floor at medium depth. */
public final class Island {
	public static final StructureType<IslandStructure> TYPE = () -> IslandStructure.CODEC;

	private Island() {
	}

	public static void register() {
		Registry.register(BuiltInRegistries.STRUCTURE_TYPE, Heraldia.id("isla"), TYPE);
	}
}
