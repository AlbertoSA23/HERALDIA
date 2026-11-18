package io.github.albertosa23.heraldia.arena;

/**
 * The arena placed in the world: its origin (the template's minimum corner) and its blueprint. It gives the protected box
 * (an integer AABB in memory: checking each block is six comparisons), whether a point is in the ring and the
 * world positions of the bell, the gate, the spawn points and the respawn point. No game classes.
 */
public record Zone(int ox, int oy, int oz, Blueprint plan) {
	/** Blocks around the box where buckets cannot be emptied (non-operator players and dispensers). */
	public static final int BUCKET_RADIUS = 6;

	/** Template origin so its center falls on column (cx, cz) and its ground at height {@code ground}. */
	public static Zone centered(int cx, int cz, int ground, Blueprint plan) {
		return new Zone(cx - plan.center()[0], ground - plan.ground(), cz - plan.center()[2], plan);
	}

	public int minX() {
		return ox;
	}

	public int minY() {
		return oy;
	}

	public int minZ() {
		return oz;
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

	/** Block inside the protected box (the whole template)? */
	public boolean mentions(int x, int y, int z) {
		return x >= ox && y >= oy && z >= oz && x <= maxX() && y <= maxY() && z <= maxZ();
	}

	/** Block inside the box widened by {@code m} blocks on each side? */
	public boolean near(int x, int y, int z, int m) {
		return x >= ox - m && y >= oy - m && z >= oz - m && x <= maxX() + m && y <= maxY() + m && z <= maxZ() + m;
	}

	/**
	 * Is emptying a bucket at this block denied? Within {@link #BUCKET_RADIUS} of the box, except for an operator (a
	 * dispenser never is one): so a dispenser stuck to the arena neither floods it nor pours lava on it.
	 */
	public boolean bucketDenied(int x, int y, int z, boolean operator) {
		return !operator && near(x, y, z, BUCKET_RADIUS);
	}

	/** Center of the ring (x, z of its column's center). */
	public double centerX() {
		return ox + plan.center()[0] + 0.5;
	}

	public double centerZ() {
		return oz + plan.center()[2] + 0.5;
	}

	/** Center column (block). */
	public int columnX() {
		return ox + plan.center()[0];
	}

	public int columnZ() {
		return oz + plan.center()[2];
	}

	/** y of the outer ground (the template layer flush with the terrain). */
	public int groundY() {
		return oy + plan.ground();
	}

	/** Margin over the ring's radius: a player against the wall has the center of their body somewhat past the radius. */
	public static final double RING_MARGIN = 1.5;

	/**
	 * Point (an entity's feet) inside the ring? Within its radius (with {@link #RING_MARGIN}: the wall and the glass
	 * already prevent passing) and between its heights (with half a block of margin).
	 */
	public boolean inRing(double x, double y, double z) {
		double dx = x - centerX(), dz = z - centerZ();
		double r = plan.radius() + RING_MARGIN;
		return dx * dx + dz * dz < r * r && y >= oy + plan.ringY()[0] - 0.5 && y <= oy + plan.ringY()[1] + 1;
	}

	/** World position of a point relative to the blueprint. */
	public int[] world(int[] rel) {
		return new int[] {ox + rel[0], oy + rel[1], oz + rel[2]};
	}

	public int[] bell() {
		return world(plan.bell());
	}

	public int[] respawn() {
		return world(plan.respawn());
	}

	public int[] point(int i) {
		return world(plan.points().get(Math.floorMod(i, plan.points().size())));
	}

	public int points() {
		return plan.points().size();
	}

	public int[] gateMin() {
		return world(plan.gate()[0]);
	}

	public int[] gateMax() {
		return world(plan.gate()[1]);
	}

	/** Is this block the bell? */
	public boolean isBell(int x, int y, int z) {
		int[] c = bell();
		return c[0] == x && c[1] == y && c[2] == z;
	}

	/**
	 * Protection of a block: protected if it is in the box and whoever acts is not an operator. Explosions, pistons
	 * and endermen are not operators ({@code operator} = false).
	 */
	public boolean isProtected(int x, int y, int z, boolean operator) {
		return !operator && mentions(x, y, z);
	}
}
