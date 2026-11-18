package io.github.albertosa23.heraldia.arena;

/**
 * La arena colocada en el mundo: su origen (esquina mínima de la plantilla) y su plano. Da la caja protegida (una AABB
 * de enteros en memoria: la comprobación de cada bloque son seis comparaciones), si un punto está en el ruedo y las
 * posiciones del mundo de la campana, la puerta, los puntos de aparición y la reaparición. Sin clases del juego.
 */
public record Zone(int ox, int oy, int oz, Blueprint plan) {
	/** Bloques alrededor de la caja donde no se vacían cubos (jugadores que no son operadores y dispensadores). */
	public static final int BUCKET_RADIUS = 6;

	/** Origen de la plantilla para que su centro caiga en la columna (cx, cz) y su suelo en la altura {@code ground}. */
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

	/** ¿Bloque dentro de la caja protegida (toda la plantilla)? */
	public boolean mentions(int x, int y, int z) {
		return x >= ox && y >= oy && z >= oz && x <= maxX() && y <= maxY() && z <= maxZ();
	}

	/** ¿Bloque dentro de la caja ampliada {@code m} bloques por cada lado? */
	public boolean near(int x, int y, int z, int m) {
		return x >= ox - m && y >= oy - m && z >= oz - m && x <= maxX() + m && y <= maxY() + m && z <= maxZ() + m;
	}

	/**
	 * ¿Se niega vaciar un cubo en este bloque? A menos de {@link #BUCKET_RADIUS} de la caja, salvo a un operador (un
	 * dispensador nunca lo es): así un dispensador pegado a la arena no la inunda ni le echa lava.
	 */
	public boolean bucketDenied(int x, int y, int z, boolean operator) {
		return !operator && near(x, y, z, BUCKET_RADIUS);
	}

	/** Centro del ruedo (x, z del centro de su columna). */
	public double centerX() {
		return ox + plan.center()[0] + 0.5;
	}

	public double centerZ() {
		return oz + plan.center()[2] + 0.5;
	}

	/** Columna del centro (bloque). */
	public int columnX() {
		return ox + plan.center()[0];
	}

	public int columnZ() {
		return oz + plan.center()[2];
	}

	/** y del suelo exterior (la capa de la plantilla a ras del terreno). */
	public int groundY() {
		return oy + plan.ground();
	}

	/** Margen sobre el radio del ruedo: un jugador pegado al muro tiene el centro del cuerpo algo más allá del radio. */
	public static final double RING_MARGIN = 1.5;

	/**
	 * ¿Punto (pies de una entidad) dentro del ruedo? Dentro de su radio (con {@link #RING_MARGIN}: el muro y el cristal
	 * ya impiden pasar) y entre sus alturas (con medio bloque de margen).
	 */
	public boolean inRing(double x, double y, double z) {
		double dx = x - centerX(), dz = z - centerZ();
		double r = plan.radius() + RING_MARGIN;
		return dx * dx + dz * dz < r * r && y >= oy + plan.ringY()[0] - 0.5 && y <= oy + plan.ringY()[1] + 1;
	}

	/** Posición del mundo de un punto relativo del plano. */
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

	/** ¿Es este bloque la campana? */
	public boolean isBell(int x, int y, int z) {
		int[] c = bell();
		return c[0] == x && c[1] == y && c[2] == z;
	}

	/**
	 * Protección de un bloque: protegido si está en la caja y quien actúa no es operador. Las explosiones, los pistones
	 * y los endermen no son operadores ({@code operator} = false).
	 */
	public boolean isProtected(int x, int y, int z, boolean operator) {
		return !operator && mentions(x, y, z);
	}
}
