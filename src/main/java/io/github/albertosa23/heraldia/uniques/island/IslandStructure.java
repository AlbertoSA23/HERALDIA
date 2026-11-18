package io.github.albertosa23.heraldia.uniques.island;

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
import net.minecraft.world.level.levelgen.structure.BoundingBox;
import net.minecraft.world.level.levelgen.structure.PoolElementStructurePiece;
import net.minecraft.world.level.levelgen.structure.Structure;
import net.minecraft.world.level.levelgen.structure.StructureType;
import net.minecraft.world.level.levelgen.structure.pools.StructurePoolElement;
import net.minecraft.world.level.levelgen.structure.pools.StructureTemplatePool;
import net.minecraft.world.level.levelgen.structure.templatesystem.LiquidSettings;
import net.minecraft.world.level.levelgen.structure.templatesystem.StructureTemplateManager;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Corsair's island: a single template that brings its own islet (rock, sand and palm trees) and is placed in the open sea.
 * The jigsaw does not see water, so here, around the candidate chunk (which GridPlacement already chose within
 * the temperate or warm oceans), a point is searched whose biome and sea floor work across the whole footprint: water with the floor
 * between {@code fondo_min} and {@code fondo_max} blocks below sea level in a circle of {@code radio} blocks, and
 * water around up to {@code radio + margen} (no coast nearby). The template's {@code fila_mar} row sits at
 * sea level (the first air layer above the water) and the island rotates at random. It only reads the biome noise and the
 * generation height maps (cached); if nothing passes it is not generated, and with /place it is placed in the chunk as is.
 */
public final class IslandStructure extends Structure {
	public static final MapCodec<IslandStructure> CODEC = RecordCodecBuilder.mapCodec(i -> i.group(
			settingsCodec(i),
			StructureTemplatePool.CODEC.fieldOf("start_pool").forGetter(s -> s.startPool),
			Codec.intRange(0, 128).fieldOf("fila_mar").forGetter(s -> s.seaRow),
			Codec.intRange(8, 96).fieldOf("radio").forGetter(s -> s.radius),
			Codec.intRange(0, 64).fieldOf("margen").forGetter(s -> s.margin),
			Codec.intRange(-64, 0).fieldOf("fondo_min").forGetter(s -> s.depthMin),
			Codec.intRange(-64, 0).fieldOf("fondo_max").forGetter(s -> s.depthMax)
	).apply(i, IslandStructure::new));

	/** Candidates around the chunk's center (blocks), inside out, and samples per ring. */
	private static final int SEARCH = 16, STEP = 16, LOGGED = 8;
	private static final List<int[]> CANDIDATES = new ArrayList<>();
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	private static final AtomicInteger logged = new AtomicInteger();

	static {
		for (int dx = -SEARCH; dx <= SEARCH; dx += STEP) {
			for (int dz = -SEARCH; dz <= SEARCH; dz += STEP) {
				CANDIDATES.add(new int[]{dx, dz});
			}
		}
		CANDIDATES.sort(Comparator.<int[]>comparingInt(c -> c[0] * c[0] + c[1] * c[1]).thenComparingInt(c -> c[0]).thenComparingInt(c -> c[1]));
	}

	private final Holder<StructureTemplatePool> startPool;
	private final int seaRow, radius, margin, depthMin, depthMax;
	private final int[][] footprint, edge; // samples (dx, dz) inside the footprint and in the outer ring

	public IslandStructure(StructureSettings settings, Holder<StructureTemplatePool> startPool, int seaRow, int radius, int margin,
			int depthMin, int depthMax) {
		super(settings);
		this.startPool = startPool;
		this.seaRow = seaRow;
		this.radius = radius;
		this.margin = margin;
		this.depthMin = depthMin;
		this.depthMax = depthMax;
		this.footprint = ring(new int[]{0, radius / 2, radius}, new int[]{1, 8, 16});
		this.edge = ring(new int[]{radius + margin}, new int[]{16});
	}

	/** Points in rings of radius r[k] with n[k] samples each (precomputed: nothing is computed per chunk). */
	static int[][] ring(int[] r, int[] n) {
		List<int[]> out = new ArrayList<>();
		for (int k = 0; k < r.length; k++) {
			for (int j = 0; j < n[k]; j++) {
				double a = 2 * Math.PI * j / n[k];
				out.add(new int[]{(int) Math.round(r[k] * Math.cos(a)), (int) Math.round(r[k] * Math.sin(a))});
			}
		}
		return out.toArray(new int[0][]);
	}

	@Override
	public StructureType<?> type() {
		return Island.TYPE;
	}

	@Override
	protected Optional<GenerationStub> findGenerationPoint(GenerationContext ctx) {
		long t0 = System.nanoTime();
		int sea = ctx.chunkGenerator().getSeaLevel();
		int cx = ctx.chunkPos().getMiddleBlockX(), cz = ctx.chunkPos().getMiddleBlockZ();
		boolean forced = Generation.forced(ctx, biomes());
		Rotation rotation = Rotation.getRandom(ctx.random());
		Heights heights = new Heights(ctx);
		for (int[] c : CANDIDATES) {
			int px = cx + c[0], pz = cz + c[1];
			if (biomes(ctx, px, pz, sea) && floors(heights, px, pz)) {
				return Optional.of(stub(ctx, px, pz, sea, rotation, false, t0));
			}
		}
		// /place structure accepts any biome: with no open sea in sight it is placed anyway, for testing.
		return forced ? Optional.of(stub(ctx, cx, cz, sea, rotation, true, t0)) : Optional.empty();
	}

	/** The whole footprint and the outer ring in the structure's biomes (cheap: only the biome noise). */
	private boolean biomes(GenerationContext ctx, int px, int pz, int sea) {
		for (int[][] set : new int[][][]{footprint, edge}) {
			for (int[] p : set) {
				if (!Generation.biome(ctx, biomes(), px + p[0], sea - 1, pz + p[1])) {
					return false;
				}
			}
		}
		return true;
	}

	/** Floor between fondo_min and fondo_max in the footprint and water (floor below the sea) in the outer ring. */
	private boolean floors(Heights h, int px, int pz) {
		for (int[] p : footprint) {
			int f = h.floor(px + p[0], pz + p[1]) - h.sea;
			if (f < depthMin || f > depthMax) {
				return false;
			}
		}
		for (int[] p : edge) {
			if (h.floor(px + p[0], pz + p[1]) - h.sea > depthMax) {
				return false;
			}
		}
		return true;
	}

	private GenerationStub stub(GenerationContext ctx, int px, int pz, int sea, Rotation rotation, boolean forced, long t0) {
		StructureTemplateManager manager = ctx.structureTemplateManager();
		StructurePoolElement element = startPool.value().getRandomTemplate(ctx.random());
		BlockPos origin = new BlockPos(px, sea - seaRow, pz);
		BoundingBox box = element.getBoundingBox(manager, origin, rotation);
		PoolElementStructurePiece piece = new PoolElementStructurePiece(manager, element, origin, element.getGroundLevelDelta(),
				rotation, box, LiquidSettings.IGNORE_WATERLOGGING);
		piece.move(px - box.getCenter().getX(), 0, pz - box.getCenter().getZ());
		if (logged.getAndIncrement() < LOGGED) {
			LOGGER.info("Heraldia: isla del corsario en {} {} (chunk {}, {}), giro {}{}, sitio buscado en {} µs", px, pz,
					ctx.chunkPos().x(), ctx.chunkPos().z(), rotation, forced ? ", sin comprobar el mar (/place)" : "",
					(System.nanoTime() - t0) / 1000);
		}
		return new GenerationStub(new BlockPos(px, sea - 1, pz), builder -> builder.addPiece(piece));
	}
}
