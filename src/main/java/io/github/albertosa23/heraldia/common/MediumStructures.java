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
 * Estructuras medianas (heraldia:medianas/&lt;tipo&gt;/&lt;estilo&gt;, tools/gen/medianas): un structure_set por tipo con
 * su rejilla heraldia:rejilla (grupo medianas/&lt;tipo&gt;) y un estilo por bioma. Una candidata se descarta:
 * <ul>
 * <li>a menos de medianas.distancia_aldeas_unicas_bloques de una aldea o una única de Heraldia que sale de verdad (la
 * zona de {@link ForeignZone}, con su distancia y su memoria): nunca dentro de una aldea, una única o la isla del corsario
 * (la Atlántida ya la excluye {@link AtlantisAnchor});</li>
 * <li>a menos de medianas.distancia_minima.bloques de otra mediana de rango mayor que sobrevive: la regla de la distancia
 * mínima entre únicas ({@link UniqueSeparation}, recursión por rangos crecientes), con un tipo por entrada y su
 * viabilidad = algún estilo sale ahí (bioma y terreno) y no cae en la zona anterior.</li>
 * </ul>
 * Además cede el sitio a las estructuras que asoman a la superficie, vanilla o de otros mods, de rejilla random_spread
 * (puestos de saqueadores, templos, portales en ruinas, aldeas de otros mods...): se descarta si una de ellas sale a menos
 * de {@link #VANILLA_BLOCKS} bloques (vanilla) o {@link #FOREIGN_BLOCKS} (de otro mod) (su candidata y findValidGenerationPoint; sin mirar su frecuencia ni sus propias
 * exclusiones, así que cede de más, nunca de menos). Así ninguna mediana sale dentro de otra estructura y las de otros
 * mods no tienen que saber de ellas (solo las aldeas y las únicas, mucho mayores, les quitan el sitio: {@link ForeignZone}).
 * La zona de exclusión frente a las aldeas vanilla va en el propio structure_set (exclusion_zone). Coste: solo en los
 * chunks candidatos de una mediana (uno por tipo cada ~40 x 40 chunks) y lo caro en memoria por candidata y semilla.
 * Inmutable salvo las memorias (ConcurrentHashMap): la consultan los hilos de generación a la vez.
 */
public final class MediumStructures {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	public static final String PREFIX = "medianas/";
	public static final String ENABLED = "medianas.activadas", FREQUENCY = "medianas.frecuencia_porcentaje",
			DISTANCE = "medianas.distancia_minima.bloques", ZONE = "medianas.distancia_aldeas_unicas_bloques";
	private static final int CACHE_MAX = 1 << 12;
	/** Distancia (bloques, entre inicios) a la que una mediana cede el sitio a una estructura de otro mod (pueden ser aldeas
	 *  enteras) y a una vanilla (pequeñas salvo las aldeas, que ya tienen su zona de exclusión, y las mansiones, rarísimas). */
	public static final int FOREIGN_BLOCKS = 128, VANILLA_BLOCKS = 80;
	private static volatile @Nullable MediumStructures cached;

	/** ¿Sale algún estilo del tipo j en ese chunk (bioma y terreno)? En el juego, findValidGenerationPoint. */
	@FunctionalInterface
	public interface Styles {
		boolean outcome(int type, int chunkX, int chunkZ);
	}

	private final Object source;
	private final Map<Identifier, Integer> typeOf;          // estructura (estilo) -> tipo
	private final Identifier[] types;                       // heraldia:medianas/<tipo>
	private final Structure[][] styles;
	private final UniqueSeparation between;
	private final @Nullable ForeignZone zone;
	private final Foreign[] foreign;
	/** Tipos que ceden el sitio a las entradas a mina (etiqueta #heraldia:medianas/ceden_a_minas) y las rejillas de las minas. */
	private final boolean[] yieldToMines;
	private final Foreign[] mines;
	/** Etiqueta de estructura de los estilos de un tipo que cede a las minas (medianas/<id>.CEDE_A_MINAS en el generador). */
	public static final String YIELD_TO_MINES = "medianas/ceden_a_minas";
	/** En la memoria de las ajenas, las candidatas de mina van con su índice desplazado (no chocan con las ajenas). */
	private static final int MINE_KEY = 1000;
	private volatile Memory memory = new Memory(0, new ConcurrentHashMap<>(), new ConcurrentHashMap<>());
	/** Las del Nether y el End: la misma tabla con su propia memoria (y su propia zona), una por dimensión. */
	private final ConcurrentHashMap<ResourceKey<Level>, MediumStructures> others = new ConcurrentHashMap<>();

	/** Por semilla: decisión por candidata de mediana y si sale cada candidata de estructura ajena. */
	private record Memory(long seed, ConcurrentHashMap<Long, Boolean> optionValues, ConcurrentHashMap<Long, Boolean> foreign) {
	}

	/** Rejilla de una estructura ajena (vanilla o de otro mod), sus estructuras que asoman y la distancia a la que se le
	 *  cede el sitio (bloques). */
	public record Foreign(RandomSpreadStructurePlacement placement, Structure[] structures, int blocks) {
	}

	/** Pública para las pruebas: zona null = sin aldeas ni únicas alrededor (o desactivada); sin estructuras ajenas. */
	public MediumStructures(Object source, List<Identifier> types, List<List<Identifier>> ids, List<List<Structure>> styles,
					List<RandomSpreadStructurePlacement> placements, @Nullable ForeignZone zone, int distance) {
		this(source, types, ids, styles, placements, zone, distance, List.of());
	}

	/** Pública para las pruebas: con las rejillas de las estructuras ajenas a las que cede el sitio. */
	public MediumStructures(Object source, List<Identifier> types, List<List<Identifier>> ids, List<List<Structure>> styles,
					List<RandomSpreadStructurePlacement> placements, @Nullable ForeignZone zone, int distance, List<Foreign> foreign) {
		this(source, types, ids, styles, placements, zone, distance, foreign, new boolean[types.size()], List.of());
	}

	/** Pública para las pruebas: además, qué tipos ceden el sitio a las entradas a mina y las rejillas de las minas. */
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

	/** Barato: solo las heraldia:medianas/* pasan de aquí. */
	public static boolean isMedium(Identifier id) {
		return id.getNamespace().equals("heraldia") && id.getPath().startsWith(PREFIX);
	}

	/** Tabla del registro de structure_set en uso; se construye una vez por mundo. */
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

	/** Rejilla de un structure_set vanilla o de otro mod con estructuras que asoman (random_spread), o null. */
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

	/** Tipo de una estructura (estilo) o -1. */
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

	/** En el juego: la misma comprobación que /locate (findValidGenerationPoint con su bioma) para cada estilo. */
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

	/** findValidGenerationPoint de una estructura en un chunk (lo que mira /locate). */
	private static Outcome outcome(RegistryAccess access, ChunkGenerator generator, BiomeSource biomeSource, Climate.Sampler sampler,
							 RandomState randomState, StructureTemplateManager templates, long seed, LevelHeightAccessor height) {
		return (s, cx, cz) -> s.findValidGenerationPoint(new Structure.GenerationContext(access, generator, biomeSource, sampler,
				randomState, templates, seed, new ChunkPos(cx, cz), height, s.biomes()::contains)).isPresent();
	}

	/**
	 * La mediana id con inicio en (chunkX, chunkZ) no sale: cae en la zona de una aldea o una única que sale de verdad,
	 * o junto a otra mediana de rango mayor que sobrevive. Solo para medianas (esMediana); el resto, falso. En cualquier
	 * dimensión: las del Nether y el End (heraldia:dimension) siguen las mismas reglas con las de su dimensión (las
	 * demás no salen ahí: {@link Dimensions#possible}).
	 */
	public boolean rejects(Identifier id, int chunkX, int chunkZ, long seed, RegistryAccess access, ChunkGenerator generator,
						   BiomeSource biomeSource, Climate.Sampler sampler, RandomState randomState, StructureTemplateManager templates,
						   LevelHeightAccessor height, ResourceKey<Level> dimension) {
		int i = type(id);
		if (i < 0) {
			return false;
		}
		if (dimension != Level.OVERWORLD) { // memoria aparte: un mismo chunk no vale lo mismo en otra dimensión
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

	/** Lo que decide si sale una mediana: la zona de aldeas, únicas y estructuras ajenas, sus estilos y la Atlántida. */
	public record Context(Zone zone, Styles styles, Zone atlantis) {
	}

	/** El contexto del juego (las mismas comprobaciones que la generación y /locate); id: la estructura que pregunta. */
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
	 * ¿Sale una mediana (de cualquier tipo) a menos de `bloques` del chunk? La usan las entradas a mina (comun/Minas en
	 * minas/), que ceden el sitio a las medianas sin que estas sepan de ellas: así su regla no cambia. Pública para las
	 * pruebas (con el contexto inyectado).
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

	/** ¿Cae el chunk en la zona de una aldea o una única que sale? */
	@FunctionalInterface
	public interface Zone {
		boolean occupied(int chunkX, int chunkZ);
	}

	/** ¿Sale la estructura (ajena) con inicio en ese chunk? En el juego, findValidGenerationPoint. */
	@FunctionalInterface
	public interface Outcome {
		boolean outcome(Structure structure, int chunkX, int chunkZ);
	}

	/** Lógica pura (pruebas): zona, estilos y Atlántida inyectados. En memoria por tipo, candidata y semilla. */
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
		if (m.seed != seed) { // otra semilla, memoria nueva: un hilo atrasado no mezcla mundos
			m = new Memory(seed, new ConcurrentHashMap<>(), new ConcurrentHashMap<>());
			memory = m;
		}
		return m;
	}

	/**
	 * Sale cerca del chunk (a VANILLA_BLOQUES o AJENAS_BLOQUES) una estructura que asoma, vanilla o de otro mod (de rejilla
	 * random_spread).
	 * Barato salvo junto a una candidata (findValidGenerationPoint), que queda en memoria. Pública para las pruebas.
	 */
	public boolean yieldsToForeign(int chunkX, int chunkZ, long seed, Outcome outcome) {
		return yields(foreign, 0, chunkX, chunkZ, seed, outcome);
	}

	/**
	 * ¿Cede el tipo j el sitio a una entrada a mina? Solo los de #heraldia:medianas/ceden_a_minas (las chozas de mago, que
	 * buscan el mismo interior de los mismos biomas que las minas: sin esto, cada una le quitaría el sitio a la mina de al
	 * lado, porque las minas ceden siempre a las medianas). Sale una candidata de mina (findValidGenerationPoint, sin sus
	 * propias reglas: cede de más, nunca de menos) a menos de medianas.distancia_minima.bloques. Sin ciclo: las minas no
	 * miran a las medianas para eso. Pública para las pruebas.
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
