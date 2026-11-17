package io.github.albertosa23.heraldia.tesoro;

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
 * Dónde enterrar el cofre final sin tocar nada de los jugadores: lógica pura sobre una {@link Vista} del mundo
 * (SitioTest con mundos de mentira; en el juego, {@link Tesoro} la da con los chunks ya cargados, sin cargar ninguno).
 * <p>Se recorren las columnas a menos de {@code radio} bloques de la marca, de la más cercana a la más lejana; vale la
 * primera en la que: la cima (el bloque sólido más alto, sin hojas) y el de debajo son suelo natural ({@link #suelo}), no
 * hay líquido encima, el sitio del cofre (un bloque bajo la cima: queda enterrado) no está en las piezas de ninguna
 * estructura, y en ninguna columna a menos de {@code margen} bloques hay un bloque hecho por jugadores
 * ({@link #artificial}) entre 6 bloques bajo su cima y 10 sobre ella. Una columna sin cargar no vale ni deja valer a las
 * de su margen.
 */
public final class Sitio {
	public static final int RADIO = 16, MARGEN = 6, BAJO = 6, SOBRE = 10;

	private Sitio() {
	}

	/** Lo que el sitio necesita saber del mundo (ids de bloque sin espacio de nombres si es minecraft). */
	public interface Vista {
		/** y del bloque sólido más alto (sin contar hojas); vacío si la columna no está cargada. */
		OptionalInt cima(int x, int z);

		String bloque(int x, int y, int z);

		boolean liquido(int x, int y, int z);

		boolean enEstructura(int x, int y, int z);
	}

	public enum Motivo {
		BIEN, SIN_CARGAR, SIN_SITIO
	}

	public record Eleccion(Motivo motivo, Optional<BlockPos> cofre) {
	}

	public static Eleccion elegir(Vista v, int cx, int cz) {
		return elegir(v, cx, cz, RADIO, MARGEN);
	}

	public static Eleccion elegir(Vista v, int cx, int cz, int radio, int margen) {
		Map<Long, Boolean> sucia = new HashMap<>();   // columna con algo de jugadores (o sin cargar)
		boolean sinCargar = false;
		for (int[] o : espiral(radio)) {
			int x = cx + o[0], z = cz + o[1];
			OptionalInt cima = v.cima(x, z);
			if (cima.isEmpty()) {
				sinCargar = true;
				continue;
			}
			int y = cima.getAsInt();
			if (!suelo(v.bloque(x, y, z)) || !suelo(v.bloque(x, y - 1, z)) || v.liquido(x, y + 1, z) || v.enEstructura(x, y - 1, z)) {
				continue;
			}
			boolean limpio = true;
			for (int dx = -margen; dx <= margen && limpio; dx++) {
				for (int dz = -margen; dz <= margen && limpio; dz++) {
					int sx = x + dx, sz = z + dz;
					Boolean s = sucia.computeIfAbsent(clave(sx, sz), k -> columnaSucia(v, sx, sz));
					if (s) {
						limpio = false;
					}
				}
			}
			if (limpio) {
				return new Eleccion(Motivo.BIEN, Optional.of(new BlockPos(x, y - 1, z)));
			}
		}
		return new Eleccion(sinCargar ? Motivo.SIN_CARGAR : Motivo.SIN_SITIO, Optional.empty());
	}

	static boolean columnaSucia(Vista v, int x, int z) {
		OptionalInt cima = v.cima(x, z);
		if (cima.isEmpty()) {
			return true;
		}
		int y0 = cima.getAsInt();
		for (int y = y0 - BAJO; y <= y0 + SOBRE; y++) {
			if (artificial(v.bloque(x, y, z))) {
				return true;
			}
		}
		return false;
	}

	/** Desplazamientos (dx, dz) a menos de radio, del más cercano al más lejano (con un orden fijo en los empates). */
	static List<int[]> espiral(int radio) {
		List<int[]> out = new ArrayList<>();
		for (int dx = -radio; dx <= radio; dx++) {
			for (int dz = -radio; dz <= radio; dz++) {
				if (dx * dx + dz * dz <= radio * radio) {
					out.add(new int[]{dx, dz});
				}
			}
		}
		out.sort(Comparator.comparingInt((int[] o) -> o[0] * o[0] + o[1] * o[1]).thenComparingInt(o -> o[0]).thenComparingInt(o -> o[1]));
		return out;
	}

	private static long clave(int x, int z) {
		return ((long) x << 32) ^ (z & 0xFFFFFFFFL);
	}

	private static String corto(String id) {
		return id.startsWith("minecraft:") ? id.substring("minecraft:".length()) : id;
	}

	/** Suelo natural donde se puede enterrar algo (tierra, arena, grava, piedra y parecidos). */
	public static boolean suelo(String id) {
		String b = corto(id);
		return SUELO.contains(b) || b.endsWith("terracotta") && !b.contains("glazed");
	}

	private static final Set<String> SUELO = Set.of("grass_block", "dirt", "coarse_dirt", "rooted_dirt", "podzol", "mycelium", "mud",
			"sand", "red_sand", "gravel", "clay", "snow_block", "moss_block", "pale_moss_block", "stone", "granite", "diorite",
			"andesite", "deepslate", "tuff", "calcite", "sandstone", "red_sandstone", "dripstone_block", "suspicious_sand",
			"suspicious_gravel", "packed_mud");

	/** Palabras (trozos del id separados por «_») de los bloques que solo pone un jugador (o una estructura). */
	private static final Set<String> PALABRAS = Set.of("planks", "glass", "pane", "wool", "carpet", "bed", "door", "trapdoor",
			"fence", "gate", "wall", "stairs", "slab", "torch", "lantern", "lamp", "rail", "sign", "banner", "candle", "concrete",
			"bricks", "chest", "barrel", "furnace", "smoker", "anvil", "bookshelf", "lectern", "bell", "hopper", "dispenser",
			"dropper", "piston", "observer", "repeater", "comparator", "lever", "button", "plate", "bars", "chain", "ladder",
			"scaffolding", "farmland", "path", "polished", "smooth", "cut", "chiseled", "glazed", "beacon", "campfire", "hay",
			"composter", "cauldron", "pot", "potted", "shulker", "jukebox", "table", "stripped", "tnt", "stand", "box", "head",
			"skull", "tiles", "pillar", "conduit", "grindstone", "loom", "stonecutter", "crafter", "vault", "spawner",
			"wire", "hook");
	private static final Set<String> EXACTOS = Set.of("cobblestone", "quartz_block", "crafting_table", "note_block", "target",
			"sea_lantern", "glowstone", "end_rod", "redstone_block", "iron_block", "gold_block", "diamond_block", "emerald_block",
			"lapis_block", "coal_block", "copper_block", "netherite_block", "slime_block", "honey_block", "obsidian",
			"crying_obsidian", "respawn_anchor", "lodestone", "enchanting_table", "ender_chest", "beehive", "sponge", "wet_sponge",
			"dirt_path", "tripwire");
	/** Naturales que comparten palabra con los artificiales. */
	private static final Set<String> NATURALES = Set.of("moss_carpet", "pale_moss_carpet", "pointed_dripstone", "redstone_ore",
			"deepslate_redstone_ore", "bee_nest", "mushroom_stem", "brown_mushroom_block", "red_mushroom_block");

	/** ¿Bloque puesto por un jugador (o por una construcción)? Por su id; los naturales con palabras compartidas, no. */
	public static boolean artificial(String id) {
		String b = corto(id);
		if (NATURALES.contains(b)) {
			return false;
		}
		if (EXACTOS.contains(b)) {
			return true;
		}
		for (String p : b.split("_")) {
			if (PALABRAS.contains(p)) {
				return true;
			}
		}
		return false;
	}
}
