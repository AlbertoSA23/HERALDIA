package io.github.albertosa23.heraldia.uniques.island;

import io.github.albertosa23.heraldia.config.UniqueSeparation;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import net.minecraft.resources.Identifier;
import net.minecraft.resources.ResourceKey;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.levelgen.structure.placement.RandomSpreadStructurePlacement;

/**
 * Corsair's island zone: no foreign structure (shipwrecks, ocean ruins, ruined portals...) is born
 * inside the islet or right next to it, as with Atlantis. A foreign start is rejected if it falls within REACH chunks of the
 * island candidate of its cell and the island really wins there (the same viability as the minimum distance between
 * uniques: biome, sea floor, Atlantis and separation). The expensive part (the viability) is only computed next to an island
 * candidate (a few chunks per 4,000-block cell) and is memoized; the rest pays a table lookup
 * and the cell's candidate (already memoized in GridPlacement).
 */
public final class IslandZone {
	public static final long NONE = Long.MIN_VALUE;
	private static final Identifier ISLAND = Identifier.fromNamespaceAndPath("heraldia", "unicas/isla_corsario");
	/** Island footprint (54 blocks) + site search (16) + a foreign structure (about 40), in chunks. */
	private static final int REACH = 7, CACHE_MAX = 1 << 12;
	private static final Set<Identifier> REQUIRED = Set.of(Identifier.fromNamespaceAndPath("minecraft", "stronghold"));
	private static final ConcurrentHashMap<Long, Boolean> OUTCOME = new ConcurrentHashMap<>();

	private IslandZone() {
	}

	/** Island candidate near the chunk (packed with ChunkPos.pack) or NONE. Cheap: no terrain or biomes. */
	public static long candidate(Identifier structure, ResourceKey<Level> dimension, UniqueSeparation sep, long seed, int chunkX, int chunkZ) {
		if (dimension != Level.OVERWORLD || "heraldia".equals(structure.getNamespace()) || REQUIRED.contains(structure)) {
			return NONE;
		}
		int i = sep.indexOf(ISLAND);
		if (i < 0) {
			return NONE;
		}
		RandomSpreadStructurePlacement p = sep.placement(i);
		int s = p.spacing(), ox = UniqueSeparation.offsetX(p), oz = UniqueSeparation.offsetZ(p);
		for (int gx = Math.floorDiv(chunkX - REACH - ox, s), gxMax = Math.floorDiv(chunkX + REACH - ox, s); gx <= gxMax; gx++) {
			for (int gz = Math.floorDiv(chunkZ - REACH - oz, s), gzMax = Math.floorDiv(chunkZ + REACH - oz, s); gz <= gzMax; gz++) {
				ChunkPos c = p.getPotentialStructureChunk(seed, gx * s + ox, gz * s + oz);
				if (Math.abs(c.x() - chunkX) <= REACH && Math.abs(c.z() - chunkZ) <= REACH && p.applyAdditionalChunkRestrictions(c.x(), c.z(), seed)) {
					return ChunkPos.pack(c.x(), c.z());
				}
			}
		}
		return NONE;
	}

	/** The island really wins at that candidate (viability and minimum distance between uniques); memoized per seed. */
	public static boolean outcome(UniqueSeparation sep, long candidate, long seed, UniqueSeparation.Viability viability) {
		long key = candidate * 31 + seed;
		Boolean v = OUTCOME.get(key);
		if (v == null) {
			int i = sep.indexOf(ISLAND), x = ChunkPos.getX(candidate), z = ChunkPos.getZ(candidate);
			v = viability.valid(i, x, z) && !sep.blocked(i, x, z, seed, viability);
			if (OUTCOME.size() > CACHE_MAX) {
				OUTCOME.clear();
			}
			OUTCOME.put(key, v);
		}
		return v;
	}
}
