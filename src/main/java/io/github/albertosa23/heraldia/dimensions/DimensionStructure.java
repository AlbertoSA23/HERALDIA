package io.github.albertosa23.heraldia.dimensions;

import com.mojang.serialization.Codec;
import com.mojang.serialization.MapCodec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import io.github.albertosa23.heraldia.common.Generation;
import java.util.Optional;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Holder;
import net.minecraft.util.StringRepresentable;
import net.minecraft.world.level.NoiseColumn;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.level.levelgen.structure.Structure;
import net.minecraft.world.level.levelgen.structure.StructureType;
import net.minecraft.world.level.levelgen.structure.pools.DimensionPadding;
import net.minecraft.world.level.levelgen.structure.pools.JigsawPlacement;
import net.minecraft.world.level.levelgen.structure.pools.StructureTemplatePool;
import net.minecraft.world.level.levelgen.structure.pools.alias.PoolAliasLookup;
import net.minecraft.world.level.levelgen.structure.structures.JigsawStructure;
import net.minecraft.world.level.levelgen.structure.templatesystem.LiquidSettings;

/**
 * heraldia:dimension: a jigsaw structure (one piece for the mediums, several for the uniques) for the Nether or the End,
 * where vanilla jigsaw's {@code project_start_to_heightmap} does not work (in the Nether it gives the bedrock ceiling; in the
 * End, the void). The start height is decided by {@link Ground} with the noise column of the center and of the four
 * corners of the footprint ({@code radius} blocks from the center): only in the grid's candidate chunks, a few
 * columns per candidate. Without a site, it does not spawn; with /place structure (which accepts any biome) it is placed in the center at
 * y = 64 so it can be tested anywhere. The start's y is the first free one above the ground: with the rigid piece
 * (getGroundLevelDelta = 1) the template's y = 0 row sits flush with the ground, as in the overworld.
 */
public final class DimensionStructure extends Structure {
	/** Where it rests. */
	public enum Mode implements StringRepresentable {
		NETHER("nether"), END("end");
		public static final Codec<Mode> CODEC = StringRepresentable.fromEnum(Mode::values);
		private final String name;

		Mode(String name) {
			this.name = name;
		}

		@Override
		public String getSerializedName() {
			return name;
		}
	}

	public static final MapCodec<DimensionStructure> CODEC = RecordCodecBuilder.mapCodec(i -> i.group(
			settingsCodec(i),
			StructureTemplatePool.CODEC.fieldOf("start_pool").forGetter(s -> s.startPool),
			Codec.intRange(1, 20).fieldOf("size").forGetter(s -> s.size),
			Codec.intRange(1, 116).fieldOf("max_distance_from_center").forGetter(s -> s.maxDistance),
			Mode.CODEC.fieldOf("modo").forGetter(s -> s.mode),
			Codec.intRange(1, 64).fieldOf("radio").forGetter(s -> s.radius),
			Codec.intRange(2, 64).fieldOf("libre").forGetter(s -> s.free)
	).apply(i, DimensionStructure::new));
	/** Start height with /place structure with no site in sight (tests). */
	static final int FORCED_Y = 64;

	private final Holder<StructureTemplatePool> startPool;
	private final int size, maxDistance, radius, free;
	private final Mode mode;

	public DimensionStructure(StructureSettings settings, Holder<StructureTemplatePool> startPool, int size, int maxDistance,
							  Mode mode, int radius, int free) {
		super(settings);
		this.startPool = startPool;
		this.size = size;
		this.maxDistance = maxDistance;
		this.mode = mode;
		this.radius = radius;
		this.free = free;
	}

	@Override
	public StructureType<?> type() {
		return Dimensions.TYPE;
	}

	public Mode mode() {
		return mode;
	}

	@Override
	protected Optional<GenerationStub> findGenerationPoint(GenerationContext ctx) {
		int cx = ctx.chunkPos().getMiddleBlockX(), cz = ctx.chunkPos().getMiddleBlockZ();
		Site s = mode == Mode.NETHER
				? site((x, z) -> ctx.chunkGenerator().getBaseColumn(x, z, ctx.heightAccessor(), ctx.randomState()), null, cx, cz, radius, free)
				: site(null, (x, z) -> ctx.chunkGenerator().getBaseHeight(x, z, Heightmap.Types.WORLD_SURFACE_WG, ctx.heightAccessor(),
				ctx.randomState()), cx, cz, radius, free);
		if (s == null) {
			if (!Generation.forced(ctx, biomes())) {
				return Optional.empty();
			}
			s = new Site(cx, FORCED_Y, cz);
		}
		return JigsawPlacement.addPieces(ctx, startPool, Optional.empty(), size, new BlockPos(s.x(), s.y(), s.z()), false, Optional.empty(),
				new JigsawStructure.MaxDistance(maxDistance), PoolAliasLookup.EMPTY, DimensionPadding.ZERO, LiquidSettings.IGNORE_WATERLOGGING);
	}

	/** Where the start goes (the y is the first free one above the ground). */
	public record Site(int x, int y, int z) {
	}

	/** Points tried around the chunk's center (blocks), in order: the center and a cross at half a chunk. */
	static final int[][] POINTS = {{0, 0}, {8, 0}, {-8, 0}, {0, 8}, {0, -8}};
	/** Grounds of the same Nether column that are tried, top down (stacked caves). */
	static final int GROUNDS = 4;

	/**
	 * The first valid site of {@link #POINTS} (Nether with {@code columns}, End with {@code heights}) or null. Only in the
	 * grid's candidate chunks: at most 5 points x 5 columns, and in the Nether each column is read once.
	 */
	public static Site site(Columns columns, Heights heights, int cx, int cz, int radius, int free) {
		java.util.Map<Long, NoiseColumn> read = new java.util.HashMap<>();
		Columns memo = columns == null ? null : (x, z) -> read.computeIfAbsent(BlockPos.asLong(x, 0, z), k -> columns.en(x, z));
		for (int[] d : POINTS) {
			int x = cx + d[0], z = cz + d[1];
			int y = memo != null ? nether(memo, x, z, radius, free) : end(heights, x, z, radius);
			if (y != Ground.NONE) {
				return new Site(x, y, z);
			}
		}
		return null;
	}

	/** Noise column of a point (in the game, ChunkGenerator.getBaseColumn: does not load or generate chunks). */
	@FunctionalInterface
	public interface Columns {
		NoiseColumn en(int x, int z);
	}

	/** First free y of a point by the WORLD_SURFACE_WG heightmap (in the game, ChunkGenerator.getBaseHeight). */
	@FunctionalInterface
	public interface Heights {
		int en(int x, int z);
	}

	/** Start height in the Nether (Ground.nether at the center, corners within ±DROP; up to GROUNDS grounds top down) or Ground.NONE. Public for the tests. */
	public static int nether(Columns columns, int x, int z, int radius, int free) {
		NoiseColumn c = columns.en(x, z);
		int from = Ground.NETHER_FROM;
		for (int n = 0; n < GROUNDS; n++) {
			int y = Ground.nether(k -> solid(c.getBlock(k)), k -> air(c.getBlock(k)), from, Ground.NETHER_TO, free);
			if (y == Ground.NONE) {
				return y;
			}
			int[] corners = new int[4];
			int k = 0;
			for (int dx = -radius; dx <= radius; dx += 2 * radius) {
				for (int dz = -radius; dz <= radius; dz += 2 * radius) {
					NoiseColumn e = columns.en(x + dx, z + dz);
					corners[k++] = Ground.netherNear(j -> solid(e.getBlock(j)), j -> air(e.getBlock(j)), y);
				}
			}
			if (Ground.flat(y, corners)) {
				return y;
			}
			from = y - 2;                                   // the next ground, below this one
		}
		return Ground.NONE;
	}

	/** Start height in the End (Ground.end with the center and the four corners) or Ground.NONE. Public for the tests. */
	public static int end(Heights heights, int x, int z, int radius) {
		return Ground.end(x, z, heights.en(x, z), heights.en(x - radius, z - radius), heights.en(x - radius, z + radius),
				heights.en(x + radius, z - radius), heights.en(x + radius, z + radius));
	}

	private static boolean solid(BlockState s) {
		return !s.isAir() && s.getFluidState().isEmpty();
	}

	private static boolean air(BlockState s) {
		return s.isAir() && s.getFluidState().isEmpty();
	}
}
