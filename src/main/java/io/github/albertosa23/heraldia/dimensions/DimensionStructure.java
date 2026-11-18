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
 * heraldia:dimension: una estructura de jigsaw (una pieza en las medianas, varias en las únicas) para el Nether o el End,
 * donde el {@code project_start_to_heightmap} del jigsaw vanilla no sirve (en el Nether da el techo de bedrock; en el
 * End, el vacío). La altura del inicio la decide {@link Ground} con la columna de ruido del centro y de las cuatro
 * esquinas de la huella ({@code radius} bloques del centro): solo en los chunks candidatos de la rejilla, unas pocas
 * columnas por candidata. Sin sitio, no sale; con /place structure (que acepta cualquier bioma) se coloca en el centro a
 * y = 64 para poder probarla en cualquier sitio. La y del inicio es la primera libre sobre el suelo: con la pieza rígida
 * (getGroundLevelDelta = 1) la fila y = 0 de la plantilla queda a ras de suelo, como en el mundo principal.
 */
public final class DimensionStructure extends Structure {
	/** Dónde se apoya. */
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
	/** Altura del inicio con /place structure sin sitio a la vista (pruebas). */
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

	/** Dónde va el inicio (la y es la primera libre sobre el suelo). */
	public record Site(int x, int y, int z) {
	}

	/** Puntos que se prueban alrededor del centro del chunk (bloques), en orden: el centro y una cruz a medio chunk. */
	static final int[][] POINTS = {{0, 0}, {8, 0}, {-8, 0}, {0, 8}, {0, -8}};
	/** Suelos de una misma columna del Nether que se prueban, de arriba abajo (cuevas superpuestas). */
	static final int GROUNDS = 4;

	/**
	 * El primer sitio válido de {@link #POINTS} (Nether con {@code columns}, End con {@code heights}) o null. Solo en los
	 * chunks candidatos de la rejilla: como mucho 5 puntos x 5 columnas, y en el Nether cada columna se lee una vez.
	 */
	public static Site site(Columns columns, Heights heights, int cx, int cz, int radius, int free) {
		java.util.Map<Long, NoiseColumn> read = new java.util.HashMap<>();
		Columns memo = columns == null ? null : (x, z) -> read.computeIfAbsent(BlockPos.asLong(x, 0, z), k -> columns.en(x, z));
		for (int[] d : POINTS) {
			int x = cx + d[0], z = cz + d[1];
			int y = memo != null ? nether(memo, x, z, radius, free) : end(heights, x, z, radius);
			if (y != Ground.DRY) {
				return new Site(x, y, z);
			}
		}
		return null;
	}

	/** Columna de ruido de un punto (en el juego, ChunkGenerator.getBaseColumn: no carga ni genera chunks). */
	@FunctionalInterface
	public interface Columns {
		NoiseColumn en(int x, int z);
	}

	/** Primera y libre de un punto según el heightmap WORLD_SURFACE_WG (en el juego, ChunkGenerator.getBaseHeight). */
	@FunctionalInterface
	public interface Heights {
		int en(int x, int z);
	}

	/** Altura del inicio en el Nether (Suelo.nether en el centro, esquinas a ±DESNIVEL; hasta SUELOS suelos de arriba abajo) o Suelo.NINGUNO. Pública para las pruebas. */
	public static int nether(Columns columns, int x, int z, int radius, int free) {
		NoiseColumn c = columns.en(x, z);
		int from = Ground.NETHER_FROM;
		for (int n = 0; n < GROUNDS; n++) {
			int y = Ground.nether(k -> solid(c.getBlock(k)), k -> air(c.getBlock(k)), from, Ground.NETHER_TO, free);
			if (y == Ground.DRY) {
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
			from = y - 2;                                   // el siguiente suelo, por debajo de este
		}
		return Ground.DRY;
	}

	/** Altura del inicio en el End (Suelo.end con el centro y las cuatro esquinas) o Suelo.NINGUNO. Pública para las pruebas. */
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
