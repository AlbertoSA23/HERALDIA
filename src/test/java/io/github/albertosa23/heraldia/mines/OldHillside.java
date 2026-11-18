package io.github.albertosa23.heraldia.mines;

import io.github.albertosa23.heraldia.mines.Hillside.Shape;
import io.github.albertosa23.heraldia.mines.Hillside.Site;
import io.github.albertosa23.heraldia.mines.Hillside.Terrain;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.block.Rotation;
import org.jspecify.annotations.Nullable;

/**
 * Literal copy of the 0.1.0 hillside search (before T36), to compare in MinesDeterminismTest. It finds a hillside for a
 * mine's mouth (pure logic: the terrain comes through {@link Terrain}, in the game the cached generation height map,
 * {@code common/Heights}). The same idea as the citadel (flat and dry in front of the gate,
 * the hill behind), but cheap, because mines are frequent:
 * <ol>
 * <li>five columns (the center and four at {@link #RADIUS} blocks) give the slope; if the terrain does not rise towards any
 * side (plain, plateau), it stops there;</li>
 * <li>the mouth faces downhill (the two directions that rise the most, at most) and is tried at three points along
 * the slope: the yard (nine samples of its box) dry and almost flat ({@link #DROP}), behind the mouth (nine
 * samples at 3-10 blocks) the hill at least {@link #RISE_MIN} higher on average and never less than {@link #HIGH_MIN}
 * above the yard, and above the gallery (the template's {@code ceiling} samples) terrain above its shell;</li>
 * <li>the one with the most rise (up to {@link #RISE_CAP}) and least drop in the yard wins.</li>
 * </ol>
 * With /place (forced) it is always placed: the best there is or, if none, facing downhill at the center.
 */
final class OldHillside {
	public static final int RADIUS = 16, DROP = 4, RISE_MIN = 5, HIGH_MIN = 3, RISE_CAP = 16, STEP = 8;
	/** Samples behind the mouth (dx, dz in template coordinates, from the mouth). */
	private static final int[][] BEHIND = {{-2, 3}, {0, 3}, {2, 3}, {-2, 6}, {0, 6}, {2, 6}, {-2, 10}, {0, 10}, {2, 10}};
	/** Rotations with which the back of the template (+z) faces south, west, north and east. */
	private static final Rotation[] ROTATION = {Rotation.NONE, Rotation.CLOCKWISE_90, Rotation.CLOCKWISE_180, Rotation.COUNTERCLOCKWISE_90};
	private static final int[][] DIR = {{0, 1}, {-1, 0}, {0, -1}, {1, 0}};

	private OldHillside() {
	}


	/**
	 * Template shape: the mouth (the ground block under its center), the yard box and the ceiling samples
	 * (x, z and how far above or below the mouth's feet the ground must be), in template coordinates.
	 */

	/** Chosen site: rotation, mouth (x, z), feet of the mouth and score. */

	/** World position of the template point (lx, lz) with the mouth at (bx, bz) and that rotation. */
	public static int[] world(Shape f, Rotation rotation, int bx, int bz, int lx, int lz) {
		BlockPos d = new BlockPos(lx - f.entry().getX(), 0, lz - f.entry().getZ()).rotate(rotation);
		return new int[] {bx + d.getX(), bz + d.getZ()};
	}

	/**
	 * The best hillside near (cx, cz), or null. minY is the world's minimum height: the template does not go below minY + 2.
	 */
	public static @Nullable Site search(Terrain t, int cx, int cz, Shape f, int minY, boolean forced) {
		int h0 = t.ground(cx, cz);
		int[] side = new int[4];
		for (int k = 0; k < 4; k++) {
			side[k] = t.ground(cx + DIR[k][0] * RADIUS, cz + DIR[k][1] * RADIUS);
		}
		List<Integer> dirs = new ArrayList<>(List.of(0, 1, 2, 3));
		dirs.sort(Comparator.comparingInt(k -> -(side[k] - side[(k + 2) % 4])));
		Site best = null;
		for (int n = 0; n < 2; n++) {
			int k = dirs.get(n);
			if (side[k] - side[(k + 2) % 4] < RISE_MIN && !forced) {
				break;                                  // it does not rise enough towards any other side
			}
			for (int o : new int[] {0, -STEP, STEP}) {
				int bx = cx + DIR[k][0] * o, bz = cz + DIR[k][1] * o;
				Site s = evaluateAt(t, f, ROTATION[k], bx, bz, minY, best == null ? Double.NEGATIVE_INFINITY : best.note());
				if (s != null && (best == null || s.note() > best.note())) {
					best = s;
				}
			}
		}
		if (best == null && forced) {
			best = new Site(ROTATION[dirs.get(0)], cx, cz, h0, 0);
		}
		return best;
	}

	/** Score of the mouth at (bx, bz) with that rotation, or null if the terrain does not work (or cannot beat `beat`). */
	static @Nullable Site evaluateAt(Terrain t, Shape f, Rotation rotation, int bx, int bz, int minY, double beat) {
		int[] xs = {f.yardX0(), (f.yardX0() + f.yardX1()) / 2, f.yardX1()};
		int[] zs = {f.yardZ0(), (f.yardZ0() + f.yardZ1()) / 2, f.yardZ1()};
		int[] ahead = new int[9];
		int i = 0;
		for (int lx : xs) {
			for (int lz : zs) {
				int[] p = world(f, rotation, bx, bz, lx, lz);
				if (t.water(p[0], p[1])) {
					return null;                        // water in the yard
				}
				ahead[i++] = t.ground(p[0], p[1]);
			}
		}
		int[] order = ahead.clone();
		java.util.Arrays.sort(order);
		int drop = order[8] - order[0];
		if (drop > DROP) {
			return null;
		}
		int feet = order[4];                            // the median: the yard cuts the excess and its foundation fills
		if (feet - 1 - f.entry().getY() < minY + 2) {
			return null;
		}
		double sum = 0;
		for (int[] d : BEHIND) {
			int[] p = world(f, rotation, bx, bz, f.entry().getX() + d[0], f.entry().getZ() + d[1]);
			int h = t.ground(p[0], p[1]);
			if (h < feet + HIGH_MIN) {
				return null;                            // there is no hill behind the mouth
			}
			sum += h - feet;
		}
		double rise = sum / BEHIND.length;
		if (rise < RISE_MIN) {
			return null;
		}
		double note = Math.min(rise, RISE_CAP) - drop;
		if (note <= beat) {
			return null;
		}
		for (int[] m : f.ceiling()) {
			int[] p = world(f, rotation, bx, bz, m[0], m[1]);
			if (t.ground(p[0], p[1]) < feet + m[2]) {
				return null;                            // the gallery's shell would stick out
			}
		}
		return new Site(rotation, bx, bz, feet, note);
	}
}
