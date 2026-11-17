package io.github.albertosa23.heraldia.comun;

import io.github.albertosa23.heraldia.config.GridPlacement;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.config.UniqueSeparation;
import io.github.albertosa23.heraldia.unicas.atlantida.AtlantisAnchor;
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
 * zona de {@link ZonaAjenas}, con su distancia y su memoria): nunca dentro de una aldea, una única o la isla del corsario
 * (la Atlántida ya la excluye {@link AtlantisAnchor});</li>
 * <li>a menos de medianas.distancia_minima.bloques de otra mediana de rango mayor que sobrevive: la regla de la distancia
 * mínima entre únicas ({@link UniqueSeparation}, recursión por rangos crecientes), con un tipo por entrada y su
 * viabilidad = algún estilo sale ahí (bioma y terreno) y no cae en la zona anterior.</li>
 * </ul>
 * Además cede el sitio a las estructuras que asoman a la superficie, vanilla o de otros mods, de rejilla random_spread
 * (puestos de saqueadores, templos, portales en ruinas, aldeas de otros mods...): se descarta si una de ellas sale a menos
 * de {@link #VANILLA_BLOQUES} bloques (vanilla) o {@link #AJENAS_BLOQUES} (de otro mod) (su candidata y findValidGenerationPoint; sin mirar su frecuencia ni sus propias
 * exclusiones, así que cede de más, nunca de menos). Así ninguna mediana sale dentro de otra estructura y las de otros
 * mods no tienen que saber de ellas (solo las aldeas y las únicas, mucho mayores, les quitan el sitio: {@link ZonaAjenas}).
 * La zona de exclusión frente a las aldeas vanilla va en el propio structure_set (exclusion_zone). Coste: solo en los
 * chunks candidatos de una mediana (uno por tipo cada ~40 x 40 chunks) y lo caro en memoria por candidata y semilla.
 * Inmutable salvo las memorias (ConcurrentHashMap): la consultan los hilos de generación a la vez.
 */
public final class Medianas {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	public static final String PREFIJO = "medianas/";
	public static final String ACTIVADAS = "medianas.activadas", FRECUENCIA = "medianas.frecuencia_porcentaje",
			DISTANCIA = "medianas.distancia_minima.bloques", ZONA = "medianas.distancia_aldeas_unicas_bloques";
	private static final int CACHE_MAX = 1 << 12;
	/** Distancia (bloques, entre inicios) a la que una mediana cede el sitio a una estructura de otro mod (pueden ser aldeas
	 *  enteras) y a una vanilla (pequeñas salvo las aldeas, que ya tienen su zona de exclusión, y las mansiones, rarísimas). */
	public static final int AJENAS_BLOQUES = 128, VANILLA_BLOQUES = 80;
	private static volatile @Nullable Medianas cached;

	/** ¿Sale algún estilo del tipo j en ese chunk (bioma y terreno)? En el juego, findValidGenerationPoint. */
	@FunctionalInterface
	public interface Estilos {
		boolean sale(int tipo, int chunkX, int chunkZ);
	}

	private final Object source;
	private final Map<Identifier, Integer> tipoDe;          // estructura (estilo) -> tipo
	private final Identifier[] tipos;                       // heraldia:medianas/<tipo>
	private final Structure[][] estilos;
	private final UniqueSeparation entre;
	private final @Nullable ZonaAjenas zona;
	private final Ajena[] ajenas;
	/** Tipos que ceden el sitio a las entradas a mina (etiqueta #heraldia:medianas/ceden_a_minas) y las rejillas de las minas. */
	private final boolean[] cedenMinas;
	private final Ajena[] minas;
	/** Etiqueta de estructura de los estilos de un tipo que cede a las minas (medianas/<id>.CEDE_A_MINAS en el generador). */
	public static final String CEDEN_A_MINAS = "medianas/ceden_a_minas";
	/** En la memoria de las ajenas, las candidatas de mina van con su índice desplazado (no chocan con las ajenas). */
	private static final int MINA_CLAVE = 1000;
	private volatile Memoria memoria = new Memoria(0, new ConcurrentHashMap<>(), new ConcurrentHashMap<>());

	/** Por semilla: decisión por candidata de mediana y si sale cada candidata de estructura ajena. */
	private record Memoria(long seed, ConcurrentHashMap<Long, Boolean> valores, ConcurrentHashMap<Long, Boolean> ajenas) {
	}

	/** Rejilla de una estructura ajena (vanilla o de otro mod), sus estructuras que asoman y la distancia a la que se le
	 *  cede el sitio (bloques). */
	public record Ajena(RandomSpreadStructurePlacement placement, Structure[] structures, int bloques) {
	}

	/** Pública para las pruebas: zona null = sin aldeas ni únicas alrededor (o desactivada); sin estructuras ajenas. */
	public Medianas(Object source, List<Identifier> tipos, List<List<Identifier>> ids, List<List<Structure>> estilos,
					List<RandomSpreadStructurePlacement> placements, @Nullable ZonaAjenas zona, int distancia) {
		this(source, tipos, ids, estilos, placements, zona, distancia, List.of());
	}

	/** Pública para las pruebas: con las rejillas de las estructuras ajenas a las que cede el sitio. */
	public Medianas(Object source, List<Identifier> tipos, List<List<Identifier>> ids, List<List<Structure>> estilos,
					List<RandomSpreadStructurePlacement> placements, @Nullable ZonaAjenas zona, int distancia, List<Ajena> ajenas) {
		this(source, tipos, ids, estilos, placements, zona, distancia, ajenas, new boolean[tipos.size()], List.of());
	}

	/** Pública para las pruebas: además, qué tipos ceden el sitio a las entradas a mina y las rejillas de las minas. */
	public Medianas(Object source, List<Identifier> tipos, List<List<Identifier>> ids, List<List<Structure>> estilos,
					List<RandomSpreadStructurePlacement> placements, @Nullable ZonaAjenas zona, int distancia, List<Ajena> ajenas,
					boolean[] cedenMinas, List<Ajena> minas) {
		this.source = source;
		this.ajenas = ajenas.toArray(new Ajena[0]);
		this.cedenMinas = cedenMinas.clone();
		this.minas = minas.toArray(new Ajena[0]);

		this.tipos = tipos.toArray(new Identifier[0]);
		Map<Identifier, Integer> m = new HashMap<>();
		this.estilos = new Structure[tipos.size()][];
		for (int i = 0; i < tipos.size(); i++) {
			for (Identifier id : ids.get(i)) {
				m.put(id, i);
			}
			this.estilos[i] = estilos.get(i).toArray(new Structure[0]);
		}
		this.tipoDe = Map.copyOf(m);
		this.zona = zona;
		this.entre = new UniqueSeparation(source, tipos, Collections.nCopies(tipos.size(), (Structure) null), placements,
				Collections.nCopies(tipos.size(), false), distancia > 0, distancia);
	}

	/** Barato: solo las heraldia:medianas/* pasan de aquí. */
	public static boolean esMediana(Identifier id) {
		return id.getNamespace().equals("heraldia") && id.getPath().startsWith(PREFIJO);
	}

	/** Tabla del registro de structure_set en uso; se construye una vez por mundo. */
	public static Medianas of(RegistryAccess registryAccess) {
		Registry<StructureSet> sets = registryAccess.lookupOrThrow(Registries.STRUCTURE_SET);
		Medianas t = cached;
		if (t == null || t.source != sets) {
			t = build(sets, registryAccess);
			cached = t;
		}
		return t;
	}

	private static Medianas build(Registry<StructureSet> sets, RegistryAccess registryAccess) {
		Registry<Structure> structures = registryAccess.lookupOrThrow(Registries.STRUCTURE);
		List<Identifier> tipos = new ArrayList<>();
		List<List<Identifier>> ids = new ArrayList<>();
		List<List<Structure>> estilos = new ArrayList<>();
		List<RandomSpreadStructurePlacement> placements = new ArrayList<>();
		List<Ajena> ajenas = new ArrayList<>(), minas = new ArrayList<>();
		List<Boolean> ceden = new ArrayList<>();
		TagKey<Structure> cedenTag = TagKey.create(Registries.STRUCTURE, Identifier.fromNamespaceAndPath("heraldia", CEDEN_A_MINAS));
		int distanciaMinas = HeraldiaConfig.get().getInt(DISTANCIA);
		sets.listElements().forEach(set -> {
			if (set.value().placement() instanceof GridPlacement g && g.group().startsWith("minas/")) {
				minas.add(new Ajena(g, set.value().structures().stream().map(e -> e.structure().value()).toArray(Structure[]::new),
						distanciaMinas));
			}
			Ajena a = ajena(set.key().identifier(), set.value());
			if (a != null) {
				ajenas.add(a);
			}
			if (set.value().placement() instanceof GridPlacement g && g.group().startsWith(PREFIJO)) {
				List<Identifier> i = new ArrayList<>();
				List<Structure> s = new ArrayList<>();
				ceden.add(set.value().structures().stream().anyMatch(e -> e.structure().is(cedenTag)));
				for (StructureSet.StructureSelectionEntry e : set.value().structures()) {
					Identifier id = structures.getKey(e.structure().value());
					if (id != null) {
						i.add(id);
						s.add(e.structure().value());
					}
				}
				tipos.add(Identifier.fromNamespaceAndPath("heraldia", g.group()));
				ids.add(i);
				estilos.add(s);
				placements.add(g);
			}
		});
		HeraldiaConfig cfg = HeraldiaConfig.get();
		int zona = cfg.getInt(ZONA), distancia = cfg.getInt(DISTANCIA);
		LOGGER.info("Heraldia: estructuras medianas: {}, {} tipos, frecuencia {} %, a {} bloques de aldeas y únicas y a {} entre ellas; "
						+ "ceden el sitio a {} rejillas de estructuras vanilla o de otros mods", cfg.getBool(ACTIVADAS) ? "activadas" : "desactivadas",
				tipos.size(), cfg.getInt(FRECUENCIA), zona, distancia, ajenas.size());
		boolean[] cedenMinas = new boolean[ceden.size()];
		for (int k = 0; k < cedenMinas.length; k++) {
			cedenMinas[k] = ceden.get(k);
		}
		return new Medianas(sets, tipos, ids, estilos, placements, ZonaAjenas.conDistancia(sets, registryAccess, zona), distancia, ajenas,
				cedenMinas, minas);
	}

	/** Rejilla de un structure_set vanilla o de otro mod con estructuras que asoman (random_spread), o null. */
	public static @Nullable Ajena ajena(Identifier id, StructureSet set) {
		if (id.getNamespace().equals("heraldia") || !(set.placement() instanceof RandomSpreadStructurePlacement p)) {
			return null;
		}
		List<Structure> visibles = new ArrayList<>();
		for (StructureSet.StructureSelectionEntry e : set.structures()) {
			if (ZonaAjenas.visible(e.structure().value().step())) {
				visibles.add(e.structure().value());
			}
		}
		return visibles.isEmpty() ? null : new Ajena(p, visibles.toArray(new Structure[0]),
				id.getNamespace().equals("minecraft") ? VANILLA_BLOQUES : AJENAS_BLOQUES);
	}

	public int tipos() {
		return tipos.length;
	}

	/** Tipo de una estructura (estilo) o -1. */
	public int tipo(Identifier id) {
		Integer i = tipoDe.get(id);
		return i == null ? -1 : i;
	}

	public Identifier tipoId(int i) {
		return tipos[i];
	}

	public RandomSpreadStructurePlacement placement(int i) {
		return entre.placement(i);
	}

	/** En el juego: la misma comprobación que /locate (findValidGenerationPoint con su bioma) para cada estilo. */
	public Estilos estilos(RegistryAccess access, ChunkGenerator generator, BiomeSource biomeSource, Climate.Sampler sampler,
						   RandomState randomState, StructureTemplateManager templates, long seed, LevelHeightAccessor height) {
		Sale sale = sale(access, generator, biomeSource, sampler, randomState, templates, seed, height);
		return (j, x, z) -> {
			for (Structure s : estilos[j]) {
				if (s.findValidGenerationPoint(new Structure.GenerationContext(access, generator, biomeSource, sampler, randomState,
						templates, seed, new ChunkPos(x, z), height, s.biomes()::contains)).isPresent()) {
					return !cedeMina(j, x, z, seed, sale);
				}
			}
			return false;
		};
	}

	/** findValidGenerationPoint de una estructura en un chunk (lo que mira /locate). */
	private static Sale sale(RegistryAccess access, ChunkGenerator generator, BiomeSource biomeSource, Climate.Sampler sampler,
							 RandomState randomState, StructureTemplateManager templates, long seed, LevelHeightAccessor height) {
		return (s, cx, cz) -> s.findValidGenerationPoint(new Structure.GenerationContext(access, generator, biomeSource, sampler,
				randomState, templates, seed, new ChunkPos(cx, cz), height, s.biomes()::contains)).isPresent();
	}

	/**
	 * La mediana id con inicio en (chunkX, chunkZ) no sale: cae en la zona de una aldea o una única que sale de verdad,
	 * o junto a otra mediana de rango mayor que sobrevive. Solo para medianas (esMediana); el resto, falso.
	 */
	public boolean rechaza(Identifier id, int chunkX, int chunkZ, long seed, RegistryAccess access, ChunkGenerator generator,
						   BiomeSource biomeSource, Climate.Sampler sampler, RandomState randomState, StructureTemplateManager templates,
						   LevelHeightAccessor height, ResourceKey<Level> dimension) {
		int i = tipo(id);
		if (i < 0 || dimension != Level.OVERWORLD) {
			return false;
		}
		Contexto c = contexto(id, access, generator, biomeSource, sampler, randomState, templates, seed, height, dimension);
		return cedeMina(i, chunkX, chunkZ, seed, sale(access, generator, biomeSource, sampler, randomState, templates, seed, height))
				|| rechaza(i, chunkX, chunkZ, seed, c.zona(), c.estilos(), c.atlantida());
	}

	/** Lo que decide si sale una mediana: la zona de aldeas, únicas y estructuras ajenas, sus estilos y la Atlántida. */
	public record Contexto(Zona zona, Estilos estilos, Zona atlantida) {
	}

	/** El contexto del juego (las mismas comprobaciones que la generación y /locate); id: la estructura que pregunta. */
	public Contexto contexto(Identifier id, RegistryAccess access, ChunkGenerator generator, BiomeSource biomeSource,
							 Climate.Sampler sampler, RandomState randomState, StructureTemplateManager templates, long seed,
							 LevelHeightAccessor height, ResourceKey<Level> dimension) {
		UniqueSeparation unicas = UniqueSeparation.of(access);
		UniqueSeparation.Viability unica = unicas.viability(access, generator, biomeSource, sampler, randomState, templates, seed, height, dimension);
		ZonaAjenas.Aldea aldea = zona == null ? null : zona.aldea(access, generator, biomeSource, sampler, randomState, templates, seed, height, dimension);
		return new Contexto((x, z) -> zona != null && enZona(unicas, seed, x, z, unica, aldea)
						|| cedeAjena(x, z, seed, (s, cx, cz) -> s.findValidGenerationPoint(new Structure.GenerationContext(access, generator,
						biomeSource, sampler, randomState, templates, seed, new ChunkPos(cx, cz), height, s.biomes()::contains)).isPresent()),
				estilos(access, generator, biomeSource, sampler, randomState, templates, seed, height),
				(x, z) -> AtlantisAnchor.excludes(id, dimension, seed, x, z));
	}

	/**
	 * ¿Sale una mediana (de cualquier tipo) a menos de `bloques` del chunk? La usan las entradas a mina (comun/Minas en
	 * minas/), que ceden el sitio a las medianas sin que estas sepan de ellas: así su regla no cambia. Pública para las
	 * pruebas (con el contexto inyectado).
	 */
	public boolean cerca(int chunkX, int chunkZ, int bloques, long seed, Contexto c) {
		int alcance = (bloques + 15) / 16;
		long d2 = (long) bloques * bloques;
		for (int j = 0; j < tipos.length; j++) {
			RandomSpreadStructurePlacement p = entre.placement(j);
			int s = p.spacing(), ox = UniqueSeparation.offsetX(p), oz = UniqueSeparation.offsetZ(p);
			for (int gx = Math.floorDiv(chunkX - alcance - ox, s), gxMax = Math.floorDiv(chunkX + alcance - ox, s); gx <= gxMax; gx++) {
				for (int gz = Math.floorDiv(chunkZ - alcance - oz, s), gzMax = Math.floorDiv(chunkZ + alcance - oz, s); gz <= gzMax; gz++) {
					ChunkPos m = p.getPotentialStructureChunk(seed, gx * s + ox, gz * s + oz);
					long dx = (m.x() - (long) chunkX) * 16, dz = (m.z() - (long) chunkZ) * 16;
					if (dx * dx + dz * dz >= d2 || !p.applyAdditionalChunkRestrictions(m.x(), m.z(), seed)) {
						continue;
					}
					if (!c.atlantida().ocupada(m.x(), m.z()) && c.estilos().sale(j, m.x(), m.z())
							&& !rechaza(j, m.x(), m.z(), seed, c.zona(), c.estilos(), c.atlantida())) {
						return true;
					}
				}
			}
		}
		return false;
	}

	/** ¿Cae el chunk en la zona de una aldea o una única que sale? */
	@FunctionalInterface
	public interface Zona {
		boolean ocupada(int chunkX, int chunkZ);
	}

	/** ¿Sale la estructura (ajena) con inicio en ese chunk? En el juego, findValidGenerationPoint. */
	@FunctionalInterface
	public interface Sale {
		boolean sale(Structure structure, int chunkX, int chunkZ);
	}

	/** Lógica pura (pruebas): zona, estilos y Atlántida inyectados. En memoria por tipo, candidata y semilla. */
	public boolean rechaza(int i, int chunkX, int chunkZ, long seed, Zona zona, Estilos estilos, Zona atlantida) {
		Memoria m = memoria(seed);
		long key = ZonaAjenas.clave(i, chunkX, chunkZ);
		Boolean v = m.valores.get(key);
		if (v == null) {
			v = zona.ocupada(chunkX, chunkZ) || entre.blocked(i, chunkX, chunkZ, seed,
					(j, x, z) -> !atlantida.ocupada(x, z) && estilos.sale(j, x, z) && !zona.ocupada(x, z));
			if (m.valores.size() > CACHE_MAX) {
				m.valores.clear();
			}
			m.valores.put(key, v);
		}
		return v;
	}

	private Memoria memoria(long seed) {
		Memoria m = memoria;
		if (m.seed != seed) { // otra semilla, memoria nueva: un hilo atrasado no mezcla mundos
			m = new Memoria(seed, new ConcurrentHashMap<>(), new ConcurrentHashMap<>());
			memoria = m;
		}
		return m;
	}

	/**
	 * Sale cerca del chunk (a VANILLA_BLOQUES o AJENAS_BLOQUES) una estructura que asoma, vanilla o de otro mod (de rejilla
	 * random_spread).
	 * Barato salvo junto a una candidata (findValidGenerationPoint), que queda en memoria. Pública para las pruebas.
	 */
	public boolean cedeAjena(int chunkX, int chunkZ, long seed, Sale sale) {
		return cede(ajenas, 0, chunkX, chunkZ, seed, sale);
	}

	/**
	 * ¿Cede el tipo j el sitio a una entrada a mina? Solo los de #heraldia:medianas/ceden_a_minas (las chozas de mago, que
	 * buscan el mismo interior de los mismos biomas que las minas: sin esto, cada una le quitaría el sitio a la mina de al
	 * lado, porque las minas ceden siempre a las medianas). Sale una candidata de mina (findValidGenerationPoint, sin sus
	 * propias reglas: cede de más, nunca de menos) a menos de medianas.distancia_minima.bloques. Sin ciclo: las minas no
	 * miran a las medianas para eso. Pública para las pruebas.
	 */
	public boolean cedeMina(int j, int chunkX, int chunkZ, long seed, Sale sale) {
		return j >= 0 && j < cedenMinas.length && cedenMinas[j] && cede(minas, MINA_CLAVE, chunkX, chunkZ, seed, sale);
	}

	private boolean cede(Ajena[] ajenas, int base, int chunkX, int chunkZ, long seed, Sale sale) {
		for (int k = 0; k < ajenas.length; k++) {
			RandomSpreadStructurePlacement p = ajenas[k].placement;
			int ajenasReach = (ajenas[k].bloques + 15) / 16;
			long d2 = (long) ajenas[k].bloques * ajenas[k].bloques;
			int s = p.spacing(), ox = UniqueSeparation.offsetX(p), oz = UniqueSeparation.offsetZ(p);
			for (int gx = Math.floorDiv(chunkX - ajenasReach - ox, s), gxMax = Math.floorDiv(chunkX + ajenasReach - ox, s); gx <= gxMax; gx++) {
				for (int gz = Math.floorDiv(chunkZ - ajenasReach - oz, s), gzMax = Math.floorDiv(chunkZ + ajenasReach - oz, s); gz <= gzMax; gz++) {
					ChunkPos c = p.getPotentialStructureChunk(seed, gx * s + ox, gz * s + oz);
					long dx = (c.x() - (long) chunkX) * 16, dz = (c.z() - (long) chunkZ) * 16;
					if (dx * dx + dz * dz > d2 || !p.applyAdditionalChunkRestrictions(c.x(), c.z(), seed)) {
						continue;
					}
					Memoria m = memoria(seed);
					long key = ZonaAjenas.clave(base + k, c.x(), c.z());
					Boolean v = m.ajenas.get(key);
					if (v == null) {
						v = false;
						for (Structure st : ajenas[k].structures) {
							if (sale.sale(st, c.x(), c.z())) {
								v = true;
								break;
							}
						}
						if (m.ajenas.size() > CACHE_MAX) {
							m.ajenas.clear();
						}
						m.ajenas.put(key, v);
					}
					if (v) {
						return true;
					}
				}
			}
		}
		return false;
	}

	private boolean enZona(UniqueSeparation unicas, long seed, int x, int z, UniqueSeparation.Viability unica, ZonaAjenas.Aldea aldea) {
		long[] cerca = zona.cercanas(unicas, seed, x, z);
		return cerca != null && zona.ocupada(cerca, unicas, seed, unica, aldea);
	}
}
