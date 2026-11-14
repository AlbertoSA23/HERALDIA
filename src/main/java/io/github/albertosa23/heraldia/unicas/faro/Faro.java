package io.github.albertosa23.heraldia.unicas.faro;

import io.github.albertosa23.heraldia.Heraldia;
import net.minecraft.core.Registry;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.world.level.levelgen.structure.StructureType;

/** Registro del faro con cueva de contrabandistas: su tipo de estructura busca la línea de costa. */
public final class Faro {
	public static final StructureType<FaroStructure> TYPE = () -> FaroStructure.CODEC;

	private Faro() {
	}

	public static void init() {
		Registry.register(BuiltInRegistries.STRUCTURE_TYPE, Heraldia.id("faro"), TYPE);
	}
}
