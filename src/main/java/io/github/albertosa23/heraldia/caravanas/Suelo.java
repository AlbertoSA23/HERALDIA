package io.github.albertosa23.heraldia.caravanas;

import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;

/**
 * ¿Hay camino en un vértice? En un mundo existente, los chunks generados antes que los caminos no los tienen aunque la
 * ruta pase por ahí: la caravana solo va por donde el camino existe. Se miran los bloques de la superficie en el 3 × 3
 * del eje (el camino tiene al menos 3 de ancho) y hace falta que {@link #MINIMO} sean de los que pone el camino
 * (caminos/CaminoFeature.suelo, y las tablas de los puentes y pasarelas).
 */
public final class Suelo {
	/** Bloques del 3 × 3 que deben ser del camino. */
	public static final int MINIMO = 4;
	private static final Block[] CAMINO = {Blocks.DIRT_PATH, Blocks.COARSE_DIRT, Blocks.GRAVEL, Blocks.COBBLESTONE, Blocks.STONE_BRICKS,
			Blocks.SMOOTH_SANDSTONE, Blocks.SANDSTONE, Blocks.CUT_SANDSTONE, Blocks.SMOOTH_RED_SANDSTONE, Blocks.RED_SANDSTONE,
			Blocks.CUT_RED_SANDSTONE, Blocks.PACKED_MUD, Blocks.MUD_BRICKS,
			// las tablas de los puentes y pasarelas (las maderas de CaminoFeature)
			Blocks.OAK_PLANKS, Blocks.SPRUCE_PLANKS, Blocks.BIRCH_PLANKS, Blocks.JUNGLE_PLANKS, Blocks.ACACIA_PLANKS, Blocks.DARK_OAK_PLANKS,
			Blocks.MANGROVE_PLANKS, Blocks.CHERRY_PLANKS, Blocks.PALE_OAK_PLANKS};

	private Suelo() {
	}

	/** ¿Es un bloque que pone el camino en la superficie (o el tablero de un puente)? */
	public static boolean delCamino(BlockState s) {
		for (Block b : CAMINO) {
			if (s.is(b)) {
				return true;
			}
		}
		return false;
	}

	/** Con {@code delCamino} bloques del camino en el 3 × 3, ¿hay camino? */
	public static boolean hayCamino(int delCamino) {
		return delCamino >= MINIMO;
	}
}
