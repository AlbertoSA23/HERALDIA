package io.github.albertosa23.heraldia.config;

import com.google.gson.JsonElement;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import net.minecraft.resources.Identifier;
import net.minecraft.world.level.levelgen.LegacyRandomSource;
import net.minecraft.world.level.levelgen.WorldgenRandom;

/**
 * Which villages the heraldia:aldeas structure_set can generate in a cell. Immutable: queried from the
 * generation threads. If a structure is not valid, the set tries the next one (just like when the biome fails).
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

	/** False if the structure is a Heraldia village that is disabled or of a different size than the one due in this cell. */
	public boolean allows(Identifier structure, long seed, int chunkX, int chunkZ) {
		if (!villages.contains(structure)) {
			return true;
		}
		if (disabled.contains(structure)) {
			return false;
		}
		return large.contains(structure) == isLarge(seed, chunkX, chunkZ);
	}

	/** Village size of a cell: deterministic by seed and position, no saved data. */
	private boolean isLarge(long seed, int chunkX, int chunkZ) {
		WorldgenRandom random = new WorldgenRandom(new LegacyRandomSource(0L));
		random.setLargeFeatureWithSalt(seed, chunkX, chunkZ, SIZE_SALT);
		return random.nextInt(100) < largePercent;
	}

	public int enabledStyles() {
		return (villages.size() - disabled.size()) / 2;
	}
}
