package io.github.albertosa23.heraldia.arena;

/**
 * La arena colocada en el mundo: su origen (esquina mínima de la plantilla) y su plano. Da la caja protegida (una AABB
 * de enteros en memoria: la comprobación de cada bloque son seis comparaciones), si un punto está en el ruedo y las
 * posiciones del mundo de la campana, la puerta, los puntos de aparición y la reaparición. Sin clases del juego.
 */
public record Zona(int ox, int oy, int oz, Plano plano) {
	/** Bloques alrededor de la caja donde no se vacían cubos (jugadores que no son operadores y dispensadores). */
	public static final int RADIO_CUBOS = 6;

	/** Origen de la plantilla para que su centro caiga en la columna (cx, cz) y su suelo en la altura {@code suelo}. */
	public static Zona centrada(int cx, int cz, int suelo, Plano plano) {
		return new Zona(cx - plano.centro()[0], suelo - plano.suelo(), cz - plano.centro()[2], plano);
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
		return ox + plano.tamano()[0] - 1;
	}

	public int maxY() {
		return oy + plano.tamano()[1] - 1;
	}

	public int maxZ() {
		return oz + plano.tamano()[2] - 1;
	}

	/** ¿Bloque dentro de la caja protegida (toda la plantilla)? */
	public boolean contiene(int x, int y, int z) {
		return x >= ox && y >= oy && z >= oz && x <= maxX() && y <= maxY() && z <= maxZ();
	}

	/** ¿Bloque dentro de la caja ampliada {@code m} bloques por cada lado? */
	public boolean cerca(int x, int y, int z, int m) {
		return x >= ox - m && y >= oy - m && z >= oz - m && x <= maxX() + m && y <= maxY() + m && z <= maxZ() + m;
	}

	/**
	 * ¿Se niega vaciar un cubo en este bloque? A menos de {@link #RADIO_CUBOS} de la caja, salvo a un operador (un
	 * dispensador nunca lo es): así un dispensador pegado a la arena no la inunda ni le echa lava.
	 */
	public boolean cuboNegado(int x, int y, int z, boolean operador) {
		return !operador && cerca(x, y, z, RADIO_CUBOS);
	}

	/** Centro del ruedo (x, z del centro de su columna). */
	public double centroX() {
		return ox + plano.centro()[0] + 0.5;
	}

	public double centroZ() {
		return oz + plano.centro()[2] + 0.5;
	}

	/** Columna del centro (bloque). */
	public int columnaX() {
		return ox + plano.centro()[0];
	}

	public int columnaZ() {
		return oz + plano.centro()[2];
	}

	/** y del suelo exterior (la capa de la plantilla a ras del terreno). */
	public int sueloY() {
		return oy + plano.suelo();
	}

	/** Margen sobre el radio del ruedo: un jugador pegado al muro tiene el centro del cuerpo algo más allá del radio. */
	public static final double MARGEN_RUEDO = 1.5;

	/**
	 * ¿Punto (pies de una entidad) dentro del ruedo? Dentro de su radio (con {@link #MARGEN_RUEDO}: el muro y el cristal
	 * ya impiden pasar) y entre sus alturas (con medio bloque de margen).
	 */
	public boolean enRuedo(double x, double y, double z) {
		double dx = x - centroX(), dz = z - centroZ();
		double r = plano.radio() + MARGEN_RUEDO;
		return dx * dx + dz * dz < r * r && y >= oy + plano.ruedoY()[0] - 0.5 && y <= oy + plano.ruedoY()[1] + 1;
	}

	/** Posición del mundo de un punto relativo del plano. */
	public int[] mundo(int[] rel) {
		return new int[] {ox + rel[0], oy + rel[1], oz + rel[2]};
	}

	public int[] campana() {
		return mundo(plano.campana());
	}

	public int[] reaparicion() {
		return mundo(plano.reaparicion());
	}

	public int[] punto(int i) {
		return mundo(plano.puntos().get(Math.floorMod(i, plano.puntos().size())));
	}

	public int puntos() {
		return plano.puntos().size();
	}

	public int[] puertaMin() {
		return mundo(plano.puerta()[0]);
	}

	public int[] puertaMax() {
		return mundo(plano.puerta()[1]);
	}

	/** ¿Es este bloque la campana? */
	public boolean esCampana(int x, int y, int z) {
		int[] c = campana();
		return c[0] == x && c[1] == y && c[2] == z;
	}

	/**
	 * Protección de un bloque: protegido si está en la caja y quien actúa no es operador. Las explosiones, los pistones
	 * y los endermen no son operadores ({@code operador} = false).
	 */
	public boolean protegido(int x, int y, int z, boolean operador) {
		return !operador && contiene(x, y, z);
	}
}
