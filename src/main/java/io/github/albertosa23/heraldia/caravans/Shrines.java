package io.github.albertosa23.heraldia.caravans;

import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.config.UniqueSeparation;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import net.minecraft.core.RegistryAccess;
import net.minecraft.resources.Identifier;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.chunk.ChunkGenerator;
import net.minecraft.world.level.chunk.ChunkGeneratorStructureState;
import net.minecraft.world.level.levelgen.RandomState;
import net.minecraft.world.level.levelgen.densityfunction.SamplerContext;
import net.minecraft.world.level.levelgen.structure.placement.RandomSpreadStructurePlacement;
import org.jspecify.annotations.Nullable;

/**
 * Where a pilgrim walks to: the nearest monastery or cathedral that really spawns (the same check as /locate and the roads'
 * milestones: its grid cell, its biome and terrain and the separation between unique structures), within
 * {@link Wayfarers#SHRINE_RANGE} blocks. Off the server thread (it reads no chunk: only the noise); each candidate cell is
 * decided once per world and remembered (a few per world: the unique structures are thousands of blocks apart).
 */
final class Shrines {
	static final List<Identifier> SHRINES = List.of(Heraldia.id("unicas/monasterio"), Heraldia.id("unicas/catedral"));
	/** (structure index, chunk) → it spawns there. */
	private static final Map<Long, Boolean> MEMO = new ConcurrentHashMap<>();
	private static volatile @Nullable Object world;

	private Shrines() {
	}

	/** A shrine: which one and its center in blocks. */
	record Shrine(Identifier id, int x, int z) {
	}

	static void clear() {
		MEMO.clear();
		world = null;
	}

	static @Nullable Shrine nearest(ServerLevel level, int x, int z) {
		if (level.dimension() != Level.OVERWORLD) {
			return null;
		}
		if (world != level) {
			MEMO.clear();
			world = level;
		}
		RegistryAccess access = level.registryAccess();
		ChunkGenerator generator = level.getChunkSource().getGenerator();
		RandomState randomState = level.getChunkSource().randomState();
		ChunkGeneratorStructureState state = level.getChunkSource().getGeneratorState();
		long seed = state.getLevelSeed();
		UniqueSeparation sep = UniqueSeparation.of(access);
		UniqueSeparation.Viability viability = null;
		Shrine best = null;
		double bestD = Wayfarers.SHRINE_RANGE;
		int r = Wayfarers.SHRINE_RANGE;
		for (Identifier id : SHRINES) {
			int i = sep.indexOf(id);
			if (i < 0 || sep.fixed(i)) {
				continue;
			}
			RandomSpreadStructurePlacement p = sep.placement(i);
			int s = p.spacing() * 16, ox = UniqueSeparation.offsetX(p), oz = UniqueSeparation.offsetZ(p);
			for (int gx = Math.floorDiv(x - r - ox * 16, s); gx <= Math.floorDiv(x + r - ox * 16, s); gx++) {
				for (int gz = Math.floorDiv(z - r - oz * 16, s); gz <= Math.floorDiv(z + r - oz * 16, s); gz++) {
					ChunkPos c = p.getPotentialStructureChunk(seed, gx * p.spacing() + ox, gz * p.spacing() + oz);
					int cx = c.x() * 16 + 8, cz = c.z() * 16 + 8;
					double d = Math.hypot(cx - x, cz - z);
					if (d >= bestD) {
						continue;
					}
					long key = ((long) i << 56) ^ ((long) c.x() << 28) ^ (c.z() & 0xFFFFFFFL);
					Boolean ok = MEMO.get(key);
					if (ok == null) {
						if (viability == null) {
							viability = sep.viability(access, generator, generator.getBiomeSource(),
									randomState.createClimateSampler(SamplerContext.EMPTY_UNCACHED), randomState, level.getStructureTemplateManager(),
									seed, level, level.dimension());
						}
						ok = p.isStructureChunk(state, c.x(), c.z()) && viability.valid(i, c.x(), c.z()) && !sep.blocked(i, c.x(), c.z(), seed, viability);
						MEMO.put(key, ok);
					}
					if (ok) {
						bestD = d;
						best = new Shrine(id, cx, cz);
					}
				}
			}
		}
		return best;
	}
}
