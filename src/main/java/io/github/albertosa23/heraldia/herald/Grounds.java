package io.github.albertosa23.heraldia.herald;

import java.util.Set;

/**
 * The Herald's House placed in the world: its origin (the template's minimum corner) and its blueprint. It answers, with
 * integer comparisons only, whether a block is in the footprint, in the protected area (the footprint and {@link #RING}
 * blocks around it, every height), in a stall's box, on a stall sign, a return barrel or the portal frame; and which
 * blocks a player who is not an operator may use there. No game classes: the tests check it.
 */
public record Grounds(int ox, int oy, int oz, HousePlan plan) {
	/** Protected blocks beyond the footprint, on each side (the owner: at least 50). */
	public static final int RING = 50;

	/** Template origin so its spawn point falls on column (x, z) and its ground at height {@code ground}. */
	public static Grounds centered(int x, int z, int ground, HousePlan plan) {
		return new Grounds(x - plan.size()[0] / 2, ground - plan.ground(), z - plan.size()[2] / 2, plan);
	}

	public int maxX() {
		return ox + plan.size()[0] - 1;
	}

	public int maxY() {
		return oy + plan.size()[1] - 1;
	}

	public int maxZ() {
		return oz + plan.size()[2] - 1;
	}

	public int groundY() {
		return oy + plan.ground();
	}

	public int centerX() {
		return ox + plan.size()[0] / 2;
	}

	public int centerZ() {
		return oz + plan.size()[2] / 2;
	}

	public int[] world(int[] rel) {
		return new int[] {ox + rel[0], oy + rel[1], oz + rel[2]};
	}

	public int[] spawn() {
		return world(plan.spawn());
	}

	/** In the template's box (template heights)? */
	public boolean inFootprint(int x, int y, int z) {
		return x >= ox && z >= oz && x <= maxX() && z <= maxZ() && y >= oy && y <= maxY();
	}

	/** In the footprint's columns (any height)? */
	public boolean inColumns(int x, int z) {
		return x >= ox && z >= oz && x <= maxX() && z <= maxZ();
	}

	/** In the protected area: the footprint and {@link #RING} blocks around it, from bedrock to the sky. */
	public boolean inArea(int x, int z) {
		return x >= ox - RING && z >= oz - RING && x <= maxX() + RING && z <= maxZ() + RING;
	}

	/** Within {@code m} blocks of the protected area (horizontally)? */
	public boolean nearArea(int x, int z, int m) {
		return x >= ox - RING - m && z >= oz - RING - m && x <= maxX() + RING + m && z <= maxZ() + RING + m;
	}

	/** Does the protected area touch the rectangle (inclusive)? */
	public boolean areaOverlaps(int minX, int minZ, int maxX, int maxZ) {
		return minX <= maxX() + RING && maxX >= ox - RING && minZ <= maxZ() + RING && maxZ >= oz - RING;
	}

	/** Number of the stall whose box holds the block, or 0. */
	public int stallAt(int x, int y, int z) {
		for (HousePlan.Stall s : plan.stalls()) {
			int[] a = world(s.min()), b = world(s.max());
			if (x >= a[0] && y >= a[1] && z >= a[2] && x <= b[0] && y <= b[1] && z <= b[2]) {
				return s.id();
			}
		}
		return 0;
	}

	/** Number of the stall whose sign this is, or 0. */
	public int signAt(int x, int y, int z) {
		for (HousePlan.Stall s : plan.stalls()) {
			int[] c = world(s.sign());
			if (c[0] == x && c[1] == y && c[2] == z) {
				return s.id();
			}
		}
		return 0;
	}

	/** Index of the return barrel at this block, or -1. */
	public int barrelAt(int x, int y, int z) {
		for (int i = 0; i < plan.returns().size(); i++) {
			int[] c = world(plan.returns().get(i));
			if (c[0] == x && c[1] == y && c[2] == z) {
				return i;
			}
		}
		return -1;
	}

	/** On the portal frame or inside it? */
	public boolean inPortal(int x, int y, int z) {
		int[] a = world(plan.portal()[0]), b = world(plan.portal()[1]);
		return x >= a[0] && y >= a[1] && z >= a[2] && x <= b[0] && y <= b[1] && z <= b[2];
	}

	/**
	 * Is this block protected against whoever acts? Yes in the area, except for an operator and, inside their own stall's
	 * box, for its tenant ({@code ownStall}: the stall the actor rents, 0 if none). Explosions, pistons, endermen and
	 * dispensers are nobody: {@code operator} false, {@code ownStall} 0.
	 */
	public boolean isProtected(int x, int y, int z, boolean operator, int ownStall) {
		if (operator || !inArea(x, z)) {
			return false;
		}
		return ownStall == 0 || stallAt(x, y, z) != ownStall;
	}

	private static final Set<String> USABLE = Set.of("bell", "crafting_table", "cartography_table", "smithing_table",
			"stonecutter", "loom", "grindstone", "enchanting_table", "ender_chest", "fletching_table");
	private static final String[] USABLE_SUFFIXES = {"_door", "_trapdoor", "_fence_gate", "_button", "_bed"};

	/**
	 * Blocks anyone may use in the area (by id path, e.g. "crimson_door"): doors, trapdoors, gates and buttons (not
	 * iron ones), beds, the bell and the workstations whose screen changes nothing in the world. Containers, lecterns,
	 * signs, anvils, cauldrons, composters, flower pots... are not.
	 */
	public static boolean usable(String block) {
		if (USABLE.contains(block)) {
			return true;
		}
		if (block.startsWith("iron_")) {
			return false;
		}
		for (String s : USABLE_SUFFIXES) {
			if (block.endsWith(s)) {
				return true;
			}
		}
		return false;
	}
}
