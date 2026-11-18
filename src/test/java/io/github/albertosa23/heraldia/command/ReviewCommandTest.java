package io.github.albertosa23.heraldia.command;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import io.github.albertosa23.heraldia.command.Revision.Stop;
import io.github.albertosa23.heraldia.command.Revision.Type;
import java.util.Map;
import net.minecraft.SharedConstants;
import net.minecraft.resources.Identifier;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.level.block.Blocks;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/**
 * La parte de /heraldia review que toca clases del juego sin un mundo: qué estructuras son de cada parada, cómo se
 * clasifica cada bloque para el teletransporte seguro y la lista de qué mirar.
 */
class ReviewCommandTest {
	@BeforeAll
	static void game() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	private static Identifier h(String path) {
		return Identifier.fromNamespaceAndPath("heraldia", path);
	}

	@Test
	void structuresOfEachStop() {
		Map<String, String> styles = Map.of("llanuras_castellana", "llanuras", "bosque_lenadores", "bosque");
		Stop village = new Stop("aldea/llanuras", Type.VILLAGE, "llanuras");
		assertTrue(ReviewCommand.ofStop(village, h("llanuras_castellana"), styles));
		assertTrue(ReviewCommand.ofStop(village, h("llanuras_castellana_grande"), styles));
		assertFalse(ReviewCommand.ofStop(village, h("bosque_lenadores"), styles));
		assertFalse(ReviewCommand.ofStop(village, Identifier.fromNamespaceAndPath("minecraft", "llanuras_castellana"), styles));
		Stop unique = new Stop("unica/castillo", Type.UNIQUE, "castillo");
		assertTrue(ReviewCommand.ofStop(unique, h("unicas/castillo"), styles));
		assertFalse(ReviewCommand.ofStop(unique, h("unicas/castillo_negro"), styles));
		Stop medium = new Stop("mediana/posada", Type.MEDIUM, "posada");
		assertTrue(ReviewCommand.ofStop(medium, h("medianas/posada/llanura"), styles));
		assertFalse(ReviewCommand.ofStop(medium, h("medianas/posadas/llanura"), styles));
		Stop mine = new Stop("mina/pequena", Type.MINE, "pequena");
		assertTrue(ReviewCommand.ofStop(mine, h("minas/pequena/roca/a"), styles));
		assertFalse(ReviewCommand.ofStop(mine, h("minas/mediana/roca/a"), styles));
		Stop lighthouse = new Stop("costa/faro", Type.COAST, "faro");
		assertTrue(ReviewCommand.ofStop(lighthouse, h("costa/faro/templada/a"), styles));
		assertFalse(ReviewCommand.ofStop(lighthouse, h("costa/naufragio/templada/a"), styles));
		assertFalse(ReviewCommand.ofStop(lighthouse, h("unicas/faro"), styles), "el faro único es su propia parada");
		assertFalse(ReviewCommand.ofStop(new Stop("arena", Type.ARENA, ""), h("arena"), styles));
	}

	@Test
	void teleportCells() {
		assertEquals(SafeSpot.Cell.FREE, ReviewCommand.cell(Blocks.AIR.defaultBlockState(), false));
		assertEquals(SafeSpot.Cell.FREE, ReviewCommand.cell(Blocks.SHORT_GRASS.defaultBlockState(), false));
		assertEquals(SafeSpot.Cell.SOLID, ReviewCommand.cell(Blocks.STONE.defaultBlockState(), true));
		assertEquals(SafeSpot.Cell.WATER, ReviewCommand.cell(Blocks.WATER.defaultBlockState(), false));
		assertEquals(SafeSpot.Cell.DANGER, ReviewCommand.cell(Blocks.LAVA.defaultBlockState(), false));
		assertEquals(SafeSpot.Cell.DANGER, ReviewCommand.cell(Blocks.FIRE.defaultBlockState(), false));
		assertEquals(SafeSpot.Cell.DANGER, ReviewCommand.cell(Blocks.MAGMA_BLOCK.defaultBlockState(), true));
		assertEquals(SafeSpot.Cell.DANGER, ReviewCommand.cell(Blocks.CACTUS.defaultBlockState(), true));
		assertEquals(SafeSpot.Cell.DANGER, ReviewCommand.cell(Blocks.POWDER_SNOW.defaultBlockState(), false));
		assertEquals(SafeSpot.Cell.DANGER, ReviewCommand.cell(Blocks.CAMPFIRE.defaultBlockState(), true));
		assertEquals(SafeSpot.Cell.DANGER, ReviewCommand.cell(Blocks.SOUL_FIRE.defaultBlockState(), false));
		assertEquals(SafeSpot.Cell.SOLID, ReviewCommand.cell(Blocks.OAK_LEAVES.defaultBlockState(), true));
		// un bloque anegado con colisión sostiene (no es agua donde flotar)
		assertEquals(SafeSpot.Cell.SOLID, ReviewCommand.cell(Blocks.OAK_STAIRS.defaultBlockState()
				.setValue(net.minecraft.world.level.block.state.properties.BlockStateProperties.WATERLOGGED, true), true));
		assertEquals(SafeSpot.Cell.WATER, ReviewCommand.cell(Blocks.SEAGRASS.defaultBlockState(), false), "hierba marina: agua");
	}

	@Test
	void checklist() {
		assertEquals(4, ReviewCommand.points(new Stop("unica/castillo", Type.UNIQUE, "castillo")).size());
		assertEquals("heraldia.revisar.mirar.unica.atlantida",
				ReviewCommand.points(new Stop("unica/atlantida", Type.UNIQUE, "atlantida")).getLast());
		assertEquals(3, ReviewCommand.points(new Stop("camino", Type.ROAD, "")).size());
		for (Type t : Type.values()) {
			assertTrue(ReviewCommand.POINTS.containsKey(t), t.toString());
		}
	}

	@Test
	void routeTextsInJar() {
		Map<String, String> es = Texts.language(Texts.ES);
		for (Type t : Type.values()) {
			for (String k : ReviewCommand.points(new Stop("x", t, "atlantida"))) {
				assertTrue(es.containsKey(k), k);
			}
		}
		for (Revision.Mark m : Revision.Mark.values()) {
			assertTrue(es.containsKey("heraldia.revisar.estado." + m.name().toLowerCase(java.util.Locale.ROOT)), m.toString());
		}
		assertEquals("Un tramo de camino", ReviewCommand.spanishName(new Stop("camino", Type.ROAD, "")));
		assertTrue(ReviewCommand.spanishName(new Stop("aldea/llanuras", Type.VILLAGE, "llanuras")).contains("Aldea"));
	}
}
