package io.github.albertosa23.heraldia.mines;

import com.mojang.serialization.Codec;
import com.mojang.serialization.MapCodec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import io.github.albertosa23.heraldia.common.Heights;
import io.github.albertosa23.heraldia.common.HeightCache;
import io.github.albertosa23.heraldia.common.Generation;
import io.github.albertosa23.heraldia.common.Profiler;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.atomic.AtomicInteger;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Holder;
import net.minecraft.world.level.levelgen.structure.PoolElementStructurePiece;
import net.minecraft.world.level.levelgen.structure.Structure;
import net.minecraft.world.level.levelgen.structure.StructureType;
import net.minecraft.world.level.levelgen.structure.pools.StructurePoolElement;
import net.minecraft.world.level.levelgen.structure.pools.StructureTemplatePool;
import net.minecraft.world.level.levelgen.structure.templatesystem.LiquidSettings;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Heraldia mine entrance (heraldia:mina_entrada, tools/gen/mines): a single template with the yard, the mouth, the
 * descent and the gallery, placed on a hillside that {@link Hillside} finds with the generation height map (cached,
 * {@link Heights}, and columns on a 4-block lattice that share the samples). Before searching it checks the biome at the
 * chunk's center (one column): a structure_set with one style per biome tries its entries one by one, and those not
 * of that biome return without paying for the search. The mouth (template z = 0) faces downhill; if nothing works it is not
 * generated, except with /place (which accepts any biome), which places it anyway.
 */
public final class MineEntranceStructure extends Structure implements ParallelLocate.Precomputable {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	private static final AtomicInteger REGISTERED = new AtomicInteger(); // the first ones, in the log (tests)
	private static final int LOGGED = 6;

	public static final MapCodec<MineEntranceStructure> CODEC = RecordCodecBuilder.mapCodec(i -> i.group(
			settingsCodec(i),
			StructureTemplatePool.CODEC.fieldOf("start_pool").forGetter(s -> s.pool),
			BlockPos.CODEC.fieldOf("entrada").forGetter(s -> s.shape.entry()),
			Codec.INT.listOf(4, 4).fieldOf("patio").forGetter(s -> List.of(s.shape.yardX0(), s.shape.yardZ0(), s.shape.yardX1(),
					s.shape.yardZ1())),
			Codec.INT.listOf(3, 3).listOf().fieldOf("techo").forGetter(s -> s.shape.ceiling().stream().map(a -> List.of(a[0], a[1], a[2])).toList())
	).apply(i, MineEntranceStructure::new));
	public static final StructureType<MineEntranceStructure> TYPE = () -> CODEC;

	private final Holder<StructureTemplatePool> pool;
	private final Hillside.Shape shape;

	public MineEntranceStructure(StructureSettings settings, Holder<StructureTemplatePool> pool, BlockPos entry, List<Integer> yard,
			List<List<Integer>> ceiling) {
		super(settings);
		this.pool = pool;
		this.shape = new Hillside.Shape(entry, yard.get(0), yard.get(1), yard.get(2), yard.get(3),
				ceiling.stream().map(l -> new int[] {l.get(0), l.get(1), l.get(2)}).toList());
	}

	@Override
	protected Optional<GenerationStub> findGenerationPoint(GenerationContext ctx) {
		boolean forced = Generation.forced(ctx, biomes());
		Hillside.Terrain terrain = terrain(HeightCache.of(ctx));
		int mx = ctx.chunkPos().getMiddleBlockX(), mz = ctx.chunkPos().getMiddleBlockZ();
		if (!forced && !Generation.biome(ctx, biomes(), mx, terrain.ground(mx, mz), mz)) {
			return Optional.empty();                    // another style of the set: no search at all
		}
		long t0 = System.nanoTime();
		Hillside.Site site = Hillside.search(terrain, mx, mz, shape, ctx.heightAccessor().getMinY(), forced);
		Profiler.end(Profiler.Segment.HILLSIDE, t0);
		if (site == null) {
			return Optional.empty();
		}
		var manager = ctx.structureTemplateManager();
		StructurePoolElement element = pool.value().getRandomTemplate(ctx.random());
		BlockPos e = shape.entry().rotate(site.rotation());
		BlockPos origin = new BlockPos(site.x() - e.getX(), site.feet() - 1 - e.getY(), site.z() - e.getZ());
		if (forced || REGISTERED.getAndIncrement() < LOGGED) {
			LOGGER.info("Heraldia: entrada a mina en {} {} {} (giro {}, nota {}): ladera en {} µs", site.x(), site.feet(), site.z(),
					site.rotation(), Math.round(site.note()), (System.nanoTime() - t0) / 1000);
		}
		return Optional.of(new GenerationStub(new BlockPos(site.x(), site.feet(), site.z()), builder -> builder.addPiece(
				new PoolElementStructurePiece(manager, element, origin, element.getGroundLevelDelta(), site.rotation(),
						element.getBoundingBox(manager, origin, site.rotation()), LiquidSettings.IGNORE_WATERLOGGING))));
	}

	/**
	 * Precomputes what {@link #findGenerationPoint} would look at in that chunk (the center's biome and, if it is its own, the
	 * hillside search): it only fills the shared height cache, without creating anything or writing to the log.
	 * {@link ParallelLocate} uses it from other threads so /locate finds the columns already computed.
	 */
	@Override
	public void precompute(GenerationContext ctx) {
		Hillside.Terrain terrain = terrain(HeightCache.of(ctx));
		int mx = ctx.chunkPos().getMiddleBlockX(), mz = ctx.chunkPos().getMiddleBlockZ();
		if (Generation.biome(ctx, biomes(), mx, terrain.ground(mx, mz), mz)) {
			long t0 = Profiler.start();
			Hillside.search(terrain, mx, mz, shape, ctx.heightAccessor().getMinY(), false);
			Profiler.end(Profiler.Segment.HILLSIDE_EARLY, t0);
		}
	}

	/**
	 * The search terrain over the world's shared cache ({@link HeightCache}): the styles and variants of the
	 * structure_set, /locate and the placement rule look at the same columns and no longer compute them again. Same
	 * values as with a per-search cache ({@link Heights}, the old way): MinesDeterminismTest checks it.
	 */
	public static Hillside.Terrain terrain(HeightCache c) {
		return terrain(c::floor, c::water);
	}

	/** The old way (one cache per search): only for comparison in the tests. */
	public static Hillside.Terrain terrain(Heights a) {
		return terrain(a::floor, a::water);
	}

	private static Hillside.Terrain terrain(java.util.function.IntBinaryOperator floor, java.util.function.BiPredicate<Integer, Integer> water) {
		return new Hillside.Terrain() {
			@Override
			public int ground(int x, int z) {
				return floor.applyAsInt(mesh(x), mesh(z));
			}

			@Override
			public boolean water(int x, int z) {
				return water.test(mesh(x), mesh(z));
			}
		};
	}

	/** Columns on a 4-block lattice (center of each cell): neighboring samples share the cache. */
	static int mesh(int v) {
		return (v >> 2 << 2) + 2;
	}

	public Hillside.Shape shape() {
		return shape;
	}

	@Override
	public StructureType<?> type() {
		return TYPE;
	}
}
