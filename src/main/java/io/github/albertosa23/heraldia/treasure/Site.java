package io.github.albertosa23.heraldia.treasure;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.OptionalInt;
import java.util.Set;
import net.minecraft.core.BlockPos;

/**
 * Where to bury the final chest without touching anything of the players': pure logic over a {@link View} of the world
 * (SiteTest with fake worlds; in the game, {@link Treasure} provides it with the already loaded chunks, without loading any).
 * <p>The columns within {@code radius} blocks of the mark are walked, from nearest to farthest; the first one wins
 * in which: the top (the highest solid block, not counting leaves) and the one below are natural ground ({@link #ground}), there is
 * no liquid above, the chest's spot (one block below the top: it ends up buried) is not in the pieces of any
 * structure, and no column within {@code margin} blocks has a player-made block
 * ({@link #artificial}) between 6 blocks below its top and 10 above it. An unloaded column is not valid nor lets the
 * ones in its margin be valid.
 */
public final class Site {
	public static final int RADIUS = 16, MARGIN = 6, LOW = 6, ABOVE = 10;

	private Site() {
	}

	/** What the site needs to know about the world (block ids without namespace if they are minecraft's). */
	public interface View {
		/** y of the highest solid block (not counting leaves); empty if the column is not loaded. */
		OptionalInt top(int x, int z);

		String block(int x, int y, int z);

		boolean liquid(int x, int y, int z);

		boolean inStructure(int x, int y, int z);
	}

	public enum Reason {
		OK, UNLOADED, NO_SITE
	}

	public record Choice(Reason reason, Optional<BlockPos> chest) {
	}

	public static Choice choose(View v, int cx, int cz) {
		return choose(v, cx, cz, RADIUS, MARGIN);
	}

	public static Choice choose(View v, int cx, int cz, int radius, int margin) {
		Map<Long, Boolean> dirty = new HashMap<>();   // column with player stuff (or not loaded)
		boolean unloaded = false;
		for (int[] o : spiral(radius)) {
			int x = cx + o[0], z = cz + o[1];
			OptionalInt top = v.top(x, z);
			if (top.isEmpty()) {
				unloaded = true;
				continue;
			}
			int y = top.getAsInt();
			if (!ground(v.block(x, y, z)) || !ground(v.block(x, y - 1, z)) || v.liquid(x, y + 1, z) || v.inStructure(x, y - 1, z)) {
				continue;
			}
			boolean clean = true;
			for (int dx = -margin; dx <= margin && clean; dx++) {
				for (int dz = -margin; dz <= margin && clean; dz++) {
					int sx = x + dx, sz = z + dz;
					Boolean s = dirty.computeIfAbsent(key(sx, sz), k -> dirtyColumn(v, sx, sz));
					if (s) {
						clean = false;
					}
				}
			}
			if (clean) {
				return new Choice(Reason.OK, Optional.of(new BlockPos(x, y - 1, z)));
			}
		}
		return new Choice(unloaded ? Reason.UNLOADED : Reason.NO_SITE, Optional.empty());
	}

	static boolean dirtyColumn(View v, int x, int z) {
		OptionalInt top = v.top(x, z);
		if (top.isEmpty()) {
			return true;
		}
		int y0 = top.getAsInt();
		for (int y = y0 - LOW; y <= y0 + ABOVE; y++) {
			if (artificial(v.block(x, y, z))) {
				return true;
			}
		}
		return false;
	}

	/** Offsets (dx, dz) within the radius, from nearest to farthest (with a fixed order on ties). */
	static List<int[]> spiral(int radius) {
		List<int[]> out = new ArrayList<>();
		for (int dx = -radius; dx <= radius; dx++) {
			for (int dz = -radius; dz <= radius; dz++) {
				if (dx * dx + dz * dz <= radius * radius) {
					out.add(new int[]{dx, dz});
				}
			}
		}
		out.sort(Comparator.comparingInt((int[] o) -> o[0] * o[0] + o[1] * o[1]).thenComparingInt(o -> o[0]).thenComparingInt(o -> o[1]));
		return out;
	}

	private static long key(int x, int z) {
		return ((long) x << 32) ^ (z & 0xFFFFFFFFL);
	}

	private static String shortRange(String id) {
		return id.startsWith("minecraft:") ? id.substring("minecraft:".length()) : id;
	}

	/** Natural ground where something can be buried (dirt, sand, gravel, stone and the like). */
	public static boolean ground(String id) {
		String b = shortRange(id);
		return GROUND.contains(b) || b.endsWith("terracotta") && !b.contains("glazed");
	}

	private static final Set<String> GROUND = Set.of("grass_block", "dirt", "coarse_dirt", "rooted_dirt", "podzol", "mycelium", "mud",
			"sand", "red_sand", "gravel", "clay", "snow_block", "moss_block", "pale_moss_block", "stone", "granite", "diorite",
			"andesite", "deepslate", "tuff", "calcite", "sandstone", "red_sandstone", "dripstone_block", "suspicious_sand",
			"suspicious_gravel", "packed_mud");

	/** Words (pieces of the id separated by "_") of the blocks only a player (or a structure) places. */
	private static final Set<String> WORDS = Set.of("planks", "glass", "pane", "wool", "carpet", "bed", "door", "trapdoor",
			"fence", "gate", "wall", "stairs", "slab", "torch", "lantern", "lamp", "rail", "sign", "banner", "candle", "concrete",
			"bricks", "chest", "barrel", "furnace", "smoker", "anvil", "bookshelf", "lectern", "bell", "hopper", "dispenser",
			"dropper", "piston", "observer", "repeater", "comparator", "lever", "button", "plate", "bars", "chain", "ladder",
			"scaffolding", "farmland", "path", "polished", "smooth", "cut", "chiseled", "glazed", "beacon", "campfire", "hay",
			"composter", "cauldron", "pot", "potted", "shulker", "jukebox", "table", "stripped", "tnt", "stand", "box", "head",
			"skull", "tiles", "pillar", "conduit", "grindstone", "loom", "stonecutter", "crafter", "vault", "spawner",
			"wire", "hook");
	private static final Set<String> EXACT = Set.of("cobblestone", "quartz_block", "crafting_table", "note_block", "target",
			"sea_lantern", "glowstone", "end_rod", "redstone_block", "iron_block", "gold_block", "diamond_block", "emerald_block",
			"lapis_block", "coal_block", "copper_block", "netherite_block", "slime_block", "honey_block", "obsidian",
			"crying_obsidian", "respawn_anchor", "lodestone", "enchanting_table", "ender_chest", "beehive", "sponge", "wet_sponge",
			"dirt_path", "tripwire");
	/** Natural ones that share a word with the artificial ones. */
	private static final Set<String> NATURAL = Set.of("moss_carpet", "pale_moss_carpet", "pointed_dripstone", "redstone_ore",
			"deepslate_redstone_ore", "bee_nest", "mushroom_stem", "brown_mushroom_block", "red_mushroom_block");

	/** Block placed by a player (or by a construction)? By its id; the natural ones with shared words, no. */
	public static boolean artificial(String id) {
		String b = shortRange(id);
		if (NATURAL.contains(b)) {
			return false;
		}
		if (EXACT.contains(b)) {
			return true;
		}
		for (String p : b.split("_")) {
			if (WORDS.contains(p)) {
				return true;
			}
		}
		return false;
	}
}
