package io.github.albertosa23.heraldia.treasure;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.OptionalInt;
import java.util.Set;
import net.minecraft.core.BlockPos;

/**
 * Dónde enterrar el cofre final sin tocar nada de los jugadores: lógica pura sobre una {@link View} del mundo
 * (SitioTest con mundos de mentira; en el juego, {@link Treasure} la da con los chunks ya cargados, sin cargar ninguno).
 * <p>Se recorren las columnas a menos de {@code radius} bloques de la marca, de la más cercana a la más lejana; vale la
 * primera en la que: la cima (el bloque sólido más alto, sin hojas) y el de debajo son suelo natural ({@link #ground}), no
 * hay líquido encima, el sitio del cofre (un bloque bajo la cima: queda enterrado) no está en las piezas de ninguna
 * estructura, y en ninguna columna a menos de {@code margin} bloques hay un bloque hecho por jugadores
 * ({@link #artificial}) entre 6 bloques bajo su cima y 10 sobre ella. Una columna sin cargar no vale ni deja valer a las
 * de su margen.
 */
public final class Site {
	public static final int RADIUS = 16, MARGIN = 6, LOW = 6, ABOVE = 10;

	private Site() {
	}

	/** Lo que el sitio necesita saber del mundo (ids de bloque sin espacio de nombres si es minecraft). */
	public interface View {
		/** y del bloque sólido más alto (sin contar hojas); vacío si la columna no está cargada. */
		OptionalInt top(int x, int z);

		String block(int x, int y, int z);

		boolean liquid(int x, int y, int z);

		boolean inStructure(int x, int y, int z);
	}

	public enum Reason {
		OK, UNLOADED, NO_SITE
	}

	public record Choice(Reason reason, Optional<BlockPos> chest) {
	}

	public static Choice choose(View v, int cx, int cz) {
		return choose(v, cx, cz, RADIUS, MARGIN);
	}

	public static Choice choose(View v, int cx, int cz, int radius, int margin) {
		Map<Long, Boolean> dirty = new HashMap<>();   // columna con algo de jugadores (o sin cargar)
		boolean unloaded = false;
		for (int[] o : spiral(radius)) {
			int x = cx + o[0], z = cz + o[1];
			OptionalInt top = v.top(x, z);
			if (top.isEmpty()) {
				unloaded = true;
				continue;
			}
			int y = top.getAsInt();
			if (!ground(v.block(x, y, z)) || !ground(v.block(x, y - 1, z)) || v.liquid(x, y + 1, z) || v.inStructure(x, y - 1, z)) {
				continue;
			}
			boolean clean = true;
			for (int dx = -margin; dx <= margin && clean; dx++) {
				for (int dz = -margin; dz <= margin && clean; dz++) {
					int sx = x + dx, sz = z + dz;
					Boolean s = dirty.computeIfAbsent(key(sx, sz), k -> dirtyColumn(v, sx, sz));
					if (s) {
						clean = false;
					}
				}
			}
			if (clean) {
				return new Choice(Reason.OK, Optional.of(new BlockPos(x, y - 1, z)));
			}
		}
		return new Choice(unloaded ? Reason.UNLOADED : Reason.NO_SITE, Optional.empty());
	}

	static boolean dirtyColumn(View v, int x, int z) {
		OptionalInt top = v.top(x, z);
		if (top.isEmpty()) {
			return true;
		}
		int y0 = top.getAsInt();
		for (int y = y0 - LOW; y <= y0 + ABOVE; y++) {
			if (artificial(v.block(x, y, z))) {
				return true;
			}
		}
		return false;
	}

	/** Desplazamientos (dx, dz) a menos de radio, del más cercano al más lejano (con un orden fijo en los empates). */
	static List<int[]> spiral(int radius) {
		List<int[]> out = new ArrayList<>();
		for (int dx = -radius; dx <= radius; dx++) {
			for (int dz = -radius; dz <= radius; dz++) {
				if (dx * dx + dz * dz <= radius * radius) {
					out.add(new int[]{dx, dz});
				}
			}
		}
		out.sort(Comparator.comparingInt((int[] o) -> o[0] * o[0] + o[1] * o[1]).thenComparingInt(o -> o[0]).thenComparingInt(o -> o[1]));
		return out;
	}

	private static long key(int x, int z) {
		return ((long) x << 32) ^ (z & 0xFFFFFFFFL);
	}

	private static String shortRange(String id) {
		return id.startsWith("minecraft:") ? id.substring("minecraft:".length()) : id;
	}

	/** Suelo natural donde se puede enterrar algo (tierra, arena, grava, piedra y parecidos). */
	public static boolean ground(String id) {
		String b = shortRange(id);
		return GROUND.contains(b) || b.endsWith("terracotta") && !b.contains("glazed");
	}

	private static final Set<String> GROUND = Set.of("grass_block", "dirt", "coarse_dirt", "rooted_dirt", "podzol", "mycelium", "mud",
			"sand", "red_sand", "gravel", "clay", "snow_block", "moss_block", "pale_moss_block", "stone", "granite", "diorite",
			"andesite", "deepslate", "tuff", "calcite", "sandstone", "red_sandstone", "dripstone_block", "suspicious_sand",
			"suspicious_gravel", "packed_mud");

	/** Palabras (trozos del id separados por «_») de los bloques que solo pone un jugador (o una estructura). */
	private static final Set<String> WORDS = Set.of("planks", "glass", "pane", "wool", "carpet", "bed", "door", "trapdoor",
			"fence", "gate", "wall", "stairs", "slab", "torch", "lantern", "lamp", "rail", "sign", "banner", "candle", "concrete",
			"bricks", "chest", "barrel", "furnace", "smoker", "anvil", "bookshelf", "lectern", "bell", "hopper", "dispenser",
			"dropper", "piston", "observer", "repeater", "comparator", "lever", "button", "plate", "bars", "chain", "ladder",
			"scaffolding", "farmland", "path", "polished", "smooth", "cut", "chiseled", "glazed", "beacon", "campfire", "hay",
			"composter", "cauldron", "pot", "potted", "shulker", "jukebox", "table", "stripped", "tnt", "stand", "box", "head",
			"skull", "tiles", "pillar", "conduit", "grindstone", "loom", "stonecutter", "crafter", "vault", "spawner",
			"wire", "hook");
	private static final Set<String> EXACT = Set.of("cobblestone", "quartz_block", "crafting_table", "note_block", "target",
			"sea_lantern", "glowstone", "end_rod", "redstone_block", "iron_block", "gold_block", "diamond_block", "emerald_block",
			"lapis_block", "coal_block", "copper_block", "netherite_block", "slime_block", "honey_block", "obsidian",
			"crying_obsidian", "respawn_anchor", "lodestone", "enchanting_table", "ender_chest", "beehive", "sponge", "wet_sponge",
			"dirt_path", "tripwire");
	/** Naturales que comparten palabra con los artificiales. */
	private static final Set<String> NATURAL = Set.of("moss_carpet", "pale_moss_carpet", "pointed_dripstone", "redstone_ore",
			"deepslate_redstone_ore", "bee_nest", "mushroom_stem", "brown_mushroom_block", "red_mushroom_block");

	/** ¿Bloque puesto por un jugador (o por una construcción)? Por su id; los naturales con palabras compartidas, no. */
	public static boolean artificial(String id) {
		String b = shortRange(id);
		if (NATURAL.contains(b)) {
			return false;
		}
		if (EXACT.contains(b)) {
			return true;
		}
		for (String p : b.split("_")) {
			if (WORDS.contains(p)) {
				return true;
			}
		}
		return false;
	}
}
