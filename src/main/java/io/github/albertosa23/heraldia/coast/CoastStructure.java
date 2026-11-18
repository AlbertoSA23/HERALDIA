package io.github.albertosa23.heraldia.coast;

import com.mojang.serialization.Codec;
import com.mojang.serialization.MapCodec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import io.github.albertosa23.heraldia.common.HeightCache;
import io.github.albertosa23.heraldia.common.Generation;
import io.github.albertosa23.heraldia.common.Profiler;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.atomic.AtomicInteger;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.Holder;
import net.minecraft.core.QuartPos;
import net.minecraft.core.registries.Registries;
import net.minecraft.tags.TagKey;
import net.minecraft.world.level.biome.Biome;
import net.minecraft.world.level.block.Rotation;
import net.minecraft.world.level.levelgen.structure.BoundingBox;
import net.minecraft.world.level.levelgen.structure.PoolElementStructurePiece;
import net.minecraft.world.level.levelgen.structure.Structure;
import net.minecraft.world.level.levelgen.structure.StructureType;
import net.minecraft.world.level.levelgen.structure.pools.StructurePoolElement;
import net.minecraft.world.level.levelgen.structure.pools.StructureTemplatePool;
import net.minecraft.world.level.levelgen.structure.templatesystem.LiquidSettings;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Coast lighthouse or shipwreck (heraldia:costa, tools/gen/litoral): a single template placed on the shore that
 * {@link Shoreline} finds with the shared generation height cache ({@link HeightCache}), rotated so its +z faces the
 * sea and with its anchor on the last land block. The lighthouse sits at terrain height (the platform; its foundations and
 * piles go down to the ground with the template's processor); the shipwreck, with row {@code fila_mar} at sea
 * level - 1. The style is that of the coast's climate: one of the {@code climates} pairs (land biome at the
 * anchor and sea biome 12 blocks offshore); the structure_set's other styles do not spawn there. With /place (which accepts
 * any biome) it is placed on whatever shore it finds or, without one, in the center facing south.
 */
public final class CoastStructure extends Structure implements io.github.albertosa23.heraldia.mines.ParallelLocate.Precomputable {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	private static final AtomicInteger REGISTERED = new AtomicInteger(); // the first ones, in the log (tests)
	private static final int LOGGED = 6, OFFSHORE = 12;
	/** With -Dheraldia.depurar.costa=true, each site goes to the log (tools/smoke/costa.py reads it to know where each one ended up). */
	private static final boolean DEBUG = Boolean.getBoolean("heraldia.depurar.costa");

	/** Climate pair: land biome on the shore and sea biome in front. */
	public record Climate(TagKey<Biome> land, TagKey<Biome> seaSide) {
		static final Codec<Climate> CODEC = RecordCodecBuilder.create(i -> i.group(
				TagKey.hashedCodec(Registries.BIOME).fieldOf("tierra").forGetter(Climate::land),
				TagKey.hashedCodec(Registries.BIOME).fieldOf("mar").forGetter(Climate::seaSide)
		).apply(i, Climate::new));
	}

	public static final MapCodec<CoastStructure> CODEC = RecordCodecBuilder.mapCodec(i -> i.group(
			settingsCodec(i),
			StructureTemplatePool.CODEC.fieldOf("start_pool").forGetter(s -> s.pool),
			Codec.STRING.fieldOf("modo").forGetter(s -> s.shape.mode().id),
			Codec.INT.listOf(2, 2).fieldOf("ancla").forGetter(s -> List.of(s.anchorX, s.anchorZ)),
			Codec.INT.listOf(4, 4).fieldOf("tierra").forGetter(s -> list(s.shape.land())),
			Codec.INT.listOf(4, 4).fieldOf("mar").forGetter(s -> list(s.shape.seaSide())),
			Codec.intRange(-1, 64).fieldOf("fila_mar").forGetter(s -> s.seaRow),
			Climate.CODEC.listOf().fieldOf("climas").forGetter(s -> s.climates)
	).apply(i, CoastStructure::new));
	public static final StructureType<CoastStructure> TYPE = () -> CODEC;

	private final Holder<StructureTemplatePool> pool;
	private final Shoreline.Shape shape;
	private final int anchorX, anchorZ, seaRow;
	private final List<Climate> climates;

	public CoastStructure(StructureSettings settings, Holder<StructureTemplatePool> pool, String mode, List<Integer> anchor,
			List<Integer> land, List<Integer> seaSide, int seaRow, List<Climate> climates) {
		super(settings);
		this.pool = pool;
		this.shape = new Shoreline.Shape(Shoreline.Mode.of(mode), array(land), array(seaSide));
		this.anchorX = anchor.get(0);
		this.anchorZ = anchor.get(1);
		this.seaRow = seaRow;
		this.climates = List.copyOf(climates);
	}

	private static int[] array(List<Integer> l) {
		return l.stream().mapToInt(Integer::intValue).toArray();
	}

	private static List<Integer> list(int[] a) {
		return java.util.Arrays.stream(a).boxed().toList();
	}

	public Shoreline.Shape shape() {
		return shape;
	}

	@Override
	protected Optional<GenerationStub> findGenerationPoint(GenerationContext ctx) {
		boolean forced = Generation.forced(ctx, biomes());
		HeightCache c = HeightCache.of(ctx);
		int sea = ctx.chunkGenerator().getSeaLevel();
		int mx = ctx.chunkPos().getMiddleBlockX(), mz = ctx.chunkPos().getMiddleBlockZ();
		long t0 = System.nanoTime();
		Shoreline.Site site = Shoreline.search(terrain(c), sea, mx, mz, shape);
		Profiler.end(Profiler.Segment.COAST_SHORE, t0);
		if (site != null && !forced && !climate(ctx, site, c, sea)) {
			return Optional.empty();                     // another style of the set: this coast's is a different one
		}
		boolean noShore = site == null;
		if (site == null) {
			if (!forced) {
				return Optional.empty();
			}
			site = new Shoreline.Site(mx, mz, Direction.SOUTH, Math.max(c.floor(mx, mz) - 1, sea), 0);
		}
		Rotation rotation = rotation(site.seaSide());
		int y = shape.mode() == Shoreline.Mode.LIGHTHOUSE ? site.y() : sea - 1 - seaRow;
		BlockPos a = new BlockPos(anchorX, 0, anchorZ).rotate(rotation);
		BlockPos origin = new BlockPos(site.x() - a.getX(), y, site.z() - a.getZ());
		var manager = ctx.structureTemplateManager();
		StructurePoolElement element = pool.value().getRandomTemplate(ctx.random());
		BoundingBox box = element.getBoundingBox(manager, origin, rotation);
		if (forced || DEBUG || REGISTERED.getAndIncrement() < LOGGED) {
			LOGGER.info("Heraldia: costa ({}) en {} {} {} hacia el {} (nota {}{}): orilla en {} µs", shape.mode().id,
					site.x(), y, site.z(), site.seaSide().getSerializedName(), site.note(), noShore ? ", sin orilla" : "",
					(System.nanoTime() - t0) / 1000);
		}
		PoolElementStructurePiece piece = new PoolElementStructurePiece(manager, element, origin, element.getGroundLevelDelta(), rotation, box,
				LiquidSettings.IGNORE_WATERLOGGING);
		return Optional.of(new GenerationStub(new BlockPos(site.x(), c.floor(site.x(), site.z()), site.z()), b -> b.addPiece(piece)));
	}

	/**
	 * What {@link #findGenerationPoint} would look at in that chunk (the shore search), only to fill the shared
	 * height cache: /locate uses it from other threads (mines/ParallelLocate). It creates nothing and writes nothing to the log.
	 */
	@Override
	public void precompute(GenerationContext ctx) {
		long t0 = Profiler.start();
		Shoreline.search(terrain(HeightCache.of(ctx)), ctx.chunkGenerator().getSeaLevel(), ctx.chunkPos().getMiddleBlockX(),
				ctx.chunkPos().getMiddleBlockZ(), shape);
		Profiler.end(Profiler.Segment.HILLSIDE_EARLY, t0);
	}

	/** The rotation that turns the template's +z towards d. */
	public static Rotation rotation(Direction d) {
		for (Rotation r : Rotation.values()) {
			BlockPos v = new BlockPos(0, 0, 1).rotate(r);
			if (v.getX() == d.getStepX() && v.getZ() == d.getStepZ()) {
				return r;
			}
		}
		return Rotation.NONE;
	}

	/** Is this shore's climate one of the style's? Two biome-noise reads (cheap: they do not evaluate terrain). */
	private boolean climate(GenerationContext ctx, Shoreline.Site s, HeightCache c, int sea) {
		Holder<Biome> land = biome(ctx, s.x(), c.floor(s.x(), s.z()), s.z());
		Holder<Biome> seaSide = biome(ctx, s.x() + s.seaSide().getStepX() * OFFSHORE, sea - 1, s.z() + s.seaSide().getStepZ() * OFFSHORE);
		for (Climate k : climates) {
			if (land.is(k.land()) && seaSide.is(k.seaSide())) {
				return true;
			}
		}
		return false;
	}

	private static Holder<Biome> biome(GenerationContext ctx, int x, int y, int z) {
		return ctx.biomeResolver().getNoiseBiome(QuartPos.fromBlock(x), QuartPos.fromBlock(y), QuartPos.fromBlock(z));
	}

	/** The search terrain over the world's shared cache. */
	public static Shoreline.Terrain terrain(HeightCache c) {
		return new Shoreline.Terrain() {
			@Override
			public int ground(int x, int z) {
				return c.floor(x, z);
			}

			@Override
			public boolean water(int x, int z) {
				return c.water(x, z);
			}
		};
	}

	@Override
	public StructureType<?> type() {
		return TYPE;
	}
}
