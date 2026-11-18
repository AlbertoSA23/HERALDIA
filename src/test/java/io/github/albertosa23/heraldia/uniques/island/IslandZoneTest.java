package io.github.albertosa23.heraldia.uniques.island;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import io.github.albertosa23.heraldia.config.UniqueSeparation;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;
import net.minecraft.SharedConstants;
import net.minecraft.resources.Identifier;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.levelgen.structure.Structure;
import net.minecraft.world.level.levelgen.structure.placement.RandomSpreadStructurePlacement;
import net.minecraft.world.level.levelgen.structure.placement.RandomSpreadType;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/** Zona de exclusión de la isla del corsario: qué inicios ajenos caen junto a la candidata de la isla y la memoria de «sale». */
class IslandZoneTest {
	private static final Identifier ISLAND = Identifier.fromNamespaceAndPath("heraldia", "unicas/isla_corsario");
	private static final Identifier OTHER = Identifier.fromNamespaceAndPath("heraldia", "unicas/faro");
	private static final Identifier SHIPWRECK = Identifier.fromNamespaceAndPath("minecraft", "shipwreck");
	private static final RandomSpreadStructurePlacement GRID = new RandomSpreadStructurePlacement(250, 63, RandomSpreadType.LINEAR, 4242);
	private static UniqueSeparation sep;

	@BeforeAll
	static void bootstrap() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
		List<Structure> none = new ArrayList<>();
		none.add(null);
		none.add(null);
		sep = new UniqueSeparation("prueba", List.of(OTHER, ISLAND), none,
				List.of(new RandomSpreadStructurePlacement(250, 63, RandomSpreadType.LINEAR, 99), GRID), List.of(false, false), true, 1000);
	}

	@Test
	void foreignNextToCandidateIsSeen() {
		long seed = 77;
		ChunkPos c = GRID.getPotentialStructureChunk(seed, 0, 0);
		assertEquals(ChunkPos.pack(c.x(), c.z()), IslandZone.candidate(SHIPWRECK, Level.OVERWORLD, sep, seed, c.x() + 7, c.z() - 7));
		assertEquals(ChunkPos.pack(c.x(), c.z()), IslandZone.candidate(SHIPWRECK, Level.OVERWORLD, sep, seed, c.x(), c.z()));
		assertEquals(IslandZone.NONE, IslandZone.candidate(SHIPWRECK, Level.OVERWORLD, sep, seed, c.x() + 8, c.z()));
	}

	@Test
	void exempt() {
		long seed = 77;
		ChunkPos c = GRID.getPotentialStructureChunk(seed, 0, 0);
		assertEquals(IslandZone.NONE, IslandZone.candidate(SHIPWRECK, Level.NETHER, sep, seed, c.x(), c.z()));
		assertEquals(IslandZone.NONE, IslandZone.candidate(OTHER, Level.OVERWORLD, sep, seed, c.x(), c.z()));       // las de Heraldia van por UniqueSeparation
		assertEquals(IslandZone.NONE, IslandZone.candidate(Identifier.fromNamespaceAndPath("minecraft", "stronghold"),
				Level.OVERWORLD, sep, seed, c.x(), c.z()));
		UniqueSeparation noIsland = new UniqueSeparation("x", List.of(OTHER), java.util.Collections.singletonList(null),
				List.of(GRID), List.of(false), true, 1000);
		assertEquals(IslandZone.NONE, IslandZone.candidate(SHIPWRECK, Level.OVERWORLD, noIsland, seed, c.x(), c.z()));
	}

	@Test
	void winIsComputedOncePerCandidateAndSeed() {
		long seed = 123_456;
		ChunkPos c = GRID.getPotentialStructureChunk(seed, 0, 0);
		long cand = ChunkPos.pack(c.x(), c.z());
		AtomicInteger calls = new AtomicInteger();
		UniqueSeparation.Viability only = (j, x, z) -> {
			calls.incrementAndGet();
			return j == 1;    // solo la isla es viable: nadie la descarta
		};
		assertTrue(IslandZone.outcome(sep, cand, seed, only));
		int n = calls.get();
		assertTrue(IslandZone.outcome(sep, cand, seed, only));
		assertEquals(n, calls.get(), "la segunda consulta sale de la memoria");
		assertFalse(IslandZone.outcome(sep, cand, seed + 1, (j, x, z) -> false), "no viable: no sale");
	}

	@Test
	void footprintRings() {
		int[][] pts = IslandStructure.ring(new int[]{0, 10, 20}, new int[]{1, 8, 16});
		assertEquals(25, pts.length);
		assertEquals(0, pts[0][0]);
		assertEquals(0, pts[0][1]);
		for (int k = 1; k < pts.length; k++) {
			double r = Math.hypot(pts[k][0], pts[k][1]);
			assertTrue(Math.abs(r - (k <= 8 ? 10 : 20)) <= 0.75, "radio " + r);
		}
		assertEquals(10, pts[1][0]);       // el primer punto de cada anillo, al este
		assertEquals(0, pts[1][1]);
	}
}
