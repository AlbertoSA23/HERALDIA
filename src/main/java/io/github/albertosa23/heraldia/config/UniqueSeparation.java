package io.github.albertosa23.heraldia.config;

import io.github.albertosa23.heraldia.unicas.atlantida.AtlantisAnchor;
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
 * Distancia mínima entre estructuras únicas distintas (heraldia:unicas/*), sin recorrer el mundo ni guardar datos.
 * Para una candidata se calculan las casillas de las demás rejillas a menos de N bloques (el mismo
 * getPotentialStructureChunk que usa el juego) y la candidata se descarta si alguna de rango mayor <em>sobrevive</em>:
 * se generaría de verdad (findValidGenerationPoint, el mismo cálculo que /locate, con su bioma real) y no la descarta a
 * su vez otra de rango aún mayor. El rango es un hash de la semilla, el tipo y el chunk (reparto justo entre tipos);
 * las de colocación propia (la Atlántida) ganan siempre. Como la recursión sigue rangos estrictamente crecientes, la
 * relación es la misma la evalúe quien la evalúe: dos supervivientes nunca quedan a menos de N y toda descartada tiene
 * cerca una superviviente. Inmutable una vez construida: la consultan varios hilos de generación a la vez.
 * <p>Con unicas.rejilla_compatible ({@link GridPlacement#legacy()}) el orden tiene un escalón más: colocación propia,
 * luego las únicas de la rejilla antigua y luego las nuevas; el rango solo desempata dentro del mismo escalón. Una
 * antigua no ve a las nuevas (se descarta exactamente como en la 0.1.0, donde no existían: las ya generadas siguen
 * donde /locate las busca) y una nueva se descarta si cae a menos de N de una antigua que sobrevive (no sale encima de
 * una ya generada). Sin la opción todas son del mismo escalón y nada cambia.
 */
public final class UniqueSeparation {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	private static volatile @Nullable UniqueSeparation cached;

	/** Si la estructura index saldría en ese chunk sin contar la separación (bioma, terreno, reglas del mod). */
	@FunctionalInterface
	public interface Viability {
		boolean valid(int index, int chunkX, int chunkZ);
	}

	private final Object source;
	private final Identifier[] ids;
	private final @Nullable Structure[] structures;
	private final RandomSpreadStructurePlacement[] placements;
	private final long[] salts;
	private final boolean[] always;
	private final byte[] tier; // 2 colocación propia, 1 rejilla antigua, 0 el resto: gana el escalón y luego el rango
	private final Map<Identifier, Integer> index;
	private final boolean enabled;
	private final int reachChunks;
	private final long distanceSq;

	/** Tabla de las estructuras únicas: always = colocación propia (gana siempre). Pública para las pruebas. */
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

	/** Barato y sin reservas: solo las heraldia:unicas/* pasan de aquí. */
	public static boolean isUnique(Identifier id) {
		return id.getNamespace().equals("heraldia") && id.getPath().startsWith("unicas/");
	}

	/** Tabla del registro de structure_set en uso; se construye una vez por mundo. */
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

	/** Colocación propia (la Atlántida): no sigue una rejilla y gana siempre. */
	public boolean fixed(int i) {
		return always[i];
	}

	public Identifier id(int i) {
		return ids[i];
	}

	/** Viabilidad real en el juego: la misma comprobación que /locate (StructureCheck.canCreateStructure) más la Atlántida. */
	public Viability viability(RegistryAccess registryAccess, ChunkGenerator generator, BiomeSource biomeSource, Climate.Sampler sampler,
							   RandomState randomState, StructureTemplateManager templates, long seed, LevelHeightAccessor height,
							   ResourceKey<Level> dimension) {
		return (j, x, z) -> {
			Structure s = structures[j];
			return s != null && !AtlantisAnchor.excludes(ids[j], dimension, seed, x, z)
					&& s.findValidGenerationPoint(new Structure.GenerationContext(registryAccess, generator, biomeSource, sampler, randomState,
					templates, seed, new ChunkPos(x, z), height, s.biomes()::contains)).isPresent();
		};
	}

	/** La candidata i en (chunkX, chunkZ) se descarta: otra estructura única que sobrevive cae a menos de N bloques. */
	public boolean blocked(int i, int chunkX, int chunkZ, long seed, Viability viability) {
		return enabled && !always[i] && blockedBy(i, chunkX, chunkZ, rank(i, chunkX, chunkZ, seed), seed, viability, null);
	}

	/**
	 * Hay una vecina de rango mayor que sobrevive. Se prueban de mayor a menor rango: la de rango más alto casi nunca
	 * tiene a su vez vecinas por encima, así que la recursión acaba enseguida; la memoria evita repetir viabilidades.
	 * Solo corre en los chunks candidatos de una estructura única (unos pocos por mundo): las listas pequeñas que
	 * reserva no están en la ruta caliente de la generación.
	 */
	private boolean blockedBy(int i, int cx, int cz, long rank, long seed, Viability viability, @Nullable Map<Long, Boolean> memo) {
		List<long[]> near = null; // {tipo, x, z, rango}
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
						continue; // escalón o rango menor, o casilla desactivada
					}
					if (always[j]) {
						return true;
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

	/** Desfase del origen de la rejilla (las casillas de p empiezan en gx * spacing + offsetX). */
	public static int offsetX(RandomSpreadStructurePlacement p) {
		return p instanceof GridPlacement g ? g.offsetX() : 0;
	}

	public static int offsetZ(RandomSpreadStructurePlacement p) {
		return p instanceof GridPlacement g ? g.offsetZ() : 0;
	}

	/** Rango de desempate: determinista por semilla, tipo y chunk; las de colocación propia, el máximo. */
	public long rank(int i, int chunkX, int chunkZ, long seed) {
		return always[i] ? Long.MAX_VALUE : mix(seed ^ salts[i] ^ mix(ChunkPos.pack(chunkX, chunkZ)));
	}

	static long mix(long z) { // finalizador de SplitMix64 (también lo usa GridPlacement)
		z = (z ^ (z >>> 30)) * 0xBF58476D1CE4E5B9L;
		z = (z ^ (z >>> 27)) * 0x94D049BB133111EBL;
		return z ^ (z >>> 31);
	}
}
