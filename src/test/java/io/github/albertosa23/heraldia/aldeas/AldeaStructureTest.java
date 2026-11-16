package io.github.albertosa23.heraldia.aldeas;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.level.block.Rotation;
import net.minecraft.world.level.levelgen.structure.BoundingBox;
import net.minecraft.SharedConstants;
import net.minecraft.server.Bootstrap;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/** Partes puras del puerto de las aldeas de la costa: qué piezas desplaza, cuáles se pueden quitar y su giro. */
class AldeaStructureTest {
	@BeforeAll
	static void bootstrap() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	/** Pieza de prueba: nombre, caja, calle (terrain_matching) y ruta de plantilla. */
	private record P(String name, BoundingBox box, boolean street, String path) {
	}

	private static P p(String name, String path, int x0, int z0, int x1, int z1) {
		return new P(name, new BoundingBox(x0, 60, z0, x1, 70, z1), false, path);
	}

	private static P street(String name, int x0, int z0, int x1, int z1) {
		return new P(name, new BoundingBox(x0, 60, z0, x1, 62, z1), true, "llanuras_castellana/streets/s0");
	}

	private static final BoundingBox CASETA = new BoundingBox(0, 60, 0, 9, 68, 9);
	private static final BoundingBox MUELLE = new BoundingBox(2, 60, 10, 6, 63, 30);

	private static List<P> run(List<P> village) {
		return AldeaStructure.displaced(village, P::box, P::street, q -> AldeaStructure.removable(q.path), CASETA, MUELLE);
	}

	@Test
	void quitaLasCasasQueEstorbanYLoQueLlevanDentro() {
		P casa = p("casa", "llanuras_castellana/houses/small_0", 5, 5, 14, 14);
		P aldeano = p("aldeano", "villagers/plains/librarian", 6, 6, 6, 6);          // dentro de la casa (y en su caja)
		P lejos = p("lejos", "llanuras_castellana/houses/small_1", 50, 50, 60, 60);
		P calleBajoCaseta = street("calle", 0, 0, 1, 9);                               // bajo la caseta: vale
		List<P> out = run(List.of(casa, aldeano, lejos, calleBajoCaseta));
		assertEquals(List.of(casa, aldeano), out);
	}

	@Test
	void descartaLaOrillaSiChocaConAlgoQueNoSeQuita() {
		P iglesia = p("iglesia", "llanuras_castellana/specials/church", 3, 3, 12, 12);
		assertNull(run(List.of(iglesia)));
		P plaza = p("plaza", "llanuras_castellana/plaza/std", 0, 20, 20, 40);
		assertNull(run(List.of(plaza)));
	}

	@Test
	void unaCalleBajoElMuelleDescartaLaOrilla() {
		assertNull(run(List.of(street("calle", 4, 20, 5, 40))));
		assertEquals(List.of(), run(List.of(street("lejos", 40, 20, 41, 40))));
	}

	@Test
	void queSePuedeQuitar() {
		for (String ok : List.of("x/houses/a", "x/fillers/well", "x/decor/lamp", "x/terminators/tower", "villagers/plains/e_farmer", "golem")) {
			assertTrue(AldeaStructure.removable(ok), ok);
		}
		for (String no : List.of("x/specials/church", "x/plaza/std", "x/streets/s0", "x/avenues/a", "x/tablon", "golems")) {
			assertFalse(AldeaStructure.removable(no), no);
		}
		assertTrue(AldeaStructure.esTablon("costa_puerto/tablon"));
		assertFalse(AldeaStructure.esTablon("costa_puerto/tablon_b"));
	}

	@Test
	void giroHaciaElMar() {
		for (Direction d : Direction.Plane.HORIZONTAL) {
			Rotation r = AldeaStructure.facing(d);
			BlockPos v = new BlockPos(0, 0, 1).rotate(r);
			assertEquals(d.getStepX(), v.getX(), d.toString());
			assertEquals(d.getStepZ(), v.getZ(), d.toString());
		}
		assertEquals(Rotation.NONE, AldeaStructure.facing(Direction.SOUTH));
		assertEquals(Rotation.NONE, AldeaStructure.facing(Direction.UP));      // sin giro horizontal posible
	}
}
