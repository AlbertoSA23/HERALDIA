package io.github.albertosa23.heraldia.roads;

/**
 * Nombre propio de una aldea de Heraldia, sacado de la semilla y de la posición de su plaza (sin datos guardados): el
 * mismo en cada cartel que la señala. Dos partes, «Torre» + «del Roble», que caben cada una en una línea de cartel y
 * concuerdan entre sí en cualquier combinación (cada segunda parte lleva su propio artículo). Es un topónimo: igual en
 * todos los idiomas, como en los mapas.
 */
public final class Names {
	static final String[] FIRST = {"Torre", "Fuente", "Puente", "Villa", "Casar", "Molino", "Val", "Castro",
			"Puebla", "Vado", "Prado", "Cerro", "Soto", "Peña", "Cañada", "Robledo"};
	static final String[] SECOND = {"del Roble", "de la Encina", "del Lobo", "de los Olmos", "del Río", "de la Sierra",
			"del Cierzo", "de las Hayas", "del Alba", "de la Vega", "del Halcón", "de los Pinos", "de la Laguna",
			"del Cuervo", "de las Moras", "del Brezo"};

	private Names() {
	}

	/** Las dos líneas del nombre de la aldea con la plaza en (x, z) bloques. */
	public static String[] of(long seed, int x, int z) {
		long h = RoadLayout.mix(seed ^ RoadLayout.mix(RoadLayout.pack(x, z) * 0x9E3779B97F4A7C15L + 0x5EED));
		return new String[]{FIRST[(int) Math.floorMod(h, (long) FIRST.length)], SECOND[(int) Math.floorMod(h >>> 20, (long) SECOND.length)]};
	}
}
