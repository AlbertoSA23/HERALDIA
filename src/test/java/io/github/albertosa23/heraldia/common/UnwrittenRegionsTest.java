package io.github.albertosa23.heraldia.common;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import net.minecraft.world.level.ChunkPos;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * "Surely not on disk" only when the region file is missing and nothing of that region was handed to the storage: in any
 * other case the storage thread is asked as always (a file that appears later is seen; a chunk waiting to be written too).
 */
class UnwrittenRegionsTest {
	@TempDir
	Path dir;

	private UnwrittenRegions regions() {
		return new UnwrittenRegions(p -> dir.resolve("r." + p.getRegionX() + "." + p.getRegionZ() + ".mca"));
	}

	@Test
	void aChunkWithoutRegionFileAndNeverWrittenIsAbsent() {
		UnwrittenRegions r = regions();
		assertTrue(r.absent(new ChunkPos(0, 0)));
		assertTrue(r.absent(new ChunkPos(-1, -1)));
		assertTrue(r.absent(new ChunkPos(12500, 12500)));
	}

	@Test
	void aRegionWithItsFileIsNeverAbsent() throws IOException {
		UnwrittenRegions r = regions();
		Files.writeString(dir.resolve("r.1.0.mca"), "");
		assertFalse(r.absent(new ChunkPos(40, 7)));
		assertFalse(r.absent(new ChunkPos(63, 31)), "the same region");
		assertTrue(r.absent(new ChunkPos(64, 31)), "the next region");
		Files.delete(dir.resolve("r.1.0.mca"));
		assertFalse(r.absent(new ChunkPos(40, 7)), "once seen, the storage is always asked");
	}

	@Test
	void aMissingRegionIsRememberedUntilSomethingIsWrittenInIt() throws IOException {
		UnwrittenRegions r = regions();
		assertTrue(r.absent(new ChunkPos(40, 7)));
		Files.writeString(dir.resolve("r.1.0.mca"), "");          // copied in by hand: like the game's region cache, not seen
		assertTrue(r.absent(new ChunkPos(41, 7)));
		r.written(new ChunkPos(50, 20));                          // the storage writes in that region: from now on, asked
		assertFalse(r.absent(new ChunkPos(40, 7)));
	}

	@Test
	void aRegionHandedToTheStorageIsNeverAbsentEvenWithoutItsFile() {
		UnwrittenRegions r = regions();
		r.written(new ChunkPos(-33, 5));                          // region -2, 0: waiting to be written, no file yet
		assertFalse(r.absent(new ChunkPos(-33, 5)));
		assertFalse(r.absent(new ChunkPos(-64, 0)), "the same region");
		assertTrue(r.absent(new ChunkPos(-32, 0)), "region -1, 0");
	}
}
