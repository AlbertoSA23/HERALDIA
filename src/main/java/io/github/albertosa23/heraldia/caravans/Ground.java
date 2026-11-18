package io.github.albertosa23.heraldia.caravans;

import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;

/**
 * Is there a road at a vertex? In an existing world, chunks generated before the roads do not have them even if the
 * route passes there: the caravan only goes where the road exists. The surface blocks in the 3 × 3 around the axis are
 * checked (the road is at least 3 wide) and {@link #MIN} of them must be ones the road places
 * (roads/RoadFeature.ground, and the planks of the bridges and walkways).
 */
public final class Ground {
	/** Blocks of the 3 × 3 that must belong to the road. */
	public static final int MIN = 4;
	private static final Block[] ROAD = {Blocks.DIRT_PATH, Blocks.COARSE_DIRT, Blocks.GRAVEL, Blocks.COBBLESTONE, Blocks.STONE_BRICKS,
			Blocks.SMOOTH_SANDSTONE, Blocks.SANDSTONE, Blocks.CUT_SANDSTONE, Blocks.SMOOTH_RED_SANDSTONE, Blocks.RED_SANDSTONE,
			Blocks.CUT_RED_SANDSTONE, Blocks.PACKED_MUD, Blocks.MUD_BRICKS,
			// the planks of the bridges and walkways (the woods of RoadFeature)
			Blocks.OAK_PLANKS, Blocks.SPRUCE_PLANKS, Blocks.BIRCH_PLANKS, Blocks.JUNGLE_PLANKS, Blocks.ACACIA_PLANKS, Blocks.DARK_OAK_PLANKS,
			Blocks.MANGROVE_PLANKS, Blocks.CHERRY_PLANKS, Blocks.PALE_OAK_PLANKS};

	private Ground() {
	}

	/** Is it a block the road places on the surface (or a bridge deck)? */
	public static boolean ofRoad(BlockState s) {
		for (Block b : ROAD) {
			if (s.is(b)) {
				return true;
			}
		}
		return false;
	}

	/** With {@code ofRoad} road blocks in the 3 × 3, is there a road? */
	public static boolean hasRoad(int ofRoad) {
		return ofRoad >= MIN;
	}
}
