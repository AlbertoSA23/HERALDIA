package io.github.albertosa23.heraldia.tesoro;

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
class SitioTest {
	/** Un llano de hierba a y = 64 (tierra debajo), con bloques sueltos, agua, estructuras y columnas sin cargar. */
	static final class Llano implements Sitio.Vista {
		final Map<BlockPos, String> bloques = new HashMap<>();
		final Map<Long, Integer> cimas = new HashMap<>();
		final Set<Long> sinCargar = new HashSet<>();
		final Set<BlockPos> agua = new HashSet<>(), estructura = new HashSet<>();
		int lecturas;

		static long k(int x, int z) {
			return ((long) x << 32) ^ (z & 0xFFFFFFFFL);
		}

		@Override
		public OptionalInt cima(int x, int z) {
			return sinCargar.contains(k(x, z)) ? OptionalInt.empty() : OptionalInt.of(cimas.getOrDefault(k(x, z), 64));
		}

		@Override
		public String bloque(int x, int y, int z) {
			lecturas++;
			String b = bloques.get(new BlockPos(x, y, z));
			if (b != null) {
				return b;
			}
			int c = cima(x, z).orElse(64);
			return y > c ? "minecraft:air" : y == c ? "minecraft:grass_block" : y > c - 4 ? "minecraft:dirt" : "minecraft:stone";
		}

		@Override
		public boolean liquido(int x, int y, int z) {
			return agua.contains(new BlockPos(x, y, z));
		}

		@Override
		public boolean enEstructura(int x, int y, int z) {
			return estructura.contains(new BlockPos(x, y, z));
		}
	}

	@Test
	void enUnLlanoLimpioEnLaMarcaYEnterrado() {
		Sitio.Eleccion e = Sitio.elegir(new Llano(), 100, -50);
		assertEquals(Sitio.Motivo.BIEN, e.motivo());
		assertEquals(new BlockPos(100, 63, -50), e.cofre().orElseThrow(), "un bloque bajo la cima: enterrado");
	}

	@Test
	void respetaElMargenAlrededorDeLoDeLosJugadores() {
		Llano w = new Llano();
		w.bloques.put(new BlockPos(103, 65, -50), "minecraft:oak_planks");   // a 3 bloques de la marca, sobre la cima
		BlockPos p = Sitio.elegir(w, 100, -50).cofre().orElseThrow();
		assertTrue(Math.max(Math.abs(p.getX() - 103), Math.abs(p.getZ() + 50)) > Sitio.MARGEN, "lejos de la tabla: " + p);
	}

	@Test
	void nuncaEncimaDeUnSotano() {
		Llano w = new Llano();
		for (int x = 95; x <= 105; x++) {
			for (int z = -55; z <= -45; z++) {
				w.bloques.put(new BlockPos(x, 60, z), "minecraft:stone_bricks");   // un sótano 4 bloques bajo la hierba
			}
		}
		BlockPos p = Sitio.elegir(w, 100, -50).cofre().orElseThrow();
		assertTrue(p.getX() < 95 - Sitio.MARGEN || p.getX() > 105 + Sitio.MARGEN || p.getZ() < -55 - Sitio.MARGEN || p.getZ() > -45 + Sitio.MARGEN,
				"fuera del sótano y su margen: " + p);
	}

	@Test
	void nadaSeguroSinSitio() {
		Llano w = new Llano();
		for (int x = -30; x <= 30; x++) {
			for (int z = -30; z <= 30; z += 5) {
				w.bloques.put(new BlockPos(x, 66, z), "minecraft:glass");
			}
		}
		Sitio.Eleccion e = Sitio.elegir(w, 0, 0);
		assertEquals(Sitio.Motivo.SIN_SITIO, e.motivo());
		assertTrue(e.cofre().isEmpty());
	}

	@Test
	void sinCargarNoSeEligeNiDejaElegirASuMargen() {
		Llano w = new Llano();
		for (int x = -40; x <= 40; x++) {
			for (int z = -40; z <= 40; z++) {
				if (x > -3) {
					w.sinCargar.add(Llano.k(x, z));
				}
			}
		}
		Sitio.Eleccion e = Sitio.elegir(w, 0, 0);
		BlockPos p = e.cofre().orElseThrow();
		assertTrue(p.getX() + Sitio.MARGEN <= -3, "con su margen entero cargado: " + p);
		Llano todo = new Llano();
		for (int x = -40; x <= 40; x++) {
			for (int z = -40; z <= 40; z++) {
				todo.sinCargar.add(Llano.k(x, z));
			}
		}
		assertEquals(Sitio.Motivo.SIN_CARGAR, Sitio.elegir(todo, 0, 0).motivo());
	}

	@Test
	void niBajoElAguaNiEnEstructurasNiEnRocaSinSuelo() {
		Llano w = new Llano();
		w.agua.add(new BlockPos(0, 65, 0));
		w.estructura.add(new BlockPos(1, 63, 0));
		w.bloques.put(new BlockPos(0, 64, 1), "minecraft:bedrock");
		w.bloques.put(new BlockPos(-1, 63, 0), "minecraft:oak_log");   // un árbol: no es suelo, pero tampoco obra
		Sitio.Eleccion e = Sitio.elegir(w, 0, 0, 1, 0);
		assertEquals(new BlockPos(0, 63, -1), e.cofre().orElseThrow());
	}

	@Test
	void ordenDeterministaDeCercaALejos() {
		List<int[]> o = Sitio.espiral(5);
		assertEquals(0, o.getFirst()[0]);
		assertEquals(0, o.getFirst()[1]);
		for (int i = 1; i < o.size(); i++) {
			int a = o.get(i - 1)[0] * o.get(i - 1)[0] + o.get(i - 1)[1] * o.get(i - 1)[1];
			int b = o.get(i)[0] * o.get(i)[0] + o.get(i)[1] * o.get(i)[1];
			assertTrue(a <= b);
		}
		assertEquals(Sitio.elegir(new Llano(), 7, 7), Sitio.elegir(new Llano(), 7, 7));
	}

	@Test
	void cadaColumnaSeMiraUnaVez() {
		Llano w = new Llano();
		w.bloques.put(new BlockPos(0, 65, 0), "minecraft:torch");   // obliga a recorrer muchas candidatas
		Sitio.elegir(w, 0, 0);
		int columnas = (2 * (Sitio.RADIO + Sitio.MARGEN) + 1) * (2 * (Sitio.RADIO + Sitio.MARGEN) + 1);
		assertTrue(w.lecturas < columnas * (Sitio.BAJO + Sitio.SOBRE + 1) + 4 * 1000, "lecturas acotadas: " + w.lecturas);
	}

	@Test
	void bloquesDeJugadores() {
		for (String b : List.of("minecraft:oak_planks", "minecraft:glass", "minecraft:glass_pane", "minecraft:white_wool", "minecraft:red_bed",
				"minecraft:oak_door", "minecraft:spruce_trapdoor", "minecraft:oak_fence", "minecraft:cobblestone_wall", "minecraft:stone_stairs",
				"minecraft:oak_slab", "minecraft:torch", "minecraft:wall_torch", "minecraft:lantern", "minecraft:rail", "minecraft:oak_sign",
				"minecraft:white_banner", "minecraft:chest", "minecraft:barrel", "minecraft:furnace", "minecraft:crafting_table",
				"minecraft:bricks", "minecraft:stone_bricks", "minecraft:farmland", "minecraft:dirt_path", "minecraft:cobblestone",
				"minecraft:stripped_oak_log", "minecraft:polished_andesite", "minecraft:white_concrete", "minecraft:flower_pot",
				"minecraft:potted_poppy", "minecraft:redstone_wire", "minecraft:iron_bars", "minecraft:iron_chain", "minecraft:ladder",
				"minecraft:hay_block", "minecraft:shulker_box", "minecraft:obsidian", "minecraft:smooth_stone", "minecraft:glowstone",
				"minecraft:tripwire", "minecraft:tripwire_hook", "minecraft:oak_pressure_plate", "minecraft:stone_button", "minecraft:white_carpet")) {
			assertTrue(Sitio.artificial(b), b);
		}
		for (String b : List.of("minecraft:grass_block", "minecraft:dirt", "minecraft:stone", "minecraft:oak_log", "minecraft:oak_leaves",
				"minecraft:short_grass", "minecraft:poppy", "minecraft:sand", "minecraft:gravel", "minecraft:water", "minecraft:snow",
				"minecraft:moss_carpet", "minecraft:pale_moss_carpet", "minecraft:redstone_ore", "minecraft:bee_nest", "minecraft:mossy_cobblestone",
				"minecraft:pointed_dripstone", "minecraft:sugar_cane", "minecraft:pumpkin", "minecraft:mushroom_stem", "minecraft:air",
				"minecraft:sweet_berry_bush", "minecraft:terracotta", "minecraft:red_terracotta", "minecraft:sandstone", "minecraft:ice")) {
			assertFalse(Sitio.artificial(b), b);
		}
	}

	@Test
	void sueloNatural() {
		for (String b : List.of("minecraft:grass_block", "dirt", "minecraft:sand", "minecraft:gravel", "minecraft:stone", "minecraft:podzol",
				"minecraft:red_terracotta", "minecraft:snow_block", "minecraft:deepslate")) {
			assertTrue(Sitio.suelo(b), b);
		}
		for (String b : List.of("minecraft:water", "minecraft:oak_planks", "minecraft:bedrock", "minecraft:white_glazed_terracotta",
				"minecraft:ice", "minecraft:oak_log", "minecraft:lava", "minecraft:air", "minecraft:powder_snow")) {
			assertFalse(Sitio.suelo(b), b);
		}
	}
}
