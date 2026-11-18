package io.github.albertosa23.heraldia.config;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonParser;
import com.mojang.serialization.JsonOps;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import net.minecraft.SharedConstants;
import net.minecraft.resources.Identifier;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.levelgen.structure.Structure;
import net.minecraft.world.level.levelgen.structure.placement.RandomSpreadStructurePlacement;
import net.minecraft.world.level.levelgen.structure.placement.RandomSpreadType;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/**
 * What the generation threads query at once (with C2ME, many more than in vanilla): the candidate with the biome
 * search of GridPlacement (memo shared per cell) and the minimum distance between uniques (UniqueSeparation, with its
 * recursion and its per-query memo). Several threads on the same instance must give the same as a single one, and a
 * search still running with the previous world cannot leave its result in the new one's memo.
 */
class ConcurrencyTest {
	private static final long SEED = 42L;
	private static final int THREADS = 8;
	private static final String MYCELIUM = "{\"grupo\": \"unicas/laboratorio_micelio\", \"spacing\": 250, \"separation\": 190,"
			+ " \"salt\": 98765, \"bioma\": \"minecraft:is_ocean\"}";

	@BeforeAll
	static void bootstrap() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	@AfterEach
	void restore() {
		GridPlacement.testContext(0, null);
		HeraldiaConfig.load(null);
	}

	private static GridPlacement mycelium() {
		return GridPlacement.CODEC.codec().parse(JsonOps.INSTANCE, JsonParser.parseString(MYCELIUM)).getOrThrow();
	}

	/** Fake biome: strips of 32 chunks (quarter blocks / 4 = blocks / 16 = chunks). */
	private static boolean bands(int qx, int qz) {
		return Math.floorMod(Math.floorDiv(qx, 4 * 32), 2) == 0 && Math.floorMod(Math.floorDiv(qz, 4 * 48), 3) != 1;
	}

	private static long[] candidates(GridPlacement g, int cells) {
		long[] out = new long[cells * cells];
		int s = g.spacing(), k = 0;
		for (int gx = 0; gx < cells; gx++) {
			for (int gz = 0; gz < cells; gz++) {
				ChunkPos c = g.getPotentialStructureChunk(SEED, (gx - cells / 2) * s + g.offsetX(), (gz - cells / 2) * s + g.offsetZ());
				out[k++] = ChunkPos.pack(c.x(), c.z());
			}
		}
		return out;
	}

	@Test
	void multithreadedBiomeSearchMatchesSerial() throws Exception {
		GridPlacement.testContext(SEED, (tag, qx, qy, qz) -> bands(qx, qz));
		long[] expected = candidates(mycelium(), 12);
		GridPlacement shared = mycelium();
		ExecutorService pool = Executors.newFixedThreadPool(THREADS);
		try {
			List<Future<long[]>> futures = new ArrayList<>();
			for (int h = 0; h < THREADS; h++) {
				futures.add(pool.submit(() -> candidates(shared, 12)));
			}
			for (Future<long[]> f : futures) {
				assertArrayEquals(expected, f.get(60, TimeUnit.SECONDS));
			}
		} finally {
			pool.shutdownNow();
		}
	}

	/**
	 * World change with searches in progress: the threads search with a slow context (another world) while switching to the
	 * new one; once the race is over, every candidate must be that of the new context. With a single memo per instance (the old
	 * way), an old search finishing after the switch left its candidate forever.
	 */
	@Test
	void searchFromPreviousWorldDoesNotLeakIntoNew() throws Exception {
		GridPlacement.testContext(SEED, (tag, qx, qy, qz) -> bands(qx, qz));
		long[] newValue = candidates(mycelium(), 6);
		GridPlacement g = mycelium();
		CountDownLatch started = new CountDownLatch(THREADS);
		AtomicBoolean slow = new AtomicBoolean(true);
		GridPlacement.testContext(SEED, (tag, qx, qy, qz) -> {
			if (slow.get()) {
				started.countDown();
				long end = System.nanoTime() + 20_000;
				while (System.nanoTime() < end) {
					Thread.onSpinWait();
				}
			}
			return true; // the previous world: everything is in the biome (a different candidate in each cell)
		});
		ExecutorService pool = Executors.newFixedThreadPool(THREADS);
		try {
			List<Future<long[]>> futures = new ArrayList<>();
			for (int h = 0; h < THREADS; h++) {
				futures.add(pool.submit(() -> candidates(g, 6)));
			}
			assertTrue(started.await(30, TimeUnit.SECONDS));
			GridPlacement.testContext(SEED, (tag, qx, qy, qz) -> bands(qx, qz)); // the new world (same seed)
			candidates(g, 6); // first queries of the new world while the old ones continue (slowly)
			slow.set(false); // now the old ones finish: their result must not overwrite the new world's
			for (Future<long[]> f : futures) {
				f.get(120, TimeUnit.SECONDS);
			}
		} finally {
			pool.shutdownNow();
		}
		assertArrayEquals(newValue, candidates(g, 6));
	}

	@Test
	void multithreadedMinDistanceMatchesSerial() throws Exception {
		int n = 6;
		List<Identifier> ids = new ArrayList<>();
		List<RandomSpreadStructurePlacement> grids = new ArrayList<>();
		for (int i = 0; i < n; i++) {
			ids.add(Identifier.fromNamespaceAndPath("heraldia", "unicas/u" + i));
			grids.add(new RandomSpreadStructurePlacement(40 + 3 * i, 20, RandomSpreadType.LINEAR, 1000 + 7919 * i));
		}
		List<Structure> none = new ArrayList<>(Collections.nCopies(n, (Structure) null));
		UniqueSeparation sep = new UniqueSeparation("prueba", ids, none, grids, Collections.nCopies(n, false), true, 1000);
		UniqueSeparation.Viability v = (j, x, z) -> Long.hashCode(UniqueSeparation.mix(ChunkPos.pack(x, z) * 31 + j)) % 3 != 0;
		int cells = 30;
		boolean[] expected = new boolean[n * cells * cells];
		int[][] pos = new int[expected.length][];
		int k = 0;
		for (int i = 0; i < n; i++) {
			int s = grids.get(i).spacing();
			for (int gx = 0; gx < cells; gx++) {
				for (int gz = 0; gz < cells; gz++) {
					ChunkPos c = grids.get(i).getPotentialStructureChunk(SEED, gx * s, gz * s);
					pos[k] = new int[]{i, c.x(), c.z()};
					expected[k] = sep.blocked(i, c.x(), c.z(), SEED, v);
					k++;
				}
			}
		}
		int discarded = 0;
		for (boolean b : expected) {
			discarded += b ? 1 : 0;
		}
		assertTrue(discarded > 0 && discarded < expected.length, "la prueba debe tener de las dos: " + discarded);
		ExecutorService pool = Executors.newFixedThreadPool(THREADS);
		try {
			List<Future<boolean[]>> futures = new ArrayList<>();
			for (int h = 0; h < THREADS; h++) {
				int from = h;
				futures.add(pool.submit(() -> {
					boolean[] got = new boolean[expected.length];
					for (int m = 0; m < got.length; m++) {
						int q = (m * 13 + from * 977) % got.length;
						got[q] = sep.blocked(pos[q][0], pos[q][1], pos[q][2], SEED, v);
					}
					return got;
				}));
			}
			for (Future<boolean[]> f : futures) {
				assertArrayEquals(expected, f.get(120, TimeUnit.SECONDS));
			}
		} finally {
			pool.shutdownNow();
		}
		assertEquals(expected.length, pos.length);
	}
}
