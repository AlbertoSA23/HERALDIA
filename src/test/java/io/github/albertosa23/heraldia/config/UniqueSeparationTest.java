package io.github.albertosa23.heraldia.config;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.mojang.serialization.JsonOps;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Map;
import java.util.List;
import java.util.stream.Stream;
import net.minecraft.resources.Identifier;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.levelgen.structure.placement.RandomSpreadStructurePlacement;
import net.minecraft.world.level.levelgen.structure.placement.RandomSpreadType;
import net.minecraft.SharedConstants;
import net.minecraft.server.Bootstrap;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/**
 * Simula la colocación de todas las estructuras únicas con el mismo código que el juego: las rejillas salen de los
 * structure_set generados (leídos con GridPlacement.CODEC, como el juego al cargar el datapack) y la decisión, de
 * UniqueSeparation.blocked, la misma llamada que hacen los mixins. Lo único simulado es la viabilidad de cada candidata
 * (bioma y terreno), con un hash determinista del ~35 %; el bioma real lo comprueba la prueba de humo con /locate.
 */
class UniqueSeparationTest {
	

	private record Cand(int type, int x, int z, boolean valid, boolean survives) {
	}

	/** La Atlántida: un solo ancla por semilla, como heraldia:mundial (siempre gana). */
	private static final class FixedAnchor extends RandomSpreadStructurePlacement {
		FixedAnchor() {
			super(4096, 0, RandomSpreadType.LINEAR, 0);
		}

		@Override
		public ChunkPos getPotentialStructureChunk(long seed, int chunkX, int chunkZ) {
			return anchor(seed);
		}

		static ChunkPos anchor(long seed) {
			long h = mix(seed ^ 0x5EEDL);
			return new ChunkPos((int) Math.floorMod(h, 1200L) - 600, (int) Math.floorMod(h >>> 20, 1200L) - 600);
		}
	}

	private static List<Identifier> ids;
	private static List<RandomSpreadStructurePlacement> grids;
	private static List<Boolean> always;

	@BeforeAll
	static void bootstrap() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	private static void loadSets() throws IOException {
		if (ids != null) {
			return;
		}
		List<Identifier> ids = new ArrayList<>();
		List<RandomSpreadStructurePlacement> grids = new ArrayList<>();
		List<Boolean> always = new ArrayList<>();
		Path dir = Path.of(System.getProperty("heraldia.generated"), "data", "heraldia", "worldgen", "structure_set", "unicas");
		try (Stream<Path> files = Files.list(dir)) {
			for (Path f : files.sorted().toList()) {
				JsonObject set = JsonParser.parseString(Files.readString(f)).getAsJsonObject();
				JsonObject placement = set.getAsJsonObject("placement");
				String type = placement.get("type").getAsString();
				Path estructura = dir.getParent().getParent().resolve("structure").resolve("unicas").resolve(f.getFileName());
				if (Files.isRegularFile(estructura) && JsonParser.parseString(Files.readString(estructura)).getAsJsonObject()
						.get("type").getAsString().equals("heraldia:dimension")) {
					continue; // del Nether o el End: no compiten con las del mundo principal (Dimensiones.posible)
				}
				ids.add(Identifier.parse(set.getAsJsonArray("structures").get(0).getAsJsonObject().get("structure").getAsString()));
				if (type.equals("heraldia:rejilla")) {
					grids.add(GridPlacement.CODEC.codec().parse(JsonOps.INSTANCE, placement).getOrThrow());
					always.add(false);
				} else {
					assertEquals("heraldia:mundial", type, "colocación propia sin simular en " + f);
					grids.add(new FixedAnchor());
					always.add(true);
				}
			}
		}
		assertTrue(ids.size() >= 15, "faltan structure_set de estructuras únicas: " + ids);
		UniqueSeparationTest.grids = grids;
		UniqueSeparationTest.always = always;
		UniqueSeparationTest.ids = ids;
	}

	private static List<RandomSpreadStructurePlacement> dense() {
		List<RandomSpreadStructurePlacement> out = new ArrayList<>();
		for (int i = 0; i < grids.size(); i++) {
			out.add(always.get(i) ? grids.get(i) : new RandomSpreadStructurePlacement(62, 47, RandomSpreadType.LINEAR, 1000 + 7919 * i));
		}
		return out;
	}

	/** Las rejillas de antes (separación 190 de 250 y origen común): solo para comparar en la salida de la prueba. */
	private static List<RandomSpreadStructurePlacement> legacy() {
		List<RandomSpreadStructurePlacement> out = new ArrayList<>();
		for (int i = 0; i < grids.size(); i++) {
			int s = grids.get(i).spacing();
			out.add(always.get(i) ? grids.get(i) : new RandomSpreadStructurePlacement(s, Math.round(s * 190F / 250), RandomSpreadType.LINEAR, 1000 + 7919 * i));
		}
		return out;
	}

	@Test
	void defaultGrids() throws IOException {
		loadSets();
		int n = HeraldiaConfig.get().getInt("unicas.distancia_minima.bloques");
		assertEquals(1000, n);
		for (int i = 0; i < grids.size(); i++) {
			if (!always.get(i)) {
				assertEquals((n + 15) / 16, grids.get(i).separation(), "separación interna de " + ids.get(i));
			}
		}
		double lost = simulate(grids, n, "rejillas por defecto", 300, 24_000);
		double before = simulate(legacy(), n, "antes: separación 190 y origen común", 300, 24_000);
		assertTrue(lost < 0.40 && lost < before - 0.3, "descartes: " + lost + " (antes " + before + ")");
	}

	@Test
	void denseGridsAndLargeDistance() throws IOException {
		loadSets();
		simulate(dense(), 1000, "rejillas de 1.000 bloques", 200, 6_000);
		simulate(dense(), 3000, "rejillas de 1.000 bloques", 40, 6_000);
	}

	@Test
	void disabledKeepsEverything() throws IOException {
		loadSets();
		UniqueSeparation off = new UniqueSeparation(this, ids, nulls(), dense(), always, false, 1000);
		for (int k = 0; k < 2000; k++) {
			assertTrue(!off.blocked(k % ids.size(), k, -k, k, (j, x, z) -> true));
		}
	}

	private static List<net.minecraft.world.level.levelgen.structure.Structure> nulls() {
		List<net.minecraft.world.level.levelgen.structure.Structure> out = new ArrayList<>();
		ids.forEach(i -> out.add(null));
		return out;
	}

	/** Fracción de candidatas viables descartadas. */
	private static double simulate(List<RandomSpreadStructurePlacement> placements, int n, String label, int seeds, int areaBlocks) {
		UniqueSeparation sep = new UniqueSeparation(label, ids, nulls(), placements, always, true, n);
		int area = areaBlocks / 16, bucket = (n + 15) / 16, margin = 2 * ((n + 15) / 16) + 8;
		long nSq = (long) n * n, totalNanos = 0, calls = 0, kept = 0, lost = 0, sameTypeClose = 0, validCalls[] = {0};
		for (int k = 0; k < seeds; k++) {
			long seed = mix(k * 0x9E3779B97F4A7C15L + 17);
			UniqueSeparation.Viability viability = (j, x, z) -> {
				validCalls[0]++;
				return Math.floorMod(mix(seed * 31 + j * 1_000_003L + ChunkPos.pack(x, z)), 100) < 35;
			};
			List<Cand> cands = new ArrayList<>();
			for (int i = 0; i < ids.size(); i++) {
				RandomSpreadStructurePlacement p = placements.get(i);
				if (always.get(i)) {
					ChunkPos a = p.getPotentialStructureChunk(seed, 0, 0);
					cands.add(new Cand(i, a.x(), a.z(), true, true));
					continue;
				}
				int s = p.spacing(), ox = UniqueSeparation.offsetX(p), oz = UniqueSeparation.offsetZ(p);
				for (int gx = Math.floorDiv(-area - margin - ox, s); gx <= Math.floorDiv(area + margin - ox, s); gx++) {
					for (int gz = Math.floorDiv(-area - margin - oz, s); gz <= Math.floorDiv(area + margin - oz, s); gz++) {
						ChunkPos c = p.getPotentialStructureChunk(seed, gx * s + ox, gz * s + oz);
						if (!p.applyAdditionalChunkRestrictions(c.x(), c.z(), seed)) {
							continue;
						}
						long t = System.nanoTime();
						boolean blocked = sep.blocked(i, c.x(), c.z(), seed, viability);
						totalNanos += System.nanoTime() - t;
						calls++;
						boolean valid = viability.valid(i, c.x(), c.z());
						cands.add(new Cand(i, c.x(), c.z(), valid, valid && !blocked));
					}
				}
			}
			Map<Long, List<Cand>> survivors = new HashMap<>(); // cubos de N x N: basta mirar los 3 x 3 vecinos
			for (Cand c : cands) {
				if (c.survives) {
					survivors.computeIfAbsent(ChunkPos.pack(Math.floorDiv(c.x, bucket), Math.floorDiv(c.z, bucket)), q -> new ArrayList<>()).add(c);
				}
			}
			for (Cand a : cands) {
				if (!a.valid || Math.abs(a.x) > area || Math.abs(a.z) > area) {
					continue;
				}
				boolean survivorNear = false;
				List<Cand> near = new ArrayList<>();
				for (int bx = -1; bx <= 1; bx++) {
					for (int bz = -1; bz <= 1; bz++) {
						near.addAll(survivors.getOrDefault(ChunkPos.pack(Math.floorDiv(a.x, bucket) + bx, Math.floorDiv(a.z, bucket) + bz), List.of()));
					}
				}
				for (Cand b : near) {
					if (b.type == a.type && b != a && dist2(a, b) <= 1024L * 1024 && placements.get(a.type) instanceof GridPlacement) {
						sameTypeClose++; // la separación interna de la rejilla debe impedirlo
					}
					if (b.type != a.type && b.survives && dist2(a, b) < nSq) {
						survivorNear = true;
						assertTrue(!a.survives, () -> label + ", semilla " + seed + ": " + ids.get(a.type) + " en " + a.x + "," + a.z
								+ " y " + ids.get(b.type) + " en " + b.x + "," + b.z + " a " + Math.sqrt(dist2(a, b)) + " bloques");
					}
				}
				if (a.survives) {
					kept++;
				} else {
					lost++;
					assertTrue(survivorNear, () -> label + ", semilla " + seed + ": " + ids.get(a.type) + " en " + a.x + "," + a.z
							+ " descartada sin ninguna superviviente a menos de " + n + " bloques");
				}
			}
		}
		double cells = seeds * Math.pow(2.0 * areaBlocks / 4000, 2); // casillas de 4.000 bloques (la separación por defecto)
		System.out.printf("Separación (%s, N = %d): %d semillas, %d supervivientes, %d descartadas (%.1f %%), %.2f supervivientes"
						+ " por casilla de 4.000 bloques (%.2f viables), %.2f µs por comprobación, %.2f viabilidades por candidata%n", label, n,
				seeds, kept, lost, 100.0 * lost / Math.max(1, kept + lost), kept / cells, (kept + lost) / cells,
				totalNanos / 1000.0 / calls, (double) (validCalls[0] - calls) / calls);
		assertTrue(kept > 0);
		assertEquals(0, sameTypeClose, label + ": dos del mismo tipo a menos de 1.024 bloques");
		return (double) lost / Math.max(1, kept + lost);
	}

	private static long dist2(Cand a, Cand b) {
		long dx = (a.x - (long) b.x) * 16, dz = (a.z - (long) b.z) * 16;
		return dx * dx + dz * dz;
	}

	private static long mix(long z) {
		z = (z ^ (z >>> 30)) * 0xBF58476D1CE4E5B9L;
		z = (z ^ (z >>> 27)) * 0x94D049BB133111EBL;
		return z ^ (z >>> 31);
	}
}
