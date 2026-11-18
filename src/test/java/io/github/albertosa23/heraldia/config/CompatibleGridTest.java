package io.github.albertosa23.heraldia.config;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.mojang.serialization.JsonOps;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Stream;
import net.minecraft.SharedConstants;
import net.minecraft.resources.Identifier;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.levelgen.structure.Structure;
import net.minecraft.world.level.levelgen.structure.placement.RandomSpreadStructurePlacement;
import net.minecraft.world.level.levelgen.structure.placement.RandomSpreadType;
import org.jspecify.annotations.Nullable;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * unicas.rejilla_compatible: the uniques that already existed in 0.1.0 (main branch) give, for the same seed and
 * configuration, exactly the same candidates and the same minimum-distance discards as back then. The
 * reference is a copy of the 0.1.0 algorithm (GridPlacement and UniqueSeparation from main, commit 3248f74): a
 * random_spread grid with the datapack's separation scaled (190/250), a common origin, and the rank discard among the uniques
 * of back then plus Atlantis. What is tested here comes from the code in use: the generated structure_sets read with
 * GridPlacement.CODEC and UniqueSeparation.blocked, the mixins' call. The viability (biome and terrain) is simulated with
 * a hash per id, the same for both; the real biome is checked by tools/smoke/compatible_grid.py against main's .jar.
 */
class CompatibleGridTest {
	/** 0.1.0 uniques with a grid (Atlantis has its own placement and already always won back then). */
	private static final Set<String> MAIN = Set.of("acueducto", "castillo", "catedral", "ciudadela", "coliseo", "faro", "fortaleza_hielo",
			"galeon", "mansion", "monasterio", "observatorio", "palacio", "piramide", "torre_mago");
	private static final Identifier ATLANTIS = Identifier.parse("heraldia:unicas/atlantida");

	@TempDir
	static Path dir;

	@BeforeAll
	static void bootstrap() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	@AfterAll
	static void restore() {
		HeraldiaConfig.load(null); // the default one, for the other tests
	}

	private record Sets(List<Identifier> ids, List<RandomSpreadStructurePlacement> placements, List<Boolean> always,
						List<JsonObject> json) {
	}

	private static Sets load(String config) throws IOException {
		Path file = dir.resolve("heraldia-" + Integer.toHexString(config.hashCode()) + ".json");
		Files.writeString(file, config);
		HeraldiaConfig.load(file);
		List<Identifier> ids = new ArrayList<>();
		List<RandomSpreadStructurePlacement> placements = new ArrayList<>();
		List<Boolean> always = new ArrayList<>();
		List<JsonObject> json = new ArrayList<>();
		Path sets = Path.of(System.getProperty("heraldia.generated"), "data", "heraldia", "worldgen", "structure_set", "unicas");
		try (Stream<Path> files = Files.list(sets)) {
			for (Path f : files.sorted().toList()) {
				JsonObject set = JsonParser.parseString(Files.readString(f)).getAsJsonObject();
				JsonObject placement = set.getAsJsonObject("placement");
				ids.add(Identifier.parse(set.getAsJsonArray("structures").get(0).getAsJsonObject().get("structure").getAsString()));
				json.add(placement);
				if (placement.get("type").getAsString().equals("heraldia:rejilla")) {
					placements.add(GridPlacement.CODEC.codec().parse(JsonOps.INSTANCE, placement).getOrThrow());
					always.add(false);
				} else {
					placements.add(new FixedAnchor());
					always.add(true);
				}
			}
		}
		return new Sets(ids, placements, always, json);
	}

	private static String sid(Identifier id) {
		return id.getPath().substring("unicas/".length());
	}

	@Test
	void previousVersionOnesMarked() throws IOException {
		Sets s = load("{\"unicas\": {\"rejilla_compatible\": true}}");
		Set<String> marked = new java.util.HashSet<>();
		for (int i = 0; i < s.ids.size(); i++) {
			if (s.json.get(i).has("rejilla_antigua")) {
				marked.add(sid(s.ids.get(i)));
				assertTrue(((GridPlacement) s.placements.get(i)).legacy(), s.ids.get(i) + " sin la rejilla antigua");
			} else if (s.placements.get(i) instanceof GridPlacement g) {
				assertFalse(g.legacy(), s.ids.get(i) + ": una única nueva no puede usar la rejilla antigua");
			}
		}
		assertEquals(MAIN, marked, "las únicas de la 0.1.0 son las marcadas con rejilla_antigua");
		for (String fresh : List.of("salon_jarl", "santuario", "laboratorio_micelio", "mina_perdida", "isla_corsario")) {
			assertTrue(s.ids.contains(Identifier.parse("heraldia:unicas/" + fresh)), "falta " + fresh);
		}
		s = load("{}");
		s.placements.forEach(p -> assertFalse(p instanceof GridPlacement g && g.legacy(), "por defecto, rejilla nueva"));
	}

	@Test
	void sameCandidatesAndDiscardsAsPreviousVersion() throws IOException {
		compare("{\"unicas\": {\"rejilla_compatible\": true}}", 40, 24_000);
		// Another separation and another minimum distance: the scaled ratio and the discard's reach also match.
		compare("{\"unicas\": {\"rejilla_compatible\": true, \"distancia_minima\": {\"bloques\": 1800},"
				+ " \"castillo\": {\"separacion_bloques\": 1000}, \"monasterio\": {\"separacion_bloques\": 1300},"
				+ " \"faro\": {\"separacion_bloques\": 2000}, \"palacio\": {\"activada\": false}}}", 20, 12_000);
		compare("{\"unicas\": {\"rejilla_compatible\": true, \"distancia_minima\": {\"activada\": false}}}", 10, 12_000);
	}

	@Test
	void withoutTheOptionTheGridDiffers() throws IOException {
		Sets s = load("{}");
		HeraldiaConfig cfg = HeraldiaConfig.get();
		int differ = 0, total = 0;
		for (int i = 0; i < s.ids.size(); i++) {
			if (!MAIN.contains(sid(s.ids.get(i)))) {
				continue;
			}
			RandomSpreadStructurePlacement now = s.placements.get(i), old = mainGrid(s.json.get(i), cfg);
			for (int g = -3; g <= 3; g++) {
				total++;
				ChunkPos a = now.getPotentialStructureChunk(7, g * now.spacing() + UniqueSeparation.offsetX(now), -g * now.spacing()
						+ UniqueSeparation.offsetZ(now));
				ChunkPos b = old.getPotentialStructureChunk(7, g * old.spacing(), -g * old.spacing());
				differ += a.equals(b) ? 0 : 1;
			}
		}
		assertTrue(differ > total * 9 / 10, "con la opción desactivada casi todas las candidatas cambian: " + differ + " de " + total);
	}

	/** Grid of a unique in 0.1.0 (main's GridPlacement.create): scaled separation, common origin, no biome. */
	private static MainGrid mainGrid(JsonObject placement, HeraldiaConfig cfg) {
		String key = placement.get("grupo").getAsString().replace('/', '.');
		int spacing = placement.get("spacing").getAsInt(), separation = placement.get("separation").getAsInt();
		int sp = Math.clamp(Math.round(cfg.getInt(key + ".separacion_bloques") / 16.0F), 2, 4096);
		int sep = Math.clamp(Math.round((float) sp * separation / spacing), 0, sp - 1);
		return new MainGrid(sp, sep, placement.get("salt").getAsInt(), cfg.getBool(key + ".activada"));
	}

	private static final class MainGrid extends RandomSpreadStructurePlacement {
		private final boolean enabled;

		MainGrid(int spacing, int separation, int salt, boolean enabled) {
			super(spacing, separation, RandomSpreadType.LINEAR, salt);
			this.enabled = enabled;
		}

		@Override
		public boolean applyAdditionalChunkRestrictions(int chunkX, int chunkZ, long seed) {
			return enabled && super.applyAdditionalChunkRestrictions(chunkX, chunkZ, seed);
		}
	}

	private static void compare(String config, int seeds, int areaBlocks) throws IOException {
		Sets s = load(config);
		HeraldiaConfig cfg = HeraldiaConfig.get();
		boolean on = cfg.getBool("unicas.distancia_minima.activada");
		int n = cfg.getInt("unicas.distancia_minima.bloques");
		UniqueSeparation now = new UniqueSeparation("ahora", s.ids, nulls(s.ids.size()), s.placements, s.always, on, n);
		// 0.1.0: only its uniques (and Atlantis), in the same relative order.
		List<Identifier> oldIds = new ArrayList<>();
		List<RandomSpreadStructurePlacement> oldPlacements = new ArrayList<>();
		List<Boolean> oldAlways = new ArrayList<>();
		for (int i = 0; i < s.ids.size(); i++) {
			if (s.ids.get(i).equals(ATLANTIS) || MAIN.contains(sid(s.ids.get(i)))) {
				oldIds.add(s.ids.get(i));
				oldPlacements.add(s.always.get(i) ? s.placements.get(i) : mainGrid(s.json.get(i), cfg));
				oldAlways.add(s.always.get(i));
			}
		}
		MainSeparation main = new MainSeparation(oldIds, oldPlacements, oldAlways, on, n);
		int area = areaBlocks / 16;
		long candidates = 0, discarded = 0, newSurvivors = 0, newBlockedByOld = 0;
		for (int k = 0; k < seeds; k++) {
			long seed = mix(k * 0x9E3779B97F4A7C15L + 99);
			UniqueSeparation.Viability vNow = (j, x, z) -> viable(seed, s.ids.get(j), x, z);
			UniqueSeparation.Viability vMain = (j, x, z) -> viable(seed, oldIds.get(j), x, z);
			List<long[]> oldSurvivors = new ArrayList<>();
			for (int m = 0; m < oldIds.size(); m++) {
				if (oldAlways.get(m)) {
					continue;
				}
				Identifier id = oldIds.get(m);
				int i = s.ids.indexOf(id);
				RandomSpreadStructurePlacement p = s.placements.get(i), q = oldPlacements.get(m);
				assertEquals(q.spacing(), p.spacing(), id + ": spacing");
				assertEquals(q.separation(), p.separation(), id + ": separación interna");
				assertEquals(0, UniqueSeparation.offsetX(p) | UniqueSeparation.offsetZ(p), id + ": origen desplazado");
				int sp = p.spacing();
				for (int gx = Math.floorDiv(-area, sp); gx <= Math.floorDiv(area, sp); gx++) {
					for (int gz = Math.floorDiv(-area, sp); gz <= Math.floorDiv(area, sp); gz++) {
						ChunkPos a = p.getPotentialStructureChunk(seed, gx * sp, gz * sp), b = q.getPotentialStructureChunk(seed, gx * sp, gz * sp);
						String where = id + ", semilla " + seed + ", casilla " + gx + "," + gz;
						assertEquals(b, a, where + ": candidata");
						// any chunk of the cell gives the same candidate (that is how /locate and generation walk it)
						assertEquals(b, p.getPotentialStructureChunk(seed, gx * sp + sp - 1, gz * sp + sp / 2), where + ": candidata desde otro chunk");
						boolean allowed = q.applyAdditionalChunkRestrictions(b.x(), b.z(), seed);
						assertEquals(allowed, p.applyAdditionalChunkRestrictions(a.x(), a.z(), seed), where + ": casilla permitida");
						if (!allowed) {
							continue;
						}
						candidates++;
						boolean blockedMain = main.blocked(m, b.x(), b.z(), seed, vMain);
						assertEquals(blockedMain, now.blocked(i, a.x(), a.z(), seed, vNow), where + ": descarte por distancia mínima");
						discarded += blockedMain ? 1 : 0;
						if (!blockedMain && viable(seed, id, b.x(), b.z())) {
							oldSurvivors.add(new long[]{b.x(), b.z()});
						}
					}
				}
			}
			// The new ones (new grid) never spawn within N of an old one that survives.
			for (int i = 0; i < s.ids.size(); i++) {
				if (s.always.get(i) || MAIN.contains(sid(s.ids.get(i)))) {
					continue;
				}
				RandomSpreadStructurePlacement p = s.placements.get(i);
				int sp = p.spacing(), ox = UniqueSeparation.offsetX(p), oz = UniqueSeparation.offsetZ(p);
				for (int gx = Math.floorDiv(-area - ox, sp); gx <= Math.floorDiv(area - ox, sp); gx++) {
					for (int gz = Math.floorDiv(-area - oz, sp); gz <= Math.floorDiv(area - oz, sp); gz++) {
						ChunkPos c = p.getPotentialStructureChunk(seed, gx * sp + ox, gz * sp + oz);
						if (!p.applyAdditionalChunkRestrictions(c.x(), c.z(), seed) || !viable(seed, s.ids.get(i), c.x(), c.z())) {
							continue;
						}
						boolean nearOld = false;
						for (long[] o : oldSurvivors) {
							long dx = (o[0] - c.x()) * 16, dz = (o[1] - c.z()) * 16;
							nearOld |= dx * dx + dz * dz < (long) n * n;
						}
						boolean blocked = now.blocked(i, c.x(), c.z(), seed, vNow);
						if (on && nearOld) {
							newBlockedByOld++;
							assertTrue(blocked, s.ids.get(i) + " en " + c + " sale a menos de " + n + " de una antigua que sobrevive (semilla " + seed + ")");
						}
						newSurvivors += blocked ? 0 : 1;
					}
				}
			}
		}
		System.out.printf("Rejilla compatible (%s): %d candidatas antiguas iguales a la 0.1.0 (%d descartadas), %d nuevas descartadas"
				+ " por una antigua, %d nuevas supervivientes%n", config, candidates, discarded, newBlockedByOld, newSurvivors);
		assertTrue(candidates > 1000 && newSurvivors > 0);
		assertTrue(!on || discarded > 0 && newBlockedByOld > 0, "la prueba no llegó a ejercitar el descarte");
	}

	private static boolean viable(long seed, Identifier id, int x, int z) {
		return Math.floorMod(mix(seed * 31 + id.toString().hashCode() * 1_000_003L + ChunkPos.pack(x, z)), 100) < 35;
	}

	private static List<@Nullable Structure> nulls(int n) {
		List<@Nullable Structure> out = new ArrayList<>();
		for (int i = 0; i < n; i++) {
			out.add(null);
		}
		return out;
	}

	/** Atlantis: a single anchor per seed, like heraldia:mundial (always wins). */
	private static final class FixedAnchor extends RandomSpreadStructurePlacement {
		FixedAnchor() {
			super(4096, 0, RandomSpreadType.LINEAR, 0);
		}

		@Override
		public ChunkPos getPotentialStructureChunk(long seed, int chunkX, int chunkZ) {
			long h = mix(seed ^ 0x5EEDL);
			return new ChunkPos((int) Math.floorMod(h, 1200L) - 600, (int) Math.floorMod(h >>> 20, 1200L) - 600);
		}
	}

	/**
	 * Literal copy of UniqueSeparation's discard in 0.1.0 (main, commit 3248f74): no tiers or offsets. Not to be
	 * touched: it is the reference of what was already generated in that version's worlds.
	 */
	private static final class MainSeparation {
		private final Identifier[] ids;
		private final RandomSpreadStructurePlacement[] placements;
		private final long[] salts;
		private final boolean[] always;
		private final boolean enabled;
		private final int reachChunks;
		private final long distanceSq;

		MainSeparation(List<Identifier> ids, List<RandomSpreadStructurePlacement> placements, List<Boolean> always, boolean enabled, int distance) {
			int n = ids.size();
			this.ids = ids.toArray(new Identifier[0]);
			this.placements = placements.toArray(new RandomSpreadStructurePlacement[0]);
			this.salts = new long[n];
			this.always = new boolean[n];
			for (int i = 0; i < n; i++) {
				this.salts[i] = mix(this.ids[i].toString().hashCode() * 0x9E3779B97F4A7C15L);
				this.always[i] = always.get(i);
			}
			this.enabled = enabled && distance > 0;
			this.reachChunks = (distance + 15) / 16;
			this.distanceSq = (long) distance * distance;
		}

		boolean blocked(int i, int chunkX, int chunkZ, long seed, UniqueSeparation.Viability viability) {
			return enabled && !always[i] && blockedBy(i, chunkX, chunkZ, rank(i, chunkX, chunkZ, seed), seed, viability, null);
		}

		private boolean blockedBy(int i, int cx, int cz, long rank, long seed, UniqueSeparation.Viability viability, @Nullable Map<Long, Boolean> memo) {
			List<long[]> near = null;
			for (int j = 0; j < ids.length; j++) {
				if (j == i) {
					continue;
				}
				RandomSpreadStructurePlacement p = placements[j];
				int s = p.spacing();
				for (int gx = Math.floorDiv(cx - reachChunks, s), gxMax = Math.floorDiv(cx + reachChunks, s); gx <= gxMax; gx++) {
					for (int gz = Math.floorDiv(cz - reachChunks, s), gzMax = Math.floorDiv(cz + reachChunks, s); gz <= gzMax; gz++) {
						ChunkPos c = p.getPotentialStructureChunk(seed, gx * s, gz * s);
						long dx = (c.x() - (long) cx) * 16, dz = (c.z() - (long) cz) * 16;
						if (dx * dx + dz * dz >= distanceSq) {
							continue;
						}
						long r = rank(j, c.x(), c.z(), seed);
						if (r < rank || r == rank && j < i || !p.applyAdditionalChunkRestrictions(c.x(), c.z(), seed)) {
							continue;
						}
						if (always[j]) {
							return true;
						}
						if (near == null) {
							near = new ArrayList<>(4);
						}
						near.add(new long[]{j, c.x(), c.z(), r});
					}
				}
			}
			if (near == null) {
				return false;
			}
			near.sort((a, b) -> Long.compare(b[3], a[3]));
			if (memo == null) {
				memo = new HashMap<>();
			}
			for (long[] n : near) {
				int j = (int) n[0], x = (int) n[1], z = (int) n[2];
				long key = ChunkPos.pack(x, z) * 31 + j;
				Boolean survives = memo.get(key);
				if (survives == null) {
					survives = viability.valid(j, x, z) && !blockedBy(j, x, z, n[3], seed, viability, memo);
					memo.put(key, survives);
				}
				if (survives) {
					return true;
				}
			}
			return false;
		}

		long rank(int i, int chunkX, int chunkZ, long seed) {
			return always[i] ? Long.MAX_VALUE : mix(seed ^ salts[i] ^ mix(ChunkPos.pack(chunkX, chunkZ)));
		}
	}

	private static long mix(long z) { // SplitMix64 finalizer
		z = (z ^ (z >>> 30)) * 0xBF58476D1CE4E5B9L;
		z = (z ^ (z >>> 27)) * 0x94D049BB133111EBL;
		return z ^ (z >>> 31);
	}
}
