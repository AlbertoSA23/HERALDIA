package io.github.albertosa23.heraldia.mines;

import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.common.MediumStructures;
import io.github.albertosa23.heraldia.config.GridPlacement;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.config.UniqueSeparation;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import net.minecraft.core.Registry;
import net.minecraft.core.RegistryAccess;
import net.minecraft.core.registries.BuiltInRegistries;
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
 * Mine entrances (heraldia:minas/&lt;size&gt;/&lt;style&gt;/&lt;variant&gt;, tools/gen/mines): one structure_set per size
 * with its heraldia:rejilla grid (group minas/&lt;size&gt;). A candidate is discarded with the mediums' rules
 * ({@link MediumStructures}), without changing theirs:
 * <ul>
 * <li>in the zone of a village or a unique that wins (medianas.distancia_aldeas_unicas_bloques), next to a vanilla
 * or other mod's structure that shows above ground, or inside Atlantis;</li>
 * <li>within medianas.distancia_minima.bloques of a medium that wins ({@link MediumStructures#near}): the mine always yields
 * (the mediums do not know about the mines, so no medium changes place because of them);</li>
 * <li>within that same distance of an entrance of another, higher-ranked size that survives ({@link UniqueSeparation},
 * the uniques' range recursion). Two of the same size are already kept apart by their grid.</li>
 * </ul>
 * It only runs in an entrance's candidate chunks (one per size every 48-120 chunks per side); the viabilities (the
 * hillside search) and the decisions are memoized per seed. Immutable except the memos.
 */
public final class Mines {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	public static final String PREFIX = "minas/";
	public static final String ENABLED = "minas.entradas.activado", SEPARATION = "minas.entradas.separacion_bloques",
			MULTIPLIER = "minas.vanilla.multiplicador";
	private static final int CACHE_MAX = 1 << 12;
	private static volatile @Nullable Mines cached;

	private final Object source;
	private final Map<Identifier, Integer> typeOf;
	private final Identifier[] types;
	private final Structure[][] styles;
	private final UniqueSeparation between;
	private final int distance;
	private volatile Memory memory = new Memory(0, new ConcurrentHashMap<>(), new ConcurrentHashMap<>());

	private record Memory(long seed, ConcurrentHashMap<Long, Boolean> decisions, ConcurrentHashMap<Long, Boolean> exits) {
	}

	/** Public for the tests: sizes, ids and structures of each, their grids and the minimum distance (blocks). */
	public Mines(Object source, List<Identifier> types, List<List<Identifier>> ids, List<List<Structure>> styles,
				 List<RandomSpreadStructurePlacement> placements, int distance) {
		this.source = source;
		this.types = types.toArray(new Identifier[0]);
		this.styles = new Structure[types.size()][];
		Map<Identifier, Integer> m = new HashMap<>();
		for (int i = 0; i < types.size(); i++) {
			for (Identifier id : ids.get(i)) {
				m.put(id, i);
			}
			this.styles[i] = styles.get(i).toArray(new Structure[0]);
		}
		this.typeOf = Map.copyOf(m);
		this.distance = distance;
		this.between = new UniqueSeparation(source, types, Collections.nCopies(types.size(), (Structure) null), placements,
				Collections.nCopies(types.size(), false), distance > 0, distance);
	}

	/** Structure type and placement of the multiplied vanilla mineshafts. One line in Heraldia. */
	public static void register() {
		Registry.register(BuiltInRegistries.STRUCTURE_TYPE, Heraldia.id("mina_entrada"), MineEntranceStructure.TYPE);
		Registry.register(BuiltInRegistries.STRUCTURE_PLACEMENT, Heraldia.id("minas_vanilla"), VanillaMinesPlacement.CODEC);
	}

	/** Cheap: only heraldia:minas/* get past here. */
	public static boolean isMine(Identifier id) {
		return id.getNamespace().equals(Heraldia.MOD_ID) && id.getPath().startsWith(PREFIX);
	}

	public static Mines of(RegistryAccess access) {
		Registry<StructureSet> sets = access.lookupOrThrow(Registries.STRUCTURE_SET);
		Mines t = cached;
		if (t == null || t.source != sets) {
			t = build(sets, access);
			cached = t;
		}
		return t;
	}

	private static Mines build(Registry<StructureSet> sets, RegistryAccess access) {
		HeraldiaConfig cfg = HeraldiaConfig.get();
		int distance = cfg.getInt(MediumStructures.DISTANCE);
		Mines m = family(sets, access, PREFIX, distance);
		LOGGER.info("Heraldia: entradas a mina: {}, {} tamaños, cada {} bloques las pequeñas, a {} bloques de aldeas y únicas y a {} de "
						+ "las medianas y entre ellas; minas vanilla x{}", cfg.getBool(ENABLED) ? "activadas" : "desactivadas", m.types(),
				cfg.getInt(SEPARATION), cfg.getInt(MediumStructures.ZONE), distance, cfg.getDouble(MULTIPLIER));
		return m;
	}

	/**
	 * The rule of a family of structures with a heraldia:rejilla grid of group "&lt;prefix&gt;&lt;type&gt;" (the mines;
	 * also the lighthouses and shipwrecks of coast/Coast, which reuse it as is): one type per structure_set, kept apart
	 * from each other by {@code distance}. Without writing to the log.
	 */
	public static Mines family(Registry<StructureSet> sets, RegistryAccess access, String prefix, int distance) {
		Registry<Structure> structures = access.lookupOrThrow(Registries.STRUCTURE);
		List<Identifier> types = new ArrayList<>();
		List<List<Identifier>> ids = new ArrayList<>();
		List<List<Structure>> styles = new ArrayList<>();
		List<RandomSpreadStructurePlacement> placements = new ArrayList<>();
		sets.listElements().forEach(set -> {
			if (set.value().placement() instanceof GridPlacement g && g.group().startsWith(prefix)) {
				List<Identifier> i = new ArrayList<>();
				List<Structure> s = new ArrayList<>();
				for (StructureSet.StructureSelectionEntry e : set.value().structures()) {
					Identifier id = structures.getKey(e.structure().value());
					if (id != null) {
						i.add(id);
						s.add(e.structure().value());
					}
				}
				types.add(Identifier.fromNamespaceAndPath(Heraldia.MOD_ID, g.group()));
				ids.add(i);
				styles.add(s);
				placements.add(g);
			}
		});
		return new Mines(sets, types, ids, styles, placements, distance);
	}

	public int types() {
		return types.length;
	}

	public int type(Identifier id) {
		Integer i = typeOf.get(id);
		return i == null ? -1 : i;
	}

	public Identifier typeId(int i) {
		return types[i];
	}

	/** In the game: does some style of size j win there (biome and hillside)? Memoized: it is the hillside search. */
	public MediumStructures.Styles styles(RegistryAccess access, ChunkGenerator generator, BiomeSource biomeSource, Climate.Sampler sampler,
									 RandomState randomState, StructureTemplateManager templates, long seed, LevelHeightAccessor height) {
		return (j, x, z) -> {
			Memory m = memory(seed);
			long key = key(j, x, z);
			Boolean v = m.exits.get(key);
			if (v == null) {
				v = false;
				for (Structure s : styles[j]) {
					if (s.findValidGenerationPoint(new Structure.GenerationContext(access, generator, biomeSource, sampler, randomState,
							templates, seed, new ChunkPos(x, z), height, s.biomes()::contains)).isPresent()) {
						v = true;
						break;
					}
				}
				if (m.exits.size() > CACHE_MAX) {
					m.exits.clear();
				}
				m.exits.put(key, v);
			}
			return v;
		};
	}

	/** The entrance id starting at (chunkX, chunkZ) does not win (see the class). Only for mines (isMine); the rest, false. */
	public boolean rejects(Identifier id, int chunkX, int chunkZ, long seed, RegistryAccess access, ChunkGenerator generator,
						   BiomeSource biomeSource, Climate.Sampler sampler, RandomState randomState, StructureTemplateManager templates,
						   LevelHeightAccessor height, ResourceKey<Level> dimension) {
		int i = type(id);
		if (i < 0 || dimension != Level.OVERWORLD) {
			return false;
		}
		MediumStructures med = MediumStructures.of(access);
		MediumStructures.Context c = med.context(id, access, generator, biomeSource, sampler, randomState, templates, seed, height, dimension);
		return rejects(i, chunkX, chunkZ, seed, c.zone(), styles(access, generator, biomeSource, sampler, randomState, templates, seed, height),
				c.atlantis(), (x, z) -> med.near(x, z, distance, seed, c));
	}

	/** Pure logic (tests): zone, styles, Atlantis and nearby mediums injected. Memoized per size, chunk and seed. */
	public boolean rejects(int i, int chunkX, int chunkZ, long seed, MediumStructures.Zone zone, MediumStructures.Styles styles, MediumStructures.Zone atlantis,
						   MediumStructures.Zone mediums) {
		Memory m = memory(seed);
		long key = key(i, chunkX, chunkZ);
		Boolean v = m.decisions.get(key);
		if (v == null) {
			v = zone.occupied(chunkX, chunkZ) || mediums.occupied(chunkX, chunkZ) || between.blocked(i, chunkX, chunkZ, seed,
					(j, x, z) -> !atlantis.occupied(x, z) && styles.outcome(j, x, z) && !zone.occupied(x, z) && !mediums.occupied(x, z));
			if (m.decisions.size() > CACHE_MAX) {
				m.decisions.clear();
			}
			m.decisions.put(key, v);
		}
		return v;
	}

	/**
	 * Does an entrance (of any type of the family) win within `blocks` of the chunk? The lighthouses and shipwrecks use it
	 * (coast/Coast), which yield their site to the mines without the latter knowing about them: so their rule does not change. Pure logic
	 * (tests): with the zone, the styles, Atlantis and the nearby mediums of {@link #rejects(int, int, int, long,
	 * MediumStructures.Zone, MediumStructures.Styles, MediumStructures.Zone, MediumStructures.Zone)}.
	 */
	public boolean near(int chunkX, int chunkZ, int blocks, long seed, MediumStructures.Zone zone, MediumStructures.Styles styles,
						 MediumStructures.Zone atlantis, MediumStructures.Zone mediums) {
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
					if (!atlantis.occupied(m.x(), m.z()) && styles.outcome(j, m.x(), m.z())
							&& !rejects(j, m.x(), m.z(), seed, zone, styles, atlantis, mediums)) {
						return true;
					}
				}
			}
		}
		return false;
	}

	public int distance() {
		return distance;
	}

	private Memory memory(long seed) {
		Memory m = memory;
		if (m.seed != seed) {
			m = new Memory(seed, new ConcurrentHashMap<>(), new ConcurrentHashMap<>());
			memory = m;
		}
		return m;
	}

	static long key(int type, int x, int z) {
		return (x & 0xFFFFFFL) | (long) (z & 0xFFFFFF) << 24 | (long) (type + 1) << 48;
	}
}
