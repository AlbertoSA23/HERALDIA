package io.github.albertosa23.heraldia.uniques.galleon;

import io.github.albertosa23.heraldia.Heraldia;
import net.minecraft.core.Registry;
import net.minecraft.core.registries.BuiltInRegistries;

/** Registro del tipo de estructura heraldia:galeon (galeón varado en la orilla). */
public final class GalleonUnique {
	private GalleonUnique() {
	}

	public static void register() {
		Registry.register(BuiltInRegistries.STRUCTURE_TYPE, Heraldia.id("galeon"), GalleonStructure.TYPE);
	}
}
