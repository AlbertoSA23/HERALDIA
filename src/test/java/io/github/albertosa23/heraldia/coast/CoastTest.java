package io.github.albertosa23.heraldia.coast;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonParser;
import com.mojang.serialization.JsonOps;
import io.github.albertosa23.heraldia.common.MediumStructures;
import io.github.albertosa23.heraldia.config.GridPlacement;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.loot.Restock;
import io.github.albertosa23.heraldia.mines.Mines;
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
 * Faros y naufragios sin servidor: la rejilla heraldia:rejilla de los grupos costa/faro y costa/naufragio (activación y
 * separación de faros.* y naufragios.*: la frecuencia configurable), la regla de {@link Coast} (la de las minas con su
 * familia, {@link Mines#family}) con todo inyectado: ninguna superviviente en la zona de una aldea o una única, junto a
 * una mediana o una entrada a mina que sale, ni un faro a menos de la distancia mínima de un naufragio; y
 * {@link Mines#near} (la mina más cercana que sale, la que hace ceder a la costa).
 */
class CoastTest {
	private static final String[] TYPES = {"faro", "naufragio"};
	private static final int[] SPACING = {64, 48};

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

	private static List<RandomSpreadStructurePlacement> grids() {
		List<RandomSpreadStructurePlacement> ps = new ArrayList<>();
		for (int i = 0; i < TYPES.length; i++) {
			ps.add(grid("costa/" + TYPES[i], SPACING[i], 1907261201 + i));
		}
		return ps;
	}

	/** La regla de la costa tal y como la arma Costa.of: la familia de las minas con los dos tipos de la costa. */
	private static Mines family(int distance) {
		List<Identifier> types = new ArrayList<>();
		List<List<Identifier>> ids = new ArrayList<>();
		List<List<Structure>> styles = new ArrayList<>();
		for (String t : TYPES) {
			types.add(Identifier.fromNamespaceAndPath("heraldia", "costa/" + t));
			ids.add(List.of(Identifier.fromNamespaceAndPath("heraldia", "costa/" + t + "/templada/a")));
			styles.add(List.of());
		}
		return new Mines(new Object(), types, ids, styles, grids(), distance);
	}

	@Test
	void gridWithItsOptions() throws IOException {
		config("{}");
		for (int i = 0; i < TYPES.length; i++) {
			GridPlacement g = grid("costa/" + TYPES[i], SPACING[i], 5);
			assertEquals(SPACING[i], g.spacing(), "por defecto (1024 y 768 bloques), la del datapack");
			assertEquals(12, g.separation(), "la interna: medianas.distancia_minima.bloques (192)");
			assertTrue(g.offsetX() >= 0 && g.offsetX() < g.spacing(), "origen desplazado por la sal");
		}
		config("{\"faros\": {\"separacion_bloques\": 2048}, \"naufragios\": {\"separacion_bloques\": 320}, "
				+ "\"medianas\": {\"distancia_minima\": {\"bloques\": 256}}}");
		assertEquals(128, grid("costa/faro", 64, 5).spacing());
		assertEquals(20, grid("costa/naufragio", 48, 5).spacing(), "cada tipo con su opción");
		assertEquals(10, grid("costa/naufragio", 48, 5).separation(), "la interna, como mucho media casilla");
		assertEquals(16, grid("costa/faro", 64, 5).separation());
	}

	@Test
	void frequencyBySeparation() throws IOException {
		// candidatas en un cuadrado de 400 x 400 chunks: una por casilla, así que con la mitad de separación, unas 4 veces más
		int[] howMany = new int[2];
		String[] cfg = {"{}", "{\"faros\": {\"separacion_bloques\": 512}}"};
		for (int k = 0; k < 2; k++) {
			config(cfg[k]);
			GridPlacement g = grid("costa/faro", 64, 7);
			for (int gx = -200 / g.spacing(); gx < 200 / g.spacing(); gx++) {
				for (int gz = -200 / g.spacing(); gz < 200 / g.spacing(); gz++) {
					ChunkPos c = g.getPotentialStructureChunk(3, gx * g.spacing() + g.offsetX(), gz * g.spacing() + g.offsetZ());
					if (g.applyAdditionalChunkRestrictions(c.x(), c.z(), 3)) {
						howMany[k]++;
					}
				}
			}
		}
		assertTrue(howMany[1] >= 3.5 * howMany[0] && howMany[1] <= 4.5 * howMany[0], howMany[0] + " -> " + howMany[1]);
	}

	@Test
	void disabledLeaveNone() throws IOException {
		config("{\"faros\": {\"activado\": false}}");
		GridPlacement lighthouse = grid("costa/faro", 64, 3), shipwreck = grid("costa/naufragio", 48, 4);
		for (int k = -3; k <= 3; k++) {
			ChunkPos c = lighthouse.getPotentialStructureChunk(11, k * lighthouse.spacing() + lighthouse.offsetX(), lighthouse.offsetZ());
			assertFalse(lighthouse.applyAdditionalChunkRestrictions(c.x(), c.z(), 11), "faros desactivados");
			ChunkPos n = shipwreck.getPotentialStructureChunk(11, k * shipwreck.spacing() + shipwreck.offsetX(), shipwreck.offsetZ());
			assertTrue(shipwreck.applyAdditionalChunkRestrictions(n.x(), n.z(), 11), "los naufragios, por su cuenta");
		}
		config("{\"naufragios\": {\"activado\": false}}");
		assertFalse(Coast.enabled(HeraldiaConfig.get(), "naufragio"));
		assertTrue(Coast.enabled(HeraldiaConfig.get(), "faro"));
	}

	private record Candidate(int type, int x, int z) {
	}

	private static List<Candidate> candidates(List<RandomSpreadStructurePlacement> ps, long seed, int radius) {
		List<Candidate> out = new ArrayList<>();
		for (int i = 0; i < ps.size(); i++) {
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

	@Test
	void lighthouseAndShipwreckNeverTogether() throws IOException {
		config("{}");
		int distance = 1200;
		long d2 = (long) distance * distance;
		MediumStructures.Zone free = (x, z) -> false;
		MediumStructures.Styles allStyles = (j, x, z) -> true;
		for (long seed : new long[] {2, 77, -5}) {
			Mines m = family(distance);
			List<Candidate> all = candidates(grids(), seed, 900);
			List<Candidate> alive = all.stream().filter(c -> !m.rejects(c.type, c.x, c.z, seed, free, allStyles, free, free)).toList();
			assertTrue(alive.size() > all.size() / 4 && alive.size() < all.size(), "supervivientes " + alive.size() + " de " + all.size());
			for (Candidate a : alive) {
				for (Candidate b : alive) {
					if (a != b && a.type != b.type) {
						long dx = (a.x - b.x) * 16L, dz = (a.z - b.z) * 16L;
						assertTrue(dx * dx + dz * dz >= d2, a + " y " + b + " a menos de " + distance);
					}
				}
			}
			Mines other = family(distance);              // el mismo resultado en cualquier orden
			for (int k = all.size() - 1; k >= 0; k--) {
				Candidate c = all.get(k);
				assertEquals(alive.contains(c), !other.rejects(c.type, c.x, c.z, seed, free, allStyles, free, free), c.toString());
			}
		}
	}

	@Test
	void yieldToVillagesUniquesMediumsMinesAndAtlantis() throws IOException {
		config("{}");
		MediumStructures.Zone free = (x, z) -> false;
		MediumStructures.Styles allStyles = (j, x, z) -> true;
		Candidate c = candidates(grids(), 5, 400).getFirst();
		MediumStructures.Zone here = (x, z) -> x == c.x && z == c.z;
		assertTrue(family(192).rejects(c.type, c.x, c.z, 77, here, allStyles, free, free), "en la zona de una aldea o una única");
		assertTrue(family(192).rejects(c.type, c.x, c.z, 77, free, allStyles, free, here), "junto a una mediana o una mina");
		// una entrada a mina que sale a 80 bloques: Costa compone la zona con Minas.cerca, como en el juego
		GridPlacement mouth = MinesGrid.grid();
		Mines mines = MinesGrid.mines(mouth);
		ChunkPos m = mouth.getPotentialStructureChunk(8, mouth.offsetX(), mouth.offsetZ());
		MediumStructures.Zone nearMine = (x, z) -> mines.near(x, z, 192, 8, free, allStyles, free, free);
		assertTrue(nearMine.occupied(m.x() + 5, m.z()), "a 80 bloques de una mina que sale");
		assertFalse(nearMine.occupied(m.x() + 14, m.z()), "a 224, no");
		assertFalse(MinesGrid.mines(mouth).near(m.x() + 5, m.z(), 192, 8, free, (j, x, z) -> false, free, free),
				"si la mina no sale (sin ladera), no cuenta");
		assertFalse(MinesGrid.mines(mouth).near(m.x() + 5, m.z(), 192, 8, (x, z) -> true, allStyles, free, free),
				"ni la que cae en la zona de una aldea");
		assertTrue(family(192).rejects(c.type, m.x() + 5, m.z(), 8, free, allStyles, free, nearMine), "el faro cede a la mina");
	}

	/** Una rejilla de entradas a mina pequeñas (la del datapack) para probar Minas.cerca. */
	private static final class MinesGrid {
		static GridPlacement grid() {
			return CoastTest.grid("minas/pequena", 48, 1907261101);
		}

		static Mines mines(GridPlacement g) {
			return new Mines(new Object(), List.of(Identifier.fromNamespaceAndPath("heraldia", "minas/pequena")),
					List.of(List.of(Identifier.fromNamespaceAndPath("heraldia", "minas/pequena/montana/a"))), List.of(List.of()), List.of(g), 192);
		}
	}

	@Test
	void idsOptionsAndLoot() {
		assertTrue(Coast.isCoast(Identifier.parse("heraldia:costa/faro/templada/a")));
		assertTrue(Coast.isCoast(Identifier.parse("heraldia:costa/naufragio/nevada/b")));
		assertFalse(Coast.isCoast(Identifier.parse("heraldia:aldea_costa")));
		assertFalse(Coast.isCoast(Identifier.parse("heraldia:unicas/faro")), "el faro único es otra cosa");
		assertFalse(Coast.isCoast(Identifier.parse("minecraft:shipwreck")));
		assertEquals("faro", Coast.type(Identifier.parse("heraldia:costa/faro/fria/b")));
		assertEquals("faros", Coast.option("faro"));
		assertEquals("naufragios", Coast.option("naufragio"));
		assertNull(Coast.option("muelle"));
		for (String t : new String[] {"faro", "bodega", "camarote"}) {
			assertTrue(Restock.tableRestocks("heraldia:costa/" + t), "se repone: " + t);
		}
		assertFalse(Restock.tableRestocks("heraldia:costa/"));
	}
}
