package io.github.albertosa23.heraldia.common;

import io.github.albertosa23.heraldia.config.GridPlacement;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.config.UniqueSeparation;
import io.github.albertosa23.heraldia.dimensions.Dimensions;
import io.github.albertosa23.heraldia.uniques.atlantis.AtlantisAnchor;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import net.minecraft.core.Registry;
import net.minecraft.core.RegistryAccess;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.Identifier;
import net.minecraft.resources.ResourceKey;
import net.minecraft.tags.TagKey;
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
 * Medium structures (heraldia:medianas/&lt;type&gt;/&lt;style&gt;, tools/gen/mediums): one structure_set per type with
 * its heraldia:rejilla grid (group medianas/&lt;type&gt;) and one style per biome. A candidate is discarded:
 * <ul>
 * <li>within medianas.distancia_aldeas_unicas_bloques of a Heraldia village or unique that really wins (the
 * {@link ForeignZone} zone, with its distance and its memo): never inside a village, a unique or the corsair's island
 * (Atlantis is already excluded by {@link AtlantisAnchor});</li>
 * <li>within medianas.distancia_minima.bloques of another higher-ranked medium that survives: the uniques' minimum
 * distance rule ({@link UniqueSeparation}, recursion by increasing ranks), with one type per entry and its
 * viability = some style wins there (biome and terrain) and does not fall in the previous zone.</li>
 * </ul>
 * It also yields the site to structures that show above ground, vanilla or from other mods, on a random_spread grid
 * (pillager outposts, temples, ruined portals, other mods' villages...): it is discarded if one of them wins within
 * {@link #VANILLA_BLOCKS} blocks (vanilla) or {@link #FOREIGN_BLOCKS} (another mod) (its candidate and
 * findValidGenerationPoint; without looking at its frequency or its own exclusions, so it yields too much, never too
 * little). So no medium spawns inside another structure and other mods' ones do not have to know about them (only the
 * villages and uniques, much larger, take their site: {@link ForeignZone}).
 * The exclusion zone against vanilla villages is in the structure_set itself (exclusion_zone). Cost: only in the
 * candidate chunks of a medium (one per type every ~40 x 40 chunks) and the expensive part memoized per candidate and seed.
 * Immutable except the memos (ConcurrentHashMap): the generation threads query it at once.
 */
public final class MediumStructures {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	public static final String PREFIX = "medianas/";
	public static final String ENABLED = "medianas.activadas", FREQUENCY = "medianas.frecuencia_porcentaje",
			DISTANCE = "medianas.distancia_minima.bloques", ZONE = "medianas.distancia_aldeas_unicas_bloques";
	private static final int CACHE_MAX = 1 << 12;
	/** Distance (blocks, between starts) at which a medium yields its site to another mod's structure (they can be whole
	 *  villages) and to a vanilla one (small except the villages, which already have their exclusion zone, and the very rare mansions). */
	public static final int FOREIGN_BLOCKS = 128, VANILLA_BLOCKS = 80;
	private static volatile @Nullable MediumStructures cached;

	/** Does some style of type j win in that chunk (biome and terrain)? In the game, findValidGenerationPoint. */
	@FunctionalInterface
	public interface Styles {
		boolean outcome(int type, int chunkX, int chunkZ);
	}

	private final Object source;
	private final Map<Identifier, Integer> typeOf;          // structure (style) -> type
	private final Identifier[] types;                       // heraldia:medianas/<type>
	private final Structure[][] styles;
	private final UniqueSeparation between;
	private final @Nullable ForeignZone zone;
	private final Foreign[] foreign;
	/** Types that yield their site to mine entrances (tag #heraldia:medianas/ceden_a_minas) and the mines' grids. */
	private final boolean[] yieldToMines;
	private final Foreign[] mines;
	/** Structure tag of the styles of a type that yields to mines (mediums/<module>.YIELDS_TO_MINES in the generator). */
	public static final String YIELD_TO_MINES = "medianas/ceden_a_minas";
	/** In the foreign memo, mine candidates carry a shifted index (they do not clash with the foreign ones). */
	private static final int MINE_KEY = 1000;
	private volatile Memory memory = new Memory(0, new ConcurrentHashMap<>(), new ConcurrentHashMap<>());
	/** Those of the Nether and the End: the same table with its own memo (and its own zone), one per dimension. */
	private final ConcurrentHashMap<ResourceKey<Level>, MediumStructures> others = new ConcurrentHashMap<>();

	/** Per seed: decision per medium candidate and whether each foreign structure candidate wins. */
	private record Memory(long seed, ConcurrentHashMap<Long, Boolean> optionValues, ConcurrentHashMap<Long, Boolean> foreign) {
	}

	/** Grid of a foreign structure (vanilla or another mod's), its structures that show above ground and the distance at which
	 *  the site is yielded to it (blocks). */
	public record Foreign(RandomSpreadStructurePlacement placement, Structure[] structures, int blocks) {
	}

	/** Public for the tests: null zone = no villages or uniques around (or disabled); no foreign structures. */
	public MediumStructures(Object source, List<Identifier> types, List<List<Identifier>> ids, List<List<Structure>> styles,
					List<RandomSpreadStructurePlacement> placements, @Nullable ForeignZone zone, int distance) {
		this(source, types, ids, styles, placements, zone, distance, List.of());
	}

	/** Public for the tests: with the grids of the foreign structures it yields its site to. */
	public MediumStructures(Object source, List<Identifier> types, List<List<Identifier>> ids, List<List<Structure>> styles,
					List<RandomSpreadStructurePlacement> placements, @Nullable ForeignZone zone, int distance, List<Foreign> foreign) {
		this(source, types, ids, styles, placements, zone, distance, foreign, new boolean[types.size()], List.of());
	}

	/** Public for the tests: also, which types yield their site to mine entrances and the mines' grids. */
	public MediumStructures(Object source, List<Identifier> types, List<List<Identifier>> ids, List<List<Structure>> styles,
					List<RandomSpreadStructurePlacement> placements, @Nullable ForeignZone zone, int distance, List<Foreign> foreign,
					boolean[] yieldToMines, List<Foreign> mines) {
		this.source = source;
		this.foreign = foreign.toArray(new Foreign[0]);
		this.yieldToMines = yieldToMines.clone();
		this.mines = mines.toArray(new Foreign[0]);

		this.types = types.toArray(new Identifier[0]);
		Map<Identifier, Integer> m = new HashMap<>();
		this.styles = new Structure[types.size()][];
		for (int i = 0; i < types.size(); i++) {
			for (Identifier id : ids.get(i)) {
				m.put(id, i);
			}
			this.styles[i] = styles.get(i).toArray(new Structure[0]);
		}
		this.typeOf = Map.copyOf(m);
		this.zone = zone;
		this.between = new UniqueSeparation(source, types, Collections.nCopies(types.size(), (Structure) null), placements,
				Collections.nCopies(types.size(), false), distance > 0, distance);
	}

	/** Cheap: only heraldia:medianas/* get past here. */
	public static boolean isMedium(Identifier id) {
		return id.getNamespace().equals("heraldia") && id.getPath().startsWith(PREFIX);
	}

	/** Table of the structure_set registry in use; built once per world. */
	public static MediumStructures of(RegistryAccess registryAccess) {
		Registry<StructureSet> sets = registryAccess.lookupOrThrow(Registries.STRUCTURE_SET);
		MediumStructures t = cached;
		if (t == null || t.source != sets) {
			t = build(sets, registryAccess);
			cached = t;
		}
		return t;
	}

	private static MediumStructures build(Registry<StructureSet> sets, RegistryAccess registryAccess) {
		Registry<Structure> structures = registryAccess.lookupOrThrow(Registries.STRUCTURE);
		List<Identifier> types = new ArrayList<>();
		List<List<Identifier>> ids = new ArrayList<>();
		List<List<Structure>> styles = new ArrayList<>();
		List<RandomSpreadStructurePlacement> placements = new ArrayList<>();
		List<Foreign> foreign = new ArrayList<>(), mines = new ArrayList<>();
		List<Boolean> yield = new ArrayList<>();
		TagKey<Structure> yieldTag = TagKey.create(Registries.STRUCTURE, Identifier.fromNamespaceAndPath("heraldia", YIELD_TO_MINES));
		int minesDistance = HeraldiaConfig.get().getInt(DISTANCE);
		sets.listElements().forEach(set -> {
			if (set.value().placement() instanceof GridPlacement g && g.group().startsWith("minas/")) {
				mines.add(new Foreign(g, set.value().structures().stream().map(e -> e.structure().value()).toArray(Structure[]::new),
						minesDistance));
			}
			Foreign a = foreignAt(set.key().identifier(), set.value());
			if (a != null) {
				foreign.add(a);
			}
			if (set.value().placement() instanceof GridPlacement g && g.group().startsWith(PREFIX)) {
				List<Identifier> i = new ArrayList<>();
				List<Structure> s = new ArrayList<>();
				yield.add(set.value().structures().stream().anyMatch(e -> e.structure().is(yieldTag)));
				for (StructureSet.StructureSelectionEntry e : set.value().structures()) {
					Identifier id = structures.getKey(e.structure().value());
					if (id != null) {
						i.add(id);
						s.add(e.structure().value());
					}
				}
				types.add(Identifier.fromNamespaceAndPath("heraldia", g.group()));
				ids.add(i);
				styles.add(s);
				placements.add(g);
			}
		});
		HeraldiaConfig cfg = HeraldiaConfig.get();
		int zone = cfg.getInt(ZONE), distance = cfg.getInt(DISTANCE);
		LOGGER.info("Heraldia: estructuras medianas: {}, {} tipos, frecuencia {} %, a {} bloques de aldeas y únicas y a {} entre ellas; "
						+ "ceden el sitio a {} rejillas de estructuras vanilla o de otros mods", cfg.getBool(ENABLED) ? "activadas" : "desactivadas",
				types.size(), cfg.getInt(FREQUENCY), zone, distance, foreign.size());
		boolean[] yieldToMines = new boolean[yield.size()];
		for (int k = 0; k < yieldToMines.length; k++) {
			yieldToMines[k] = yield.get(k);
		}
		return new MediumStructures(sets, types, ids, styles, placements, ForeignZone.withDistance(sets, registryAccess, zone), distance, foreign,
				yieldToMines, mines);
	}

	/** Grid of a vanilla or other mod's structure_set with structures that show above ground (random_spread), or null. */
	public static @Nullable Foreign foreignAt(Identifier id, StructureSet set) {
		if (id.getNamespace().equals("heraldia") || !(set.placement() instanceof RandomSpreadStructurePlacement p)) {
			return null;
		}
		List<Structure> visible = new ArrayList<>();
		for (StructureSet.StructureSelectionEntry e : set.structures()) {
			if (ForeignZone.visible(e.structure().value().step())) {
				visible.add(e.structure().value());
			}
		}
		return visible.isEmpty() ? null : new Foreign(p, visible.toArray(new Structure[0]),
				id.getNamespace().equals("minecraft") ? VANILLA_BLOCKS : FOREIGN_BLOCKS);
	}

	public int types() {
		return types.length;
	}

	/** Type of a structure (style) or -1. */
	public int type(Identifier id) {
		Integer i = typeOf.get(id);
		return i == null ? -1 : i;
	}

	public Identifier typeId(int i) {
		return types[i];
	}

	public RandomSpreadStructurePlacement placement(int i) {
		return between.placement(i);
	}

	/** In the game: the same check as /locate (findValidGenerationPoint with its biome) for each style. */
	public Styles styles(RegistryAccess access, ChunkGenerator generator, BiomeSource biomeSource, Climate.Sampler sampler,
						   RandomState randomState, StructureTemplateManager templates, long seed, LevelHeightAccessor height) {
		Outcome outcome = outcome(access, generator, biomeSource, sampler, randomState, templates, seed, height);
		return (j, x, z) -> {
			for (Structure s : styles[j]) {
				if (Dimensions.possible(s, biomeSource) && s.findValidGenerationPoint(new Structure.GenerationContext(access, generator, biomeSource, sampler, randomState,
						templates, seed, new ChunkPos(x, z), height, s.biomes()::contains)).isPresent()) {
					return !yieldsToMine(j, x, z, seed, outcome);
				}
			}
			return false;
		};
	}

	/** findValidGenerationPoint of a structure in a chunk (what /locate looks at). */
	private static Outcome outcome(RegistryAccess access, ChunkGenerator generator, BiomeSource biomeSource, Climate.Sampler sampler,
							 RandomState randomState, StructureTemplateManager templates, long seed, LevelHeightAccessor height) {
		return (s, cx, cz) -> s.findValidGenerationPoint(new Structure.GenerationContext(access, generator, biomeSource, sampler,
				randomState, templates, seed, new ChunkPos(cx, cz), height, s.biomes()::contains)).isPresent();
	}

	/**
	 * The medium id starting at (chunkX, chunkZ) does not win: it falls in the zone of a village or a unique that really wins,
	 * or next to another higher-ranked medium that survives. Only for mediums (isMedium); the rest, false. In any
	 * dimension: those of the Nether and the End (heraldia:dimension) follow the same rules with those of their dimension (the
	 * others do not spawn there: {@link Dimensions#possible}).
	 */
	public boolean rejects(Identifier id, int chunkX, int chunkZ, long seed, RegistryAccess access, ChunkGenerator generator,
						   BiomeSource biomeSource, Climate.Sampler sampler, RandomState randomState, StructureTemplateManager templates,
						   LevelHeightAccessor height, ResourceKey<Level> dimension) {
		int i = type(id);
		if (i < 0) {
			return false;
		}
		if (dimension != Level.OVERWORLD) { // separate memo: the same chunk is not worth the same in another dimension
			return others.computeIfAbsent(dimension, d -> build(sets(), access)).rejectsHere(i, id, chunkX, chunkZ, seed, access,
					generator, biomeSource, sampler, randomState, templates, height, dimension);
		}
		return rejectsHere(i, id, chunkX, chunkZ, seed, access, generator, biomeSource, sampler, randomState, templates, height, dimension);
	}

	@SuppressWarnings("unchecked")
	private Registry<StructureSet> sets() {
		return (Registry<StructureSet>) source;
	}

	private boolean rejectsHere(int i, Identifier id, int chunkX, int chunkZ, long seed, RegistryAccess access, ChunkGenerator generator,
								BiomeSource biomeSource, Climate.Sampler sampler, RandomState randomState, StructureTemplateManager templates,
								LevelHeightAccessor height, ResourceKey<Level> dimension) {
		Context c = context(id, access, generator, biomeSource, sampler, randomState, templates, seed, height, dimension);
		return yieldsToMine(i, chunkX, chunkZ, seed, outcome(access, generator, biomeSource, sampler, randomState, templates, seed, height))
				|| rejects(i, chunkX, chunkZ, seed, c.zone(), c.styles(), c.atlantis());
	}

	/** What decides whether a medium wins: the zone of villages, uniques and foreign structures, its styles and Atlantis. */
	public record Context(Zone zone, Styles styles, Zone atlantis) {
	}

	/** The game context (the same checks as generation and /locate); id: the structure asking. */
	public Context context(Identifier id, RegistryAccess access, ChunkGenerator generator, BiomeSource biomeSource,
							 Climate.Sampler sampler, RandomState randomState, StructureTemplateManager templates, long seed,
							 LevelHeightAccessor height, ResourceKey<Level> dimension) {
		UniqueSeparation uniques = UniqueSeparation.of(access);
		UniqueSeparation.Viability unique = uniques.viability(access, generator, biomeSource, sampler, randomState, templates, seed, height, dimension);
		ForeignZone.Village village = zone == null ? null : zone.village(access, generator, biomeSource, sampler, randomState, templates, seed, height, dimension);
		return new Context((x, z) -> zone != null && inZone(uniques, seed, x, z, unique, village)
						|| yieldsToForeign(x, z, seed, (s, cx, cz) -> Dimensions.possible(s, biomeSource) && s.findValidGenerationPoint(new Structure.GenerationContext(access, generator,
						biomeSource, sampler, randomState, templates, seed, new ChunkPos(cx, cz), height, s.biomes()::contains)).isPresent()),
				styles(access, generator, biomeSource, sampler, randomState, templates, seed, height),
				(x, z) -> AtlantisAnchor.excludes(id, dimension, seed, x, z));
	}

	/**
	 * Does a medium (of any type) win within `blocks` of the chunk? The mine entrances use it (common/Mines in
	 * mines/), which yield their site to the mediums without the latter knowing about them: so their rule does not change. Public
	 * for the tests (with the context injected).
	 */
	public boolean near(int chunkX, int chunkZ, int blocks, long seed, Context c) {
		int reach = (blocks + 15) / 16;
		long d2 = (long) blocks * blocks;
		for (int j = 0; j < types.length; j++) {
			RandomSpreadStructurePlacement p = between.placement(j);
			int s = p.spacing(), ox = UniqueSeparation.offsetX(p), oz = UniqueSeparation.offsetZ(p);
			for (int gx = Math.floorDiv(chunkX - reach - ox, s), gxMax = Math.floorDiv(chunkX + reach - ox, s); gx <= gxMax; gx++) {
				for (int gz = Math.floorDiv(chunkZ - reach - oz, s), gzMax = Math.floorDiv(chunkZ + reach - oz, s); gz <= gzMax; gz++) {
					ChunkPos m = p.getPotentialStructureChunk(seed, gx * s + ox, gz * s + oz);
					long dx = (m.x() - (long) chunkX) * 16, dz = (m.z() - (long) chunkZ) * 16;
					if (dx * dx + dz * dz >= d2 || !p.applyAdditionalChunkRestrictions(m.x(), m.z(), seed)) {
						continue;
					}
					if (!c.atlantis().occupied(m.x(), m.z()) && c.styles().outcome(j, m.x(), m.z())
							&& !rejects(j, m.x(), m.z(), seed, c.zone(), c.styles(), c.atlantis())) {
						return true;
					}
				}
			}
		}
		return false;
	}

	/** Does the chunk fall in the zone of a village or a unique that wins? */
	@FunctionalInterface
	public interface Zone {
		boolean occupied(int chunkX, int chunkZ);
	}

	/** Does the (foreign) structure starting in that chunk win? In the game, findValidGenerationPoint. */
	@FunctionalInterface
	public interface Outcome {
		boolean outcome(Structure structure, int chunkX, int chunkZ);
	}

	/** Pure logic (tests): zone, styles and Atlantis injected. Memoized per type, candidate and seed. */
	public boolean rejects(int i, int chunkX, int chunkZ, long seed, Zone zone, Styles styles, Zone atlantis) {
		Memory m = memory(seed);
		long key = ForeignZone.key(i, chunkX, chunkZ);
		Boolean v = m.optionValues.get(key);
		if (v == null) {
			v = zone.occupied(chunkX, chunkZ) || between.blocked(i, chunkX, chunkZ, seed,
					(j, x, z) -> !atlantis.occupied(x, z) && styles.outcome(j, x, z) && !zone.occupied(x, z));
			if (m.optionValues.size() > CACHE_MAX) {
				m.optionValues.clear();
			}
			m.optionValues.put(key, v);
		}
		return v;
	}

	private Memory memory(long seed) {
		Memory m = memory;
		if (m.seed != seed) { // another seed, a new memo: a late thread does not mix worlds
			m = new Memory(seed, new ConcurrentHashMap<>(), new ConcurrentHashMap<>());
			memory = m;
		}
		return m;
	}

	/**
	 * Does a structure that shows above ground, vanilla or another mod's (on a random_spread grid), win near the chunk
	 * (within VANILLA_BLOCKS or FOREIGN_BLOCKS)?
	 * Cheap except next to a candidate (findValidGenerationPoint), which is memoized. Public for the tests.
	 */
	public boolean yieldsToForeign(int chunkX, int chunkZ, long seed, Outcome outcome) {
		return yields(foreign, 0, chunkX, chunkZ, seed, outcome);
	}

	/**
	 * Does type j yield its site to a mine entrance? Only those of #heraldia:medianas/ceden_a_minas (the wizard huts, which
	 * look for the same interior of the same biomes as the mines: without this, each would take the site of the neighboring
	 * mine, because the mines always yield to the mediums). A mine candidate wins (findValidGenerationPoint, without its
	 * own rules: it yields too much, never too little) within medianas.distancia_minima.bloques. No cycle: the mines do not
	 * look at the mediums for that. Public for the tests.
	 */
	public boolean yieldsToMine(int j, int chunkX, int chunkZ, long seed, Outcome outcome) {
		return j >= 0 && j < yieldToMines.length && yieldToMines[j] && yields(mines, MINE_KEY, chunkX, chunkZ, seed, outcome);
	}

	private boolean yields(Foreign[] foreign, int base, int chunkX, int chunkZ, long seed, Outcome outcome) {
		for (int k = 0; k < foreign.length; k++) {
			RandomSpreadStructurePlacement p = foreign[k].placement;
			int foreignReach = (foreign[k].blocks + 15) / 16;
			long d2 = (long) foreign[k].blocks * foreign[k].blocks;
			int s = p.spacing(), ox = UniqueSeparation.offsetX(p), oz = UniqueSeparation.offsetZ(p);
			for (int gx = Math.floorDiv(chunkX - foreignReach - ox, s), gxMax = Math.floorDiv(chunkX + foreignReach - ox, s); gx <= gxMax; gx++) {
				for (int gz = Math.floorDiv(chunkZ - foreignReach - oz, s), gzMax = Math.floorDiv(chunkZ + foreignReach - oz, s); gz <= gzMax; gz++) {
					ChunkPos c = p.getPotentialStructureChunk(seed, gx * s + ox, gz * s + oz);
					long dx = (c.x() - (long) chunkX) * 16, dz = (c.z() - (long) chunkZ) * 16;
					if (dx * dx + dz * dz > d2 || !p.applyAdditionalChunkRestrictions(c.x(), c.z(), seed)) {
						continue;
					}
					Memory m = memory(seed);
					long key = ForeignZone.key(base + k, c.x(), c.z());
					Boolean v = m.foreign.get(key);
					if (v == null) {
						v = false;
						for (Structure st : foreign[k].structures) {
							if (outcome.outcome(st, c.x(), c.z())) {
								v = true;
								break;
							}
						}
						if (m.foreign.size() > CACHE_MAX) {
							m.foreign.clear();
						}
						m.foreign.put(key, v);
					}
					if (v) {
						return true;
					}
				}
			}
		}
		return false;
	}

	private boolean inZone(UniqueSeparation uniques, long seed, int x, int z, UniqueSeparation.Viability unique, ForeignZone.Village village) {
		long[] near = zone.nearby(uniques, seed, x, z);
		return near != null && zone.occupied(near, uniques, seed, unique, village);
	}
}
