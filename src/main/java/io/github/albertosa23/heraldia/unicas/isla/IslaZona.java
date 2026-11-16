package io.github.albertosa23.heraldia.unicas.isla;

import io.github.albertosa23.heraldia.config.UniqueSeparation;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import net.minecraft.resources.Identifier;
import net.minecraft.resources.ResourceKey;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.levelgen.structure.placement.RandomSpreadStructurePlacement;

/**
 * Zona de la isla del corsario: ninguna estructura ajena (naufragios, ruinas oceánicas, portales en ruinas...) nace
 * dentro del islote ni pegada a él, como en la Atlántida. Un inicio ajeno se rechaza si cae a menos de REACH chunks de la
 * candidata de la isla de su casilla y la isla sale allí de verdad (la misma viabilidad que la distancia mínima entre
 * únicas: bioma, fondo marino, Atlántida y separación). Lo caro (la viabilidad) solo se calcula junto a una candidata
 * de la isla (unos pocos chunks por casilla de 4.000 bloques) y queda en memoria; el resto paga una búsqueda en una
 * tabla y la candidata de la casilla (ya en memoria en GridPlacement).
 */
public final class IslaZona {
	public static final long NINGUNA = Long.MIN_VALUE;
	private static final Identifier ISLA = Identifier.fromNamespaceAndPath("heraldia", "unicas/isla_corsario");
	/** Huella de la isla (54 bloques) + búsqueda del sitio (16) + una estructura ajena (unos 40), en chunks. */
	private static final int REACH = 7, CACHE_MAX = 1 << 12;
	private static final Set<Identifier> REQUIRED = Set.of(Identifier.fromNamespaceAndPath("minecraft", "stronghold"));
	private static final ConcurrentHashMap<Long, Boolean> SALE = new ConcurrentHashMap<>();

	private IslaZona() {
	}

	/** Candidata de la isla cerca del chunk (empaquetada con ChunkPos.pack) o NINGUNA. Barato: sin terreno ni biomas. */
	public static long candidata(Identifier structure, ResourceKey<Level> dimension, UniqueSeparation sep, long seed, int chunkX, int chunkZ) {
		if (dimension != Level.OVERWORLD || "heraldia".equals(structure.getNamespace()) || REQUIRED.contains(structure)) {
			return NINGUNA;
		}
		int i = sep.indexOf(ISLA);
		if (i < 0) {
			return NINGUNA;
		}
		RandomSpreadStructurePlacement p = sep.placement(i);
		int s = p.spacing(), ox = UniqueSeparation.offsetX(p), oz = UniqueSeparation.offsetZ(p);
		for (int gx = Math.floorDiv(chunkX - REACH - ox, s), gxMax = Math.floorDiv(chunkX + REACH - ox, s); gx <= gxMax; gx++) {
			for (int gz = Math.floorDiv(chunkZ - REACH - oz, s), gzMax = Math.floorDiv(chunkZ + REACH - oz, s); gz <= gzMax; gz++) {
				ChunkPos c = p.getPotentialStructureChunk(seed, gx * s + ox, gz * s + oz);
				if (Math.abs(c.x() - chunkX) <= REACH && Math.abs(c.z() - chunkZ) <= REACH && p.applyAdditionalChunkRestrictions(c.x(), c.z(), seed)) {
					return ChunkPos.pack(c.x(), c.z());
				}
			}
		}
		return NINGUNA;
	}

	/** La isla sale de verdad en esa candidata (viabilidad y distancia mínima entre únicas); en memoria por semilla. */
	public static boolean sale(UniqueSeparation sep, long candidata, long seed, UniqueSeparation.Viability viability) {
		long key = candidata * 31 + seed;
		Boolean v = SALE.get(key);
		if (v == null) {
			int i = sep.indexOf(ISLA), x = ChunkPos.getX(candidata), z = ChunkPos.getZ(candidata);
			v = viability.valid(i, x, z) && !sep.blocked(i, x, z, seed, viability);
			if (SALE.size() > CACHE_MAX) {
				SALE.clear();
			}
			SALE.put(key, v);
		}
		return v;
	}
}
