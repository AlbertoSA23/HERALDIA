package io.github.albertosa23.heraldia.uniques.mine;

import com.mojang.serialization.Codec;
import com.mojang.serialization.MapCodec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import io.github.albertosa23.heraldia.common.Heights;
import io.github.albertosa23.heraldia.common.Generation;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.atomic.AtomicInteger;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Holder;
import net.minecraft.world.level.block.Rotation;
import net.minecraft.world.level.levelgen.structure.PoolElementStructurePiece;
import net.minecraft.world.level.levelgen.structure.Structure;
import net.minecraft.world.level.levelgen.structure.StructureType;
import net.minecraft.world.level.levelgen.structure.pieces.StructurePiecesBuilder;
import net.minecraft.world.level.levelgen.structure.pools.StructurePoolElement;
import net.minecraft.world.level.levelgen.structure.pools.StructureTemplatePool;
import net.minecraft.world.level.levelgen.structure.templatesystem.LiquidSettings;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Lost mine: the colony (a large template) at a fixed height underground, the main shaft stacked on top in stretches
 * of 8 and 1 blocks and the headframe on the surface. It searches a 5 x 5 grid of points (every 16 blocks around
 * the candidate chunk) for the spot where the cavern's center and the most sample points fall in the biome (lush or
 * dripstone caves, at the cavern's height: it only reads the biome noise) and, for the best ones, checks the
 * terrain above the shaft with the generation height map: dry, almost flat under the headframe and with a shaft of 0 to
 * pozo_max blocks. If nothing passes it is not generated; with /place (which accepts any biome) the chunk is used as is.
 */
public final class MineStructure extends Structure {
	public static final MapCodec<MineStructure> CODEC = RecordCodecBuilder.mapCodec(i -> i.group(
			settingsCodec(i),
			StructureTemplatePool.CODEC.fieldOf("start_pool").forGetter(s -> s.colony),
			StructureTemplatePool.CODEC.fieldOf("pozo").forGetter(s -> s.shaft),
			StructureTemplatePool.CODEC.fieldOf("pozo_corto").forGetter(s -> s.shortShaft),
			StructureTemplatePool.CODEC.fieldOf("castillete").forGetter(s -> s.headframe),
			Codec.INT.fieldOf("colonia_y").forGetter(s -> s.colonyY),
			BlockPos.CODEC.fieldOf("eje_colonia").forGetter(s -> s.colonyAxis),
			BlockPos.CODEC.fieldOf("centro").forGetter(s -> s.center),
			BlockPos.CODEC.listOf().fieldOf("muestras").forGetter(s -> s.samples),
			BlockPos.CODEC.fieldOf("eje_pozo").forGetter(s -> s.shaftAxis),
			Codec.intRange(1, 64).fieldOf("alto_pozo").forGetter(s -> s.shaftHeight),
			BlockPos.CODEC.fieldOf("eje_castillete").forGetter(s -> s.headframeAxis),
			Codec.INT.listOf(4, 4).fieldOf("huella").forGetter(s -> s.footprint),
			Codec.intRange(0, 512).fieldOf("pozo_max").forGetter(s -> s.shaftMax)
	).apply(i, MineStructure::new));
	public static final StructureType<MineStructure> TYPE = () -> CODEC;

	private static final int STEP = 16, REACH = 32, TRIES = 3, MAX_SPREAD = 5, LOGGED = 8;
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	private static final AtomicInteger logged = new AtomicInteger(); // the first ones, in the log (tests)

	private final Holder<StructureTemplatePool> colony, shaft, shortShaft, headframe;
	private final int colonyY, shaftHeight, shaftMax;
	private final BlockPos colonyAxis, center, shaftAxis, headframeAxis;
	private final List<BlockPos> samples;
	private final List<Integer> footprint;

	public MineStructure(StructureSettings settings, Holder<StructureTemplatePool> colony, Holder<StructureTemplatePool> shaft,
			Holder<StructureTemplatePool> shortShaft, Holder<StructureTemplatePool> headframe, int colonyY, BlockPos colonyAxis,
			BlockPos center, List<BlockPos> samples, BlockPos shaftAxis, int shaftHeight, BlockPos headframeAxis, List<Integer> footprint,
			int shaftMax) {
		super(settings);
		this.colony = colony;
		this.shaft = shaft;
		this.shortShaft = shortShaft;
		this.headframe = headframe;
		this.colonyY = colonyY;
		this.colonyAxis = colonyAxis;
		this.center = center;
		this.samples = samples;
		this.shaftAxis = shaftAxis;
		this.shaftHeight = shaftHeight;
		this.headframeAxis = headframeAxis;
		this.footprint = footprint;
		this.shaftMax = shaftMax;
	}

	private record Site(int x, int z, int score, int dist) {
	}

	@Override
	protected Optional<GenerationStub> findGenerationPoint(GenerationContext ctx) {
		boolean forced = Generation.forced(ctx, biomes());
		Rotation rot = Rotation.getRandom(ctx.random());
		int mx = ctx.chunkPos().getMiddleBlockX(), mz = ctx.chunkPos().getMiddleBlockZ();
		int cy = colonyY + center.getY();
		List<Site> sites = new ArrayList<>();
		for (int dx = -REACH; dx <= REACH; dx += STEP) {
			for (int dz = -REACH; dz <= REACH; dz += STEP) {
				if (forced && (dx != 0 || dz != 0)) {
					continue;
				}
				int x = mx + dx, z = mz + dz;
				int score = 0;
				if (!forced) {
					if (!Generation.biome(ctx, biomes(), x, cy, z)) {
						continue;                       // the cavern's center must fall in the biome
					}
					for (BlockPos m : samples) {
						BlockPos r = local(m.getX() - center.getX(), m.getZ() - center.getZ(), rot);
						if (Generation.biome(ctx, biomes(), x + r.getX(), colonyY + m.getY(), z + r.getZ())) {
							score++;
						}
					}
				}
				sites.add(new Site(x, z, score, dx * dx + dz * dz));
			}
		}
		sites.sort(Comparator.comparingInt(Site::score).reversed().thenComparingInt(Site::dist));
		Heights heights = new Heights(ctx);
		for (int k = 0; k < Math.min(TRIES, sites.size()); k++) {
			Optional<GenerationStub> stub = tryAt(ctx, heights, rot, sites.get(k), cy, forced);
			if (stub.isPresent()) {
				return stub;
			}
		}
		return Optional.empty();
	}

	private Optional<GenerationStub> tryAt(GenerationContext ctx, Heights heights, Rotation rot, Site s, int cy, boolean forced) {
		BlockPos c = local(center.getX(), center.getZ(), rot);
		int ox = s.x() - c.getX(), oz = s.z() - c.getZ();                  // origin of the colony
		BlockPos e = local(colonyAxis.getX(), colonyAxis.getZ(), rot);
		int ax = ox + e.getX(), az = oz + e.getZ();                        // shaft axis
		int ground = heights.floor(ax, az), lo = ground, hi = ground;
		boolean water = heights.water(ax, az);
		for (int i = 0; i < 4; i++) {
			BlockPos q = local(footprint.get((i & 1) == 0 ? 0 : 2), footprint.get((i & 2) == 0 ? 1 : 3), rot);
			int h = heights.floor(ax + q.getX(), az + q.getZ());
			lo = Math.min(lo, h);
			hi = Math.max(hi, h);
			water |= heights.water(ax + q.getX(), az + q.getZ());
		}
		int base = colonyY + colonyAxis.getY();                         // first layer of the shaft
		int yc = ground - 1 - headframeAxis.getY();                       // origin of the headframe (foundation)
		if (!forced && (water || hi - lo > MAX_SPREAD || yc < base || yc - base > shaftMax)) {
			return Optional.empty();
		}
		yc = Math.max(yc, base);
		List<PoolElementStructurePiece> pieces = new ArrayList<>();
		pieces.add(piece(ctx, colony, new BlockPos(ox, colonyY, oz), rot));
		int y = base;
		for (; y + shaftHeight <= yc; y += shaftHeight) {
			pieces.add(piece(ctx, shaft, axis(ax, y, az, shaftAxis, rot), rot));
		}
		for (; y < yc; y++) {
			pieces.add(piece(ctx, shortShaft, axis(ax, y, az, shaftAxis, rot), rot));
		}
		pieces.add(piece(ctx, headframe, axis(ax, yc, az, headframeAxis, rot), rot));
		if (logged.getAndIncrement() < LOGGED) {
			LOGGER.info("Heraldia: mina perdida en el chunk {}, {}: eje del pozo en {}, {}, pozo de {} bloques de y = {} a {}, "
					+ "suelo del castillete a y = {}, giro {}", ctx.chunkPos().x(), ctx.chunkPos().z(), ax, az, yc - base, base, yc,
					yc + headframeAxis.getY(), rot);
		}
		return Optional.of(new GenerationStub(new BlockPos(s.x(), cy, s.z()), (StructurePiecesBuilder b) -> pieces.forEach(b::addPiece)));
	}

	/** Origin of a piece whose local axis (x, z) falls at world (ax, az), with its layer 0 at height y. */
	private static BlockPos axis(int ax, int y, int az, BlockPos local, Rotation rot) {
		BlockPos r = local(local.getX(), local.getZ(), rot);
		return new BlockPos(ax - r.getX(), y, az - r.getZ());
	}

	private static BlockPos local(int x, int z, Rotation rot) {
		return new BlockPos(x, 0, z).rotate(rot);
	}

	private static PoolElementStructurePiece piece(GenerationContext ctx, Holder<StructureTemplatePool> pool, BlockPos origin, Rotation rot) {
		var manager = ctx.structureTemplateManager();
		StructurePoolElement element = pool.value().getRandomTemplate(ctx.random());
		return new PoolElementStructurePiece(manager, element, origin, element.getGroundLevelDelta(), rot,
				element.getBoundingBox(manager, origin, rot), LiquidSettings.IGNORE_WATERLOGGING);
	}

	@Override
	public StructureType<?> type() {
		return TYPE;
	}
}
