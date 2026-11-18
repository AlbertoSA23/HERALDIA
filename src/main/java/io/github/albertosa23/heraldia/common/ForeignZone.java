package io.github.albertosa23.heraldia.common;

import io.github.albertosa23.heraldia.config.GridPlacement;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.config.UniqueSeparation;
import io.github.albertosa23.heraldia.dimensions.Dimensions;
import io.github.albertosa23.heraldia.uniques.atlantis.AtlantisAnchor;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.EnumSet;
import java.util.List;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import net.minecraft.core.Holder;
import net.minecraft.core.Registry;
import net.minecraft.core.RegistryAccess;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.Identifier;
import net.minecraft.resources.ResourceKey;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.LevelHeightAccessor;
import net.minecraft.world.level.biome.BiomeSource;
import net.minecraft.world.level.biome.Climate;
import net.minecraft.world.level.chunk.ChunkGenerator;
import net.minecraft.world.level.levelgen.GenerationStep;
import net.minecraft.world.level.levelgen.RandomState;
import net.minecraft.world.level.levelgen.structure.Structure;
import net.minecraft.world.level.levelgen.structure.StructureSet;
import net.minecraft.world.level.levelgen.structure.placement.RandomSpreadStructurePlacement;
import net.minecraft.world.level.levelgen.structure.templatesystem.StructureTemplateManager;
import org.jspecify.annotations.Nullable;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Other mods' structures next to Heraldia's: a start from another mod (neither heraldia nor minecraft) that shows above
 * ground is not born within {@link #OPTION} blocks of the start of a Heraldia village or unique that really
 * generates (Heraldia always wins, so a Heraldia one never spawns on top of a foreign one either: the chunk generation
 * order does not matter). It is the technique of Atlantis and the corsair's island, made generic: no foreign mod has to
 * know about Heraldia or declare anything.
 * <p>Cost: only for the candidate chunks of a foreign structure (a few per area). The candidates of the nearby
 * Heraldia grids are computed (getPotentialStructureChunk, no terrain or biomes); the expensive part (whether the Heraldia
 * one wins there: biome, terrain, mod rules) only next to a candidate, and it is memoized. One instance per
 * structure_set registry (per world), immutable except the memo (ConcurrentHashMap): the generation threads query it at once.
 * <p>Vanilla ones are not touched (their villages already have the exclusion zone of ours; Atlantis and the island exclude
 * everything) nor foreign underground ones ({@link #visible}), which are not seen even if they cross a box. The village is
 * considered generated if any of its entries is valid in the cell (like the structure_set, which tries another when one
 * fails); the exclusion zone against vanilla villages is not counted, so next to a candidate that loses because of it, it
 * also excludes (rarely).
 */
public final class ForeignZone {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	public static final String OPTION = "compatibilidad.zona_estructuras_ajenas_bloques";
	private static final Identifier VILLAGES = Identifier.fromNamespaceAndPath("heraldia", "aldeas");
	/** Generation steps of what does not show above ground (mineshafts, dungeons, strongholds). */
	private static final Set<GenerationStep.Decoration> UNDERGROUND = EnumSet.of(GenerationStep.Decoration.UNDERGROUND_STRUCTURES,
			GenerationStep.Decoration.STRONGHOLDS, GenerationStep.Decoration.UNDERGROUND_ORES, GenerationStep.Decoration.UNDERGROUND_DECORATION);
	static final int VILLAGE = -1;
	private static final int CACHE_MAX = 1 << 12;
	private static volatile @Nullable ForeignZone cached;

	/** Does a Heraldia village really spawn with its start in that chunk? */
	@FunctionalInterface
	public interface Village {
		boolean outcome(int chunkX, int chunkZ);
	}

	private final Object source;
	private final int reach;            // chunks
	private final long distanceSq;      // blocks²
	private final @Nullable RandomSpreadStructurePlacement villages;
	private final Identifier[] villageIds;
	private final Structure[] villageStructures;
	private volatile Memory memory = new Memory(0, new ConcurrentHashMap<>());

	/** Results per candidate for one seed (another seed, a new memo: a late thread does not mix worlds). */
	private record Memory(long seed, ConcurrentHashMap<Long, Boolean> optionValues) {
	}

	/** Public for the tests: distance in blocks (0 = disabled) and the villages' grid (null if none). */
	public ForeignZone(Object source, int distance, @Nullable RandomSpreadStructurePlacement villages, List<Identifier> ids, List<Structure> structures) {
		this.source = source;
		this.reach = distance <= 0 ? 0 : (distance + 15) / 16;
		this.distanceSq = (long) distance * distance;
		this.villages = villages;
		this.villageIds = ids.toArray(new Identifier[0]);
		this.villageStructures = structures.toArray(new Structure[0]);
	}

	/** Table of the structure_set registry in use; built once per world. */
	public static ForeignZone of(RegistryAccess registryAccess) {
		Registry<StructureSet> sets = registryAccess.lookupOrThrow(Registries.STRUCTURE_SET);
		ForeignZone z = cached;
		if (z == null || z.source != sets) {
			z = build(sets, registryAccess);
			cached = z;
		}
		return z;
	}

	private static ForeignZone build(Registry<StructureSet> sets, RegistryAccess registryAccess) {
		int distance = HeraldiaConfig.get().getInt(OPTION);
		LOGGER.info("Heraldia: estructuras de otros mods a {} bloques como mínimo de las de Heraldia{}", distance,
				distance == 0 ? " (desactivado)" : "");
		return withDistance(sets, registryAccess, distance);
	}

	/**
	 * Zone of another distance around the same candidates (Heraldia villages and uniques that really win), with its
	 * own memo: the medium structures use it ({@link MediumStructures}). One per structure_set registry.
	 */
	static ForeignZone withDistance(Registry<StructureSet> sets, RegistryAccess registryAccess, int distance) {
		Registry<Structure> structures = registryAccess.lookupOrThrow(Registries.STRUCTURE);
		RandomSpreadStructurePlacement placement = null;
		List<Identifier> ids = new ArrayList<>();
		List<Structure> list = new ArrayList<>();
		StructureSet set = sets.getValue(VILLAGES);
		if (set != null && set.placement() instanceof GridPlacement g && g.group().equals("aldeas")) {
			placement = g;
			for (StructureSet.StructureSelectionEntry e : set.structures()) {
				Holder<Structure> h = e.structure();
				Identifier id = structures.getKey(h.value());
				if (id != null) {
					ids.add(id);
					list.add(h.value());
				}
			}
		}
		return new ForeignZone(sets, distance, placement, ids, list);
	}

	/** From another mod (neither heraldia nor minecraft). Cheap: one string comparison. */
	public static boolean fromOtherMod(Identifier id) {
		String ns = id.getNamespace();
		return !ns.equals("heraldia") && !ns.equals("minecraft");
	}

	/** Shows above ground (it is not a mineshaft, a dungeon or a stronghold). */
	public static boolean visible(GenerationStep.Decoration step) {
		return !UNDERGROUND.contains(step);
	}

	/** Enabled and in the overworld (Heraldia's structures only spawn there). */
	public boolean active(ResourceKey<Level> dimension) {
		return reach > 0 && dimension == Level.OVERWORLD;
	}

	/**
	 * Heraldia candidates (grid uniques and villages) with their start within the distance of the chunk, as triples
	 * {type, x, z} (type = index of the unique in sep or {@link #VILLAGE}), or null if there are none. No terrain or biomes.
	 */
	public long @Nullable [] nearby(UniqueSeparation sep, long seed, int chunkX, int chunkZ) {
		long[] out = null;
		int n = 0;
		for (int i = -1; i < sep.size(); i++) {
			RandomSpreadStructurePlacement p = i < 0 ? villages : sep.fixed(i) ? null : sep.placement(i);
			if (p == null) {
				continue; // no villages, or Atlantis (AtlantisAnchor already excludes everything next to it)
			}
			int s = p.spacing(), ox = UniqueSeparation.offsetX(p), oz = UniqueSeparation.offsetZ(p);
			for (int gx = Math.floorDiv(chunkX - reach - ox, s), gxMax = Math.floorDiv(chunkX + reach - ox, s); gx <= gxMax; gx++) {
				for (int gz = Math.floorDiv(chunkZ - reach - oz, s), gzMax = Math.floorDiv(chunkZ + reach - oz, s); gz <= gzMax; gz++) {
					ChunkPos c = p.getPotentialStructureChunk(seed, gx * s + ox, gz * s + oz);
					long dx = (c.x() - (long) chunkX) * 16, dz = (c.z() - (long) chunkZ) * 16;
					if (dx * dx + dz * dz > distanceSq || !p.applyAdditionalChunkRestrictions(c.x(), c.z(), seed)) {
						continue;
					}
					if (out == null) {
						out = new long[9];
					} else if (n + 3 > out.length) {
						out = Arrays.copyOf(out, out.length * 2);
					}
					out[n++] = i < 0 ? VILLAGE : i;
					out[n++] = c.x();
					out[n++] = c.z();
				}
			}
		}
		return out == null || n == out.length ? out : Arrays.copyOf(out, n);
	}

	/** One of the nearby candidates really wins (memoized per candidate and seed). */
	public boolean occupied(long[] nearby, UniqueSeparation sep, long seed, UniqueSeparation.Viability unique, Village village) {
		for (int k = 0; k + 2 < nearby.length; k += 3) {
			int type = (int) nearby[k], x = (int) nearby[k + 1], z = (int) nearby[k + 2];
			Memory m = memory;
			if (m.seed != seed) {
				m = new Memory(seed, new ConcurrentHashMap<>());
				memory = m;
			}
			long key = key(type, x, z);
			Boolean v = m.optionValues.get(key);
			if (v == null) {
				v = type == VILLAGE ? village.outcome(x, z) : unique.valid(type, x, z) && !sep.blocked(type, x, z, seed, unique);
				if (m.optionValues.size() > CACHE_MAX) {
					m.optionValues.clear();
				}
				m.optionValues.put(key, v);
			}
			if (v) {
				return true;
			}
		}
		return false;
	}

	/** Real village in the game: some entry of the set allowed by the mod's rules with a valid site (biome and terrain). */
	public Village village(RegistryAccess registryAccess, ChunkGenerator generator, BiomeSource biomeSource, Climate.Sampler sampler,
					   RandomState randomState, StructureTemplateManager templates, long seed, LevelHeightAccessor height,
					   ResourceKey<Level> dimension) {
		return (x, z) -> {
			for (int j = 0; j < villageIds.length; j++) {
				Structure s = villageStructures[j];
				if (HeraldiaConfig.get().villages().allows(villageIds[j], seed, x, z) && !AtlantisAnchor.excludes(villageIds[j], dimension, seed, x, z)
						&& Dimensions.possible(s, biomeSource) && s.findValidGenerationPoint(new Structure.GenerationContext(registryAccess, generator, biomeSource, sampler,
						randomState, templates, seed, new ChunkPos(x, z), height, s.biomes()::contains)).isPresent()) {
					return true;
				}
			}
			return false;
		};
	}

	/** Exact memo key: 24 bits per coordinate (±8 million chunks, more than the world border) and the type. */
	static long key(int type, int x, int z) {
		return (x & 0xFFFFFFL) | (long) (z & 0xFFFFFF) << 24 | (long) (type + 1) << 48;
	}
}
