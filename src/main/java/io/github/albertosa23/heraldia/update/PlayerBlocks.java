package io.github.albertosa23.heraldia.update;

import java.util.Set;

/**
 * Typical player blocks (T46), pure logic over the block's name: what the terrain does not generate on its own and almost
 * always someone places (beds, chests, barrels, signs, crafting tables, furnaces, rails, fences, doors, torches,
 * planks, glass, wool, bricks, farmland...). Structures also bring them (villages, abandoned
 * mineshafts, ruins): the analysis only counts the ones outside the pieces of the structures saved in the
 * chunk. And the "natural top" to compare with the regeneration: logs, leaves, mushrooms, snow, ice, growing plants
 * and fluids, which change without anyone building.
 */
public final class PlayerBlocks {
	private static final Set<String> EXACT = Set.of("chest", "trapped_chest", "barrel", "crafting_table", "furnace",
			"blast_furnace", "smoker", "rail", "powered_rail", "detector_rail", "activator_rail", "torch", "wall_torch",
			"soul_torch", "soul_wall_torch", "lantern", "soul_lantern", "ladder", "farmland", "bookshelf", "chiseled_bookshelf",
			"enchanting_table", "anvil", "chipped_anvil", "damaged_anvil", "brewing_stand", "cartography_table",
			"fletching_table", "smithing_table", "loom", "stonecutter", "grindstone", "composter", "lectern", "jukebox",
			"note_block", "beacon", "respawn_anchor", "ender_chest", "hopper", "dropper", "dispenser", "observer", "piston",
			"sticky_piston", "lever", "repeater", "comparator", "redstone_lamp", "glass", "glass_pane", "tinted_glass", "bricks",
			"stone_bricks", "cobblestone_wall", "hay_block", "campfire", "soul_campfire", "scaffolding", "iron_bars", "chain",
			"iron_chain", "item_frame", "flower_pot", "cake", "crafter", "decorated_pot", "copper_bulb", "target", "bell",
			"white_concrete", "smooth_stone", "polished_andesite", "polished_diorite", "polished_granite");
	private static final String[] SUFFIXES = {"_bed", "_planks", "_sign", "_hanging_sign", "_wall_sign", "_wall_hanging_sign",
			"_fence", "_fence_gate", "_door", "_trapdoor", "_wool", "_carpet", "_stained_glass", "_stained_glass_pane",
			"_shulker_box", "_concrete", "_terracotta_slab", "_banner", "_wall_banner", "_bricks", "_brick_stairs",
			"_brick_slab", "_brick_wall", "_candle"};
	private static final String[] NATURAL_SUFFIXES = {"_log", "_wood", "_stem", "_hyphae", "_leaves", "_sapling",
			"_mushroom_block", "_mushroom", "_ice", "_coral", "_coral_block", "_coral_fan"};
	private static final Set<String> NATURAL = Set.of("snow", "snow_block", "ice", "powder_snow", "water", "lava", "vine",
			"cactus", "bamboo", "sugar_cane", "kelp", "kelp_plant", "seagrass", "tall_seagrass", "pumpkin", "melon",
			"mushroom_stem", "bee_nest", "moss_block", "moss_carpet", "pale_moss_block", "pale_moss_carpet", "cocoa",
			"sweet_berry_bush", "big_dripleaf", "big_dripleaf_stem", "pointed_dripstone", "mossy_cobblestone", "glow_lichen",
			"short_grass", "tall_grass", "fern", "large_fern", "dead_bush", "mangrove_roots", "muddy_mangrove_roots",
			"bubble_column", "obsidian", "magma_block", "basalt", "blackstone", "calcite", "amethyst_block",
			"budding_amethyst", "creaking_heart", "resin_clump", "leaf_litter", "firefly_bush", "bush", "cactus_flower");

	/**
	 * Player blocks that generation also places outside the structure boxes: planks and chains of the
	 * abandoned mineshafts (the bridges under the galleries), fences and rails, and the dungeon chests (which are a terrain
	 * feature, not a structure). Seen in a 26.3 test world (tools/smoke/update.py).
	 */
	private static final Set<String> AMBIGUOUS_EXACT = Set.of("chest", "rail", "chain", "iron_chain");
	private static final String[] AMBIGUOUS_SUFFIXES = {"_planks", "_fence"};

	private PlayerBlocks() {
	}

	/**
	 * A player block that also spawns on its own? Those only count as a build in a chunk some
	 * player has passed through (InhabitedTime greater than 0): to place them by hand one has to be nearby.
	 */
	public static boolean ambiguous(String id) {
		String r = route(id);
		if (AMBIGUOUS_EXACT.contains(r)) {
			return true;
		}
		for (String s : AMBIGUOUS_SUFFIXES) {
			if (r.endsWith(s)) {
				return true;
			}
		}
		return false;
	}

	private static String route(String id) {
		int i = id.indexOf(':');
		return i >= 0 ? id.substring(i + 1) : id;
	}

	/** Typical player block? ({@code minecraft:oak_planks}, {@code red_bed}...) Other mods' do not count. */
	public static boolean playerSource(String id) {
		if (id.indexOf(':') >= 0 && !id.startsWith("minecraft:")) {
			return false;
		}
		String r = route(id);
		if (EXACT.contains(r)) {
			return true;
		}
		for (String s : SUFFIXES) {
			if (r.endsWith(s)) {
				return true;
			}
		}
		return false;
	}

	/**
	 * Can it be at the top of a column without anyone having built? (trees, huge mushrooms, snow, ice, growing
	 * plants, fluids, terrain-feature rocks). Such a top does not count as a difference with the regeneration.
	 */
	public static boolean naturalTop(String id) {
		String r = route(id);
		if (NATURAL.contains(r)) {
			return true;
		}
		for (String s : NATURAL_SUFFIXES) {
			if (r.endsWith(s)) {
				return true;
			}
		}
		return false;
	}
}
