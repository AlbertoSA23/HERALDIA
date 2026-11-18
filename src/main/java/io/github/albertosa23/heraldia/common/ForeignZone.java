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
 * Estructuras de otros mods junto a las de Heraldia: un inicio de otro mod (ni heraldia ni minecraft) que asome a la
 * superficie no nace a menos de {@link #OPTION} bloques del inicio de una aldea o una única de Heraldia que se genera
 * de verdad (Heraldia gana siempre, así que tampoco sale una de Heraldia encima de otra ajena: el orden de generación de
 * los chunks no importa). Es la técnica de la Atlántida y la isla del corsario, genérica: ningún mod ajeno tiene que
 * saber de Heraldia ni declarar nada.
 * <p>Coste: solo para los chunks candidatos de una estructura ajena (unos pocos por zona). Se calculan las candidatas de
 * las rejillas de Heraldia cercanas (getPotentialStructureChunk, sin terreno ni biomas); lo caro (si la de Heraldia sale
 * allí: bioma, terreno, reglas del mod) solo junto a una candidata y queda en memoria. Una instancia por registro de
 * structure_set (por mundo), inmutable salvo la memoria (ConcurrentHashMap): la consultan los hilos de generación a la vez.
 * <p>No se tocan las vanilla (sus aldeas ya tienen la zona de exclusión de las nuestras; la Atlántida y la isla excluyen
 * todo) ni las subterráneas ajenas ({@link #visible}), que no se ven aunque crucen una caja. La aldea se da por generada si
 * alguna de sus entradas vale en la casilla (como el structure_set, que prueba otra al fallar una); no se cuenta la zona
 * de exclusión frente a las aldeas vanilla, así que junto a una candidata que pierde por eso también se excluye (rara vez).
 */
public final class ForeignZone {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	public static final String OPTION = "compatibilidad.zona_estructuras_ajenas_bloques";
	private static final Identifier VILLAGES = Identifier.fromNamespaceAndPath("heraldia", "aldeas");
	/** Pasos de generación de lo que no asoma a la superficie (minas, mazmorras, fortalezas). */
	private static final Set<GenerationStep.Decoration> UNDERGROUND = EnumSet.of(GenerationStep.Decoration.UNDERGROUND_STRUCTURES,
			GenerationStep.Decoration.STRONGHOLDS, GenerationStep.Decoration.UNDERGROUND_ORES, GenerationStep.Decoration.UNDERGROUND_DECORATION);
	static final int VILLAGE = -1;
	private static final int CACHE_MAX = 1 << 12;
	private static volatile @Nullable ForeignZone cached;

	/** ¿Sale de verdad una aldea de Heraldia con inicio en ese chunk? */
	@FunctionalInterface
	public interface Village {
		boolean outcome(int chunkX, int chunkZ);
	}

	private final Object source;
	private final int reach;            // chunks
	private final long distanceSq;      // bloques²
	private final @Nullable RandomSpreadStructurePlacement villages;
	private final Identifier[] villageIds;
	private final Structure[] villageStructures;
	private volatile Memory memory = new Memory(0, new ConcurrentHashMap<>());

	/** Resultados por candidata de una semilla (otra semilla, memoria nueva: un hilo atrasado no mezcla mundos). */
	private record Memory(long seed, ConcurrentHashMap<Long, Boolean> optionValues) {
	}

	/** Pública para las pruebas: distancia en bloques (0 = desactivada) y la rejilla de las aldeas (null si no hay). */
	public ForeignZone(Object source, int distance, @Nullable RandomSpreadStructurePlacement villages, List<Identifier> ids, List<Structure> structures) {
		this.source = source;
		this.reach = distance <= 0 ? 0 : (distance + 15) / 16;
		this.distanceSq = (long) distance * distance;
		this.villages = villages;
		this.villageIds = ids.toArray(new Identifier[0]);
		this.villageStructures = structures.toArray(new Structure[0]);
	}

	/** Tabla del registro de structure_set en uso; se construye una vez por mundo. */
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
	 * Zona de otra distancia alrededor de las mismas candidatas (aldeas y únicas de Heraldia que salen de verdad), con su
	 * propia memoria: la usan las estructuras medianas ({@link MediumStructures}). Una por registro de structure_set.
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

	/** De otro mod (ni heraldia ni minecraft). Barato: una comparación de cadenas. */
	public static boolean fromOtherMod(Identifier id) {
		String ns = id.getNamespace();
		return !ns.equals("heraldia") && !ns.equals("minecraft");
	}

	/** Asoma a la superficie (no es una mina, una mazmorra o una fortaleza). */
	public static boolean visible(GenerationStep.Decoration step) {
		return !UNDERGROUND.contains(step);
	}

	/** Activada y en el mundo principal (las estructuras de Heraldia solo salen en él). */
	public boolean active(ResourceKey<Level> dimension) {
		return reach > 0 && dimension == Level.OVERWORLD;
	}

	/**
	 * Candidatas de Heraldia (únicas de rejilla y aldeas) con inicio a menos de la distancia del chunk, como triples
	 * {tipo, x, z} (tipo = índice de la única en sep o {@link #VILLAGE}), o null si no hay ninguna. Sin terreno ni biomas.
	 */
	public long @Nullable [] nearby(UniqueSeparation sep, long seed, int chunkX, int chunkZ) {
		long[] out = null;
		int n = 0;
		for (int i = -1; i < sep.size(); i++) {
			RandomSpreadStructurePlacement p = i < 0 ? villages : sep.fixed(i) ? null : sep.placement(i);
			if (p == null) {
				continue; // sin aldeas, o la Atlántida (AtlantisAnchor ya excluye todo junto a ella)
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

	/** Alguna de las candidatas cercanas sale de verdad (en memoria por candidata y semilla). */
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

	/** Aldea real en el juego: alguna entrada del set permitida por las reglas del mod con sitio válido (bioma y terreno). */
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

	/** Clave exacta de la memoria: 24 bits por coordenada (±8 millones de chunks, más que el borde del mundo) y el tipo. */
	static long key(int type, int x, int z) {
		return (x & 0xFFFFFFL) | (long) (z & 0xFFFFFF) << 24 | (long) (type + 1) << 48;
	}
}
