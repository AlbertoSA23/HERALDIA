package io.github.albertosa23.heraldia.uniques.lighthouse;

import io.github.albertosa23.heraldia.Heraldia;
import net.minecraft.core.Registry;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.world.level.levelgen.structure.StructureType;

/** Registration of the lighthouse with the smugglers' cave: its structure type looks for the coastline. */
public final class Lighthouse {
	public static final StructureType<LighthouseStructure> TYPE = () -> LighthouseStructure.CODEC;

	private Lighthouse() {
	}

	public static void init() {
		Registry.register(BuiltInRegistries.STRUCTURE_TYPE, Heraldia.id("faro"), TYPE);
	}
}
