package io.github.albertosa23.heraldia.minas;

import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.comun.Medianas;
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
 * Entradas a mina (heraldia:minas/&lt;tamaño&gt;/&lt;estilo&gt;/&lt;variante&gt;, tools/gen/minas): un structure_set por tamaño
 * con su rejilla heraldia:rejilla (grupo minas/&lt;tamaño&gt;). Una candidata se descarta con las reglas de las medianas
 * ({@link Medianas}), sin cambiar las de estas:
 * <ul>
 * <li>en la zona de una aldea o una única que sale (medianas.distancia_aldeas_unicas_bloques), junto a una estructura
 * vanilla o de otro mod que asoma, o dentro de la Atlántida;</li>
 * <li>a menos de medianas.distancia_minima.bloques de una mediana que sale ({@link Medianas#cerca}): la mina cede siempre
 * (las medianas no saben de las minas, así que ninguna mediana cambia de sitio por ellas);</li>
 * <li>a menos de esa misma distancia de una entrada de otro tamaño de rango mayor que sobrevive ({@link UniqueSeparation},
 * la recursión por rangos de las únicas). Dos del mismo tamaño ya las separa su rejilla.</li>
 * </ul>
 * Solo corre en los chunks candidatos de una entrada (uno por tamaño cada 48-120 chunks de lado); las viabilidades (la
 * búsqueda de ladera) y las decisiones quedan en memoria por semilla. Inmutable salvo las memorias.
 */
public final class Minas {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	public static final String PREFIJO = "minas/";
	public static final String ACTIVADO = "minas.entradas.activado", SEPARACION = "minas.entradas.separacion_bloques",
			MULTIPLICADOR = "minas.vanilla.multiplicador";
	private static final int CACHE_MAX = 1 << 12;
	private static volatile @Nullable Minas cached;

	private final Object source;
	private final Map<Identifier, Integer> tipoDe;
	private final Identifier[] tipos;
	private final Structure[][] estilos;
	private final UniqueSeparation entre;
	private final int distancia;
	private volatile Memoria memoria = new Memoria(0, new ConcurrentHashMap<>(), new ConcurrentHashMap<>());

	private record Memoria(long seed, ConcurrentHashMap<Long, Boolean> decisiones, ConcurrentHashMap<Long, Boolean> salen) {
	}

	/** Pública para las pruebas: tamaños, ids y estructuras de cada uno, sus rejillas y la distancia mínima (bloques). */
	public Minas(Object source, List<Identifier> tipos, List<List<Identifier>> ids, List<List<Structure>> estilos,
				 List<RandomSpreadStructurePlacement> placements, int distancia) {
		this.source = source;
		this.tipos = tipos.toArray(new Identifier[0]);
		this.estilos = new Structure[tipos.size()][];
		Map<Identifier, Integer> m = new HashMap<>();
		for (int i = 0; i < tipos.size(); i++) {
			for (Identifier id : ids.get(i)) {
				m.put(id, i);
			}
			this.estilos[i] = estilos.get(i).toArray(new Structure[0]);
		}
		this.tipoDe = Map.copyOf(m);
		this.distancia = distancia;
		this.entre = new UniqueSeparation(source, tipos, Collections.nCopies(tipos.size(), (Structure) null), placements,
				Collections.nCopies(tipos.size(), false), distancia > 0, distancia);
	}

	/** Tipo de estructura y colocación de las minas vanilla multiplicadas. Una línea en Heraldia. */
	public static void registrar() {
		Registry.register(BuiltInRegistries.STRUCTURE_TYPE, Heraldia.id("mina_entrada"), MinaEntradaStructure.TYPE);
		Registry.register(BuiltInRegistries.STRUCTURE_PLACEMENT, Heraldia.id("minas_vanilla"), MinasVanillaPlacement.CODEC);
	}

	/** Barato: solo las heraldia:minas/* pasan de aquí. */
	public static boolean esMina(Identifier id) {
		return id.getNamespace().equals(Heraldia.MOD_ID) && id.getPath().startsWith(PREFIJO);
	}

	public static Minas of(RegistryAccess access) {
		Registry<StructureSet> sets = access.lookupOrThrow(Registries.STRUCTURE_SET);
		Minas t = cached;
		if (t == null || t.source != sets) {
			t = build(sets, access);
			cached = t;
		}
		return t;
	}

	private static Minas build(Registry<StructureSet> sets, RegistryAccess access) {
		Registry<Structure> structures = access.lookupOrThrow(Registries.STRUCTURE);
		List<Identifier> tipos = new ArrayList<>();
		List<List<Identifier>> ids = new ArrayList<>();
		List<List<Structure>> estilos = new ArrayList<>();
		List<RandomSpreadStructurePlacement> placements = new ArrayList<>();
		sets.listElements().forEach(set -> {
			if (set.value().placement() instanceof GridPlacement g && g.group().startsWith(PREFIJO)) {
				List<Identifier> i = new ArrayList<>();
				List<Structure> s = new ArrayList<>();
				for (StructureSet.StructureSelectionEntry e : set.value().structures()) {
					Identifier id = structures.getKey(e.structure().value());
					if (id != null) {
						i.add(id);
						s.add(e.structure().value());
					}
				}
				tipos.add(Identifier.fromNamespaceAndPath(Heraldia.MOD_ID, g.group()));
				ids.add(i);
				estilos.add(s);
				placements.add(g);
			}
		});
		HeraldiaConfig cfg = HeraldiaConfig.get();
		int distancia = cfg.getInt(Medianas.DISTANCIA);
		LOGGER.info("Heraldia: entradas a mina: {}, {} tamaños, cada {} bloques las pequeñas, a {} bloques de aldeas y únicas y a {} de "
						+ "las medianas y entre ellas; minas vanilla x{}", cfg.getBool(ACTIVADO) ? "activadas" : "desactivadas", tipos.size(),
				cfg.getInt(SEPARACION), cfg.getInt(Medianas.ZONA), distancia, cfg.getDouble(MULTIPLICADOR));
		return new Minas(sets, tipos, ids, estilos, placements, distancia);
	}

	public int tipos() {
		return tipos.length;
	}

	public int tipo(Identifier id) {
		Integer i = tipoDe.get(id);
		return i == null ? -1 : i;
	}

	public Identifier tipoId(int i) {
		return tipos[i];
	}

	/** En el juego: ¿sale algún estilo del tamaño j ahí (bioma y ladera)? En memoria: es la búsqueda de ladera. */
	private Medianas.Estilos estilos(RegistryAccess access, ChunkGenerator generator, BiomeSource biomeSource, Climate.Sampler sampler,
									 RandomState randomState, StructureTemplateManager templates, long seed, LevelHeightAccessor height) {
		return (j, x, z) -> {
			Memoria m = memoria(seed);
			long key = clave(j, x, z);
			Boolean v = m.salen.get(key);
			if (v == null) {
				v = false;
				for (Structure s : estilos[j]) {
					if (s.findValidGenerationPoint(new Structure.GenerationContext(access, generator, biomeSource, sampler, randomState,
							templates, seed, new ChunkPos(x, z), height, s.biomes()::contains)).isPresent()) {
						v = true;
						break;
					}
				}
				if (m.salen.size() > CACHE_MAX) {
					m.salen.clear();
				}
				m.salen.put(key, v);
			}
			return v;
		};
	}

	/** La entrada id con inicio en (chunkX, chunkZ) no sale (ver la clase). Solo para minas (esMina); el resto, falso. */
	public boolean rechaza(Identifier id, int chunkX, int chunkZ, long seed, RegistryAccess access, ChunkGenerator generator,
						   BiomeSource biomeSource, Climate.Sampler sampler, RandomState randomState, StructureTemplateManager templates,
						   LevelHeightAccessor height, ResourceKey<Level> dimension) {
		int i = tipo(id);
		if (i < 0 || dimension != Level.OVERWORLD) {
			return false;
		}
		Medianas med = Medianas.of(access);
		Medianas.Contexto c = med.contexto(id, access, generator, biomeSource, sampler, randomState, templates, seed, height, dimension);
		return rechaza(i, chunkX, chunkZ, seed, c.zona(), estilos(access, generator, biomeSource, sampler, randomState, templates, seed, height),
				c.atlantida(), (x, z) -> med.cerca(x, z, distancia, seed, c));
	}

	/** Lógica pura (pruebas): zona, estilos, Atlántida y medianas cercanas inyectados. En memoria por tamaño, chunk y semilla. */
	public boolean rechaza(int i, int chunkX, int chunkZ, long seed, Medianas.Zona zona, Medianas.Estilos estilos, Medianas.Zona atlantida,
						   Medianas.Zona medianas) {
		Memoria m = memoria(seed);
		long key = clave(i, chunkX, chunkZ);
		Boolean v = m.decisiones.get(key);
		if (v == null) {
			v = zona.ocupada(chunkX, chunkZ) || medianas.ocupada(chunkX, chunkZ) || entre.blocked(i, chunkX, chunkZ, seed,
					(j, x, z) -> !atlantida.ocupada(x, z) && estilos.sale(j, x, z) && !zona.ocupada(x, z) && !medianas.ocupada(x, z));
			if (m.decisiones.size() > CACHE_MAX) {
				m.decisiones.clear();
			}
			m.decisiones.put(key, v);
		}
		return v;
	}

	private Memoria memoria(long seed) {
		Memoria m = memoria;
		if (m.seed != seed) {
			m = new Memoria(seed, new ConcurrentHashMap<>(), new ConcurrentHashMap<>());
			memoria = m;
		}
		return m;
	}

	static long clave(int tipo, int x, int z) {
		return (x & 0xFFFFFFL) | (long) (z & 0xFFFFFF) << 24 | (long) (tipo + 1) << 48;
	}
}
