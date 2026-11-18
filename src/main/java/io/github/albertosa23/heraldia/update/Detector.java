package io.github.albertosa23.heraldia.update;

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
 * los resúmenes de los chunks guardados ({@link ChunkSummary}) y unos puntos sueltos. Una construcción es cualquiera de:
 * <ul>
 * <li>un bloque típico de jugador ({@link PlayerBlocks}) fuera de las piezas de las estructuras guardadas;</li>
 * <li>columnas cuya cima no coincide con la de la regeneración con la misma semilla (sin contar las cimas naturales: árboles,
 * nieve, fluidos...) en un chunk donde ha estado algún jugador ({@link Parameters#minDifferences} o más);</li>
 * <li>un chunk muy habitado (InhabitedTime de {@link Parameters#inhabitedBase} o más: alguien pasó ahí mucho tiempo);</li>
 * <li>el punto de aparición del mundo, las camas y puntos de reaparición de los jugadores y su última posición;</li>
 * <li>las zonas reclamadas con mods de protección, si se pueden leer.</li>
 * </ul>
 * Alrededor de cada construcción hay un margen ({@link Parameters#margin}, 50 bloques por defecto, en horizontal): un chunk
 * con algún bloque a esa distancia o menos queda <em>protegido</em>, y ahí no se borra ni se coloca nada. Un chunk es
 * <em>virgen</em> si está generado del todo, casi nadie ha pasado por él (InhabitedTime menor que
 * {@link Parameters#inhabitedPristine}), no tiene bloques de jugador fuera de las estructuras y no está protegido (lo de
 * dentro de las estructuras lo vuelve a poner la regeneración), ni él ni ninguno de sus 8 vecinos están protegidos (al
 * regenerarse, sus rasgos del terreno escriben también en los vecinos). Los bloques de jugador que la generación también
 * pone sueltos ({@link PlayerBlocks#ambiguous}) solo cuentan en chunks por los que ha pasado alguien.
 */
public final class Detector {
	public enum Reason { BLOCKS, DIFFERENCE, INHABITED, SPAWN, RESPAWN, PLAYER, CLAIM }

	public enum Kind {
		/** Tiene una construcción. */
		BUILD,
		/** A menos del margen de una construcción. */
		PROTECTED,
		/** Se puede regenerar. */
		PRISTINE,
		/** Generado, ni virgen ni protegido: ahí se pueden colocar estructuras nuevas. */
		NORMAL,
		/** A medio generar: no se toca. */
		INCOMPLETE
	}

	/**
	 * @param margen         bloques alrededor de cada construcción donde no se toca nada (actualizar.margen_bloques)
	 * @param habitadoVirgen InhabitedTime por debajo del cual un chunk puede ser virgen (ticks)
	 * @param habitadoBase   InhabitedTime desde el cual el chunk cuenta como construcción (ticks)
	 * @param minDiferencias columnas distintas de la regeneración para que el chunk cuente como construcción
	 */
	public record Parameters(int margin, long inhabitedPristine, long inhabitedBase, int minDifferences) {
		/** 50 bloques; virgen con menos de 1 min de jugadores cerca; construcción desde 1 h; 3 columnas de 16. */
		public static Parameters defaults(int margin) {
			return new Parameters(margin, 1200, 72_000, 3);
		}
	}

	/** Una construcción: el rectángulo (en bloques, inclusive) que ocupa y por qué cuenta. */
	public record Build(int minX, int minZ, int maxX, int maxZ, Reason reason) {
		public static Build point(int x, int z, Reason m) {
			return new Build(x, z, x, z, m);
		}

		public static Build chunk(int cx, int cz, Reason m) {
			return new Build(cx * 16, cz * 16, cx * 16 + 15, cz * 16 + 15, m);
		}
	}

	public record Result(Map<Long, Kind> classes, List<Build> builds, Map<Reason, Integer> byReason,
							Set<Long> protectedChunks) {
		public Kind clazz(int cx, int cz) {
			return classes.get(ChunkSummary.key(cx, cz));
		}

		public long tally(Kind c) {
			return classes.values().stream().filter(c::equals).count();
		}
	}

	private Detector() {
	}

	/** Distancia horizontal (euclídea, en bloques) entre dos rectángulos de bloques; 0 si se tocan o se solapan. */
	public static double distance(int aMinX, int aMinZ, int aMaxX, int aMaxZ, int bMinX, int bMinZ, int bMaxX, int bMaxZ) {
		int dx = Math.max(0, Math.max(aMinX - bMaxX, bMinX - aMaxX));
		int dz = Math.max(0, Math.max(aMinZ - bMaxZ, bMinZ - aMaxZ));
		return Math.sqrt((double) dx * dx + (double) dz * dz);
	}

	/** ¿Tiene el chunk algún bloque a {@code margin} bloques o menos de la construcción? */
	public static boolean near(Build c, int cx, int cz, int margin) {
		return distance(c.minX(), c.minZ(), c.maxX(), c.maxZ(), cx * 16, cz * 16, cx * 16 + 15, cz * 16 + 15) <= margin;
	}

	/** Los chunks a {@code margin} o menos de alguna construcción (los de la construcción incluidos). */
	public static Set<Long> protectedChunks(Collection<Build> cs, int margin) {
		Set<Long> out = new HashSet<>();
		for (Build c : cs) {
			int x0 = Math.floorDiv(c.minX() - margin, 16), x1 = Math.floorDiv(c.maxX() + margin, 16);
			int z0 = Math.floorDiv(c.minZ() - margin, 16), z1 = Math.floorDiv(c.maxZ() + margin, 16);
			for (int cx = x0; cx <= x1; cx++) {
				for (int cz = z0; cz <= z1; cz++) {
					if (near(c, cx, cz, margin)) {
						out.add(ChunkSummary.key(cx, cz));
					}
				}
			}
		}
		return out;
	}

	/** ¿Está el bloque dentro de la caja {minX, minY, minZ, maxX, maxY, maxZ}? */
	public static boolean inside(int[] bb, int x, int y, int z) {
		return x >= bb[0] && y >= bb[1] && z >= bb[2] && x <= bb[3] && y <= bb[4] && z <= bb[5];
	}

	/** ¿Se solapan en planta dos cajas? */
	public static boolean overlap(int[] a, int[] b) {
		return a[0] <= b[3] && b[0] <= a[3] && a[2] <= b[5] && b[2] <= a[5];
	}

	/** Las piezas de las estructuras guardadas, por cada chunk que toca su caja (en planta). */
	public static Map<Long, List<int[]>> piecesByChunk(Collection<ChunkSummary> chunks) {
		Map<Long, List<int[]>> out = new HashMap<>();
		for (ChunkSummary r : chunks) {
			for (List<int[]> boxes : r.structureStarts().values()) {
				for (int[] bb : boxes) {
					for (int cx = Math.floorDiv(bb[0], 16); cx <= Math.floorDiv(bb[3], 16); cx++) {
						for (int cz = Math.floorDiv(bb[2], 16); cz <= Math.floorDiv(bb[5], 16); cz++) {
							out.computeIfAbsent(ChunkSummary.key(cx, cz), k -> new ArrayList<>()).add(bb);
						}
					}
				}
			}
		}
		return out;
	}

	/** Los bloques de jugador de un chunk que no están dentro de ninguna pieza de estructura: {x, z}. */
	static List<int[]> outsideStructures(ChunkSummary r, List<int[]> pieces) {
		List<int[]> out = new ArrayList<>();
		for (int i = 0; i < r.player().length; i++) {
			if (r.ambiguous(i) && r.inhabited() <= 0) {
				continue;            // tablones, vallas, raíles y cofres que pone la generación: sin jugadores cerca no cuentan
			}
			int[] b = r.playerBlock(i);
			boolean inside = false;
			for (int[] bb : pieces) {
				if (inside(bb, b[0], b[1], b[2])) {
					inside = true;
					break;
				}
			}
			if (!inside) {
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
	public static Result classify(Collection<ChunkSummary> chunks, Map<Long, List<int[]>> differences, List<Build> extra,
									   Parameters p) {
		Map<Long, List<int[]>> pieces = piecesByChunk(chunks);
		List<Build> cs = new ArrayList<>(extra);
		Set<Long> withBuild = new HashSet<>();
		for (ChunkSummary r : chunks) {
			List<int[]> outside = outsideStructures(r, pieces.getOrDefault(r.key(), List.of()));
			boolean has = false;
			for (int[] b : outside) {
				cs.add(Build.point(b[0], b[1], Reason.BLOCKS));
				has = true;
			}
			List<int[]> dif = differences.getOrDefault(r.key(), List.of());
			if (dif.size() >= p.minDifferences()) {
				for (int[] d : dif) {
					cs.add(Build.point(d[0], d[1], Reason.DIFFERENCE));
				}
				has = true;
			}
			if (r.inhabited() >= p.inhabitedBase()) {
				cs.add(Build.chunk(r.cx(), r.cz(), Reason.INHABITED));
				has = true;
			}
			if (has) {
				withBuild.add(r.key());
			}
		}
		for (Build c : extra) {
			withBuild.add(ChunkSummary.key(Math.floorDiv(c.minX(), 16), Math.floorDiv(c.minZ(), 16)));
		}
		Set<Long> protectedChunks = protectedChunks(cs, p.margin());
		// al regenerarse, los rasgos de un chunk (vetas, árboles, rocas) escriben también en los 8 de alrededor: un chunk
		// junto a uno protegido no se regenera (visto en tools/smoke/actualizar.py: vetas de andesita en un chunk protegido)
		Set<Long> beside = new HashSet<>();
		for (long k : protectedChunks) {
			for (int dx = -1; dx <= 1; dx++) {
				for (int dz = -1; dz <= 1; dz++) {
					beside.add(ChunkSummary.key(ChunkSummary.cx(k) + dx, ChunkSummary.cz(k) + dz));
				}
			}
		}
		Map<Long, Kind> classes = new LinkedHashMap<>();
		for (ChunkSummary r : chunks) {
			long k = r.key();
			Kind c;
			if (withBuild.contains(k)) {
				c = Kind.BUILD;
			} else if (protectedChunks.contains(k)) {
				c = Kind.PROTECTED;
			} else if (!r.complete()) {
				c = Kind.INCOMPLETE;
			} else if (r.inhabited() < p.inhabitedPristine() && !beside.contains(k)) {   // y sin bloques de jugador fuera de estructuras (si no, sería construcción)
				c = Kind.PRISTINE;
			} else {
				c = Kind.NORMAL;
			}
			classes.put(k, c);
		}
		Map<Reason, Integer> byReason = new EnumMap<>(Reason.class);
		cs.forEach(c -> byReason.merge(c.reason(), 1, Integer::sum));
		return new Result(classes, List.copyOf(cs), byReason, protectedChunks);
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
	public static Set<Long> regenerable(Set<Long> pristine, Set<Long> generated, Map<Long, List<int[]>> requirements) {
		Set<Long> out = new HashSet<>(pristine);
		boolean changes = true;
		while (changes) {
			changes = false;
			for (Long k : List.copyOf(out)) {
				for (int[] bb : requirements.getOrDefault(k, List.of())) {
					if (!covers(bb, out, generated)) {
						out.remove(k);
						changes = true;
						break;
					}
				}
			}
		}
		return out;
	}

	/** ¿Cae la caja entera en chunks que se borran o que no están generados? */
	static boolean covers(int[] bb, Set<Long> deleted, Set<Long> generated) {
		for (int cx = Math.floorDiv(bb[0], 16); cx <= Math.floorDiv(bb[3], 16); cx++) {
			for (int cz = Math.floorDiv(bb[2], 16); cz <= Math.floorDiv(bb[5], 16); cz++) {
				long k = ChunkSummary.key(cx, cz);
				if (generated.contains(k) && !deleted.contains(k)) {
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
	public static boolean placeable(int[] box, long start, Result r, Set<Long> regenerate, Map<Long, List<int[]>> pieces,
									List<int[]> chosen) {
		Kind ci = r.classes().get(start);
		if (ci != Kind.NORMAL && ci != Kind.PRISTINE || regenerate.contains(start)) {
			return false;
		}
		for (int cx = Math.floorDiv(box[0], 16); cx <= Math.floorDiv(box[3], 16); cx++) {
			for (int cz = Math.floorDiv(box[2], 16); cz <= Math.floorDiv(box[5], 16); cz++) {
				long k = ChunkSummary.key(cx, cz);
				Kind c = r.classes().get(k);
				if (r.protectedChunks().contains(k) || c == Kind.BUILD || c == Kind.PROTECTED) {
					return false;
				}
				for (int[] bb : pieces.getOrDefault(k, List.of())) {
					if (overlap(box, bb)) {
						return false;
					}
				}
			}
		}
		for (int[] e : chosen) {
			if (overlap(box, e)) {
				return false;
			}
		}
		return true;
	}
}
