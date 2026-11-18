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
 * Isla del corsario: una sola plantilla que trae su propio islote (roca, arena y palmeras) y se coloca en mar abierto.
 * El jigsaw no ve el agua, así que aquí se busca, alrededor del chunk candidato (que GridPlacement ya eligió dentro de
 * los océanos templados o cálidos), un punto cuyo bioma y cuyo fondo marino valgan en toda la huella: agua con el fondo
 * entre {@code fondo_min} y {@code fondo_max} bloques bajo el nivel del mar en un círculo de {@code radius} bloques, y
 * agua alrededor hasta {@code radius + margin} (nada de costa cerca). La fila {@code fila_mar} de la plantilla queda en
 * el nivel del mar (la primera capa de aire sobre el agua) y la isla gira al azar. Solo lee el ruido de biomas y los
 * mapas de alturas de generación (con caché); si nada cumple no se genera, y con /place se coloca en el chunk tal cual.
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

	/** Candidatos alrededor del centro del chunk (bloques), de dentro afuera, y muestras por anillo. */
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
	private final int[][] footprint, edge; // muestras (dx, dz) dentro de la huella y en el anillo exterior

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

	/** Puntos en anillos de radio r[k] con n[k] muestras cada uno (precalculado: nada se calcula por chunk). */
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
		// /place structure acepta cualquier bioma: sin mar abierto a la vista se coloca igualmente, para probar.
		return forced ? Optional.of(stub(ctx, cx, cz, sea, rotation, true, t0)) : Optional.empty();
	}

	/** Toda la huella y el anillo exterior en los biomas de la estructura (barato: solo el ruido de biomas). */
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

	/** Fondo entre fondo_min y fondo_max en la huella y agua (fondo bajo el mar) en el anillo exterior. */
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
