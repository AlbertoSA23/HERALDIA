package io.github.albertosa23.heraldia.uniques.galleon;

import com.mojang.serialization.Codec;
import io.github.albertosa23.heraldia.common.Generation;
import com.mojang.serialization.MapCodec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import java.util.List;
import java.util.Optional;
import it.unimi.dsi.fastutil.longs.Long2IntOpenHashMap;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Holder;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.block.Mirror;
import net.minecraft.world.level.block.Rotation;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.level.levelgen.structure.Structure;
import net.minecraft.world.level.levelgen.structure.StructureType;
import net.minecraft.world.level.levelgen.structure.pools.DimensionPadding;
import net.minecraft.world.level.levelgen.structure.pools.JigsawPlacement;
import net.minecraft.world.level.levelgen.structure.pools.StructureTemplatePool;
import net.minecraft.world.level.levelgen.structure.pools.alias.PoolAliasLookup;
import net.minecraft.world.level.levelgen.structure.structures.JigsawStructure;
import net.minecraft.world.level.levelgen.structure.templatesystem.LiquidSettings;
import net.minecraft.world.level.levelgen.structure.templatesystem.StructureTemplate;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Stranded galleon: a jigsaw piece placed on the shore. The jigsaw does not see water, so before placing it
 * the spot is searched, on a grid around the chunk and with the four rotations, where all the template's probes
 * (sea on one side of the hull, beach on the other, camp and rock on land) fall within their floor height range.
 */
public final class GalleonStructure extends Structure {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	public record Probe(int dx, int dz, int min, int max, boolean required) {
		public static final Codec<Probe> CODEC = RecordCodecBuilder.create(i -> i.group(
				Codec.INT.fieldOf("dx").forGetter(Probe::dx), Codec.INT.fieldOf("dz").forGetter(Probe::dz),
				Codec.INT.fieldOf("min").forGetter(Probe::min), Codec.INT.fieldOf("max").forGetter(Probe::max),
				Codec.BOOL.fieldOf("required").forGetter(Probe::required)).apply(i, Probe::new));
	}

	public static final MapCodec<GalleonStructure> CODEC = RecordCodecBuilder.mapCodec(i -> i.group(
			settingsCodec(i),
			StructureTemplatePool.CODEC.fieldOf("start_pool").forGetter(s -> s.startPool),
			BlockPos.CODEC.fieldOf("anchor").forGetter(s -> s.anchor),
			Probe.CODEC.listOf().fieldOf("probes").forGetter(s -> s.probes),
			Codec.intRange(0, 32).fieldOf("max_misses").forGetter(s -> s.maxMisses),
			Codec.intRange(8, 64).fieldOf("search_radius").forGetter(s -> s.searchRadius)).apply(i, GalleonStructure::new));
	public static final StructureType<GalleonStructure> TYPE = () -> CODEC;

	private final Holder<StructureTemplatePool> startPool;
	private final BlockPos anchor;
	private final List<Probe> probes;
	private final int maxMisses;
	private final int searchRadius;

	public GalleonStructure(Structure.StructureSettings settings, Holder<StructureTemplatePool> startPool, BlockPos anchor,
			List<Probe> probes, int maxMisses, int searchRadius) {
		super(settings);
		this.startPool = startPool;
		this.anchor = anchor;
		this.probes = probes;
		this.maxMisses = maxMisses;
		this.searchRadius = searchRadius;
	}

	private record Site(BlockPos anchor, Rotation rotation) {
	}

	@Override
	protected Optional<Structure.GenerationStub> findGenerationPoint(Structure.GenerationContext context) {
		ChunkPos chunk = context.chunkPos();
		int sea = context.chunkGenerator().getSeaLevel();
		Optional<Site> site = findSite(context, chunk.getMiddleBlockX(), chunk.getMiddleBlockZ(), sea);
		if (site.isEmpty()) {
			if (!Generation.forced(context, this.biomes())) {
				return Optional.empty();
			}
			// /place structure: with no shore nearby it is placed anyway in the center of the chunk (for tests)
			int x = chunk.getMiddleBlockX(), z = chunk.getMiddleBlockZ();
			int y = Math.max(sea, context.chunkGenerator().getBaseHeight(x, z, Heightmap.Types.WORLD_SURFACE_WG,
					context.heightAccessor(), context.randomState()));
			site = Optional.of(new Site(new BlockPos(x, y, z), Rotation.NONE));
		}
		Site s = site.get();
		LOGGER.info("Heraldia: galeón en la orilla, ancla {} {} {} giro {}", s.anchor().getX(), s.anchor().getY(), s.anchor().getZ(), s.rotation());
		BlockPos origin = s.anchor().subtract(StructureTemplate.transform(this.anchor, Mirror.NONE, s.rotation(), BlockPos.ZERO));
		// maxDepth >= 1: with 0, addPieces does not even add the central piece. JigsawPlacement leaves the piece's base one block below the position (getGroundLevelDelta = 1)
		Optional<Structure.GenerationStub> stub = JigsawPlacement.addPieces(Generation.withRotation(context, s.rotation()), this.startPool,
				Optional.empty(), 1, origin.above(), false, Optional.empty(), new JigsawStructure.MaxDistance(116),
				PoolAliasLookup.EMPTY, DimensionPadding.ZERO, LiquidSettings.IGNORE_WATERLOGGING);
		// the biome is validated at the anchor (at sea level), not at the box's center, which is underground
		return stub.map(g -> new Structure.GenerationStub(s.anchor(), g.generator()));
	}

	private Optional<Site> findSite(Structure.GenerationContext c, int cx, int cz, int sea) {
		boolean anyBeach = false;
		for (int dx = -64; dx <= 64 && !anyBeach; dx += 16) {
			for (int dz = -64; dz <= 64 && !anyBeach; dz += 16) {
				anyBeach = Generation.biome(c, this.biomes(), cx + dx, sea, cz + dz);
			}
		}
		if (!anyBeach) {
			return Optional.empty();
		}
		Long2IntOpenHashMap heights = new Long2IntOpenHashMap();
		Site best = null;
		int bestScore = Integer.MAX_VALUE;
		for (int ox = -this.searchRadius; ox <= this.searchRadius; ox += 8) {
			for (int oz = -this.searchRadius; oz <= this.searchRadius; oz += 8) {
				int ax = cx + ox, az = cz + oz;
				if (!Generation.biome(c, this.biomes(), ax, sea, az)) {
					continue;
				}
				for (Rotation rotation : Rotation.values()) {
					int score = score(c, heights, ax, az, rotation, sea);
					if (score < bestScore) {
						bestScore = score;
						best = new Site(new BlockPos(ax, sea, az), rotation);
					}
				}
			}
		}
		return Optional.ofNullable(best);
	}

	/** Failures * 1000 + terrain drop; MAX_VALUE if a mandatory probe fails or there are too many failures. */
	private int score(Structure.GenerationContext c, Long2IntOpenHashMap heights, int ax, int az, Rotation rotation, int sea) {
		int misses = 0, roughness = 0;
		for (Probe p : this.probes) {
			BlockPos o = StructureTemplate.transform(new BlockPos(p.dx(), 0, p.dz()), Mirror.NONE, rotation, BlockPos.ZERO);
			int x = ax + o.getX(), z = az + o.getZ();
			int h = heights.computeIfAbsent(BlockPos.asLong(x, 0, z), key -> c.chunkGenerator()
					.getBaseHeight(x, z, Heightmap.Types.OCEAN_FLOOR_WG, c.heightAccessor(), c.randomState())) - sea;
			if (h < p.min() || h > p.max()) {
				if (p.required() || ++misses > this.maxMisses) {
					return Integer.MAX_VALUE;
				}
			} else if (p.min() >= 0) {
				roughness += h - p.min();
			}
		}
		return misses * 1000 + roughness;
	}

	@Override
	public StructureType<?> type() {
		return TYPE;
	}
}
