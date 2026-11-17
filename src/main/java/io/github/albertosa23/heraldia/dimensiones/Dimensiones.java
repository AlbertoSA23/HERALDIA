package io.github.albertosa23.heraldia.dimensiones;

import io.github.albertosa23.heraldia.Heraldia;
import java.util.Set;
import net.minecraft.core.Holder;
import net.minecraft.core.Registry;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.world.level.biome.Biome;
import net.minecraft.world.level.biome.BiomeSource;
import net.minecraft.world.level.levelgen.structure.Structure;
import net.minecraft.world.level.levelgen.structure.StructureType;

/**
 * Contenido de Heraldia en el Nether y el End: el tipo de estructura heraldia:dimension ({@link DimensionStructure}) y
 * {@link #posible}, el filtro barato que deja fuera de las reglas de separación (únicas, medianas, zona de aldeas) las
 * estructuras que no pueden salir en la dimensión que se genera.
 */
public final class Dimensiones {
	public static final StructureType<DimensionStructure> TYPE = () -> DimensionStructure.CODEC;

	private Dimensiones() {
	}

	public static void registrar() {
		Registry.register(BuiltInRegistries.STRUCTURE_TYPE, Heraldia.id("dimension"), TYPE);
	}

	/**
	 * ¿Puede salir la estructura en la dimensión de esta fuente de biomas (alguno de sus biomas está en ella)? Así una
	 * única del Nether no se compara con las del mundo principal, ni al revés, sin ensamblar su jigsaw en un terreno que
	 * no es el suyo. Solo en los chunks candidatos (unos pocos por zona): recorre la etiqueta de biomas de la estructura.
	 */
	public static boolean posible(Structure s, BiomeSource fuente) {
		Set<Holder<Biome>> posibles = fuente.possibleBiomes();
		for (Holder<Biome> b : s.biomes()) {
			if (posibles.contains(b)) {
				return true;
			}
		}
		return false;
	}
}
