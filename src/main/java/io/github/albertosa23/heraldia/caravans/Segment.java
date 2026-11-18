package io.github.albertosa23.heraldia.caravans;

import io.github.albertosa23.heraldia.roads.RoadLayout;
import java.util.List;
import org.jspecify.annotations.Nullable;

/**
 * Stretch of road a caravan travels (pure logic): from one vertex of the canonical route between two neighboring villages
 * ({@link RoadLayout.Route}) to another, in one direction. The caravan starts at a vertex between {@link #DIST_MIN} and
 * {@link #DIST_MAX} blocks from the player (never on top of them nor inside a village) and heads to the point of the route
 * closest to the player, so it passes in front of them; it travels at most {@link #LENGTH} vertices and stops before the
 * destination village's plaza.
 *
 * @param start index of the starting vertex in the route
 * @param end   index of the arrival vertex
 * @param step  +1 (from {@code route.from} to {@code route.until}) or -1
 */
public record Segment(RoadLayout.Route route, int start, int end, int step) {
	/** Vertices it travels at most (16 blocks each: about 128 blocks) and at least. */
	public static final int LENGTH = 8, MIN = 4;
	/** Vertices left free at each end of the route: the start is not in a village and the arrival is not the plaza. */
	public static final int VILLAGE_MARGIN = 3;
	/** Distance in blocks (horizontal) from the player to the starting vertex. */
	public static final int DIST_MIN = 24, DIST_MAX = 80;

	/** Village it is going to (its plaza, packed with {@link RoadLayout#pack}). */
	public long destination() {
		return step > 0 ? route.until : route.from;
	}

	/** Village it comes from. */
	public long origin() {
		return step > 0 ? route.from : route.until;
	}

	/** Vertices of the segment, counting the start and the arrival. */
	public int vertices() {
		return Math.abs(end - start) + 1;
	}

	/** Route index of the segment's k-th vertex (0 = start). */
	public int vertex(int k) {
		return start + k * step;
	}

	public int x(int k) {
		return (int) Math.floor(route.x(vertex(k)));
	}

	public int z(int k) {
		return (int) Math.floor(route.z(vertex(k)));
	}

	/** Length of the segment in blocks (along the road). */
	public double length() {
		return Math.abs(route.arc(end) - route.arc(start));
	}

	/**
	 * The segment for a caravan near the player at (x, z), or null if no route passes close enough. Of the
	 * given routes, the valid starting vertex closest to the player is taken (at equal distance, the one from the earlier
	 * route in the list and the lower index: deterministic); the direction, towards that route's vertex closest to the
	 * player (if it is the same one, the one {@code seed} says), and if {@link #MIN} vertices do not fit that way, the other.
	 */
	public static @Nullable Segment choose(List<RoadLayout.Route> routes, int x, int z, long seed) {
		Segment best = null;
		double bestD = Double.MAX_VALUE;
		for (RoadLayout.Route r : routes) {
			int n = r.vertices();
			int lo = VILLAGE_MARGIN, hi = n - 1 - VILLAGE_MARGIN;
			if (hi - lo < MIN) {
				continue;           // route too short for a segment outside the villages
			}
			int near = 0;
			double nearD = Double.MAX_VALUE;
			for (int i = 0; i < n; i++) {
				double d = dist(r, i, x, z);
				if (d < nearD) {
					nearD = d;
					near = i;
				}
			}
			for (int i = lo; i <= hi; i++) {
				double d = dist(r, i, x, z);
				if (d < DIST_MIN || d > DIST_MAX || d >= bestD) {
					continue;
				}
				int step = near > i ? 1 : near < i ? -1 : ((seed & 1) == 0 ? 1 : -1);
				int fits = step > 0 ? hi - i : i - lo;
				if (fits < MIN) {
					step = -step;
					fits = step > 0 ? hi - i : i - lo;
				}
				if (fits < MIN) {
					continue;
				}
				bestD = d;
				best = new Segment(r, i, i + step * Math.min(LENGTH, fits), step);
			}
		}
		return best;
	}

	static double dist(RoadLayout.Route r, int i, int x, int z) {
		return Math.hypot(r.x(i) - x, r.z(i) - z);
	}

	/** The same stretch the other way round (the wayfarers: a pilgrim walks it towards its shrine). */
	public Segment reversed() {
		return new Segment(route, end, start, -step);
	}

	/** Trims the segment so it ends at its k-th vertex (the road does not go further in an existing world). */
	public Segment until(int k) {
		return new Segment(route, start, vertex(k), step);
	}
}
