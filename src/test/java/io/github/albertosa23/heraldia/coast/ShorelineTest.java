package io.github.albertosa23.heraldia.coast;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.function.IntBinaryOperator;
import net.minecraft.SharedConstants;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.level.block.Rotation;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/**
 * The shore of the lighthouses and shipwrecks ({@link Shoreline}) with synthetic height maps: a straight coast in each of
 * the four directions (the anchor on the last land block and the template's +z towards the sea), no coast, cliff,
 * drop, a narrow river, the depth each variant asks for, the lighthouse's preference for capes and the shapes of the
 * generated datapack (the real footprints: the lighthouse on land, its jetty and the stern or hull on the water).
 */
class ShorelineTest {
	private static final int SEA = 63;
	private static final Shoreline.Shape LIGHTHOUSE = new Shoreline.Shape(Shoreline.Mode.LIGHTHOUSE, new int[]{-7, -20, 7, -1}, new int[]{-1, 2, 1, 10});
	private static final Shoreline.Shape STRANDED = new Shoreline.Shape(Shoreline.Mode.STRANDED, new int[]{-3, -14, 3, -3}, new int[]{-3, 3, 3, 16});
	private static final Shoreline.Shape SUNKEN = new Shoreline.Shape(Shoreline.Mode.SUNKEN, new int[]{-2, -6, 2, -2}, new int[]{-4, 8, 4, 38});

	@BeforeAll
	static void bootstrap() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	/** Terrain: ground(x, z); water where the ground is below the sea. */
	private static Shoreline.Terrain terrain(IntBinaryOperator ground) {
		return new Shoreline.Terrain() {
			@Override
			public int ground(int x, int z) {
				return ground.applyAsInt(x, z);
			}

			@Override
			public boolean water(int x, int z) {
				return ground.applyAsInt(x, z) < SEA;
			}
		};
	}

	/** Straight coast: land at `land` up to the shore (10 blocks from the center towards d) and sea of `deep` after it. */
	private static Shoreline.Terrain straight(Direction d, int land, int deep) {
		return terrain((x, z) -> x * d.getStepX() + z * d.getStepZ() < 10 ? land : SEA - deep);
	}

	@Test
	void straightCoastInEachDirection() {
		for (Direction d : Direction.Plane.HORIZONTAL) {
			Shoreline.Site s = Shoreline.search(straight(d, SEA + 2, 6), SEA, 0, 0, LIGHTHOUSE);
			assertNotNull(s, "faro hacia el " + d);
			assertEquals(d, s.seaSide(), "el +z de la plantilla mira al mar");
			assertEquals(9, s.x() * d.getStepX() + s.z() * d.getStepZ(), "el ancla en el último bloque de tierra");
			assertEquals(SEA + 1, s.y(), "la plataforma a ras de lo más alto (suelo - 1)");
			Rotation r = CoastStructure.rotation(d);
			BlockPos v = new BlockPos(0, 0, 1).rotate(r);
			assertEquals(d.getStepX(), v.getX());
			assertEquals(d.getStepZ(), v.getZ());
			BlockPos width = new BlockPos(1, 0, 0).rotate(r);
			assertEquals(d.getCounterClockWise().getStepX(), width.getX(), "el +x de la plantilla, como en la búsqueda");
			assertEquals(d.getCounterClockWise().getStepZ(), width.getZ());
		}
	}

	@Test
	void noCoastNoSite() {
		assertNull(Shoreline.search(terrain((x, z) -> SEA + 3), SEA, 0, 0, LIGHTHOUSE), "todo tierra");
		assertNull(Shoreline.search(terrain((x, z) -> SEA - 20), SEA, 0, 0, LIGHTHOUSE), "todo mar");
		assertNull(Shoreline.search(terrain((x, z) -> SEA - 20), SEA, 0, 0, SUNKEN), "todo mar, tampoco el naufragio");
		// the shore far from the center (beyond the search's reach)
		assertNull(Shoreline.search(terrain((x, z) -> z < 90 ? SEA + 2 : SEA - 6), SEA, 0, 0, LIGHTHOUSE));
	}

	@Test
	void lighthousesOnlyOnFirmLowLand() {
		assertNull(Shoreline.search(straight(Direction.SOUTH, SEA + 12, 6), SEA, 0, 0, LIGHTHOUSE), "un risco: la tierra está demasiado alta");
		assertNull(Shoreline.search(terrain((x, z) -> z >= 10 ? SEA - 6 : z > -10 ? SEA + 1 : SEA + 6), SEA, 0, 0, LIGHTHOUSE),
				"más de 4 bloques de desnivel en la huella");
		Shoreline.Site s = Shoreline.search(terrain((x, z) -> z >= 10 ? SEA - 6 : z > -5 ? SEA + 1 : SEA + 4), SEA, 0, 0, LIGHTHOUSE);
		assertNotNull(s, "con 3 de desnivel sí");
		assertEquals(SEA + 3, s.y(), "a la altura de lo más alto (lo demás con cimientos)");
		assertNull(Shoreline.search(straight(Direction.SOUTH, SEA + 2, 1), SEA, 0, 0, LIGHTHOUSE), "sin fondo para el embarcadero");
	}

	@Test
	void narrowRiverIsNotCoast() {
		// land on both sides of a 4-block channel: there is no sea for the jetty or the stern
		Shoreline.Terrain river = terrain((x, z) -> z >= 10 && z < 14 ? SEA - 4 : SEA + 2);
		assertNull(Shoreline.search(river, SEA, 0, 0, LIGHTHOUSE));
		assertNull(Shoreline.search(river, SEA, 0, 0, STRANDED));
		assertNull(Shoreline.search(river, SEA, 0, 0, SUNKEN));
	}

	@Test
	void depthOfEachShipwreck() {
		assertNotNull(Shoreline.search(straight(Direction.EAST, SEA + 1, 3), SEA, 0, 0, STRANDED), "encallado: playa y bajío");
		assertNull(Shoreline.search(straight(Direction.EAST, SEA + 1, 14), SEA, 0, 0, STRANDED), "encallado: mar hondo, no");
		assertNull(Shoreline.search(straight(Direction.EAST, SEA + 6, 3), SEA, 0, 0, STRANDED), "encallado: la proa no sube a un risco");
		assertNotNull(Shoreline.search(straight(Direction.EAST, SEA + 2, 6), SEA, 0, 0, SUNKEN), "semihundido: aguas de 6");
		assertNull(Shoreline.search(straight(Direction.EAST, SEA + 2, 1), SEA, 0, 0, SUNKEN), "semihundido: demasiado poco hondo");
		assertNull(Shoreline.search(straight(Direction.EAST, SEA + 2, 16), SEA, 0, 0, SUNKEN), "semihundido: demasiado hondo");
		assertEquals(-1, Shoreline.search(straight(Direction.EAST, SEA + 2, 6), SEA, 0, 0, SUNKEN).y(), "la altura la da la fila del mar");
	}

	@Test
	void someRockInShoalDoesNotMatter() {
		// one dry sea sample out of 20 (a 1 x 1 islet): 80 % is enough
		Shoreline.Terrain t = terrain((x, z) -> x == 1 && z == 22 ? SEA + 1 : z < 10 ? SEA + 1 : SEA - 5);
		assertNotNull(Shoreline.evaluateAt(t, SEA, 0, 9, Direction.SOUTH, SUNKEN));
		Shoreline.Terrain many = terrain((x, z) -> z >= 20 && z <= 40 && Math.floorMod(x, 2) == 0 ? SEA + 1 : z < 10 ? SEA + 1 : SEA - 5);
		assertNull(Shoreline.evaluateAt(many, SEA, 0, 9, Direction.SOUTH, SUNKEN), "un arrecife entero, no");
	}

	@Test
	void lighthousePrefersCapes() {
		// a coast corner: sea to the south (z >= 24) and east (x >= 24); near the corner there is more water around
		Shoreline.Terrain corner = terrain((x, z) -> z >= 24 || x >= 24 && z >= -40 ? SEA - 8 : SEA + 2);
		Shoreline.Site s = Shoreline.search(corner, SEA, 0, 0, LIGHTHOUSE);
		assertNotNull(s);
		Shoreline.Site straight = Shoreline.evaluateAt(terrain((x, z) -> z >= 24 ? SEA - 8 : SEA + 2), SEA, 0, 23, Direction.SOUTH, LIGHTHOUSE);
		assertNotNull(straight);
		assertTrue(s.note() > straight.note(), "más agua alrededor que en la costa recta: " + s + " / " + straight);
		assertTrue(s.x() > 0 && s.z() > 0, "hacia la esquina: " + s);
	}

	@Test
	void generatedDatapackShapes() throws IOException {
		Path dir = Path.of(System.getProperty("heraldia.generated", "build/generated/heraldia"), "data", "heraldia", "worldgen", "structure", "costa");
		if (!Files.isDirectory(dir)) {
			return;                                       // not generated (the unit test alone)
		}
		List<Path> fs = new ArrayList<>();
		try (var w = Files.walk(dir)) {
			w.filter(p -> p.toString().endsWith(".json")).forEach(fs::add);
		}
		assertEquals(16, fs.size(), "2 tipos x 4 estilos x 2 variantes");
		for (Path f : fs) {
			JsonObject o = JsonParser.parseString(Files.readString(f)).getAsJsonObject();
			Shoreline.Mode mode = Shoreline.Mode.of(o.get("modo").getAsString());
			int[] land = arr(o, "tierra"), seaSide = arr(o, "mar");
			assertTrue(land[3] < 0 && seaSide[1] > 0, f + ": la tierra detrás del ancla y el mar delante");
			Shoreline.Shape shape = new Shoreline.Shape(mode, land, seaSide);
			int deep = mode == Shoreline.Mode.SUNKEN ? 6 : mode == Shoreline.Mode.STRANDED ? 3 : 5;
			assertNotNull(Shoreline.search(straight(Direction.NORTH, SEA + 1, deep), SEA, 0, 0, shape), f + " en una costa normal");
			assertTrue(f.toString().contains("/faro/") == (mode == Shoreline.Mode.LIGHTHOUSE), f.toString());
			assertTrue(o.get("fila_mar").getAsInt() >= (mode == Shoreline.Mode.LIGHTHOUSE ? -1 : 0));
			assertEquals(o.getAsJsonArray("climas").isEmpty(), false, f + ": sin climas");
		}
	}

	private static int[] arr(JsonObject o, String k) {
		var a = o.getAsJsonArray(k);
		int[] out = new int[a.size()];
		for (int i = 0; i < out.length; i++) {
			out[i] = a.get(i).getAsInt();
		}
		return out;
	}

	@Test
	void howManySamples() {
		assertEquals(4 * 5, Shoreline.howMany(new int[]{-7, -20, 7, -1}), "15 x 20 cada 5: 4 x 5 muestras (con el borde)");
		assertEquals(1, Shoreline.howMany(new int[]{0, 0, 0, 0}));
	}
}
