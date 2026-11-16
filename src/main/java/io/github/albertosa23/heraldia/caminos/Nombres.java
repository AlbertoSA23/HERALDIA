package io.github.albertosa23.heraldia.caminos;

/**
 * Nombre propio de una aldea de Heraldia, sacado de la semilla y de la posición de su plaza (sin datos guardados): el
 * mismo en cada cartel que la señala. Dos partes, «Torre» + «del Roble», que caben cada una en una línea de cartel y
 * concuerdan entre sí en cualquier combinación (cada segunda parte lleva su propio artículo). Es un topónimo: igual en
 * todos los idiomas, como en los mapas.
 */
public final class Nombres {
	static final String[] PRIMERA = {"Torre", "Fuente", "Puente", "Villa", "Casar", "Molino", "Val", "Castro",
			"Puebla", "Vado", "Prado", "Cerro", "Soto", "Peña", "Cañada", "Robledo"};
	static final String[] SEGUNDA = {"del Roble", "de la Encina", "del Lobo", "de los Olmos", "del Río", "de la Sierra",
			"del Cierzo", "de las Hayas", "del Alba", "de la Vega", "del Halcón", "de los Pinos", "de la Laguna",
			"del Cuervo", "de las Moras", "del Brezo"};

	private Nombres() {
	}

	/** Las dos líneas del nombre de la aldea con la plaza en (x, z) bloques. */
	public static String[] de(long seed, int x, int z) {
		long h = Trazado.mix(seed ^ Trazado.mix(Trazado.pack(x, z) * 0x9E3779B97F4A7C15L + 0x5EED));
		return new String[]{PRIMERA[(int) Math.floorMod(h, (long) PRIMERA.length)], SEGUNDA[(int) Math.floorMod(h >>> 20, (long) SEGUNDA.length)]};
	}
}
