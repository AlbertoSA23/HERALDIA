package io.github.albertosa23.heraldia.aldeas;

import java.util.ArrayList;
import java.util.List;
import java.util.function.Function;
import java.util.function.Predicate;
import net.minecraft.core.Direction;

/**
 * Elección de la orilla del puerto de una aldea de la costa (lógica pura: el fondo y los obstáculos llegan como
 * funciones, así que se prueba con mapas de alturas sintéticos).
 *
 * <p>Se mira el fondo en una malla de {@link #PASO} bloques dentro de un círculo de radio {@code alcance} alrededor de la
 * plaza, de dentro afuera. Cada nudo de tierra baja (de 0 a {@link #BAJA} bloques sobre el mar) con un vecino de agua da
 * una orilla candidata hacia ese vecino, afinada entre los dos con una búsqueda binaria. Así salen todas las orillas a lo
 * largo de la costa y no solo las de cuatro rayos (que seguían las avenidas y caían junto a la plaza o sobre una calle).
 * Las piezas de la aldea no cuestan terreno, así que se miran antes: las direcciones de un nudo en las que el puerto
 * chocaría en cualquier punto entre el nudo y su vecino se descartan sin consultar el fondo, y en cada candidata se
 * comprueban los obstáculos antes que el agua: fondo bajo la punta, a la mitad, más allá y a los lados (mar abierto, no una ensenada). Gana la
 * más cercana libre; si no hay ninguna libre, la más cercana que solo desplaza casas. El fondo de cada columna se pide
 * una vez como mucho (la caché va en la función) y solo hasta encontrar una orilla libre.
 */
final class Orilla {
	/** Paso de la malla. */
	static final int PASO = 16;
	/** Altura máxima sobre el mar de la tierra de la orilla (una playa; un risco junto al agua no sirve). */
	static final int BAJA = 4;
	/** Mar más allá de la punta y a cada lado de ella (los botes del muelle). */
	static final int MAS_ALLA = 6, LADO = 7;

	private Orilla() {
	}

	/** Altura del fondo ({@code OCEAN_FLOOR_WG}) de una columna. */
	@FunctionalInterface
	interface Fondo {
		int en(int x, int z);
	}

	/** Orilla candidata: último punto de tierra baja antes del agua, con la dirección hacia el mar. */
	record Shore(int x, int z, int y, Direction sea) {
	}

	/**
	 * Orilla elegida (null si no hay) con lo que desplaza, y cuentas para el registro: orillas candidatas, sin fondo,
	 * bloqueadas, direcciones de nudo descartadas por las piezas antes de mirar el terreno, y llamadas al fondo.
	 */
	record Eleccion<R>(Shore shore, R gone, int candidatas, int sinFondo, int bloqueadas, int descartadas, int consultas) {
	}

	/** Distancias desde el nudo a las que se estima la orilla para descartar direcciones solo con las piezas. */
	private static final int[] ESTIMA = {2, 8, 14};
	/** Desplazamientos a lo largo de la costa de la línea de un nudo cuando las piezas la tapan. */
	private static final int[] LATERAL = {0, 8, -8};

	/**
	 * Busca la orilla. {@code obstaculo} da, para una orilla, lo que habría que quitar de la aldea para poner allí el
	 * puerto o null si choca con algo que no se quita; {@code libre} dice si eso no quita nada. Antes de mirar el fondo de
	 * un nudo se prueba cada dirección con la orilla estimada a 2, 8 y 14 bloques (altura del mar + 1): si choca en las
	 * tres, se prueba la línea paralela 8 bloques a cada lado (a lo largo de la costa) y, si también, esa dirección no se
	 * mira (las piezas no cuestan terreno; el centro de la aldea no gasta consultas). Una línea de al lado solo se consulta
	 * donde la malla ya ve costa (nudo de tierra baja y vecino de agua).
	 */
	static <R> Eleccion<R> elegir(Fondo fondo, int sea, int cx, int cz, int alcance, int largo, Function<Shore, R> obstaculo,
								  Predicate<R> libre) {
		int[] consultas = {0};
		Fondo h = (x, z) -> {
			consultas[0]++;
			return fondo.en(x, z);
		};
		int k = alcance / PASO, sinFondo = 0, bloqueadas = 0, candidatas = 0, descartadas = 0;
		List<Shore> desplazan = new ArrayList<>();
		List<R> quitan = new ArrayList<>();
		int[] off = new int[4];
		for (int[] n : nudos(k)) {
			int gx = cx + n[0] * PASO, gz = cz + n[1] * PASO;
			// la línea del nudo hacia cada dirección o, si las piezas la tapan, la de al lado (8 bloques a lo largo de la costa)
			boolean alguna = false;
			for (Direction d : Direction.Plane.HORIZONTAL) {
				off[d.get2DDataValue()] = linea(obstaculo, gx, gz, sea, d);
				if (off[d.get2DDataValue()] == NINGUNA) {
					descartadas++;
				} else {
					alguna = true;
				}
			}
			if (!alguna) {
				continue;
			}
			int fg = h.en(gx, gz);
			if (fg < sea || fg - sea > BAJA) {
				continue;
			}
			for (Direction d : Direction.Plane.HORIZONTAL) {
				int o = off[d.get2DDataValue()];
				// la malla debe ver costa en esta dirección (nudo de tierra baja, vecino de agua) antes de afinar
				if (o == NINGUNA || h.en(gx + d.getStepX() * PASO, gz + d.getStepZ() * PASO) >= sea) {
					continue;
				}
				Direction side = d.getClockWise();
				int x = gx + side.getStepX() * o, z = gz + side.getStepZ() * o, f = o == 0 ? fg : h.en(x, z);
				if (f < sea || f - sea > BAJA || (o != 0 && h.en(x + d.getStepX() * PASO, z + d.getStepZ() * PASO) >= sea)) {
					continue;
				}
				Shore s = afinar(h, sea, x, z, f, d);
				if (s == null) {
					continue;
				}
				candidatas++;
				R gone = obstaculo.apply(s);
				if (gone == null) {
					bloqueadas++;
				} else if (!libre.test(gone)) {
					desplazan.add(s);
					quitan.add(gone);
				} else if (mar(h, sea, s, largo)) {
					return new Eleccion<>(s, gone, candidatas, sinFondo, bloqueadas, descartadas, consultas[0]);
				} else {
					sinFondo++;
				}
			}
		}
		for (int i = 0; i < desplazan.size(); i++) {
			if (mar(h, sea, desplazan.get(i), largo)) {
				return new Eleccion<>(desplazan.get(i), quitan.get(i), candidatas, sinFondo, bloqueadas, descartadas, consultas[0]);
			}
			sinFondo++;
		}
		return new Eleccion<>(null, null, candidatas, sinFondo, bloqueadas, descartadas, consultas[0]);
	}

	/** Ninguna línea posible (en {@link #linea}). */
	static final int NINGUNA = Integer.MIN_VALUE;

	/** Desplazamiento lateral de la primera línea del nudo hacia d en la que las piezas dejan poner el puerto, o NINGUNA. */
	static <R> int linea(Function<Shore, R> obstaculo, int x, int z, int sea, Direction d) {
		Direction side = d.getClockWise();
		for (int o : LATERAL) {
			if (posible(obstaculo, x + side.getStepX() * o, z + side.getStepZ() * o, sea, d)) {
				return o;
			}
		}
		return NINGUNA;
	}

	/** ¿Alguna orilla estimada entre el nudo y su vecino en la dirección d deja poner el puerto? (sin mirar el terreno) */
	static <R> boolean posible(Function<Shore, R> obstaculo, int x, int z, int sea, Direction d) {
		for (int lo : ESTIMA) {
			if (obstaculo.apply(new Shore(x + d.getStepX() * lo, z + d.getStepZ() * lo, sea + 1, d)) != null) {
				return true;
			}
		}
		return false;
	}

	/** Nudos (i, j) de la malla dentro del círculo de radio k, de dentro afuera (mismo orden siempre). */
	static List<int[]> nudos(int k) {
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
	static Shore afinar(Fondo h, int sea, int x, int z, int f, Direction d) {
		int lo = 0, hi = PASO, flo = f;
		while (hi - lo > 2) {
			int mid = (lo + hi) / 2, fm = h.en(x + d.getStepX() * mid, z + d.getStepZ() * mid);
			if (fm >= sea) {
				lo = mid;
				flo = fm;
			} else {
				hi = mid;
			}
		}
		return flo - sea > BAJA ? null : new Shore(x + d.getStepX() * lo, z + d.getStepZ() * lo, flo, d);
	}

	/**
	 * Agua para el muelle desde la orilla: fondo de 2 bajo la punta, agua a la mitad, más allá de la punta y a los lados
	 * (mar abierto, no una ensenada que acabe en tierra). De lo más probable a lo menos, para cortar pronto.
	 */
	static boolean mar(Fondo h, int sea, Shore s, int largo) {
		Direction d = s.sea(), side = d.getClockWise();
		int tx = s.x() + d.getStepX() * largo, tz = s.z() + d.getStepZ() * largo;
		return h.en(tx, tz) <= sea - 2
				&& h.en(s.x() + d.getStepX() * (largo / 2), s.z() + d.getStepZ() * (largo / 2)) < sea
				&& h.en(tx + d.getStepX() * MAS_ALLA, tz + d.getStepZ() * MAS_ALLA) < sea
				&& h.en(tx + side.getStepX() * LADO, tz + side.getStepZ() * LADO) < sea
				&& h.en(tx - side.getStepX() * LADO, tz - side.getStepZ() * LADO) < sea;
	}
}
