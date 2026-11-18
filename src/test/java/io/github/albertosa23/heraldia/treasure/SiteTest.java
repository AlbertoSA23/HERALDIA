package io.github.albertosa23.heraldia.treasure;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.OptionalInt;
import java.util.Set;
import net.minecraft.core.BlockPos;
import org.junit.jupiter.api.Test;

/** Dónde se entierra el cofre: nunca dentro, encima ni al lado (margen) de lo que construyen los jugadores. */
class SiteTest {
	/** Un llano de hierba a y = 64 (tierra debajo), con bloques sueltos, agua, estructuras y columnas sin cargar. */
	static final class Flat implements Site.View {
		final Map<BlockPos, String> blocks = new HashMap<>();
		final Map<Long, Integer> tops = new HashMap<>();
		final Set<Long> unloaded = new HashSet<>();
		final Set<BlockPos> water = new HashSet<>(), structure = new HashSet<>();
		int reads;

		static long k(int x, int z) {
			return ((long) x << 32) ^ (z & 0xFFFFFFFFL);
		}

		@Override
		public OptionalInt top(int x, int z) {
			return unloaded.contains(k(x, z)) ? OptionalInt.empty() : OptionalInt.of(tops.getOrDefault(k(x, z), 64));
		}

		@Override
		public String block(int x, int y, int z) {
			reads++;
			String b = blocks.get(new BlockPos(x, y, z));
			if (b != null) {
				return b;
			}
			int c = top(x, z).orElse(64);
			return y > c ? "minecraft:air" : y == c ? "minecraft:grass_block" : y > c - 4 ? "minecraft:dirt" : "minecraft:stone";
		}

		@Override
		public boolean liquid(int x, int y, int z) {
			return water.contains(new BlockPos(x, y, z));
		}

		@Override
		public boolean inStructure(int x, int y, int z) {
			return structure.contains(new BlockPos(x, y, z));
		}
	}

	@Test
	void onCleanFlatAtTheMarkAndBuried() {
		Site.Choice e = Site.choose(new Flat(), 100, -50);
		assertEquals(Site.Reason.OK, e.reason());
		assertEquals(new BlockPos(100, 63, -50), e.chest().orElseThrow(), "un bloque bajo la cima: enterrado");
	}

	@Test
	void respectsMarginAroundPlayerBuilds() {
		Flat w = new Flat();
		w.blocks.put(new BlockPos(103, 65, -50), "minecraft:oak_planks");   // a 3 bloques de la marca, sobre la cima
		BlockPos p = Site.choose(w, 100, -50).chest().orElseThrow();
		assertTrue(Math.max(Math.abs(p.getX() - 103), Math.abs(p.getZ() + 50)) > Site.MARGIN, "lejos de la tabla: " + p);
	}

	@Test
	void neverAboveABasement() {
		Flat w = new Flat();
		for (int x = 95; x <= 105; x++) {
			for (int z = -55; z <= -45; z++) {
				w.blocks.put(new BlockPos(x, 60, z), "minecraft:stone_bricks");   // un sótano 4 bloques bajo la hierba
			}
		}
		BlockPos p = Site.choose(w, 100, -50).chest().orElseThrow();
		assertTrue(p.getX() < 95 - Site.MARGIN || p.getX() > 105 + Site.MARGIN || p.getZ() < -55 - Site.MARGIN || p.getZ() > -45 + Site.MARGIN,
				"fuera del sótano y su margen: " + p);
	}

	@Test
	void nothingSafeNoSite() {
		Flat w = new Flat();
		for (int x = -30; x <= 30; x++) {
			for (int z = -30; z <= 30; z += 5) {
				w.blocks.put(new BlockPos(x, 66, z), "minecraft:glass");
			}
		}
		Site.Choice e = Site.choose(w, 0, 0);
		assertEquals(Site.Reason.NO_SITE, e.reason());
		assertTrue(e.chest().isEmpty());
	}

	@Test
	void unloadedIsNotChosenNorLetsItsMarginBeChosen() {
		Flat w = new Flat();
		for (int x = -40; x <= 40; x++) {
			for (int z = -40; z <= 40; z++) {
				if (x > -3) {
					w.unloaded.add(Flat.k(x, z));
				}
			}
		}
		Site.Choice e = Site.choose(w, 0, 0);
		BlockPos p = e.chest().orElseThrow();
		assertTrue(p.getX() + Site.MARGIN <= -3, "con su margen entero cargado: " + p);
		Flat everything = new Flat();
		for (int x = -40; x <= 40; x++) {
			for (int z = -40; z <= 40; z++) {
				everything.unloaded.add(Flat.k(x, z));
			}
		}
		assertEquals(Site.Reason.UNLOADED, Site.choose(everything, 0, 0).reason());
	}

	@Test
	void notUnderwaterNorInStructuresNorInRockWithoutGround() {
		Flat w = new Flat();
		w.water.add(new BlockPos(0, 65, 0));
		w.structure.add(new BlockPos(1, 63, 0));
		w.blocks.put(new BlockPos(0, 64, 1), "minecraft:bedrock");
		w.blocks.put(new BlockPos(-1, 63, 0), "minecraft:oak_log");   // un árbol: no es suelo, pero tampoco obra
		Site.Choice e = Site.choose(w, 0, 0, 1, 0);
		assertEquals(new BlockPos(0, 63, -1), e.chest().orElseThrow());
	}

	@Test
	void deterministicOrderNearToFar() {
		List<int[]> o = Site.spiral(5);
		assertEquals(0, o.getFirst()[0]);
		assertEquals(0, o.getFirst()[1]);
		for (int i = 1; i < o.size(); i++) {
			int a = o.get(i - 1)[0] * o.get(i - 1)[0] + o.get(i - 1)[1] * o.get(i - 1)[1];
			int b = o.get(i)[0] * o.get(i)[0] + o.get(i)[1] * o.get(i)[1];
			assertTrue(a <= b);
		}
		assertEquals(Site.choose(new Flat(), 7, 7), Site.choose(new Flat(), 7, 7));
	}

	@Test
	void eachColumnIsCheckedOnce() {
		Flat w = new Flat();
		w.blocks.put(new BlockPos(0, 65, 0), "minecraft:torch");   // obliga a recorrer muchas candidatas
		Site.choose(w, 0, 0);
		int columns = (2 * (Site.RADIUS + Site.MARGIN) + 1) * (2 * (Site.RADIUS + Site.MARGIN) + 1);
		assertTrue(w.reads < columns * (Site.LOW + Site.ABOVE + 1) + 4 * 1000, "lecturas acotadas: " + w.reads);
	}

	@Test
	void playerBlocks() {
		for (String b : List.of("minecraft:oak_planks", "minecraft:glass", "minecraft:glass_pane", "minecraft:white_wool", "minecraft:red_bed",
				"minecraft:oak_door", "minecraft:spruce_trapdoor", "minecraft:oak_fence", "minecraft:cobblestone_wall", "minecraft:stone_stairs",
				"minecraft:oak_slab", "minecraft:torch", "minecraft:wall_torch", "minecraft:lantern", "minecraft:rail", "minecraft:oak_sign",
				"minecraft:white_banner", "minecraft:chest", "minecraft:barrel", "minecraft:furnace", "minecraft:crafting_table",
				"minecraft:bricks", "minecraft:stone_bricks", "minecraft:farmland", "minecraft:dirt_path", "minecraft:cobblestone",
				"minecraft:stripped_oak_log", "minecraft:polished_andesite", "minecraft:white_concrete", "minecraft:flower_pot",
				"minecraft:potted_poppy", "minecraft:redstone_wire", "minecraft:iron_bars", "minecraft:iron_chain", "minecraft:ladder",
				"minecraft:hay_block", "minecraft:shulker_box", "minecraft:obsidian", "minecraft:smooth_stone", "minecraft:glowstone",
				"minecraft:tripwire", "minecraft:tripwire_hook", "minecraft:oak_pressure_plate", "minecraft:stone_button", "minecraft:white_carpet")) {
			assertTrue(Site.artificial(b), b);
		}
		for (String b : List.of("minecraft:grass_block", "minecraft:dirt", "minecraft:stone", "minecraft:oak_log", "minecraft:oak_leaves",
				"minecraft:short_grass", "minecraft:poppy", "minecraft:sand", "minecraft:gravel", "minecraft:water", "minecraft:snow",
				"minecraft:moss_carpet", "minecraft:pale_moss_carpet", "minecraft:redstone_ore", "minecraft:bee_nest", "minecraft:mossy_cobblestone",
				"minecraft:pointed_dripstone", "minecraft:sugar_cane", "minecraft:pumpkin", "minecraft:mushroom_stem", "minecraft:air",
				"minecraft:sweet_berry_bush", "minecraft:terracotta", "minecraft:red_terracotta", "minecraft:sandstone", "minecraft:ice")) {
			assertFalse(Site.artificial(b), b);
		}
	}

	@Test
	void naturalGround() {
		for (String b : List.of("minecraft:grass_block", "dirt", "minecraft:sand", "minecraft:gravel", "minecraft:stone", "minecraft:podzol",
				"minecraft:red_terracotta", "minecraft:snow_block", "minecraft:deepslate")) {
			assertTrue(Site.ground(b), b);
		}
		for (String b : List.of("minecraft:water", "minecraft:oak_planks", "minecraft:bedrock", "minecraft:white_glazed_terracotta",
				"minecraft:ice", "minecraft:oak_log", "minecraft:lava", "minecraft:air", "minecraft:powder_snow")) {
			assertFalse(Site.ground(b), b);
		}
	}
}
