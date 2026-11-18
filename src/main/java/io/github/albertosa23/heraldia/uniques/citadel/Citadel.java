package io.github.albertosa23.heraldia.uniques.citadel;

import io.github.albertosa23.heraldia.Heraldia;
import net.minecraft.core.Registry;
import net.minecraft.core.registries.BuiltInRegistries;

/** Registro de la Ciudadela enana: su tipo de estructura heraldia:ciudadela. */
public final class Citadel {
	private Citadel() {
	}

	public static void register() {
		Registry.register(BuiltInRegistries.STRUCTURE_TYPE, Heraldia.id("ciudadela"), CitadelStructure.TYPE);
	}
}
