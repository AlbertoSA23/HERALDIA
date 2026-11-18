package io.github.albertosa23.heraldia.uniques.citadel;

import com.mojang.serialization.Codec;
import com.mojang.serialization.MapCodec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Holder;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.Identifier;
import net.minecraft.world.level.biome.Biome;
import net.minecraft.world.level.block.Rotation;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.level.levelgen.structure.PoolElementStructurePiece;
import net.minecraft.world.level.levelgen.structure.Structure;
import net.minecraft.world.level.levelgen.structure.StructureType;
import net.minecraft.world.level.levelgen.structure.pools.StructurePoolElement;
import net.minecraft.world.level.levelgen.structure.pools.StructureTemplatePool;
import net.minecraft.world.level.levelgen.structure.templatesystem.LiquidSettings;

/**
 * Dwarven citadel: a single piece whose gate (template z=0, facing north) is oriented towards where the
 * hillside goes down. It tries 4 rotations x 25 positions with the generation height map: in front of the gate almost
 * flat and dry terrain, further ahead no wall, and over the city rock on at least 75 % of the ceiling grid the
 * generator writes. If nothing passes it is not generated; with /place (which accepts any biome) the best option is used.
 */
public final class CitadelStructure extends Structure {
	public static final MapCodec<CitadelStructure> CODEC = RecordCodecBuilder.mapCodec(i -> i.group(
			settingsCodec(i),
			StructureTemplatePool.CODEC.fieldOf("start_pool").forGetter(s -> s.startPool),
			BlockPos.CODEC.fieldOf("entrance").forGetter(s -> s.entrance),
			Codec.INT.fieldOf("roof_cell").forGetter(s -> s.cell),
			Codec.INT.fieldOf("roof_width").forGetter(s -> s.width),
			Codec.INT.listOf().fieldOf("roof").forGetter(s -> s.roof)
	).apply(i, CitadelStructure::new));
	public static final StructureType<CitadelStructure> TYPE = () -> CODEC;

	private static final double MIN_COVER = 0.75;
	private static final int MAX_FRONT_SPREAD = 5, MAX_RISE_AHEAD = 3, STEP = 16, REACH = 32;

	private final Holder<StructureTemplatePool> startPool;
	private final BlockPos entrance;
	private final int cell, width;
	private final List<Integer> roof;

	public CitadelStructure(StructureSettings settings, Holder<StructureTemplatePool> startPool, BlockPos entrance,
			int cell, int width, List<Integer> roof) {
		super(settings);
		this.startPool = startPool;
		this.entrance = entrance;
		this.cell = cell;
		this.width = width;
		this.roof = roof;
	}

	private record Candidate(BlockPos origin, Rotation rotation, double score) {
	}

	@Override
	protected Optional<GenerationStub> findGenerationPoint(GenerationContext ctx) {
		if (!ctx.couldValidBiomeExistOnTopOfChunkCenter()) {
			return Optional.empty();
		}
		boolean forced = acceptsAnyBiome(ctx);
		var manager = ctx.structureTemplateManager();
		StructurePoolElement element = startPool.value().getRandomTemplate(ctx.random());
		Map<Long, int[]> cache = new HashMap<>();
		int cx = ctx.chunkPos().getMiddleBlockX(), cz = ctx.chunkPos().getMiddleBlockZ();
		Candidate best = null;
		for (Rotation rot : Rotation.getShuffled(ctx.random())) {
			for (int dx = -REACH; dx <= REACH; dx += STEP) {
				for (int dz = -REACH; dz <= REACH; dz += STEP) {
					Candidate c = evaluate(ctx, cache, rot, cx + dx, cz + dz, best == null ? 0 : best.score(), forced);
					if (c != null && (best == null || c.score() > best.score())) {
						best = c;
					}
				}
			}
		}
		if (best == null || (!forced && best.score() < MIN_COVER)) {
			return Optional.empty();
		}
		BlockPos origin = best.origin();
		Rotation rot = best.rotation();
		var size = element.getSize(manager, Rotation.NONE);
		BlockPos center = origin.offset(new BlockPos(size.getX() / 2, entrance.getY(), size.getZ() / 2).rotate(rot));
		return Optional.of(new GenerationStub(center, builder -> builder.addPiece(new PoolElementStructurePiece(manager, element,
				origin, element.getGroundLevelDelta(), rot, element.getBoundingBox(manager, origin, rot),
				LiquidSettings.IGNORE_WATERLOGGING))));
	}

	/** Candidate with the entrance at (ax, az) and the given rotation, or null if the terrain does not work. */
	private Candidate evaluate(GenerationContext ctx, Map<Long, int[]> cache, Rotation rot, int ax, int az, double toBeat,
			boolean forced) {
		BlockPos e = new BlockPos(entrance.getX(), 0, entrance.getZ()).rotate(rot);
		int ox = ax - e.getX(), oz = az - e.getZ();
		List<Integer> front = new ArrayList<>();
		for (int k = -6; k <= 6; k += 3) {
			int[] h = height(ctx, cache, ox, oz, rot, entrance.getX() + k, entrance.getZ() - 2);
			if (h[0] != h[1] && !forced) {
				return null;                            // water in front of the gate
			}
			front.add(h[0]);
		}
		front.sort(null);
		int floor = front.get(front.size() / 2);
		if (!forced && front.get(front.size() - 1) - front.get(0) > MAX_FRONT_SPREAD) {
			return null;
		}
		for (int k = -4; k <= 4; k += 4) {
			if (!forced && height(ctx, cache, ox, oz, rot, entrance.getX() + k, entrance.getZ() - 10)[0] > floor + MAX_RISE_AHEAD) {
				return null;
			}
		}
		int oy = floor - entrance.getY();
		if (oy < ctx.heightAccessor().getMinY() + 2) {
			return null;
		}
		int total = 0, covered = 0, rows = roof.size() / width;
		for (int v : roof) {
			if (v >= 0) {
				total++;
			}
		}
		int seen = 0;
		for (int j = 0; j < rows; j++) {
			for (int i = 0; i < width; i++) {
				int v = roof.get(j * width + i);
				if (v < 0) {
					continue;
				}
				seen++;
				int h = height(ctx, cache, ox, oz, rot, i * cell + cell / 2, j * cell + cell / 2)[1];
				if (h >= oy + v - 1) {
					covered++;
				}
				if ((covered + (total - seen)) / (double) total < Math.max(forced ? 0 : MIN_COVER, toBeat)) {
					return null;                        // it can no longer improve
				}
			}
		}
		return new Candidate(new BlockPos(ox, oy, oz), rot, covered / (double) total);
	}

	/** {surface with water, solid floor} in the column of the template's local position (lx, lz). */
	private static int[] height(GenerationContext ctx, Map<Long, int[]> cache, int ox, int oz, Rotation rot, int lx, int lz) {
		BlockPos p = new BlockPos(lx, 0, lz).rotate(rot);
		int x = ((ox + p.getX()) >> 2 << 2) + 2, z = ((oz + p.getZ()) >> 2 << 2) + 2;
		return cache.computeIfAbsent(((long) x << 32) ^ (z & 0xffffffffL), k -> new int[] {
				ctx.chunkGenerator().getBaseHeight(x, z, Heightmap.Types.WORLD_SURFACE_WG, ctx.heightAccessor(), ctx.randomState()),
				ctx.chunkGenerator().getBaseHeight(x, z, Heightmap.Types.OCEAN_FLOOR_WG, ctx.heightAccessor(), ctx.randomState())});
	}

	/** /place structure passes a predicate that accepts any biome: then it is placed even if the terrain does not fit. */
	private boolean acceptsAnyBiome(GenerationContext ctx) {
		Optional<? extends Holder<Biome>> plains = ctx.registryAccess().lookupOrThrow(Registries.BIOME)
				.get(Identifier.withDefaultNamespace("plains"));
		return plains.isPresent() && !biomes().contains(plains.get()) && ctx.validBiome().test(plains.get());
	}

	@Override
	public StructureType<?> type() {
		return TYPE;
	}
}
