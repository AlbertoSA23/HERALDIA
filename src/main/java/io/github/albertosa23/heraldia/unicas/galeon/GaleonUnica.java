package io.github.albertosa23.heraldia.unicas.galeon;

import io.github.albertosa23.heraldia.Heraldia;
import net.minecraft.core.Registry;
import net.minecraft.core.registries.BuiltInRegistries;

/** Registro del tipo de estructura heraldia:galeon (galeón varado en la orilla). */
public final class GaleonUnica {
	private GaleonUnica() {
	}

	public static void registrar() {
		Registry.register(BuiltInRegistries.STRUCTURE_TYPE, Heraldia.id("galeon"), GaleonStructure.TYPE);
	}
}
