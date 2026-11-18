package io.github.albertosa23.heraldia.mines;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonParser;
import com.mojang.serialization.JsonOps;
import io.github.albertosa23.heraldia.common.MediumStructures;
import io.github.albertosa23.heraldia.config.GridPlacement;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import net.minecraft.SharedConstants;
import net.minecraft.resources.Identifier;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.levelgen.structure.Structure;
import net.minecraft.world.level.levelgen.structure.placement.RandomSpreadStructurePlacement;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * Mine entrances without a server: the heraldia:rejilla grid of the group minas/&lt;size&gt; (activation and separation from the
 * configuration, proportional between sizes) and the rule of {@link Mines} with everything injected: no survivor in
 * the zone of a village or a unique nor next to a medium that wins, two of different sizes never within the minimum
 * distance, every one discarded by another mine has a survivor nearby, and the result does not depend on the order; and
 * {@link MediumStructures#near} (the nearest medium that wins, the one that makes a mine yield).
 */
class MinesTest {
	private static final String[] SIZES = {"pequena", "mediana", "grande"};
	private static final int[] SPACING = {48, 72, 120};

	@TempDir
	Path dir;

	@BeforeAll
	static void bootstrap() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	@AfterEach
	void restore() {
		HeraldiaConfig.load(null);
	}

	private void config(String json) throws IOException {
		Path file = dir.resolve("heraldia.json");
		Files.writeString(file, json);
		HeraldiaConfig.load(file);
	}

	static GridPlacement grid(String group, int spacing, int salt) {
		return GridPlacement.CODEC.codec().parse(JsonOps.INSTANCE, JsonParser.parseString(
				"{\"grupo\": \"" + group + "\", \"spacing\": " + spacing + ", \"separation\": " + spacing / 3
						+ ", \"salt\": " + salt + "}")).getOrThrow();
	}

	private static Mines mines(int distance) {
		List<Identifier> types = new ArrayList<>();
		List<List<Identifier>> ids = new ArrayList<>();
		List<List<Structure>> styles = new ArrayList<>();
		List<RandomSpreadStructurePlacement> placements = new ArrayList<>();
		for (int i = 0; i < SIZES.length; i++) {
			types.add(Identifier.fromNamespaceAndPath("heraldia", "minas/" + SIZES[i]));
			ids.add(List.of(Identifier.fromNamespaceAndPath("heraldia", "minas/" + SIZES[i] + "/montana/a")));
			styles.add(List.of());
			placements.add(grid("minas/" + SIZES[i], SPACING[i], 1907261101 + i));
		}
		return new Mines(new Object(), types, ids, styles, placements, distance);
	}

	@Test
	void gridScalesTheThreeSizesWithTheOption() throws IOException {
		config("{}");
		for (int i = 0; i < 3; i++) {
			GridPlacement g = grid("minas/" + SIZES[i], SPACING[i], 5);
			assertEquals(SPACING[i], g.spacing(), "por defecto, la del datapack");
			assertEquals(12, g.separation(), "la interna: medianas.distancia_minima.bloques (192)");
			assertTrue(g.offsetX() >= 0 && g.offsetX() < g.spacing(), "origen desplazado por la sal");
		}
		config("{\"minas\": {\"entradas\": {\"separacion_bloques\": 1536}}, \"medianas\": {\"distancia_minima\": {\"bloques\": 320}}}");
		assertEquals(96, grid("minas/pequena", 48, 5).spacing(), "el doble de la de por defecto (768)");
		assertEquals(144, grid("minas/mediana", 72, 5).spacing(), "y las otras en proporción");
		assertEquals(240, grid("minas/grande", 120, 5).spacing());
		assertEquals(20, grid("minas/grande", 120, 5).separation());
		config("{\"minas\": {\"entradas\": {\"separacion_bloques\": 256}}, \"medianas\": {\"distancia_minima\": {\"bloques\": 1024}}}");
		GridPlacement p = grid("minas/pequena", 48, 5);
		assertEquals(16, p.spacing());
		assertEquals(8, p.separation(), "la interna, como mucho media casilla");
	}

	@Test
	void disabledLeaveNone() throws IOException {
		config("{\"minas\": {\"entradas\": {\"activado\": false}}}");
		for (int i = 0; i < 3; i++) {
			GridPlacement g = grid("minas/" + SIZES[i], SPACING[i], 3);
			for (int k = -3; k <= 3; k++) {
				ChunkPos c = g.getPotentialStructureChunk(11, k * g.spacing() + g.offsetX(), g.offsetZ());
				assertFalse(g.applyAdditionalChunkRestrictions(c.x(), c.z(), 11));
			}
		}
		config("{}");
		GridPlacement g = grid("minas/grande", 120, 3);
		ChunkPos c = g.getPotentialStructureChunk(11, g.offsetX(), g.offsetZ());
		assertTrue(g.applyAdditionalChunkRestrictions(c.x(), c.z(), 11));
	}

	private record Candidate(int type, int x, int z) {
	}

	private static List<Candidate> candidates(Mines m, List<RandomSpreadStructurePlacement> ps, long seed, int radius) {
		List<Candidate> out = new ArrayList<>();
		for (int i = 0; i < m.types(); i++) {
			RandomSpreadStructurePlacement p = ps.get(i);
			int s = p.spacing(), ox = ((GridPlacement) p).offsetX(), oz = ((GridPlacement) p).offsetZ();
			for (int gx = -radius / s - 1; gx <= radius / s + 1; gx++) {
				for (int gz = -radius / s - 1; gz <= radius / s + 1; gz++) {
					ChunkPos c = p.getPotentialStructureChunk(seed, gx * s + ox, gz * s + oz);
					out.add(new Candidate(i, c.x(), c.z()));
				}
			}
		}
		return out;
	}

	private static List<RandomSpreadStructurePlacement> grids() {
		List<RandomSpreadStructurePlacement> ps = new ArrayList<>();
		for (int i = 0; i < 3; i++) {
			ps.add(grid("minas/" + SIZES[i], SPACING[i], 1907261101 + i));
		}
		return ps;
	}

	@Test
	void consistentSeparationBetweenSizes() throws IOException {
		config("{}");
		int distance = 900;                    // much more than the default: many clashes to check
		long d2 = (long) distance * distance;
		MediumStructures.Zone free = (x, z) -> false;
		MediumStructures.Styles allStyles = (j, x, z) -> true;
		List<RandomSpreadStructurePlacement> ps = grids();
		for (long seed : new long[] {1, 42, -9}) {
			Mines m = mines(distance);
			List<Candidate> all = candidates(m, ps, seed, 900);
			List<Candidate> alive = new ArrayList<>();
			for (Candidate c : all) {
				if (!m.rejects(c.type, c.x, c.z, seed, free, allStyles, free, free)) {
					alive.add(c);
				}
			}
			assertTrue(alive.size() > all.size() / 4 && alive.size() < all.size(), "supervivientes " + alive.size() + " de " + all.size());
			for (Candidate a : alive) {
				for (Candidate b : alive) {
					if (a != b && a.type != b.type) {
						long dx = (a.x - b.x) * 16L, dz = (a.z - b.z) * 16L;
						assertTrue(dx * dx + dz * dz >= d2, a + " y " + b + " sobreviven las dos a menos de " + distance);
					}
				}
			}
			int edge = 900 - distance / 16 - 140;
			for (Candidate c : all) {
				if (alive.contains(c) || Math.abs(c.x) > edge || Math.abs(c.z) > edge) {
					continue;
				}
				boolean near = alive.stream().anyMatch(v -> v.type != c.type && Math.pow((v.x - c.x) * 16.0, 2) + Math.pow((v.z - c.z) * 16.0, 2) < d2);
				assertTrue(near, c + " descartada sin ninguna superviviente cerca");
			}
			Mines m2 = mines(distance);
			for (int k = all.size() - 1; k >= 0; k--) {
				Candidate c = all.get(k);
				assertEquals(alive.contains(c), !m2.rejects(c.type, c.x, c.z, seed, free, allStyles, free, free), c.toString());
			}
		}
	}

	@Test
	void yieldToVillagesUniquesMediumsAndAtlantis() throws IOException {
		config("{}");
		MediumStructures.Zone free = (x, z) -> false;
		MediumStructures.Styles allStyles = (j, x, z) -> true;
		List<Candidate> all = candidates(mines(192), grids(), 5, 400);
		Candidate c = all.getFirst();
		MediumStructures.Zone here = (x, z) -> x == c.x && z == c.z;
		assertTrue(mines(192).rejects(c.type, c.x, c.z, 77, here, allStyles, free, free), "en la zona de una aldea o una única");
		assertTrue(mines(192).rejects(c.type, c.x, c.z, 77, free, allStyles, free, here), "junto a una mediana que sale");
		// neighbors that do not win (biome or hillside), in Atlantis or next to a medium discard nobody
		int distance = 3000;
		for (String testCase : new String[] {"estilos", "atlantida", "medianas"}) {
			Mines m = mines(distance);
			int alive = 0;
			List<Candidate> allCandidates = candidates(m, grids(), 6, 400);
			for (Candidate o : allCandidates) {
				boolean own = testCase.equals("medianas");
				MediumStructures.Zone med = own ? (x, z) -> !(x == o.x && z == o.z) : free;
				boolean rejected = m.rejects(o.type, o.x, o.z, 6, free, testCase.equals("estilos") ? (j, x, z) -> j == o.type && x == o.x && z == o.z : allStyles,
						testCase.equals("atlantida") ? (x, z) -> !(x == o.x && z == o.z) : free, med);
				alive += rejected ? 0 : 1;
			}
			assertEquals(allCandidates.size(), alive, testCase + ": las que no salen no descartan");
		}
	}

	@Test
	void nearbyMediumOnlyIfItWins() throws IOException {
		config("{}");
		GridPlacement inn = grid("medianas/posada", 44, 1001);
		java.util.function.Supplier<MediumStructures> fresh = () -> new MediumStructures(new Object(),
				List.of(Identifier.fromNamespaceAndPath("heraldia", "medianas/posada")),
				List.of(List.of(Identifier.fromNamespaceAndPath("heraldia", "medianas/posada/a"))), List.of(List.of()), List.of(inn), null, 192);
		MediumStructures med = fresh.get();          // one per context: each medium's decision stays in its memo
		ChunkPos p = inn.getPotentialStructureChunk(8, inn.offsetX(), inn.offsetZ());
		MediumStructures.Zone free = (x, z) -> false;
		MediumStructures.Context outcome = new MediumStructures.Context(free, (j, x, z) -> true, free);
		assertTrue(med.near(p.x() + 5, p.z(), 192, 8, outcome), "a 80 bloques de una mediana que sale");
		assertFalse(med.near(p.x() + 14, p.z(), 192, 8, outcome), "a 224 bloques, no");
		assertFalse(fresh.get().near(p.x() + 5, p.z(), 192, 8, new MediumStructures.Context(free, (j, x, z) -> false, free)), "si no sale, no cuenta");
		assertFalse(fresh.get().near(p.x() + 5, p.z(), 192, 8, new MediumStructures.Context((x, z) -> true, (j, x, z) -> true, free)),
				"tampoco la que cae en la zona de una aldea (no sale)");
	}

	@Test
	void theirChestsRestockLikeHeraldiaOnes() {
		for (String t : new String[] {"galeria", "boca", "capataz", "fundicion", "filon", "vagoneta"}) {
			assertTrue(io.github.albertosa23.heraldia.loot.Restock.tableRestocks("heraldia:minas/" + t), t);
		}
		assertFalse(io.github.albertosa23.heraldia.loot.Restock.tableRestocks("heraldia:minas/"));
	}

	@Test
	void keyDistinguishesTypeAndChunk() {
		assertTrue(Mines.key(0, 1, 2) != Mines.key(1, 1, 2));
		assertTrue(Mines.key(0, -1, 2) != Mines.key(0, 1, 2));
		assertTrue(Mines.key(2, 5, -7) != Mines.key(2, -7, 5));
		assertTrue(Mines.isMine(Identifier.parse("heraldia:minas/grande/picos/b")));
		assertFalse(Mines.isMine(Identifier.parse("heraldia:medianas/posada/a")));
		assertFalse(Mines.isMine(Identifier.parse("minecraft:mineshaft")));
		assertFalse(Mines.isMine(Identifier.parse("heraldia:unicas/mina_perdida")));
	}
}
