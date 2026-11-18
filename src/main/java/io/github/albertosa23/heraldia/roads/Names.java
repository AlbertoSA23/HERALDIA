package io.github.albertosa23.heraldia.roads;

/**
 * Proper name of a Heraldia village, taken from the seed and the position of its plaza (no saved data): the
 * same on every sign that points to it. Two parts, "Torre" + "del Roble", each fitting on a sign line and
 * agreeing with each other in any combination (each second part carries its own article). It is a place name: the same in
 * all languages, as on maps.
 */
public final class Names {
	static final String[] FIRST = {"Torre", "Fuente", "Puente", "Villa", "Casar", "Molino", "Val", "Castro",
			"Puebla", "Vado", "Prado", "Cerro", "Soto", "Peña", "Cañada", "Robledo"};
	static final String[] SECOND = {"del Roble", "de la Encina", "del Lobo", "de los Olmos", "del Río", "de la Sierra",
			"del Cierzo", "de las Hayas", "del Alba", "de la Vega", "del Halcón", "de los Pinos", "de la Laguna",
			"del Cuervo", "de las Moras", "del Brezo"};

	private Names() {
	}

	/** The two lines of the name of the village with its plaza at (x, z) blocks. */
	public static String[] of(long seed, int x, int z) {
		long h = RoadLayout.mix(seed ^ RoadLayout.mix(RoadLayout.pack(x, z) * 0x9E3779B97F4A7C15L + 0x5EED));
		return new String[]{FIRST[(int) Math.floorMod(h, (long) FIRST.length)], SECOND[(int) Math.floorMod(h >>> 20, (long) SECOND.length)]};
	}
}
