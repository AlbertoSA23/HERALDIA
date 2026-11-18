package io.github.albertosa23.heraldia.config;

import io.github.albertosa23.heraldia.dimensions.Dimensions;
import io.github.albertosa23.heraldia.uniques.atlantis.AtlantisAnchor;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
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
import net.minecraft.world.level.levelgen.RandomState;
import net.minecraft.world.level.levelgen.structure.Structure;
import net.minecraft.world.level.levelgen.structure.StructureSet;
import net.minecraft.world.level.levelgen.structure.placement.RandomSpreadStructurePlacement;
import net.minecraft.world.level.levelgen.structure.templatesystem.StructureTemplateManager;
import org.jspecify.annotations.Nullable;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Minimum distance between different unique structures (heraldia:unicas/*), without walking the world or saving data.
 * For a candidate, the cells of the other grids within N blocks are computed (the same
 * getPotentialStructureChunk the game uses) and the candidate is discarded if a higher-ranked one <em>survives</em>:
 * it would really generate (findValidGenerationPoint, the same computation as /locate, with its real biome) and is not discarded
 * in turn by another even higher-ranked one. The rank is a hash of the seed, the type and the chunk (fair share between types);
 * the self-placed ones (Atlantis) always win. Since the recursion follows strictly increasing ranks, the
 * relation is the same whoever evaluates it: two survivors are never within N and every discarded one has
 * a survivor nearby. Immutable once built: several generation threads query it at once.
 * <p>With unicas.rejilla_compatible ({@link GridPlacement#legacy()}) the order has one more tier: self-placed,
 * then the uniques of the old grid and then the new ones; the rank only breaks ties within the same tier. An
 * old one does not see the new ones (it is discarded exactly as in 0.1.0, where they did not exist: the already generated ones stay
 * where /locate looks for them) and a new one is discarded if it falls within N of an old one that survives (it does not spawn on top of
 * an already generated one). Without the option they are all in the same tier and nothing changes.
 */
public final class UniqueSeparation {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	private static volatile @Nullable UniqueSeparation cached;

	/** Whether structure index would spawn in that chunk not counting the separation (biome, terrain, mod rules). */
	@FunctionalInterface
	public interface Viability {
		boolean valid(int index, int chunkX, int chunkZ);

		/** The structure can spawn in this dimension at all (a structure that always wins, Atlantis, only blocks there). */
		default boolean inDimension(int index) {
			return true;
		}
	}

	private final Object source;
	private final Identifier[] ids;
	private final @Nullable Structure[] structures;
	private final RandomSpreadStructurePlacement[] placements;
	private final long[] salts;
	private final boolean[] always;
	private final byte[] tier; // 2 self-placed, 1 old grid, 0 the rest: the tier wins and then the rank
	private final Map<Identifier, Integer> index;
	private final boolean enabled;
	private final int reachChunks;
	private final long distanceSq;

	/** Table of the unique structures: always = self-placed (always wins). Public for the tests. */
	public UniqueSeparation(Object source, List<Identifier> ids, List<@Nullable Structure> structures,
							List<RandomSpreadStructurePlacement> placements, List<Boolean> always, boolean enabled, int distance) {
		int n = ids.size();
		this.source = source;
		this.ids = ids.toArray(new Identifier[0]);
		this.structures = structures.toArray(new Structure[0]);
		this.placements = placements.toArray(new RandomSpreadStructurePlacement[0]);
		this.salts = new long[n];
		this.always = new boolean[n];
		this.tier = new byte[n];
		Map<Identifier, Integer> idx = new HashMap<>();
		for (int i = 0; i < n; i++) {
			this.salts[i] = mix(this.ids[i].toString().hashCode() * 0x9E3779B97F4A7C15L);
			this.always[i] = always.get(i);
			this.tier[i] = (byte) (this.always[i] ? 2 : this.placements[i] instanceof GridPlacement g && g.legacy() ? 1 : 0);
			idx.put(this.ids[i], i);
		}
		this.index = Map.copyOf(idx);
		this.enabled = enabled && distance > 0;
		this.reachChunks = (distance + 15) / 16;
		this.distanceSq = (long) distance * distance;
	}

	/** Cheap and allocation-free: only heraldia:unicas/* get past here. */
	public static boolean isUnique(Identifier id) {
		return id.getNamespace().equals("heraldia") && id.getPath().startsWith("unicas/");
	}

	/** Table of the structure_set registry in use; built once per world. */
	public static UniqueSeparation of(RegistryAccess registryAccess) {
		Registry<StructureSet> sets = registryAccess.lookupOrThrow(Registries.STRUCTURE_SET);
		UniqueSeparation t = cached;
		if (t == null || t.source != sets) {
			t = build(sets, registryAccess);
			cached = t;
		}
		return t;
	}

	private static UniqueSeparation build(Registry<StructureSet> sets, RegistryAccess registryAccess) {
		Registry<Structure> structureRegistry = registryAccess.lookupOrThrow(Registries.STRUCTURE);
		List<Identifier> ids = new ArrayList<>();
		List<@Nullable Structure> structures = new ArrayList<>();
		List<RandomSpreadStructurePlacement> placements = new ArrayList<>();
		List<Boolean> always = new ArrayList<>();
		sets.listElements().forEach(set -> {
			if (!(set.value().placement() instanceof RandomSpreadStructurePlacement placement)) {
				return;
			}
			for (StructureSet.StructureSelectionEntry e : set.value().structures()) {
				Holder<Structure> h = e.structure();
				Identifier id = structureRegistry.getKey(h.value());
				if (id != null && isUnique(id) && !ids.contains(id)) {
					ids.add(id);
					structures.add(h.value());
					placements.add(placement);
					always.add(!(placement instanceof GridPlacement));
				}
			}
		});
		HeraldiaConfig cfg = HeraldiaConfig.get();
		boolean on = cfg.getBool("unicas.distancia_minima.activada");
		int distance = cfg.getInt("unicas.distancia_minima.bloques");
		long old = placements.stream().filter(p -> p instanceof GridPlacement g && g.legacy()).count();
		LOGGER.info("Heraldia: distancia mínima entre estructuras únicas: {}, {} bloques entre {} estructuras{}",
				on ? "activada" : "desactivada", distance, ids.size(), old > 0 ? " (" + old + " con la rejilla antigua, con prioridad)" : "");
		return new UniqueSeparation(sets, ids, structures, placements, always, on, distance);
	}

	public int indexOf(Identifier id) {
		Integer i = index.get(id);
		return i == null ? -1 : i;
	}

	public int size() {
		return ids.length;
	}

	public RandomSpreadStructurePlacement placement(int i) {
		return placements[i];
	}

	public boolean enabled() {
		return enabled;
	}

	/** Self-placed (Atlantis): it follows no grid and always wins. */
	public boolean fixed(int i) {
		return always[i];
	}

	public Identifier id(int i) {
		return ids[i];
	}

	/** Real viability in the game: the same check as /locate (StructureCheck.canCreateStructure) plus Atlantis.
	 *  A unique from another dimension (Nether, End or the overworld seen from them) does not spawn: it is not assembled. */
	public Viability viability(RegistryAccess registryAccess, ChunkGenerator generator, BiomeSource biomeSource, Climate.Sampler sampler,
							   RandomState randomState, StructureTemplateManager templates, long seed, LevelHeightAccessor height,
							   ResourceKey<Level> dimension) {
		return new Viability() {
			@Override
			public boolean valid(int j, int x, int z) {
				Structure s = structures[j];
				return s != null && !AtlantisAnchor.excludes(ids[j], dimension, seed, x, z) && Dimensions.possible(s, biomeSource)
						&& s.findValidGenerationPoint(new Structure.GenerationContext(registryAccess, generator, biomeSource, sampler, randomState,
						templates, seed, new ChunkPos(x, z), height, s.biomes()::contains)).isPresent();
			}

			@Override
			public boolean inDimension(int j) {
				return structures[j] != null && Dimensions.possible(structures[j], biomeSource);
			}
		};
	}

	/** Candidate i at (chunkX, chunkZ) is discarded: another unique structure that survives falls within N blocks. */
	public boolean blocked(int i, int chunkX, int chunkZ, long seed, Viability viability) {
		return enabled && !always[i] && blockedBy(i, chunkX, chunkZ, rank(i, chunkX, chunkZ, seed), seed, viability, null);
	}

	/**
	 * There is a higher-ranked neighbor that survives. They are tried from higher to lower rank: the highest-ranked one almost never
	 * has neighbors above it in turn, so the recursion ends quickly; the memo avoids repeating viabilities.
	 * It only runs in the candidate chunks of a unique structure (a few per world): the small lists it
	 * allocates are not on the hot generation path.
	 */
	private boolean blockedBy(int i, int cx, int cz, long rank, long seed, Viability viability, @Nullable Map<Long, Boolean> memo) {
		List<long[]> near = null; // {type, x, z, rank}
		for (int j = 0; j < ids.length; j++) {
			if (j == i) {
				continue;
			}
			RandomSpreadStructurePlacement p = placements[j];
			int s = p.spacing(), ox = offsetX(p), oz = offsetZ(p);
			for (int gx = Math.floorDiv(cx - reachChunks - ox, s), gxMax = Math.floorDiv(cx + reachChunks - ox, s); gx <= gxMax; gx++) {
				for (int gz = Math.floorDiv(cz - reachChunks - oz, s), gzMax = Math.floorDiv(cz + reachChunks - oz, s); gz <= gzMax; gz++) {
					ChunkPos c = p.getPotentialStructureChunk(seed, gx * s + ox, gz * s + oz);
					long dx = (c.x() - (long) cx) * 16, dz = (c.z() - (long) cz) * 16;
					if (dx * dx + dz * dz >= distanceSq) {
						continue;
					}
					long r = rank(j, c.x(), c.z(), seed);
					if (tier[j] < tier[i] || tier[j] == tier[i] && (r < rank || r == rank && j < i)
							|| !p.applyAdditionalChunkRestrictions(c.x(), c.z(), seed)) {
						continue; // lower tier or rank, or disabled cell
					}
					if (always[j]) {
						if (viability.inDimension(j)) {
							return true;
						}
						continue; // the Overworld Atlantis does not block a Nether or End unique
					}
					if (near == null) {
						near = new ArrayList<>(4);
					}
					near.add(new long[]{j, c.x(), c.z(), r});
				}
			}
		}
		if (near == null) {
			return false;
		}
		near.sort((a, b) -> tier[(int) a[0]] != tier[(int) b[0]] ? tier[(int) b[0]] - tier[(int) a[0]] : Long.compare(b[3], a[3]));
		if (memo == null) {
			memo = new HashMap<>();
		}
		for (long[] n : near) {
			int j = (int) n[0], x = (int) n[1], z = (int) n[2];
			long key = ChunkPos.pack(x, z) * 31 + j;
			Boolean survives = memo.get(key);
			if (survives == null) {
				survives = viability.valid(j, x, z) && !blockedBy(j, x, z, n[3], seed, viability, memo);
				memo.put(key, survives);
			}
			if (survives) {
				return true;
			}
		}
		return false;
	}

	/** Offset of the grid's origin (the cells of p start at gx * spacing + offsetX). */
	public static int offsetX(RandomSpreadStructurePlacement p) {
		return p instanceof GridPlacement g ? g.offsetX() : 0;
	}

	public static int offsetZ(RandomSpreadStructurePlacement p) {
		return p instanceof GridPlacement g ? g.offsetZ() : 0;
	}

	/** Tiebreak rank: deterministic by seed, type and chunk; the self-placed ones, the maximum. */
	public long rank(int i, int chunkX, int chunkZ, long seed) {
		return always[i] ? Long.MAX_VALUE : mix(seed ^ salts[i] ^ mix(ChunkPos.pack(chunkX, chunkZ)));
	}

	static long mix(long z) { // SplitMix64 finalizer (GridPlacement uses it too)
		z = (z ^ (z >>> 30)) * 0xBF58476D1CE4E5B9L;
		z = (z ^ (z >>> 27)) * 0x94D049BB133111EBL;
		return z ^ (z >>> 31);
	}
}
