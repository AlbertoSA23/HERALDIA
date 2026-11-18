package io.github.albertosa23.heraldia.common;

import it.unimi.dsi.fastutil.longs.LongOpenHashSet;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.function.Function;
import net.minecraft.world.level.ChunkPos;

/**
 * "Is this chunk surely not on disk?", without asking the storage thread (mixin/IOWorkerMixin). The structure searches
 * (/locate, the maps, /heraldia info) ask the disk about every candidate chunk of every cell they walk; for one that was
 * never generated, the answer ("no data") costs a round trip to the storage thread (about 35 µs, measured): a search that
 * finds nothing walks some 40,000 cells and spent 1.4 s of its 1.6 s there. A chunk is surely not on disk if its region
 * file does not exist and no chunk of that region was handed to the storage in this session (it would be waiting to be
 * written, and the storage thread would answer with it): then the answer is the same "no data", given right away.
 * <p>One per storage (chunks, entities, POI: each one its folder). Thread-safe: {@link #written} comes from the threads that
 * save chunks and {@link #absent} from those that search. A region whose file exists, or that was written, is never
 * asked again (it only grows). A missing file is remembered too (at most {@link #MISSING_MAX} regions) until a chunk of
 * its region is handed to the storage: like the game's own region cache (RegionFileStorage keeps "no file" for the
 * regions it has looked at), a region file copied in by hand while the server runs is not seen until the next start.
 */
public final class UnwrittenRegions {
	static final int MISSING_MAX = 1 << 16;
	private final LongOpenHashSet written = new LongOpenHashSet(), present = new LongOpenHashSet(), missing = new LongOpenHashSet();
	private final Function<ChunkPos, Path> regionPath;

	/** {@code regionPath}: where the storage keeps a chunk's region (RegionFileStorage.regionPath). */
	public UnwrittenRegions(Function<ChunkPos, Path> regionPath) {
		this.regionPath = regionPath;
	}

	static long region(ChunkPos pos) {
		return ChunkPos.pack(pos.getRegionX(), pos.getRegionZ());
	}

	/** A chunk handed to the storage (IOWorker.store, before it is queued): its region can no longer be "surely absent". */
	public void written(ChunkPos pos) {
		long r = region(pos);
		synchronized (this) {
			written.add(r);
			missing.remove(r);
		}
	}

	/** Is the chunk surely not on disk nor waiting to be written? If not sure, false (the storage is asked as always). */
	public boolean absent(ChunkPos pos) {
		long r = region(pos);
		synchronized (this) {
			if (written.contains(r) || present.contains(r)) {
				return false;
			}
			if (missing.contains(r)) {
				return true;
			}
		}
		boolean exists = Files.isRegularFile(regionPath.apply(pos));   // the same check as RegionFileStorage.getRegionFile
		synchronized (this) {
			if (exists) {
				present.add(r);
				return false;
			}
			if (written.contains(r)) {
				return false;             // a chunk of the region handed to the storage meanwhile: not sure any more
			}
			if (missing.size() >= MISSING_MAX) {
				missing.clear();
			}
			missing.add(r);
			return true;
		}
	}
}
