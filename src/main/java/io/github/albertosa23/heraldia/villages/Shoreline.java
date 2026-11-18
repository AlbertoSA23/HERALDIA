package io.github.albertosa23.heraldia.villages;

import java.util.ArrayList;
import java.util.List;
import java.util.function.Function;
import java.util.function.Predicate;
import net.minecraft.core.Direction;

/**
 * Elección de la orilla del puerto de una aldea de la costa (lógica pura: el fondo y los obstáculos llegan como
 * funciones, así que se prueba con mapas de alturas sintéticos).
 *
 * <p>Se mira el fondo en una malla de {@link #STEP} bloques dentro de un círculo de radio {@code reach} alrededor de la
 * plaza, de dentro afuera. Cada nudo de tierra baja (de 0 a {@link #SHALLOW} bloques sobre el mar) con un vecino de agua da
 * una orilla candidata hacia ese vecino, afinada entre los dos con una búsqueda binaria. Así salen todas las orillas a lo
 * largo de la costa y no solo las de cuatro rayos (que seguían las avenidas y caían junto a la plaza o sobre una calle).
 * Las piezas de la aldea no cuestan terreno, así que se miran antes: las direcciones de un nudo en las que el puerto
 * chocaría en cualquier punto entre el nudo y su vecino se descartan sin consultar el fondo, y en cada candidata se
 * comprueban los obstáculos antes que el agua: fondo bajo la punta, a la mitad, más allá y a los lados (mar abierto, no una ensenada). Gana la
 * más cercana libre; si no hay ninguna libre, la más cercana que solo desplaza casas. El fondo de cada columna se pide
 * una vez como mucho (la caché va en la función) y solo hasta encontrar una orilla libre.
 */
final class Shoreline {
	/** Paso de la malla. */
	static final int STEP = 16;
	/** Altura máxima sobre el mar de la tierra de la orilla (una playa; un risco junto al agua no sirve). */
	static final int SHALLOW = 4;
	/** Mar más allá de la punta y a cada lado de ella (los botes del muelle). */
	static final int BEYOND = 6, SIDE = 7;

	private Shoreline() {
	}

	/** Altura del fondo ({@code OCEAN_FLOOR_WG}) de una columna. */
	@FunctionalInterface
	interface Seabed {
		int en(int x, int z);
	}

	/** Orilla candidata: último punto de tierra baja antes del agua, con la dirección hacia el mar. */
	record Shore(int x, int z, int y, Direction sea) {
	}

	/**
	 * Orilla elegida (null si no hay) con lo que desplaza, y cuentas para el registro: orillas candidatas, sin fondo,
	 * bloqueadas, direcciones de nudo descartadas por las piezas antes de mirar el terreno, y llamadas al fondo.
	 */
	record Choice<R>(Shore shore, R gone, int candidates, int noSeabed, int blocked, int discarded, int queries) {
	}

	/** Distancias desde el nudo a las que se estima la orilla para descartar direcciones solo con las piezas. */
	private static final int[] ESTIMATE = {2, 8, 14};
	/** Desplazamientos a lo largo de la costa de la línea de un nudo cuando las piezas la tapan. */
	private static final int[] LATERAL = {0, 8, -8};

	/**
	 * Busca la orilla. {@code obstacle} da, para una orilla, lo que habría que quitar de la aldea para poner allí el
	 * puerto o null si choca con algo que no se quita; {@code free} dice si eso no quita nada. Antes de mirar el fondo de
	 * un nudo se prueba cada dirección con la orilla estimada a 2, 8 y 14 bloques (altura del mar + 1): si choca en las
	 * tres, se prueba la línea paralela 8 bloques a cada lado (a lo largo de la costa) y, si también, esa dirección no se
	 * mira (las piezas no cuestan terreno; el centro de la aldea no gasta consultas). Una línea de al lado solo se consulta
	 * donde la malla ya ve costa (nudo de tierra baja y vecino de agua).
	 */
	static <R> Choice<R> choose(Seabed depth, int sea, int cx, int cz, int reach, int length, Function<Shore, R> obstacle,
								  Predicate<R> free) {
		int[] queries = {0};
		Seabed h = (x, z) -> {
			queries[0]++;
			return depth.en(x, z);
		};
		int k = reach / STEP, noSeabed = 0, blocked = 0, candidates = 0, discarded = 0;
		List<Shore> displace = new ArrayList<>();
		List<R> remove = new ArrayList<>();
		int[] off = new int[4];
		for (int[] n : knots(k)) {
			int gx = cx + n[0] * STEP, gz = cz + n[1] * STEP;
			// la línea del nudo hacia cada dirección o, si las piezas la tapan, la de al lado (8 bloques a lo largo de la costa)
			boolean some = false;
			for (Direction d : Direction.Plane.HORIZONTAL) {
				off[d.get2DDataValue()] = line(obstacle, gx, gz, sea, d);
				if (off[d.get2DDataValue()] == NONE) {
					discarded++;
				} else {
					some = true;
				}
			}
			if (!some) {
				continue;
			}
			int fg = h.en(gx, gz);
			if (fg < sea || fg - sea > SHALLOW) {
				continue;
			}
			for (Direction d : Direction.Plane.HORIZONTAL) {
				int o = off[d.get2DDataValue()];
				// la malla debe ver costa en esta dirección (nudo de tierra baja, vecino de agua) antes de afinar
				if (o == NONE || h.en(gx + d.getStepX() * STEP, gz + d.getStepZ() * STEP) >= sea) {
					continue;
				}
				Direction side = d.getClockWise();
				int x = gx + side.getStepX() * o, z = gz + side.getStepZ() * o, f = o == 0 ? fg : h.en(x, z);
				if (f < sea || f - sea > SHALLOW || (o != 0 && h.en(x + d.getStepX() * STEP, z + d.getStepZ() * STEP) >= sea)) {
					continue;
				}
				Shore s = refine(h, sea, x, z, f, d);
				if (s == null) {
					continue;
				}
				candidates++;
				R gone = obstacle.apply(s);
				if (gone == null) {
					blocked++;
				} else if (!free.test(gone)) {
					displace.add(s);
					remove.add(gone);
				} else if (seaSide(h, sea, s, length)) {
					return new Choice<>(s, gone, candidates, noSeabed, blocked, discarded, queries[0]);
				} else {
					noSeabed++;
				}
			}
		}
		for (int i = 0; i < displace.size(); i++) {
			if (seaSide(h, sea, displace.get(i), length)) {
				return new Choice<>(displace.get(i), remove.get(i), candidates, noSeabed, blocked, discarded, queries[0]);
			}
			noSeabed++;
		}
		return new Choice<>(null, null, candidates, noSeabed, blocked, discarded, queries[0]);
	}

	/** Ninguna línea posible (en {@link #line}). */
	static final int NONE = Integer.MIN_VALUE;

	/** Desplazamiento lateral de la primera línea del nudo hacia d en la que las piezas dejan poner el puerto, o NINGUNA. */
	static <R> int line(Function<Shore, R> obstacle, int x, int z, int sea, Direction d) {
		Direction side = d.getClockWise();
		for (int o : LATERAL) {
			if (possible(obstacle, x + side.getStepX() * o, z + side.getStepZ() * o, sea, d)) {
				return o;
			}
		}
		return NONE;
	}

	/** ¿Alguna orilla estimada entre el nudo y su vecino en la dirección d deja poner el puerto? (sin mirar el terreno) */
	static <R> boolean possible(Function<Shore, R> obstacle, int x, int z, int sea, Direction d) {
		for (int lo : ESTIMATE) {
			if (obstacle.apply(new Shore(x + d.getStepX() * lo, z + d.getStepZ() * lo, sea + 1, d)) != null) {
				return true;
			}
		}
		return false;
	}

	/** Nudos (i, j) de la malla dentro del círculo de radio k, de dentro afuera (mismo orden siempre). */
	static List<int[]> knots(int k) {
		List<int[]> out = new ArrayList<>();
		for (int r2 = 0; r2 <= k * k; r2++) {
			for (int i = -k; i <= k; i++) {
				for (int j = -k; j <= k; j++) {
					if (i * i + j * j == r2) {
						out.add(new int[]{i, j});
					}
				}
			}
		}
		return out;
	}

	/**
	 * Entre el nudo de tierra (x, z, con fondo f) y su vecino de agua en la dirección d: el último punto de tierra con
	 * paso 2 (búsqueda binaria, 3 columnas). Null si ese punto ya no es tierra baja.
	 */
	static Shore refine(Seabed h, int sea, int x, int z, int f, Direction d) {
		int lo = 0, hi = STEP, flo = f;
		while (hi - lo > 2) {
			int mid = (lo + hi) / 2, fm = h.en(x + d.getStepX() * mid, z + d.getStepZ() * mid);
			if (fm >= sea) {
				lo = mid;
				flo = fm;
			} else {
				hi = mid;
			}
		}
		return flo - sea > SHALLOW ? null : new Shore(x + d.getStepX() * lo, z + d.getStepZ() * lo, flo, d);
	}

	/**
	 * Agua para el muelle desde la orilla: fondo de 2 bajo la punta, agua a la mitad, más allá de la punta y a los lados
	 * (mar abierto, no una ensenada que acabe en tierra). De lo más probable a lo menos, para cortar pronto.
	 */
	static boolean seaSide(Seabed h, int sea, Shore s, int length) {
		Direction d = s.sea(), side = d.getClockWise();
		int tx = s.x() + d.getStepX() * length, tz = s.z() + d.getStepZ() * length;
		return h.en(tx, tz) <= sea - 2
				&& h.en(s.x() + d.getStepX() * (length / 2), s.z() + d.getStepZ() * (length / 2)) < sea
				&& h.en(tx + d.getStepX() * BEYOND, tz + d.getStepZ() * BEYOND) < sea
				&& h.en(tx + side.getStepX() * SIDE, tz + side.getStepZ() * SIDE) < sea
				&& h.en(tx - side.getStepX() * SIDE, tz - side.getStepZ() * SIDE) < sea;
	}
}
