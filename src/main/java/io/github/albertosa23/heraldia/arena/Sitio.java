package io.github.albertosa23.heraldia.arena;

import java.util.Arrays;
import java.util.Optional;

/**
 * Elección del sitio de la arena, sin clases del juego (lo prueban los tests con un terreno inventado): candidatos en
 * anillos de {@link #RADIO_MIN} a {@link #RADIO_MAX} bloques del spawn, cada {@link #PASO_GRADOS}°, y en cada uno una
 * malla de {@link #MUESTRAS}² alturas sobre la huella de la arena y un margen. Vale el que no tiene agua y menos desnivel
 * (como mucho {@link #DESNIVEL_MAX}) y ninguna estructura ya generada en sus chunks; a igualdad, el más cercano a {@link #RADIO_PREFERIDO} y luego el primero en orden.
 * Las alturas salen del generador del mundo ({@code ChunkGenerator.getBaseHeight}: solo ruido, sin cargar chunks), así
 * que la búsqueda puede ir fuera del hilo del servidor.
 */
public final class Sitio {
	public static final int RADIO_MIN = 200, RADIO_MAX = 300, RADIO_PASO = 25, RADIO_PREFERIDO = 250, PASO_GRADOS = 15;
	public static final int MUESTRAS = 5, MARGEN = 4, DESNIVEL_MAX = 12;

	private Sitio() {
	}

	/** Alturas del terreno natural en una columna. */
	public interface Alturas {
		/** Primer bloque libre sobre la superficie (agua incluida). */
		int superficie(int x, int z);

		/** Primer bloque libre o con agua sobre el suelo sólido. */
		int fondo(int x, int z);

		/** ¿Hay ya en ese chunk alguna pieza de una estructura de superficie (aldea, entrada de mina...)? */
		default boolean ocupado(int chunkX, int chunkZ) {
			return false;
		}
	}

	/**
	 * Un sitio: columna del centro, y del bloque de suelo (la mediana de las alturas: lo que se nivela), desnivel y
	 * distancia al spawn.
	 */
	public record Eleccion(int x, int z, int suelo, int desnivel, int distancia) {
	}

	/**
	 * El mejor sitio para una arena de {@code lado} bloques alrededor del spawn, o vacío si no hay ninguno llano y sin agua.
	 * {@code minY} y {@code maxY}: alturas del mundo; la arena (de {@code bajo} bloques bajo el suelo a {@code alto} por
	 * encima) tiene que caber.
	 */
	public static Optional<Eleccion> elegir(int spawnX, int spawnZ, int lado, int bajo, int alto, int minY, int maxY, Alturas a) {
		Eleccion mejor = null;
		for (int r = RADIO_MIN; r <= RADIO_MAX; r += RADIO_PASO) {
			for (int g = 0; g < 360; g += PASO_GRADOS) {
				double rad = Math.toRadians(g);
				int cx = spawnX + (int) Math.round(r * Math.cos(rad));
				int cz = spawnZ + (int) Math.round(r * Math.sin(rad));
				Eleccion e = evaluar(cx, cz, spawnX, spawnZ, lado, a);
				if (e == null || e.suelo() - bajo <= minY || e.suelo() + alto >= maxY) {
					continue;
				}
				if ((mejor == null || mejor(e, mejor)) && libre(e, lado, a)) {
					mejor = e;
				}
			}
		}
		return Optional.ofNullable(mejor);
	}

	/** El sitio con centro en (cx, cz), o null si hay agua o demasiado desnivel. */
	static Eleccion evaluar(int cx, int cz, int spawnX, int spawnZ, int lado, Alturas a) {
		int ancho = lado + 2 * MARGEN;
		int[] alturas = new int[MUESTRAS * MUESTRAS];
		int i = 0;
		for (int u = 0; u < MUESTRAS; u++) {
			for (int v = 0; v < MUESTRAS; v++) {
				int x = cx - ancho / 2 + u * (ancho - 1) / (MUESTRAS - 1);
				int z = cz - ancho / 2 + v * (ancho - 1) / (MUESTRAS - 1);
				int s = a.superficie(x, z);
				if (s > a.fondo(x, z)) {
					return null;                // agua
				}
				alturas[i++] = s - 1;
			}
		}
		Arrays.sort(alturas);
		int desnivel = alturas[alturas.length - 1] - alturas[0];
		if (desnivel > DESNIVEL_MAX) {
			return null;
		}
		int dist = (int) Math.round(Math.hypot(cx - spawnX, cz - spawnZ));
		return new Eleccion(cx, cz, alturas[alturas.length / 2], desnivel, dist);
	}

	/** ¿Ningún chunk de la huella y su margen tiene ya una estructura? (solo se mira si el sitio mejora al elegido) */
	static boolean libre(Eleccion e, int lado, Alturas a) {
		int m = lado / 2 + MARGEN;
		for (int cx = (e.x() - m) >> 4; cx <= (e.x() + m) >> 4; cx++) {
			for (int cz = (e.z() - m) >> 4; cz <= (e.z() + m) >> 4; cz++) {
				if (a.ocupado(cx, cz)) {
					return false;
				}
			}
		}
		return true;
	}

	/** ¿{@code a} es mejor que {@code b}? Menos desnivel; a igualdad, más cerca de {@link #RADIO_PREFERIDO}. */
	static boolean mejor(Eleccion a, Eleccion b) {
		if (a.desnivel() != b.desnivel()) {
			return a.desnivel() < b.desnivel();
		}
		return Math.abs(a.distancia() - RADIO_PREFERIDO) < Math.abs(b.distancia() - RADIO_PREFERIDO);
	}
}
