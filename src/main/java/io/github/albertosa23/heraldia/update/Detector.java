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
 * Detection of player builds and classification of the chunks for /heraldia update (T46), pure logic over
 * the summaries of the saved chunks ({@link ChunkSummary}) and some loose points. A build is any of:
 * <ul>
 * <li>a typical player block ({@link PlayerBlocks}) outside the pieces of the saved structures;</li>
 * <li>columns whose top does not match that of the regeneration with the same seed (not counting natural tops: trees,
 * snow, fluids...) in a chunk where some player has been ({@link Parameters#minDifferences} or more);</li>
 * <li>a heavily inhabited chunk (InhabitedTime of {@link Parameters#inhabitedBase} or more: someone spent a lot of time there);</li>
 * <li>the world spawn point, the players' beds and respawn points and their last position;</li>
 * <li>areas claimed with protection mods, if they can be read.</li>
 * </ul>
 * Around each build there is a margin ({@link Parameters#margin}, 50 blocks by default, horizontally): a chunk
 * with any block at that distance or less is <em>protected</em>, and nothing is deleted or placed there. A chunk is
 * <em>pristine</em> if it is fully generated, almost nobody has passed through it (InhabitedTime less than
 * {@link Parameters#inhabitedPristine}), it has no player blocks outside the structures and it is not protected (what is
 * inside the structures is put back by the regeneration), and neither it nor any of its 8 neighbors are protected (when
 * regenerated, its terrain features also write into the neighbors). The player blocks that generation also
 * places on its own ({@link PlayerBlocks#ambiguous}) only count in chunks someone has passed through.
 */
public final class Detector {
	public enum Reason { BLOCKS, DIFFERENCE, INHABITED, SPAWN, RESPAWN, PLAYER, CLAIM }

	public enum Kind {
		/** It has a build. */
		BUILD,
		/** Within the margin of a build. */
		PROTECTED,
		/** It can be regenerated. */
		PRISTINE,
		/** Generated, neither pristine nor protected: new structures can be placed there. */
		NORMAL,
		/** Half generated: not touched. */
		INCOMPLETE
	}

	/**
	 * @param margin            blocks around each build where nothing is touched (actualizar.margen_bloques)
	 * @param inhabitedPristine InhabitedTime below which a chunk can be pristine (ticks)
	 * @param inhabitedBase     InhabitedTime from which the chunk counts as a build (ticks)
	 * @param minDifferences    columns differing from the regeneration for the chunk to count as a build
	 */
	public record Parameters(int margin, long inhabitedPristine, long inhabitedBase, int minDifferences) {
		/** 50 blocks; pristine with less than 1 min of players nearby; build from 1 h; 3 columns out of 16. */
		public static Parameters defaults(int margin) {
			return new Parameters(margin, 1200, 72_000, 3);
		}
	}

	/** A build: the rectangle (in blocks, inclusive) it occupies and why it counts. */
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

	/** Horizontal distance (Euclidean, in blocks) between two block rectangles; 0 if they touch or overlap. */
	public static double distance(int aMinX, int aMinZ, int aMaxX, int aMaxZ, int bMinX, int bMinZ, int bMaxX, int bMaxZ) {
		int dx = Math.max(0, Math.max(aMinX - bMaxX, bMinX - aMaxX));
		int dz = Math.max(0, Math.max(aMinZ - bMaxZ, bMinZ - aMaxZ));
		return Math.sqrt((double) dx * dx + (double) dz * dz);
	}

	/** Does the chunk have any block within {@code margin} blocks of the build? */
	public static boolean near(Build c, int cx, int cz, int margin) {
		return distance(c.minX(), c.minZ(), c.maxX(), c.maxZ(), cx * 16, cz * 16, cx * 16 + 15, cz * 16 + 15) <= margin;
	}

	/** The chunks within {@code margin} of some build (the build's own included). */
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

	/** Is the block inside the box {minX, minY, minZ, maxX, maxY, maxZ}? */
	public static boolean inside(int[] bb, int x, int y, int z) {
		return x >= bb[0] && y >= bb[1] && z >= bb[2] && x <= bb[3] && y <= bb[4] && z <= bb[5];
	}

	/** Do two boxes overlap in plan view? */
	public static boolean overlap(int[] a, int[] b) {
		return a[0] <= b[3] && b[0] <= a[3] && a[2] <= b[5] && b[2] <= a[5];
	}

	/** The pieces of the saved structures, per chunk their box touches (in plan view). */
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

	/** A chunk's player blocks that are not inside any structure piece: {x, z}. */
	static List<int[]> outsideStructures(ChunkSummary r, List<int[]> pieces) {
		List<int[]> out = new ArrayList<>();
		for (int i = 0; i < r.player().length; i++) {
			if (r.ambiguous(i) && r.inhabited() <= 0) {
				continue;            // planks, fences, rails and chests that generation places: without players nearby they do not count
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
	 * Detects the builds and classifies each saved chunk.
	 *
	 * @param differences columns {x, z} differing from the regeneration, per chunk (only of the chunks that were compared)
	 * @param extra       builds that do not come from the chunks: spawn, beds and respawn, players, claims
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
		// when regenerated, a chunk's features (veins, trees, rocks) also write into the 8 around it: a chunk
		// next to a protected one is not regenerated (seen in tools/smoke/actualizar.py: andesite veins in a protected chunk)
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
			} else if (r.inhabited() < p.inhabitedPristine() && !beside.contains(k)) {   // and without player blocks outside structures (otherwise, it would be a build)
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
	 * Which pristine chunks can be deleted so they regenerate without leaving cut structures: a pristine chunk is deleted
	 * only if every structure that would change when regenerating it (a new one that would now start there, or a saved one that would no
	 * longer spawn the same) falls entirely in chunks that are also deleted or not generated yet. It repeats until it does not
	 * change (removing one may force removing another).
	 *
	 * @param requirements per pristine chunk, the boxes of the structures that would change when regenerating it
	 * @param generated    all the saved chunks
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

	/** Does the whole box fall in chunks that are deleted or not generated? */
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
	 * Can a new structure be placed there (path B)? Its box (in plan view) touches no protected chunk or chunk with a
	 * build, nor the pieces of another saved or already chosen structure, and its start chunk is generated (normal, or
	 * pristine but not regenerated) and is not going to be regenerated.
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
