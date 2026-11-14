package io.github.albertosa23.heraldia.unicas.ciudadela;

import io.github.albertosa23.heraldia.Heraldia;
import net.minecraft.core.Registry;
import net.minecraft.core.registries.BuiltInRegistries;

/** Registro de la Ciudadela enana: su tipo de estructura heraldia:ciudadela. */
public final class Ciudadela {
	private Ciudadela() {
	}

	public static void register() {
		Registry.register(BuiltInRegistries.STRUCTURE_TYPE, Heraldia.id("ciudadela"), CiudadelaStructure.TYPE);
	}
}
