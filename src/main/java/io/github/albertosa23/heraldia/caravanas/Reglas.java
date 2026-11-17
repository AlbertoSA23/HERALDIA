package io.github.albertosa23.heraldia.caravanas;

import java.util.List;
import java.util.Set;
import java.util.UUID;

/**
 * Reglas de las caravanas (lógica pura): cuándo sale una, cómo es (llamas, guardia, asalto, bandidos), qué paga y qué
 * entidades sobran. Los números al azar llegan como argumentos en [0, 1) para que los tests los fijen.
 */
public final class Reglas {
	/** Cada cuántos ticks se sortea una caravana nueva (1 min), y la espera tras acabar una (2 min). */
	public static final int SORTEO_TICKS = 60 * 20, ESPERA_TICKS = 2 * 60 * 20;
	/** Etiquetas (Tags) de todas sus entidades y de cada papel. */
	public static final String TAG = "heraldia_caravana", MERCADER = "heraldia_caravana.mercader", LLAMA = "heraldia_caravana.llama",
			GUARDIA = "heraldia_caravana.guardia", BANDIDO = "heraldia_caravana.bandido";

	private Reglas() {
	}

	/**
	 * ¿Sale una caravana en este sorteo? Con las caravanas activadas, por debajo del límite de activas, pasada la espera
	 * desde la última y con probabilidad {@code frecuencia} % (0: nunca sola, solo con el comando).
	 */
	public static boolean sale(boolean activado, int activas, int maxActivas, long tick, long ultimoFin, int frecuencia, double azar) {
		return activado && activas < maxActivas && frecuencia > 0 && tick - ultimoFin >= ESPERA_TICKS && azar * 100 < frecuencia;
	}

	/** ¿La asaltan? Con probabilidad {@code probAsalto} %. */
	public static boolean asalto(int probAsalto, double azar) {
		return probAsalto > 0 && azar * 100 < probAsalto;
	}

	/** Llamas de carga: de 1 a 3. */
	public static int llamas(double azar) {
		return 1 + Math.min(2, (int) (azar * 3));
	}

	/** ¿Lleva guardia (un gólem de hierro)? Una de cada cuatro. */
	public static boolean guardia(double azar) {
		return azar < 0.25;
	}

	/** Bandidos del asalto: uno más que jugadores cerca, de 2 a 4; con 3 o más, uno es el jefe (vindicador). */
	public static int bandidos(int jugadores) {
		return Math.max(2, Math.min(4, jugadores + 1));
	}

	public static boolean conJefe(int bandidos) {
		return bandidos >= 3;
	}

	/**
	 * Lo que gana cada jugador que la acompaña al llegar: esmeraldas (2 más una por cada 4 vértices; 4 más y un objeto
	 * si superó un asalto), reputación con la aldea de destino (5, o 15 tras un asalto) y, tras un asalto, el logro.
	 */
	public record Recompensa(int esmeraldas, int reputacion, String objeto, int cantidad, boolean logro) {
		public boolean conObjeto() {
			return objeto != null;
		}
	}

	/** Objetos de una caravana defendida: (id, cantidad). Modestos, como el botín de una mediana. */
	public static final List<Object[]> OBJETOS = List.of(new Object[]{"minecraft:name_tag", 1}, new Object[]{"minecraft:spyglass", 1},
			new Object[]{"minecraft:lead", 2}, new Object[]{"minecraft:golden_carrot", 4}, new Object[]{"minecraft:honey_bottle", 3},
			new Object[]{"minecraft:map", 1}, new Object[]{"minecraft:bundle", 1}, new Object[]{"minecraft:saddle", 1});

	public static Recompensa recompensa(int vertices, boolean superada, double azar) {
		int esmeraldas = 2 + vertices / 4 + (superada ? 4 : 0);
		if (!superada) {
			return new Recompensa(esmeraldas, 5, null, 0, false);
		}
		Object[] o = OBJETOS.get(Math.min(OBJETOS.size() - 1, (int) (azar * OBJETOS.size())));
		return new Recompensa(esmeraldas, 15, (String) o[0], (Integer) o[1], true);
	}

	/**
	 * Chunk del inicio de la aldea cuya plaza da el trazado ({@code Trazado.pack(cx * 16 + 8, cz * 16 + 8)}): el que usa la
	 * reputación de los encargos ({@code Encargos.sumarReputacion}) para saber de qué aldea se habla.
	 */
	public static int[] chunk(long aldea) {
		return new int[]{Math.floorDiv(io.github.albertosa23.heraldia.caminos.Trazado.px(aldea), 16),
				Math.floorDiv(io.github.albertosa23.heraldia.caminos.Trazado.pz(aldea), 16)};
	}

	/** ¿Sobra esta entidad? Es de una caravana y no de ninguna activa (de antes de reiniciar, o de una ya terminada). */
	public static boolean huerfana(Set<String> tags, UUID uuid, Set<UUID> activas) {
		return !tags.isEmpty() && tags.contains(TAG) && !activas.contains(uuid);
	}
}
