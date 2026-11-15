package io.github.albertosa23.heraldia.comun;

import net.minecraft.core.Holder;
import net.minecraft.core.HolderSet;
import net.minecraft.core.registries.Registries;
import net.minecraft.world.level.biome.Biome;
import net.minecraft.world.level.biome.Biomes;
import net.minecraft.world.level.block.Rotation;
import net.minecraft.world.level.levelgen.LegacyRandomSource;
import net.minecraft.world.level.levelgen.WorldgenRandom;
import net.minecraft.world.level.levelgen.structure.Structure;

/** Utilidades de los tipos de estructura propios que se sitúan respecto al terreno o al agua (faro, galeón, aldeas). */
public final class Generacion {
	private Generacion() {
	}

	/** /place structure pasa un predicado de bioma que lo acepta todo; la generación normal, solo los de la estructura. */
	public static boolean forzada(Structure.GenerationContext ctx, HolderSet<Biome> biomes) {
		return ctx.registryAccess().lookupOrThrow(Registries.BIOME).get(Biomes.THE_VOID)
				.map(v -> !biomes.contains(v) && ctx.validBiome().test(v)).orElse(false);
	}

	/** Azar de la casilla; con k = 0, el mismo que el del contexto recién creado (setLargeFeatureSeed de la semilla). */
	public static WorldgenRandom azar(Structure.GenerationContext c, long k) {
		WorldgenRandom random = new WorldgenRandom(new LegacyRandomSource(0L));
		random.setLargeFeatureSeed(c.seed() + k * 0x9E3779B97F4A7C15L, c.chunkPos().x(), c.chunkPos().z());
		return random;
	}

	/**
	 * Copia del contexto cuyo azar da como primera tirada el giro pedido (JigsawPlacement sortea el giro primero). Con el
	 * giro natural devuelve el propio contexto: el resto del ensamblado no cambia.
	 */
	public static Structure.GenerationContext conGiro(Structure.GenerationContext c, Rotation rotation) {
		for (long k = 0; ; k++) {
			if (Rotation.getRandom(azar(c, k)) == rotation) {
				return k == 0 ? c : new Structure.GenerationContext(c.registryAccess(), c.chunkGenerator(), c.biomeSource(),
						c.climateSampler(), c.biomeResolver(), c.randomState(), c.structureTemplateManager(), azar(c, k), c.seed(),
						c.chunkPos(), c.heightAccessor(), c.validBiome());
			}
		}
	}

	/** Bioma de la estructura en un punto (resolución de cuarto de chunk, barato: no evalúa el terreno). */
	public static boolean bioma(Structure.GenerationContext c, HolderSet<Biome> biomes, int x, int y, int z) {
		Holder<Biome> b = c.biomeResolver().getNoiseBiome(net.minecraft.core.QuartPos.fromBlock(x), net.minecraft.core.QuartPos.fromBlock(y),
				net.minecraft.core.QuartPos.fromBlock(z));
		return biomes.contains(b);
	}
}
