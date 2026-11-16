package io.github.albertosa23.heraldia.unicas.mina;

import io.github.albertosa23.heraldia.Heraldia;
import net.minecraft.core.Registry;
import net.minecraft.core.registries.BuiltInRegistries;

/** Registro de la Mina perdida: su tipo de estructura heraldia:mina. */
public final class Mina {
	private Mina() {
	}

	public static void register() {
		Registry.register(BuiltInRegistries.STRUCTURE_TYPE, Heraldia.id("mina"), MinaStructure.TYPE);
	}
}
