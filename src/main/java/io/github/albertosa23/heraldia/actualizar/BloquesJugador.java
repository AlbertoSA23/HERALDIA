package io.github.albertosa23.heraldia.actualizar;

import java.util.Set;

/**
 * Bloques típicos de jugador (T46), lógica pura sobre el nombre del bloque: lo que el terreno no genera solo y casi
 * siempre pone alguien (camas, cofres, barriles, carteles, mesas de trabajo, hornos, raíles, vallas, puertas, antorchas,
 * tablones, cristal, lana, ladrillos, tierra de cultivo...). Las estructuras también los traen (aldeas, minas
 * abandonadas, ruinas): el análisis solo cuenta los que quedan fuera de las piezas de las estructuras guardadas en el
 * chunk. Y la «cima natural» para comparar con la regeneración: troncos, hojas, setas, nieve, hielo, plantas que crecen
 * y fluidos, que cambian sin que nadie construya.
 */
public final class BloquesJugador {
	private static final Set<String> EXACTOS = Set.of("chest", "trapped_chest", "barrel", "crafting_table", "furnace",
			"blast_furnace", "smoker", "rail", "powered_rail", "detector_rail", "activator_rail", "torch", "wall_torch",
			"soul_torch", "soul_wall_torch", "lantern", "soul_lantern", "ladder", "farmland", "bookshelf", "chiseled_bookshelf",
			"enchanting_table", "anvil", "chipped_anvil", "damaged_anvil", "brewing_stand", "cartography_table",
			"fletching_table", "smithing_table", "loom", "stonecutter", "grindstone", "composter", "lectern", "jukebox",
			"note_block", "beacon", "respawn_anchor", "ender_chest", "hopper", "dropper", "dispenser", "observer", "piston",
			"sticky_piston", "lever", "repeater", "comparator", "redstone_lamp", "glass", "glass_pane", "tinted_glass", "bricks",
			"stone_bricks", "cobblestone_wall", "hay_block", "campfire", "soul_campfire", "scaffolding", "iron_bars", "chain",
			"iron_chain", "item_frame", "flower_pot", "cake", "crafter", "decorated_pot", "copper_bulb", "target", "bell",
			"white_concrete", "smooth_stone", "polished_andesite", "polished_diorite", "polished_granite");
	private static final String[] SUFIJOS = {"_bed", "_planks", "_sign", "_hanging_sign", "_wall_sign", "_wall_hanging_sign",
			"_fence", "_fence_gate", "_door", "_trapdoor", "_wool", "_carpet", "_stained_glass", "_stained_glass_pane",
			"_shulker_box", "_concrete", "_terracotta_slab", "_banner", "_wall_banner", "_bricks", "_brick_stairs",
			"_brick_slab", "_brick_wall", "_candle"};
	private static final String[] NATURALES_SUFIJOS = {"_log", "_wood", "_stem", "_hyphae", "_leaves", "_sapling",
			"_mushroom_block", "_mushroom", "_ice", "_coral", "_coral_block", "_coral_fan"};
	private static final Set<String> NATURALES = Set.of("snow", "snow_block", "ice", "powder_snow", "water", "lava", "vine",
			"cactus", "bamboo", "sugar_cane", "kelp", "kelp_plant", "seagrass", "tall_seagrass", "pumpkin", "melon",
			"mushroom_stem", "bee_nest", "moss_block", "moss_carpet", "pale_moss_block", "pale_moss_carpet", "cocoa",
			"sweet_berry_bush", "big_dripleaf", "big_dripleaf_stem", "pointed_dripstone", "mossy_cobblestone", "glow_lichen",
			"short_grass", "tall_grass", "fern", "large_fern", "dead_bush", "mangrove_roots", "muddy_mangrove_roots",
			"bubble_column", "obsidian", "magma_block", "basalt", "blackstone", "calcite", "amethyst_block",
			"budding_amethyst", "creaking_heart", "resin_clump", "leaf_litter", "firefly_bush", "bush", "cactus_flower");

	/**
	 * Bloques de jugador que la generación también pone fuera de las cajas de las estructuras: tablones y cadenas de las
	 * minas abandonadas (los puentes bajo las galerías), vallas y raíles, y los cofres de las mazmorras (que son un rasgo
	 * del terreno, no una estructura). Visto en un mundo de prueba de 26.3 (tools/smoke/actualizar.py).
	 */
	private static final Set<String> AMBIGUOS_EXACTOS = Set.of("chest", "rail", "chain", "iron_chain");
	private static final String[] AMBIGUOS_SUFIJOS = {"_planks", "_fence"};

	private BloquesJugador() {
	}

	/**
	 * ¿Bloque de jugador que también sale solo? Esos solo cuentan como construcción en un chunk por el que ha pasado algún
	 * jugador (InhabitedTime mayor que 0): para ponerlos a mano hay que estar cerca.
	 */
	public static boolean ambiguo(String id) {
		String r = ruta(id);
		if (AMBIGUOS_EXACTOS.contains(r)) {
			return true;
		}
		for (String s : AMBIGUOS_SUFIJOS) {
			if (r.endsWith(s)) {
				return true;
			}
		}
		return false;
	}

	private static String ruta(String id) {
		int i = id.indexOf(':');
		return i >= 0 ? id.substring(i + 1) : id;
	}

	/** ¿Bloque típico de jugador? ({@code minecraft:oak_planks}, {@code red_bed}...) Los de otros mods no cuentan. */
	public static boolean deJugador(String id) {
		if (id.indexOf(':') >= 0 && !id.startsWith("minecraft:")) {
			return false;
		}
		String r = ruta(id);
		if (EXACTOS.contains(r)) {
			return true;
		}
		for (String s : SUFIJOS) {
			if (r.endsWith(s)) {
				return true;
			}
		}
		return false;
	}

	/**
	 * ¿Puede estar en la cima de una columna sin que nadie haya construido? (árboles, setas gigantes, nieve, hielo, plantas
	 * que crecen, fluidos, rocas de los rasgos del terreno). Una cima así no cuenta como diferencia con la regeneración.
	 */
	public static boolean cimaNatural(String id) {
		String r = ruta(id);
		if (NATURALES.contains(r)) {
			return true;
		}
		for (String s : NATURALES_SUFIJOS) {
			if (r.endsWith(s)) {
				return true;
			}
		}
		return false;
	}
}
