package io.github.albertosa23.heraldia.caminos;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.HashSet;
import java.util.Set;
import net.minecraft.SharedConstants;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/** Material del camino según la superficie (CaminoFeature.suelo): solo terreno natural, y nunca grava sin apoyo. */
class CaminoFeatureTest {
	@BeforeAll
	static void bootstrap() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	private static Set<Block> materiales(Block top, boolean firme) {
		Set<Block> out = new HashSet<>();
		for (double r = 0; r < 1; r += 0.01) {
			BlockState s = CaminoFeature.suelo(top.defaultBlockState(), r, firme);
			out.add(s == null ? null : s.getBlock());
		}
		return out;
	}

	@Test
	void tierraYHierbaDanCaminoDeTierra() {
		for (Block b : new Block[]{Blocks.GRASS_BLOCK, Blocks.DIRT, Blocks.PODZOL, Blocks.MYCELIUM, Blocks.COARSE_DIRT}) {
			Set<Block> m = materiales(b, true);
			assertTrue(m.contains(Blocks.DIRT_PATH), b + ": " + m);
			assertTrue(Set.of(Blocks.DIRT_PATH, Blocks.COARSE_DIRT, Blocks.GRAVEL).containsAll(m), b + ": " + m);
		}
		assertEquals(Blocks.DIRT_PATH, CaminoFeature.suelo(Blocks.GRASS_BLOCK.defaultBlockState(), 0.9, true).getBlock());
	}

	@Test
	void arenaPiedraNieveYBarro() {
		assertEquals(Set.of(Blocks.SMOOTH_SANDSTONE, Blocks.SANDSTONE, Blocks.CUT_SANDSTONE), materiales(Blocks.SAND, true));
		assertEquals(Set.of(Blocks.SMOOTH_RED_SANDSTONE, Blocks.RED_SANDSTONE, Blocks.CUT_RED_SANDSTONE), materiales(Blocks.RED_SAND, true));
		assertEquals(Set.of(Blocks.SMOOTH_RED_SANDSTONE, Blocks.RED_SANDSTONE, Blocks.CUT_RED_SANDSTONE), materiales(Blocks.TERRACOTTA, true));
		for (Block b : new Block[]{Blocks.STONE, Blocks.GRAVEL, Blocks.SNOW_BLOCK, Blocks.POWDER_SNOW, Blocks.ANDESITE, Blocks.DEEPSLATE}) {
			assertEquals(Set.of(Blocks.GRAVEL, Blocks.COBBLESTONE, Blocks.STONE_BRICKS), materiales(b, true), b.toString());
		}
		assertEquals(Set.of(Blocks.PACKED_MUD, Blocks.MUD_BRICKS), materiales(Blocks.MUD, true));
	}

	@Test
	void sinApoyoNuncaGrava() {
		for (Block b : new Block[]{Blocks.GRASS_BLOCK, Blocks.STONE, Blocks.POWDER_SNOW}) {
			assertTrue(!materiales(b, false).contains(Blocks.GRAVEL), b.toString());
		}
	}

	@Test
	void loQueNoEsTerrenoNaturalSeDeja() {
		for (Block b : new Block[]{Blocks.OAK_PLANKS, Blocks.COBBLESTONE, Blocks.STONE_BRICKS, Blocks.WATER, Blocks.LAVA, Blocks.OAK_LOG,
				Blocks.OAK_LEAVES, Blocks.ICE, Blocks.BRICKS, Blocks.DIRT_PATH, Blocks.FARMLAND}) {
			assertNull(CaminoFeature.suelo(b.defaultBlockState(), 0.5, true), b.toString());
		}
	}
}
