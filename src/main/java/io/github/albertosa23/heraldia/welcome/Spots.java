package io.github.albertosa23.heraldia.welcome;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import org.jspecify.annotations.Nullable;

/**
 * Where a village shows its reputation (pure logic): spots in the local coordinates of the mod's own village pieces, the
 * same templates the generator writes ({@code tools/gen/streets.py} and {@code tools/gen/board.py}), and the rule that
 * decides, for each spot, whether to place, keep, take down or leave it alone.
 * <p>
 * Every spot is <b>outside</b> what the template places (a cell its template leaves to the terrain, which in a village is
 * air) and next to a block the template <b>does</b> place (its support). A decoration is only put up where the block is air
 * and the support is still the template's own block, and only taken down while it is still exactly what was put up. So a
 * player's block is never replaced or removed: see {@link #decide}.
 */
public final class Spots {
	private Spots() {
	}

	/** The village pieces that get decorations, recognized by the path of their template. */
	public enum Piece {
		/** {@code <style>/terminators/gate}: a stretch of wall with an arch; the street comes from the north (z = 0), outside is z > 2. */
		GATE,
		/** {@code <style>/terminators/tower} and {@code tower_b}: watchtower, door on its north face (z = 2), windows at y 4 and 8. */
		TOWER,
		/** {@code <style>/plaza/std} and {@code plaza/grande}: the 23 × 23 main square, fountain in the middle (11, 11). */
		PLAZA,
		/** {@code <style>/tablon}: the job board's lectern at (0, 0, 0), facing north, with the bailiff behind it. */
		BOARD;

		/** The piece of a template path, or null if it gets no decoration. */
		public static @Nullable Piece of(String path) {
			if (path.endsWith("/terminators/gate")) {
				return GATE;
			}
			if (path.endsWith("/terminators/tower") || path.endsWith("/terminators/tower_b")) {
				return TOWER;
			}
			if (path.endsWith("/plaza/std") || path.endsWith("/plaza/grande")) {
				return PLAZA;
			}
			return path.endsWith("/tablon") ? BOARD : null;
		}
	}

	/** What goes on a spot (vanilla blocks only); the materials come from the village's own style ({@link Materials}). */
	public enum Item {
		/** A banner of the style's colour hanging on a wall; {@code dir}: the direction it faces. */
		WALL_BANNER,
		/** A standing banner of the style's colour; {@code dir}: its rotation (0 south, 4 west, 8 north, 12 east). */
		BANNER,
		/** A flower pot with a flower of the village's land; {@code dir}: which of its two flowers. */
		POT,
		/** The style's lantern, standing. */
		LANTERN,
		/** A carpet of the style's colour. */
		CARPET,
		/** An open trapdoor of the style's wood flat against a window (a closed shutter); {@code dir}: the direction it faces. */
		SHUTTER
	}

	/**
	 * A spot: piece, local position, what goes there, its direction (see {@link Item}), the looks in which it is up
	 * ([{@code min}, {@code max}]), and its support: the local position of the block it leans on or stands on. With
	 * {@code templateSupport}, that block must still be the one the template put there; otherwise, any block with a
	 * sturdy top face (the board is a separate piece standing on the square's paving).
	 */
	public record Spot(Piece piece, int x, int y, int z, Item item, int dir, Look min, Look max,
			int sx, int sy, int sz, boolean templateSupport) {
		public boolean shownIn(Look look) {
			return look.within(min, max);
		}
	}

	/** Directions in the template's own frame (before the piece's rotation), as indices for {@link Spot#dir}. */
	public static final int NORTH = 0, EAST = 1, SOUTH = 2, WEST = 3;
	/** Banner rotations: the front faces south (0), west (4), north (8) or east (12). */
	public static final int R_SOUTH = 0, R_WEST = 4, R_NORTH = 8, R_EAST = 12;

	/** Square: its side and centre (streets.plaza: N = 23, c = 11). The fountain's rim is at distance 3 from the centre. */
	static final int N = 23, C = N / 2;

	private static final Map<Piece, List<Spot>> SPOTS = Map.of(
			Piece.GATE, gate(), Piece.TOWER, tower(), Piece.PLAZA, plaza(), Piece.BOARD, board());

	/** The spots of a piece. */
	public static List<Spot> of(Piece piece) {
		return SPOTS.get(piece);
	}

	/** Every spot of every piece (for the tests and the documentation). */
	public static List<Spot> all() {
		List<Spot> l = new ArrayList<>();
		for (Piece p : Piece.values()) {
			l.addAll(of(p));
		}
		return l;
	}

	private static List<Spot> gate() {
		List<Spot> l = new ArrayList<>();
		for (int x : new int[] {5, 9}) {
			// the face seen when arriving from outside: the wall (z = 2) at banner height, by the arch (x 6-8)
			l.add(new Spot(Piece.GATE, x, 4, 3, Item.WALL_BANNER, SOUTH, Look.FRIEND, Look.HERO, x, 4, 2, true));
			// on the battlement (y 5 is the wall's top; y 6 has merlons only on even x)
			l.add(new Spot(Piece.GATE, x, 6, 2, Item.LANTERN, 0, Look.HERO, Look.HERO, x, 5, 2, true));
		}
		return List.copyOf(l);
	}

	private static List<Spot> tower() {
		List<Spot> l = new ArrayList<>();
		for (int x : new int[] {2, 4}) {
			// either side of the door (3, 1..2, 2), above it, facing the street
			l.add(new Spot(Piece.TOWER, x, 3, 1, Item.WALL_BANNER, NORTH, Look.FRIEND, Look.HERO, x, 3, 2, true));
		}
		for (int y : new int[] {4, 8}) {
			// shutters over the three windows: (3, y, 6) south, (1, y, 4) west, (5, y, 4) east
			l.add(new Spot(Piece.TOWER, 3, y, 7, Item.SHUTTER, SOUTH, Look.SHUNNED, Look.SHUNNED, 3, y, 6, true));
			l.add(new Spot(Piece.TOWER, 0, y, 4, Item.SHUTTER, WEST, Look.SHUNNED, Look.SHUNNED, 1, y, 4, true));
			l.add(new Spot(Piece.TOWER, 6, y, 4, Item.SHUTTER, EAST, Look.SHUNNED, Look.SHUNNED, 5, y, 4, true));
		}
		return List.copyOf(l);
	}

	private static List<Spot> plaza() {
		List<Spot> l = new ArrayList<>();
		int lo = C - 3, hi = C + 3;
		int i = 0;
		// flowers on the four corners of the fountain's rim (y 1), then on the middle of each side
		for (int[] p : new int[][] {{lo, lo}, {hi, lo}, {lo, hi}, {hi, hi}}) {
			l.add(new Spot(Piece.PLAZA, p[0], 2, p[1], Item.POT, i++ % 2, Look.KNOWN, Look.HERO, p[0], 1, p[1], true));
		}
		for (int[] p : new int[][] {{C, lo}, {hi, C}, {C, hi}, {lo, C}}) {
			l.add(new Spot(Piece.PLAZA, p[0], 2, p[1], Item.POT, i++ % 2, Look.HERO, Look.HERO, p[0], 1, p[1], true));
		}
		// a pair of banners at each of the four avenue entrances (the avenue's path is C-2..C+2), facing the avenue
		for (int d : new int[] {-3, 3}) {
			l.add(new Spot(Piece.PLAZA, C + d, 1, 1, Item.BANNER, R_NORTH, Look.FRIEND, Look.HERO, C + d, 0, 1, true));
			l.add(new Spot(Piece.PLAZA, C + d, 1, N - 2, Item.BANNER, R_SOUTH, Look.FRIEND, Look.HERO, C + d, 0, N - 2, true));
			l.add(new Spot(Piece.PLAZA, 1, 1, C + d, Item.BANNER, R_WEST, Look.FRIEND, Look.HERO, 1, 0, C + d, true));
			l.add(new Spot(Piece.PLAZA, N - 2, 1, C + d, Item.BANNER, R_EAST, Look.FRIEND, Look.HERO, N - 2, 0, C + d, true));
		}
		return List.copyOf(l);
	}

	private static List<Spot> board() {
		return List.of(
				// banners either side of the lectern, facing whoever reads it (north)
				new Spot(Piece.BOARD, -1, 0, 0, Item.BANNER, R_NORTH, Look.FRIEND, Look.HERO, -1, -1, 0, false),
				new Spot(Piece.BOARD, 1, 0, 0, Item.BANNER, R_NORTH, Look.FRIEND, Look.HERO, 1, -1, 0, false),
				// a carpet where the reader stands
				new Spot(Piece.BOARD, 0, 0, -1, Item.CARPET, 0, Look.HERO, Look.HERO, 0, -1, -1, false));
	}

	/** What to do with one spot. */
	public enum Action {
		/** Put the decoration up (and record it). */
		PLACE,
		/** It is up and still ours: nothing. */
		KEEP,
		/** Ours and no longer wanted: take it down (back to air) and forget it. */
		REMOVE,
		/** Something else is there now (a player took it or built there): never touch this spot again. */
		DECLINE,
		/** Nothing to do (not wanted and not ours, or not possible now: not air, the support is not the template's). */
		NONE
	}

	/**
	 * The rule of the whole feature, so that no player's block is ever lost:
	 * <ul>
	 * <li>it is only <b>placed</b> on air, on its template support, and never on a spot declined before;</li>
	 * <li>it is only <b>removed</b> while the block there is exactly the one that was placed and nothing rests on it
	 * (a player's block on top of a carpet would drop); otherwise it is left as it is and declined;</li>
	 * <li>if what was placed is not there any more (broken, replaced, a pot whose flower was taken), the spot is
	 * <b>declined</b>: forgotten and never decorated again, so the village does not fight a player who took it down.</li>
	 * </ul>
	 *
	 * @param wanted   the spot is up in the village's look
	 * @param placed   what this mod placed there (null: nothing)
	 * @param current  what is there now
	 * @param air      the block there now is air
	 * @param support  its support is in place (the template's block, or a sturdy face) and the decoration would survive there
	 * @param declined the spot was declined before
	 * @param free     nothing rests on the block there (the block above is air)
	 */
	public static <S> Action decide(boolean wanted, @Nullable S placed, S current, boolean air, boolean support, boolean declined,
			boolean free) {
		if (placed != null) {
			if (!Objects.equals(placed, current)) {
				return Action.DECLINE;
			}
			return wanted ? Action.KEEP : free ? Action.REMOVE : Action.DECLINE;
		}
		if (wanted && !declined && air && support) {
			return Action.PLACE;
		}
		return Action.NONE;
	}

	/** The family of a style id ({@code llanuras_castellana} → {@code llanuras}). */
	public static String family(String style) {
		int i = style.indexOf('_');
		return i < 0 ? style : style.substring(0, i);
	}

	/** The two potted flowers of each family's land (block ids without namespace); a default pair otherwise. */
	private static final Map<String, String[]> FLOWERS = Map.ofEntries(
			Map.entry("llanuras", new String[] {"potted_poppy", "potted_dandelion"}),
			Map.entry("bosque", new String[] {"potted_allium", "potted_lily_of_the_valley"}),
			Map.entry("oscuro", new String[] {"potted_red_mushroom", "potted_brown_mushroom"}),
			Map.entry("taiga", new String[] {"potted_fern", "potted_spruce_sapling"}),
			Map.entry("nieve", new String[] {"potted_spruce_sapling", "potted_white_tulip"}),
			Map.entry("desierto", new String[] {"potted_cactus", "potted_dead_bush"}),
			Map.entry("sabana", new String[] {"potted_acacia_sapling", "potted_red_tulip"}),
			Map.entry("jungla", new String[] {"potted_bamboo", "potted_jungle_sapling"}),
			Map.entry("pantano", new String[] {"potted_blue_orchid", "potted_brown_mushroom"}),
			Map.entry("cerezos", new String[] {"potted_cherry_sapling", "potted_pink_tulip"}),
			Map.entry("badlands", new String[] {"potted_dead_bush", "potted_cactus"}),
			Map.entry("costa", new String[] {"potted_cornflower", "potted_azure_bluet"}));
	private static final String[] DEFAULT_FLOWERS = {"potted_poppy", "potted_dandelion"};

	/** The potted flower ({@code which} 0 or 1) of a style. */
	public static String flower(String style, int which) {
		return FLOWERS.getOrDefault(family(style), DEFAULT_FLOWERS)[Math.floorMod(which, 2)];
	}

	/** Families with their own flowers (for the tests). */
	static java.util.Set<String> flowerFamilies() {
		return FLOWERS.keySet();
	}

	/**
	 * The colour of a banner block id ({@code minecraft:red_wall_banner} → {@code red}), or null if it is not a banner.
	 */
	public static @Nullable String bannerColour(String blockId) {
		String path = blockId.substring(blockId.indexOf(':') + 1);
		for (String suffix : new String[] {"_wall_banner", "_banner"}) {
			if (path.endsWith(suffix) && path.length() > suffix.length()) {
				return path.substring(0, path.length() - suffix.length());
			}
		}
		return null;
	}

	/** The wood of a fence block id ({@code minecraft:spruce_fence} → {@code spruce}), or null if it is not a wooden fence. */
	public static @Nullable String fenceWood(String blockId) {
		String path = blockId.substring(blockId.indexOf(':') + 1);
		if (!path.endsWith("_fence") || path.equals("nether_brick_fence")) {
			return null;
		}
		return path.substring(0, path.length() - "_fence".length());
	}
}
