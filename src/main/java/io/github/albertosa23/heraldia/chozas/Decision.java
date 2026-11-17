package io.github.albertosa23.heraldia.chozas;

import java.util.Set;

/**
 * Lógica pura de las chozas de mago (T43, sin clases del juego, para los tests). Todo sale de la semilla del mundo y
 * del chunk del mago (es una entidad quieta, sin IA, que la plantilla pone en el centro de su choza: el chunk no cambia),
 * así que la misma choza da siempre lo mismo y no hace falta guardar nada aparte. Lo que ya se ha decidido se guarda
 * además en las etiquetas (Tags) del propio mago, para que un cambio de configuración no cambie una choza ya vista.
 */
public final class Decision {
	/** Etiqueta del mago de las plantillas (medianas/choza_mago.TAG_MAGO). */
	public static final String TAG = "heraldia_mago";
	/** Decisión ya tomada (en el mago): bondadoso o malvado. */
	public static final String BENIGNO = TAG + ".benigno", MALVADO_SIN_REVELAR = TAG + ".malvado";
	/** El mago ya tiene su nombre generado. */
	public static final String NOMBRADO = TAG + ".nombrado";
	/** El mago ya se ha revelado (se le pone justo antes de quitarlo: nunca se revela dos veces). */
	public static final String REVELADO = TAG + ".revelado";
	/** Etiqueta del evocador en que se convierte (medianas/choza_mago.TAG_MALVADO; la mira el logro). */
	public static final String MALVADO = "heraldia_mago_malvado";
	/** Su botín lleva el premio (en el evocador). */
	public static final String PREMIUM = MALVADO + ".premium";
	/** Los vexes que invoca al revelarse. */
	public static final String VEX = "heraldia_mago_vex";
	private static final long SAL_MALVADO = 0x6D61676F5F6D616CL, SAL_PREMIUM = 0x7072656D69756D21L, SAL_NOMBRE = 0x6E6F6D6272653F21L;

	/** Estado de un mago según sus etiquetas. */
	public enum Estado {
		SIN_DECIDIR, BENIGNO, MALVADO, REVELADO
	}

	private Decision() {
	}

	/** ¿Es un mago de choza? (salida temprana: casi ninguna entidad lleva etiquetas). */
	public static boolean esMago(Set<String> tags) {
		return !tags.isEmpty() && tags.contains(TAG);
	}

	public static Estado estado(Set<String> tags) {
		if (tags.contains(REVELADO)) {
			return Estado.REVELADO;
		}
		if (tags.contains(MALVADO_SIN_REVELAR)) {
			return Estado.MALVADO;
		}
		return tags.contains(BENIGNO) ? Estado.BENIGNO : Estado.SIN_DECIDIR;
	}

	/** Número de 0 a 99 de una choza (semilla, chunk del mago y sal). */
	static int tirada(long seed, int chunkX, int chunkZ, long sal) {
		long h = mezclar(seed ^ sal);
		h = mezclar(h ^ ((long) chunkX * 0x9E3779B97F4A7C15L));
		h = mezclar(h ^ ((long) chunkZ * 0xC2B2AE3D27D4EB4FL));
		return (int) Long.remainderUnsigned(h, 100);
	}

	/** SplitMix64: mezcla barata y bien repartida. */
	static long mezclar(long z) {
		z = (z ^ (z >>> 30)) * 0xBF58476D1CE4E5B9L;
		z = (z ^ (z >>> 27)) * 0x94D049BB133111EBL;
		return z ^ (z >>> 31);
	}

	/** ¿Es malvado el mago de esta choza? {@code prob} en % (0: nunca; 100: siempre). */
	public static boolean malvado(long seed, int chunkX, int chunkZ, int prob) {
		return tirada(seed, chunkX, chunkZ, SAL_MALVADO) < Math.clamp(prob, 0, 100);
	}

	/** ¿Lleva el premio el botín del Mago Malvado de esta choza? {@code prob} en %. */
	public static boolean premium(long seed, int chunkX, int chunkZ, int prob) {
		return tirada(seed, chunkX, chunkZ, SAL_PREMIUM) < Math.clamp(prob, 0, 100);
	}

	/** Índices (nombre, apodo) del mago de esta choza, de {@code nombres} y {@code apodos} posibles. */
	public static int[] nombre(long seed, int chunkX, int chunkZ, int nombres, int apodos) {
		long h = mezclar(mezclar(seed ^ SAL_NOMBRE) ^ ((long) chunkX << 32 | (chunkZ & 0xFFFFFFFFL)));
		return new int[] {(int) Long.remainderUnsigned(h, Math.max(1, nombres)),
				(int) Long.remainderUnsigned(h >>> 17, Math.max(1, apodos))};
	}
}
