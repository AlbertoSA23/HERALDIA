package io.github.albertosa23.heraldia.actualizar;

import java.util.ArrayList;
import java.util.Collection;
import java.util.EnumMap;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Detección de construcciones de jugadores y clasificación de los chunks para /heraldia update (T46), lógica pura sobre
 * los resúmenes de los chunks guardados ({@link ResumenChunk}) y unos puntos sueltos. Una construcción es cualquiera de:
 * <ul>
 * <li>un bloque típico de jugador ({@link BloquesJugador}) fuera de las piezas de las estructuras guardadas;</li>
 * <li>columnas cuya cima no coincide con la de la regeneración con la misma semilla (sin contar las cimas naturales: árboles,
 * nieve, fluidos...) en un chunk donde ha estado algún jugador ({@link Parametros#minDiferencias} o más);</li>
 * <li>un chunk muy habitado (InhabitedTime de {@link Parametros#habitadoBase} o más: alguien pasó ahí mucho tiempo);</li>
 * <li>el punto de aparición del mundo, las camas y puntos de reaparición de los jugadores y su última posición;</li>
 * <li>las zonas reclamadas con mods de protección, si se pueden leer.</li>
 * </ul>
 * Alrededor de cada construcción hay un margen ({@link Parametros#margen}, 50 bloques por defecto, en horizontal): un chunk
 * con algún bloque a esa distancia o menos queda <em>protegido</em>, y ahí no se borra ni se coloca nada. Un chunk es
 * <em>virgen</em> si está generado del todo, casi nadie ha pasado por él (InhabitedTime menor que
 * {@link Parametros#habitadoVirgen}), no tiene bloques de jugador fuera de las estructuras y no está protegido (lo de
 * dentro de las estructuras lo vuelve a poner la regeneración), ni él ni ninguno de sus 8 vecinos están protegidos (al
 * regenerarse, sus rasgos del terreno escriben también en los vecinos). Los bloques de jugador que la generación también
 * pone sueltos ({@link BloquesJugador#ambiguo}) solo cuentan en chunks por los que ha pasado alguien.
 */
public final class Detector {
	public enum Motivo { BLOQUES, DIFERENCIA, HABITADO, SPAWN, REAPARICION, JUGADOR, RECLAMO }

	public enum Clase {
		/** Tiene una construcción. */
		CONSTRUCCION,
		/** A menos del margen de una construcción. */
		PROTEGIDO,
		/** Se puede regenerar. */
		VIRGEN,
		/** Generado, ni virgen ni protegido: ahí se pueden colocar estructuras nuevas. */
		NORMAL,
		/** A medio generar: no se toca. */
		INCOMPLETO
	}

	/**
	 * @param margen         bloques alrededor de cada construcción donde no se toca nada (actualizar.margen_bloques)
	 * @param habitadoVirgen InhabitedTime por debajo del cual un chunk puede ser virgen (ticks)
	 * @param habitadoBase   InhabitedTime desde el cual el chunk cuenta como construcción (ticks)
	 * @param minDiferencias columnas distintas de la regeneración para que el chunk cuente como construcción
	 */
	public record Parametros(int margen, long habitadoVirgen, long habitadoBase, int minDiferencias) {
		/** 50 bloques; virgen con menos de 1 min de jugadores cerca; construcción desde 1 h; 3 columnas de 16. */
		public static Parametros porDefecto(int margen) {
			return new Parametros(margen, 1200, 72_000, 3);
		}
	}

	/** Una construcción: el rectángulo (en bloques, inclusive) que ocupa y por qué cuenta. */
	public record Construccion(int minX, int minZ, int maxX, int maxZ, Motivo motivo) {
		public static Construccion punto(int x, int z, Motivo m) {
			return new Construccion(x, z, x, z, m);
		}

		public static Construccion chunk(int cx, int cz, Motivo m) {
			return new Construccion(cx * 16, cz * 16, cx * 16 + 15, cz * 16 + 15, m);
		}
	}

	public record Resultado(Map<Long, Clase> clases, List<Construccion> construcciones, Map<Motivo, Integer> porMotivo,
							Set<Long> protegidos) {
		public Clase clase(int cx, int cz) {
			return clases.get(ResumenChunk.clave(cx, cz));
		}

		public long cuenta(Clase c) {
			return clases.values().stream().filter(c::equals).count();
		}
	}

	private Detector() {
	}

	/** Distancia horizontal (euclídea, en bloques) entre dos rectángulos de bloques; 0 si se tocan o se solapan. */
	public static double distancia(int aMinX, int aMinZ, int aMaxX, int aMaxZ, int bMinX, int bMinZ, int bMaxX, int bMaxZ) {
		int dx = Math.max(0, Math.max(aMinX - bMaxX, bMinX - aMaxX));
		int dz = Math.max(0, Math.max(aMinZ - bMaxZ, bMinZ - aMaxZ));
		return Math.sqrt((double) dx * dx + (double) dz * dz);
	}

	/** ¿Tiene el chunk algún bloque a {@code margen} bloques o menos de la construcción? */
	public static boolean cerca(Construccion c, int cx, int cz, int margen) {
		return distancia(c.minX(), c.minZ(), c.maxX(), c.maxZ(), cx * 16, cz * 16, cx * 16 + 15, cz * 16 + 15) <= margen;
	}

	/** Los chunks a {@code margen} o menos de alguna construcción (los de la construcción incluidos). */
	public static Set<Long> protegidos(Collection<Construccion> cs, int margen) {
		Set<Long> out = new HashSet<>();
		for (Construccion c : cs) {
			int x0 = Math.floorDiv(c.minX() - margen, 16), x1 = Math.floorDiv(c.maxX() + margen, 16);
			int z0 = Math.floorDiv(c.minZ() - margen, 16), z1 = Math.floorDiv(c.maxZ() + margen, 16);
			for (int cx = x0; cx <= x1; cx++) {
				for (int cz = z0; cz <= z1; cz++) {
					if (cerca(c, cx, cz, margen)) {
						out.add(ResumenChunk.clave(cx, cz));
					}
				}
			}
		}
		return out;
	}

	/** ¿Está el bloque dentro de la caja {minX, minY, minZ, maxX, maxY, maxZ}? */
	public static boolean dentro(int[] bb, int x, int y, int z) {
		return x >= bb[0] && y >= bb[1] && z >= bb[2] && x <= bb[3] && y <= bb[4] && z <= bb[5];
	}

	/** ¿Se solapan en planta dos cajas? */
	public static boolean solapan(int[] a, int[] b) {
		return a[0] <= b[3] && b[0] <= a[3] && a[2] <= b[5] && b[2] <= a[5];
	}

	/** Las piezas de las estructuras guardadas, por cada chunk que toca su caja (en planta). */
	public static Map<Long, List<int[]>> piezasPorChunk(Collection<ResumenChunk> chunks) {
		Map<Long, List<int[]>> out = new HashMap<>();
		for (ResumenChunk r : chunks) {
			for (List<int[]> cajas : r.inicios().values()) {
				for (int[] bb : cajas) {
					for (int cx = Math.floorDiv(bb[0], 16); cx <= Math.floorDiv(bb[3], 16); cx++) {
						for (int cz = Math.floorDiv(bb[2], 16); cz <= Math.floorDiv(bb[5], 16); cz++) {
							out.computeIfAbsent(ResumenChunk.clave(cx, cz), k -> new ArrayList<>()).add(bb);
						}
					}
				}
			}
		}
		return out;
	}

	/** Los bloques de jugador de un chunk que no están dentro de ninguna pieza de estructura: {x, z}. */
	static List<int[]> fueraDeEstructuras(ResumenChunk r, List<int[]> piezas) {
		List<int[]> out = new ArrayList<>();
		for (int i = 0; i < r.jugador().length; i++) {
			if (r.ambiguo(i) && r.habitado() <= 0) {
				continue;            // tablones, vallas, raíles y cofres que pone la generación: sin jugadores cerca no cuentan
			}
			int[] b = r.bloqueJugador(i);
			boolean dentro = false;
			for (int[] bb : piezas) {
				if (dentro(bb, b[0], b[1], b[2])) {
					dentro = true;
					break;
				}
			}
			if (!dentro) {
				out.add(new int[] {b[0], b[2]});
			}
		}
		return out;
	}

	/**
	 * Detecta las construcciones y clasifica cada chunk guardado.
	 *
	 * @param diferencias columnas {x, z} distintas de la regeneración, por chunk (solo de los chunks que se compararon)
	 * @param extra       construcciones que no salen de los chunks: spawn, camas y reaparición, jugadores, reclamos
	 */
	public static Resultado clasificar(Collection<ResumenChunk> chunks, Map<Long, List<int[]>> diferencias, List<Construccion> extra,
									   Parametros p) {
		Map<Long, List<int[]>> piezas = piezasPorChunk(chunks);
		List<Construccion> cs = new ArrayList<>(extra);
		Set<Long> conConstruccion = new HashSet<>();
		for (ResumenChunk r : chunks) {
			List<int[]> fuera = fueraDeEstructuras(r, piezas.getOrDefault(r.clave(), List.of()));
			boolean tiene = false;
			for (int[] b : fuera) {
				cs.add(Construccion.punto(b[0], b[1], Motivo.BLOQUES));
				tiene = true;
			}
			List<int[]> dif = diferencias.getOrDefault(r.clave(), List.of());
			if (dif.size() >= p.minDiferencias()) {
				for (int[] d : dif) {
					cs.add(Construccion.punto(d[0], d[1], Motivo.DIFERENCIA));
				}
				tiene = true;
			}
			if (r.habitado() >= p.habitadoBase()) {
				cs.add(Construccion.chunk(r.cx(), r.cz(), Motivo.HABITADO));
				tiene = true;
			}
			if (tiene) {
				conConstruccion.add(r.clave());
			}
		}
		for (Construccion c : extra) {
			conConstruccion.add(ResumenChunk.clave(Math.floorDiv(c.minX(), 16), Math.floorDiv(c.minZ(), 16)));
		}
		Set<Long> protegidos = protegidos(cs, p.margen());
		// al regenerarse, los rasgos de un chunk (vetas, árboles, rocas) escriben también en los 8 de alrededor: un chunk
		// junto a uno protegido no se regenera (visto en tools/smoke/actualizar.py: vetas de andesita en un chunk protegido)
		Set<Long> junto = new HashSet<>();
		for (long k : protegidos) {
			for (int dx = -1; dx <= 1; dx++) {
				for (int dz = -1; dz <= 1; dz++) {
					junto.add(ResumenChunk.clave(ResumenChunk.cx(k) + dx, ResumenChunk.cz(k) + dz));
				}
			}
		}
		Map<Long, Clase> clases = new LinkedHashMap<>();
		for (ResumenChunk r : chunks) {
			long k = r.clave();
			Clase c;
			if (conConstruccion.contains(k)) {
				c = Clase.CONSTRUCCION;
			} else if (protegidos.contains(k)) {
				c = Clase.PROTEGIDO;
			} else if (!r.completo()) {
				c = Clase.INCOMPLETO;
			} else if (r.habitado() < p.habitadoVirgen() && !junto.contains(k)) {   // y sin bloques de jugador fuera de estructuras (si no, sería construcción)
				c = Clase.VIRGEN;
			} else {
				c = Clase.NORMAL;
			}
			clases.put(k, c);
		}
		Map<Motivo, Integer> porMotivo = new EnumMap<>(Motivo.class);
		cs.forEach(c -> porMotivo.merge(c.motivo(), 1, Integer::sum));
		return new Resultado(clases, List.copyOf(cs), porMotivo, protegidos);
	}

	/**
	 * Qué chunks vírgenes se pueden borrar para que se regeneren sin dejar estructuras cortadas: un chunk virgen se borra
	 * solo si cada estructura que cambiaría al regenerarlo (una nueva que ahora empezaría ahí, o una guardada que ya no
	 * saldría igual) cae entera en chunks que también se borran o que aún no están generados. Se repite hasta que no
	 * cambia (quitar uno puede obligar a quitar otro).
	 *
	 * @param requisitos por chunk virgen, las cajas de las estructuras que cambiarían al regenerarlo
	 * @param generados  todos los chunks guardados
	 */
	public static Set<Long> regenerables(Set<Long> virgenes, Set<Long> generados, Map<Long, List<int[]>> requisitos) {
		Set<Long> out = new HashSet<>(virgenes);
		boolean cambia = true;
		while (cambia) {
			cambia = false;
			for (Long k : List.copyOf(out)) {
				for (int[] bb : requisitos.getOrDefault(k, List.of())) {
					if (!cubre(bb, out, generados)) {
						out.remove(k);
						cambia = true;
						break;
					}
				}
			}
		}
		return out;
	}

	/** ¿Cae la caja entera en chunks que se borran o que no están generados? */
	static boolean cubre(int[] bb, Set<Long> borrados, Set<Long> generados) {
		for (int cx = Math.floorDiv(bb[0], 16); cx <= Math.floorDiv(bb[3], 16); cx++) {
			for (int cz = Math.floorDiv(bb[2], 16); cz <= Math.floorDiv(bb[5], 16); cz++) {
				long k = ResumenChunk.clave(cx, cz);
				if (generados.contains(k) && !borrados.contains(k)) {
					return false;
				}
			}
		}
		return true;
	}

	/**
	 * ¿Se puede colocar ahí una estructura nueva (vía B)? Su caja (en planta) no toca ningún chunk protegido ni con
	 * construcción, ni las piezas de otra estructura guardada o ya elegida, y su chunk de inicio está generado (normal, o
	 * virgen que no se regenera) y no se va a regenerar.
	 */
	public static boolean colocable(int[] caja, long inicio, Resultado r, Set<Long> regenerar, Map<Long, List<int[]>> piezas,
									List<int[]> elegidas) {
		Clase ci = r.clases().get(inicio);
		if (ci != Clase.NORMAL && ci != Clase.VIRGEN || regenerar.contains(inicio)) {
			return false;
		}
		for (int cx = Math.floorDiv(caja[0], 16); cx <= Math.floorDiv(caja[3], 16); cx++) {
			for (int cz = Math.floorDiv(caja[2], 16); cz <= Math.floorDiv(caja[5], 16); cz++) {
				long k = ResumenChunk.clave(cx, cz);
				Clase c = r.clases().get(k);
				if (r.protegidos().contains(k) || c == Clase.CONSTRUCCION || c == Clase.PROTEGIDO) {
					return false;
				}
				for (int[] bb : piezas.getOrDefault(k, List.of())) {
					if (solapan(caja, bb)) {
						return false;
					}
				}
			}
		}
		for (int[] e : elegidas) {
			if (solapan(caja, e)) {
				return false;
			}
		}
		return true;
	}
}
