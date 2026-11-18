package io.github.albertosa23.heraldia.update;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import io.github.albertosa23.heraldia.update.Detector.Kind;
import io.github.albertosa23.heraldia.update.Detector.Build;
import io.github.albertosa23.heraldia.update.Detector.Reason;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.junit.jupiter.api.Test;

/**
 * Detección de construcciones con casos sintéticos, el margen de 50 bloques exactos y la clasificación de los chunks
 * vírgenes (lógica pura de {@link Detector}, sin el juego).
 */
class DetectorTest {
	private static final int MIN_Y = -64;
	private static final Detector.Parameters P = Detector.Parameters.defaults(50);

	/** Un chunk generado del todo, con su InhabitedTime, bloques de jugador {x, y, z} del mundo e inicios. */
	static ChunkSummary chunk(int cx, int cz, long inhabited, List<int[]> player, Map<String, List<int[]>> structureStarts) {
		int[] j = new int[player.size()];
		for (int i = 0; i < j.length; i++) {
			int[] b = player.get(i);
			j[i] = ChunkSummary.pack(b[0] - cx * 16, b[1], b[2] - cz * 16, MIN_Y);
		}
		return new ChunkSummary(cx, cz, true, inhabited, MIN_Y, j, structureStarts, new int[0], new String[0]);
	}

	static ChunkSummary empty(int cx, int cz) {
		return chunk(cx, cz, 0, List.of(), Map.of());
	}

	/** Una zona de 21 × 21 chunks (−10..10) vacía. */
	static List<ChunkSummary> world() {
		List<ChunkSummary> out = new ArrayList<>();
		for (int cx = -10; cx <= 10; cx++) {
			for (int cz = -10; cz <= 10; cz++) {
				out.add(empty(cx, cz));
			}
		}
		return out;
	}

	static void put(List<ChunkSummary> m, ChunkSummary c) {
		m.removeIf(r -> r.cx() == c.cx() && r.cz() == c.cz());
		m.add(c);
	}

	@Test
	void marginOfExactlyFiftyBlocks() {
		Build house = Build.point(0, 0, Reason.BLOCKS);
		// chunk 3 (x 48..63): su borde está a 48 bloques -> protegido; chunk 4 (x 64..79): a 64 -> libre
		assertTrue(Detector.near(house, 3, 0, 50));
		assertFalse(Detector.near(house, 4, 0, 50));
		// el borde exacto: un punto a 50 bloques del chunk cuenta (≤ 50); a 51 no
		assertTrue(Detector.near(Build.point(-2, 5, Reason.BLOCKS), 3, 0, 50));    // 48 - (-2) = 50
		assertFalse(Detector.near(Build.point(-3, 5, Reason.BLOCKS), 3, 0, 50));   // 51
		// en diagonal se mide en línea recta: (48, 48) está a 67,9 del (0, 0)
		assertFalse(Detector.near(house, 3, 3, 50));
		assertTrue(Detector.near(house, 2, 2, 50));                                          // (32, 32): 45,3
		// hacia el lado negativo, igual: el chunk −4 acaba en x = −49
		assertTrue(Detector.near(house, -4, 0, 50));
		assertFalse(Detector.near(house, -5, 0, 50));                                        // acaba en −65
	}

	@Test
	void noProtectedChunkBlockOutsideMarginOrViceVersa() {
		Build house = new Build(100, 200, 110, 215, Reason.BLOCKS);
		Set<Long> prot = Detector.protectedChunks(List.of(house), 50);
		for (int cx = 0; cx < 20; cx++) {
			for (int cz = 5; cz < 25; cz++) {
				double min = Double.MAX_VALUE;
				for (int x = cx * 16; x < cx * 16 + 16; x++) {
					for (int z = cz * 16; z < cz * 16 + 16; z++) {
						min = Math.min(min, Detector.distance(house.minX(), house.minZ(), house.maxX(), house.maxZ(), x, z, x, z));
					}
				}
				assertEquals(min <= 50, prot.contains(ChunkSummary.key(cx, cz)), "chunk " + cx + "," + cz + " a " + min);
			}
		}
	}

	@Test
	void aHouseProtectsItsMarginRestIsPristine() {
		List<ChunkSummary> m = world();
		put(m, chunk(0, 0, 0, List.of(new int[] {5, 70, 5}, new int[] {6, 70, 5}), Map.of()));   // cama y cofre en (5, 5)
		Detector.Result r = Detector.classify(m, Map.of(), List.of(), P);
		assertEquals(Kind.BUILD, r.clazz(0, 0));
		assertEquals(Kind.PROTECTED, r.clazz(3, 0));          // x 48 - 6 = 42
		assertEquals(Kind.PROTECTED, r.clazz(-3, 0));         // 5 - (-33) = 38
		assertEquals(Kind.NORMAL, r.clazz(4, 0));             // a 58 bloques, pero junto a un chunk protegido: no se regenera
		assertEquals(Kind.PRISTINE, r.clazz(5, 0));
		assertEquals(Kind.PRISTINE, r.clazz(10, 10));
		assertEquals(2, r.byReason().get(Reason.BLOCKS));
		// nada virgen a 50 bloques o menos de la casa, ni junto a un chunk protegido (sus rasgos escribirían en él)
		r.classes().forEach((k, c) -> {
			if (c == Kind.PRISTINE) {
				int cx = ChunkSummary.cx(k), cz = ChunkSummary.cz(k);
				assertFalse(Detector.near(Build.point(5, 5, Reason.BLOCKS), cx, cz, 50));
				for (int dx = -1; dx <= 1; dx++) {
					for (int dz = -1; dz <= 1; dz++) {
						assertFalse(r.protectedChunks().contains(ChunkSummary.key(cx + dx, cz + dz)), cx + "," + cz);
					}
				}
			}
		});
	}

	@Test
	void blocksInsideAStructureAreNotBuilds() {
		List<ChunkSummary> m = world();
		int[] piece = {0, 60, 0, 40, 80, 40};                    // una aldea con camas y cofres dentro
		put(m, chunk(0, 0, 0, List.of(new int[] {5, 70, 5}), Map.of("minecraft:village_plains", List.of(piece))));
		put(m, chunk(1, 1, 0, List.of(new int[] {20, 70, 20}), Map.of()));          // dentro de la pieza (de otro chunk)
		Detector.Result r = Detector.classify(m, Map.of(), List.of(), P);
		assertEquals(Kind.PRISTINE, r.clazz(0, 0));
		assertEquals(Kind.PRISTINE, r.clazz(1, 1));
		assertTrue(r.builds().isEmpty());
		// fuera de la pieza (y = 90), sí
		put(m, chunk(1, 1, 0, List.of(new int[] {20, 90, 20}), Map.of()));
		assertEquals(Kind.BUILD, Detector.classify(m, Map.of(), List.of(), P).clazz(1, 1));
	}

	@Test
	void ambiguousBlocksOnlyCountWithPlayersNearby() {
		List<ChunkSummary> m = world();
		// tablones de los puentes de una mina abandonada (fuera de su caja) o un cofre de mazmorra, sin nadie que haya pasado
		int[] board = {ChunkSummary.pack(3, 20, 3, MIN_Y) | ChunkSummary.AMBIGUOUS};
		put(m, new ChunkSummary(6, 6, true, 0, MIN_Y, board, Map.of(), new int[0], new String[0]));
		assertEquals(Kind.PRISTINE, Detector.classify(m, Map.of(), List.of(), P).clazz(6, 6));
		// el mismo bloque donde ha estado un jugador: construcción
		put(m, new ChunkSummary(6, 6, true, 40, MIN_Y, board, Map.of(), new int[0], new String[0]));
		assertEquals(Kind.BUILD, Detector.classify(m, Map.of(), List.of(), P).clazz(6, 6));
		assertTrue(PlayerBlocks.ambiguous("minecraft:oak_planks") && PlayerBlocks.ambiguous("minecraft:chest"));
		assertFalse(PlayerBlocks.ambiguous("minecraft:red_bed") || PlayerBlocks.ambiguous("minecraft:crafting_table"));
		assertTrue(PlayerBlocks.playerSource("minecraft:red_bed") && PlayerBlocks.playerSource("minecraft:oak_sign"));
		assertFalse(PlayerBlocks.playerSource("minecraft:stone") || PlayerBlocks.playerSource("minecraft:oak_log")
				|| PlayerBlocks.playerSource("othermod:fancy_bed"));
		assertTrue(PlayerBlocks.naturalTop("minecraft:oak_leaves") && !PlayerBlocks.naturalTop("minecraft:cobblestone"));
	}

	@Test
	void inhabitedTimeDecidesPristineAndBase() {
		List<ChunkSummary> m = world();
		put(m, chunk(5, 5, 1199, List.of(), Map.of()));
		put(m, chunk(6, 6, 1200, List.of(), Map.of()));
		put(m, chunk(-8, -8, 72_000, List.of(), Map.of()));      // una hora de jugadores: cuenta como construcción
		Detector.Result r = Detector.classify(m, Map.of(), List.of(), P);
		assertEquals(Kind.PRISTINE, r.clazz(5, 5));
		assertEquals(Kind.NORMAL, r.clazz(6, 6));
		assertEquals(Kind.BUILD, r.clazz(-8, -8));
		assertEquals(Kind.PROTECTED, r.clazz(-5, -8));            // a 33 bloques del chunk habitado
	}

	@Test
	void regenerationDifferencesCountFromThreeColumns() {
		List<ChunkSummary> m = world();
		long k = ChunkSummary.key(2, 2);
		Map<Long, List<int[]>> two = Map.of(k, List.of(new int[] {34, 34}, new int[] {38, 34}));
		assertEquals(Kind.PRISTINE, Detector.classify(m, two, List.of(), P).clazz(2, 2));
		Map<Long, List<int[]>> three = Map.of(k, List.of(new int[] {34, 34}, new int[] {38, 34}, new int[] {42, 34}));
		Detector.Result r = Detector.classify(m, three, List.of(), P);
		assertEquals(Kind.BUILD, r.clazz(2, 2));
		assertEquals(3, r.byReason().get(Reason.DIFFERENCE));
	}

	@Test
	void spawnBedsAndPlayersProtect() {
		List<ChunkSummary> m = world();
		List<Build> extra = List.of(Build.point(0, 0, Reason.SPAWN), Build.point(150, 150, Reason.RESPAWN),
				Build.point(-150, 100, Reason.PLAYER));
		Detector.Result r = Detector.classify(m, Map.of(), extra, P);
		assertEquals(Kind.BUILD, r.clazz(0, 0));
		assertEquals(Kind.BUILD, r.clazz(9, 9));
		assertEquals(Kind.BUILD, r.clazz(-10, 6));
		assertEquals(Kind.PROTECTED, r.clazz(7, 9));
		assertEquals(Kind.PRISTINE, r.clazz(5, -5));
	}

	@Test
	void halfGeneratedChunkIsNotPristine() {
		List<ChunkSummary> m = world();
		put(m, new ChunkSummary(8, 8, false, 0, MIN_Y, new int[0], Map.of(), new int[0], new String[0]));
		assertEquals(Kind.INCOMPLETE, Detector.classify(m, Map.of(), List.of(), P).clazz(8, 8));
	}

	@Test
	void anotherConfigurableMargin() {
		Build house = Build.point(0, 0, Reason.BLOCKS);
		assertFalse(Detector.protectedChunks(List.of(house), 16).contains(ChunkSummary.key(2, 0)));   // 32 > 16
		assertTrue(Detector.protectedChunks(List.of(house), 100).contains(ChunkSummary.key(6, 0)));   // 96 ≤ 100
	}

	@Test
	void doesNotRegenerateWhatWouldCutAStructure() {
		Set<Long> generated = new HashSet<>(), pristine = new HashSet<>();
		for (int cx = 0; cx < 6; cx++) {
			for (int cz = 0; cz < 6; cz++) {
				generated.add(ChunkSummary.key(cx, cz));
				pristine.add(ChunkSummary.key(cx, cz));
			}
		}
		pristine.remove(ChunkSummary.key(3, 0));                  // uno que se queda (no virgen)
		Map<Long, List<int[]>> req = new HashMap<>();
		req.put(ChunkSummary.key(2, 0), List.of(new int[] {32, 0, 0, 63, 50, 15}));   // pisaría el chunk 3,0
		req.put(ChunkSummary.key(0, 4), List.of(new int[] {0, 0, 64, 31, 50, 79}));   // cae en vírgenes: vale
		req.put(ChunkSummary.key(5, 5), List.of(new int[] {80, 0, 80, 120, 50, 120})); // sale a chunks sin generar: vale
		req.put(ChunkSummary.key(1, 0), List.of(new int[] {16, 0, 0, 47, 50, 15}));   // pisa el 2,0, que no se borra
		Set<Long> r = Detector.regenerable(pristine, generated, req);
		assertFalse(r.contains(ChunkSummary.key(2, 0)));
		assertFalse(r.contains(ChunkSummary.key(1, 0)));          // en cadena
		assertTrue(r.contains(ChunkSummary.key(0, 4)));
		assertTrue(r.contains(ChunkSummary.key(5, 5)));
		assertTrue(r.contains(ChunkSummary.key(4, 4)));
		assertEquals(pristine.size() - 2, r.size());
	}

	@Test
	void newStructureOnlyPlacedFarFromBuilds() {
		List<ChunkSummary> m = world();
		put(m, chunk(0, 0, 0, List.of(new int[] {5, 70, 5}), Map.of()));
		for (int cx = 5; cx <= 10; cx++) {
			put(m, chunk(cx, 0, 5000, List.of(), Map.of()));     // normales (habitados un poco)
		}
		put(m, chunk(8, 3, 0, List.of(), Map.of("minecraft:pillager_outpost", List.of(new int[] {130, 60, 50, 140, 80, 60}))));
		Detector.Result r = Detector.classify(m, Map.of(), List.of(), P);
		Map<Long, List<int[]>> pieces = Detector.piecesByChunk(m);
		List<int[]> chosen = new ArrayList<>();
		// a 5 chunks de la casa (80 bloques) y su caja de 2 × 2 chunks: lejos del margen
		assertTrue(Detector.placeable(new int[] {80, 60, 0, 111, 80, 31}, ChunkSummary.key(5, 0), r, Set.of(), pieces, chosen));
		// una caja que se acerca a la casa (x desde 40): no
		assertFalse(Detector.placeable(new int[] {40, 60, 0, 111, 80, 31}, ChunkSummary.key(5, 0), r, Set.of(), pieces, chosen));
		// encima de otra estructura guardada: no
		assertFalse(Detector.placeable(new int[] {120, 60, 40, 150, 80, 70}, ChunkSummary.key(8, 0), r, Set.of(), pieces, chosen));
		// encima de una ya elegida: no
		chosen.add(new int[] {80, 60, 0, 111, 80, 31});
		assertFalse(Detector.placeable(new int[] {100, 60, 0, 130, 80, 20}, ChunkSummary.key(6, 0), r, Set.of(), pieces, chosen));
		// en un chunk que se va a regenerar: no
		assertFalse(Detector.placeable(new int[] {160, 60, 0, 175, 80, 15}, ChunkSummary.key(10, 0), r,
				Set.of(ChunkSummary.key(10, 0)), pieces, List.of()));
	}
}
