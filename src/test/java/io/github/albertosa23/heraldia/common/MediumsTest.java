package io.github.albertosa23.heraldia.common;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonParser;
import com.mojang.serialization.JsonOps;
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
 * Medium structures without a server: the heraldia:rejilla grid of the group medianas/&lt;type&gt; (what it reads from the
 * configuration) and the rule of {@link MediumStructures} with the zone and styles injected (pure logic): no survivor
 * in the zone of a village or a unique, two survivors never within the minimum distance, every candidate discarded
 * by another medium has a survivor nearby, and the result does not depend on the order of the queries.
 */
class MediumsTest {
	private static final String[] TYPES = {"torre_vigia", "posada", "campamento", "ermita"};

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

	static GridPlacement grid(String type, int spacing, int salt) {
		return GridPlacement.CODEC.codec().parse(JsonOps.INSTANCE, JsonParser.parseString(
				"{\"grupo\": \"medianas/" + type + "\", \"spacing\": " + spacing + ", \"separation\": " + spacing / 3
						+ ", \"salt\": " + salt + "}")).getOrThrow();
	}

	private static MediumStructures mediums(int distance) {
		List<Identifier> types = new ArrayList<>();
		List<List<Identifier>> ids = new ArrayList<>();
		List<List<Structure>> styles = new ArrayList<>();
		List<RandomSpreadStructurePlacement> placements = new ArrayList<>();
		for (int i = 0; i < TYPES.length; i++) {
			Identifier t = Identifier.fromNamespaceAndPath("heraldia", "medianas/" + TYPES[i]);
			types.add(t);
			ids.add(List.of(Identifier.fromNamespaceAndPath("heraldia", "medianas/" + TYPES[i] + "/a")));
			styles.add(List.of());
			placements.add(grid(TYPES[i], 44, 1000 + i));
		}
		return new MediumStructures(new Object(), types, ids, styles, placements, null, distance);
	}

	@Test
	void gridReadsSeparationFrequencyAndDistance() throws IOException {
		config("{\"medianas\": {\"posada\": {\"separacion_bloques\": 800}, \"frecuencia_porcentaje\": 400, "
				+ "\"distancia_minima\": {\"bloques\": 160}}}");
		GridPlacement g = grid("posada", 48, 7);
		assertEquals(Math.round(800 / 2.0F / 16), g.spacing(), "400 % = la mitad de separación (cuatro veces más densas)");
		assertEquals(10, g.separation());
		assertTrue(g.offsetX() >= 0 && g.offsetX() < g.spacing() && g.offsetZ() < g.spacing());
		config("{\"medianas\": {\"posada\": {\"separacion_bloques\": 800}, \"frecuencia_porcentaje\": 100, \"distancia_minima\": {\"bloques\": 1024}}}");
		GridPlacement h = grid("posada", 48, 7);
		assertEquals(50, h.spacing(), "100 % = the type's own spacing (the previous density)");
		assertEquals(25, h.separation(), "la interna, como mucho media casilla");
		// the default frequency (60 %): the spacing divided by the square root of 0.6
		config("{\"medianas\": {\"posada\": {\"separacion_bloques\": 800}}}");
		assertEquals(Math.round(Math.round(800 / Math.sqrt(0.6)) / 16.0), grid("posada", 48, 7).spacing());
	}

	@Test
	void disabledLeaveNone() throws IOException {
		for (String cfg : new String[]{"{\"medianas\": {\"activadas\": false}}", "{\"medianas\": {\"ermita\": {\"activada\": false}}}"}) {
			config(cfg);
			GridPlacement g = grid("ermita", 56, 3);
			for (int k = -3; k <= 3; k++) {
				ChunkPos c = g.getPotentialStructureChunk(11, k * g.spacing() + g.offsetX(), g.offsetZ());
				assertFalse(g.applyAdditionalChunkRestrictions(c.x(), c.z(), 11), cfg);
			}
		}
		config("{}");
		GridPlacement g = grid("ermita", 56, 3);
		ChunkPos c = g.getPotentialStructureChunk(11, g.offsetX(), g.offsetZ());
		assertTrue(g.applyAdditionalChunkRestrictions(c.x(), c.z(), 11));
	}

	private record Candidate(int type, int x, int z) {
	}

	private static List<Candidate> candidates(MediumStructures m, long seed, int radius) {
		List<Candidate> out = new ArrayList<>();
		for (int i = 0; i < m.types(); i++) {
			RandomSpreadStructurePlacement p = m.placement(i);
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

	@Test
	void consistentSeparationBetweenMediums() throws IOException {
		config("{}");
		int distance = 400; // more than the default: more clashes to check
		long d2 = (long) distance * distance;
		MediumStructures.Zone free = (x, z) -> false;
		for (long seed : new long[]{1, 42, -9}) {
			MediumStructures m = mediums(distance);
			MediumStructures.Styles allStyles = (j, x, z) -> true;
			List<Candidate> all = candidates(m, seed, 600);
			List<Candidate> alive = new ArrayList<>();
			for (Candidate c : all) {
				if (!m.rejects(c.type, c.x, c.z, seed, free, allStyles, free)) {
					alive.add(c);
				}
			}
			assertTrue(alive.size() > all.size() / 3 && alive.size() < all.size(), "supervivientes " + alive.size() + " de " + all.size());
			for (Candidate a : alive) {
				for (Candidate b : alive) {
					if (a != b && a.type != b.type) {
						long dx = (a.x - b.x) * 16L, dz = (a.z - b.z) * 16L;
						assertTrue(dx * dx + dz * dz >= d2, a + " y " + b + " sobreviven las dos a menos de " + distance);
					}
				}
			}
			int edge = 600 - distance / 16 - 64;   // away from the edge of what was enumerated (the one that discards it may be outside)
			for (Candidate c : all) {
				if (alive.contains(c) || Math.abs(c.x) > edge || Math.abs(c.z) > edge) {
					continue;
				}
				boolean near = alive.stream().anyMatch(v -> v.type != c.type && Math.pow((v.x - c.x) * 16.0, 2) + Math.pow((v.z - c.z) * 16.0, 2) < d2);
				assertTrue(near, c + " descartada sin ninguna superviviente cerca");
			}
			// another instance, another order: same result (no state that depends on who asks first)
			MediumStructures m2 = mediums(distance);
			for (int k = all.size() - 1; k >= 0; k--) {
				Candidate c = all.get(k);
				assertEquals(alive.contains(c), !m2.rejects(c.type, c.x, c.z, seed, free, allStyles, free), c.toString());
			}
		}
	}

	@Test
	void yieldSiteToForeignStructures() throws IOException {
		config("{}");
		GridPlacement grid = grid("posada", 48, 9);   // any grid acts as a vanilla structure
		MediumStructures m = new MediumStructures(new Object(), List.of(), List.of(), List.of(), List.of(), null, 192,
				List.of(new MediumStructures.Foreign(grid, new Structure[]{null}, MediumStructures.FOREIGN_BLOCKS)));
		ChunkPos c = grid.getPotentialStructureChunk(3, grid.offsetX(), grid.offsetZ());
		int near = (MediumStructures.FOREIGN_BLOCKS - 16) / 16, far = MediumStructures.FOREIGN_BLOCKS / 16 + 2;
		assertTrue(m.yieldsToForeign(c.x() + near, c.z(), 3, (st, x, z) -> true), "sale a menos de la distancia: cede");
		assertFalse(m.yieldsToForeign(c.x() + far, c.z(), 3, (st, x, z) -> true), "más lejos: no");
		MediumStructures n = new MediumStructures(new Object(), List.of(), List.of(), List.of(), List.of(), null, 192,
				List.of(new MediumStructures.Foreign(grid, new Structure[]{null}, MediumStructures.FOREIGN_BLOCKS)));
		assertFalse(n.yieldsToForeign(c.x() + near, c.z(), 3, (st, x, z) -> false), "si no sale (bioma), no cede");
	}

	@Test
	void onlyThoseAskingYieldToMines() throws IOException {
		config("{}");
		GridPlacement mine = grid("posada", 48, 11);    // acts as a mine entrance grid
		List<Identifier> types = List.of(Identifier.fromNamespaceAndPath("heraldia", "medianas/choza_mago"),
				Identifier.fromNamespaceAndPath("heraldia", "medianas/ermita"));
		MediumStructures m = new MediumStructures(new Object(), types, List.of(List.of(), List.of()), List.of(List.of(), List.of()),
				List.of(grid("choza_mago", 64, 1), grid("ermita", 48, 2)), null, 192, List.of(), new boolean[]{true, false},
				List.of(new MediumStructures.Foreign(mine, new Structure[]{null}, 192)));
		ChunkPos c = mine.getPotentialStructureChunk(5, mine.offsetX(), mine.offsetZ());
		int near = (192 - 16) / 16, far = 192 / 16 + 2;
		assertTrue(m.yieldsToMine(0, c.x() + near, c.z(), 5, (st, x, z) -> true), "la choza cede a una mina que sale cerca");
		assertFalse(m.yieldsToMine(1, c.x() + near, c.z(), 5, (st, x, z) -> true), "la ermita no lo pide: no cede");
		assertFalse(m.yieldsToMine(0, c.x() + far, c.z(), 5, (st, x, z) -> true), "más lejos que la distancia mínima: no");
		assertFalse(m.yieldsToMine(-1, c.x(), c.z(), 5, (st, x, z) -> true), "tipo desconocido: no");
		MediumStructures n = new MediumStructures(new Object(), types, List.of(List.of(), List.of()), List.of(List.of(), List.of()),
				List.of(grid("choza_mago", 64, 1), grid("ermita", 48, 2)), null, 192, List.of(), new boolean[]{true, false},
				List.of(new MediumStructures.Foreign(mine, new Structure[]{null}, 192)));
		assertFalse(n.yieldsToMine(0, c.x() + near, c.z(), 5, (st, x, z) -> false), "si la mina no sale (bioma o ladera), no cede");
		// without the list of the yielding ones (the usual constructor), none yields
		MediumStructures o = new MediumStructures(new Object(), types, List.of(List.of(), List.of()), List.of(List.of(), List.of()),
				List.of(grid("choza_mago", 64, 1), grid("ermita", 48, 2)), null, 192, List.of());
		assertFalse(o.yieldsToMine(0, c.x() + near, c.z(), 5, (st, x, z) -> true));
	}

	@Test
	void zoneAndStylesDiscard() throws IOException {
		config("{}");
		MediumStructures m = mediums(192);
		MediumStructures.Zone free = (x, z) -> false;
		MediumStructures.Styles allStyles = (j, x, z) -> true;
		List<Candidate> all = candidates(m, 5, 300);
		Candidate c = all.getFirst();
		assertTrue(m.rejects(c.type, c.x, c.z, 77, (x, z) -> x == c.x && z == c.z, allStyles, free), "en la zona de una aldea o una única");
		// a neighbor that does not win (biome) or that falls in Atlantis discards nobody
		MediumStructures single = mediums(2000);
		int alive = 0;
		for (Candidate o : candidates(single, 6, 300)) {
			alive += single.rejects(o.type, o.x, o.z, 6, free, (j, x, z) -> j == 0, free) ? 0 : 1;
		}
		assertTrue(alive > 1, "con un solo tipo que sale, sus candidatas no las descarta nadie: " + alive);
		MediumStructures atl = mediums(2000);
		int aliveAtl = 0;
		for (Candidate o : candidates(atl, 6, 300)) {
			aliveAtl += atl.rejects(o.type, o.x, o.z, 6, free, allStyles, (x, z) -> true) ? 0 : 1;
		}
		assertEquals(candidates(atl, 6, 300).size(), aliveAtl, "las de la Atlántida no salen, así que no descartan");
	}
}
