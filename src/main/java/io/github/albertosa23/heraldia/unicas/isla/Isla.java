package io.github.albertosa23.heraldia.unicas.isla;

import io.github.albertosa23.heraldia.Heraldia;
import net.minecraft.core.Registry;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.world.level.levelgen.structure.StructureType;

/** Registro de la isla del corsario: su tipo de estructura busca mar abierto con fondo a una profundidad media. */
public final class Isla {
	public static final StructureType<IslaStructure> TYPE = () -> IslaStructure.CODEC;

	private Isla() {
	}

	public static void register() {
		Registry.register(BuiltInRegistries.STRUCTURE_TYPE, Heraldia.id("isla"), TYPE);
	}
}
