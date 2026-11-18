package io.github.albertosa23.heraldia.config;

import com.google.gson.JsonElement;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import net.minecraft.resources.Identifier;
import net.minecraft.world.level.levelgen.LegacyRandomSource;
import net.minecraft.world.level.levelgen.WorldgenRandom;

/**
 * Qué aldeas puede generar el structure_set heraldia:aldeas en una casilla. Inmutable: se consulta desde los hilos de
 * generación. Si una estructura no vale, el set prueba la siguiente (igual que cuando falla el bioma).
 */
public final class VillageRules {
	private static final int SIZE_SALT = 1845613097;
	private final Set<Identifier> villages;
	private final Set<Identifier> disabled;
	private final Set<Identifier> large;
	private final int largePercent;

	VillageRules(HeraldiaConfig config) {
		Set<Identifier> all = new HashSet<>(), off = new HashSet<>(), big = new HashSet<>();
		for (Map.Entry<String, JsonElement> e : config.schema().getAsJsonObject("aldeas").getAsJsonObject("estilos").entrySet()) {
			String style = e.getKey(), family = e.getValue().getAsString();
			boolean on = config.getBool("aldeas.familias." + family) && config.getBool("aldeas.estilos." + style);
			Identifier std = Identifier.fromNamespaceAndPath("heraldia", style), largeVariant = Identifier.fromNamespaceAndPath("heraldia", style + "_grande");
			all.add(std);
			all.add(largeVariant);
			big.add(largeVariant);
			if (!on) {
				off.add(std);
				off.add(largeVariant);
			}
		}
		this.villages = Set.copyOf(all);
		this.disabled = Set.copyOf(off);
		this.large = Set.copyOf(big);
		this.largePercent = config.getInt("aldeas.porcentaje_grandes");
	}

	/** Falso si la estructura es una aldea de Heraldia desactivada o de otro tamaño que el que toca en esta casilla. */
	public boolean allows(Identifier structure, long seed, int chunkX, int chunkZ) {
		if (!villages.contains(structure)) {
			return true;
		}
		if (disabled.contains(structure)) {
			return false;
		}
		return large.contains(structure) == isLarge(seed, chunkX, chunkZ);
	}

	/** Tamaño de la aldea de una casilla: determinista por semilla y posición, sin datos guardados. */
	private boolean isLarge(long seed, int chunkX, int chunkZ) {
		WorldgenRandom random = new WorldgenRandom(new LegacyRandomSource(0L));
		random.setLargeFeatureWithSalt(seed, chunkX, chunkZ, SIZE_SALT);
		return random.nextInt(100) < largePercent;
	}

	public int enabledStyles() {
		return (villages.size() - disabled.size()) / 2;
	}
}
