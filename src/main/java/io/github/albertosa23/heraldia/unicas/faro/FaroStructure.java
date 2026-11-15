package io.github.albertosa23.heraldia.unicas.faro;

import com.mojang.serialization.Codec;
import com.mojang.serialization.MapCodec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import io.github.albertosa23.heraldia.comun.Alturas;
import io.github.albertosa23.heraldia.comun.Generacion;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Optional;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Holder;
import net.minecraft.core.Direction;
import net.minecraft.world.level.block.Rotation;
import net.minecraft.world.level.chunk.ChunkGenerator;
import net.minecraft.world.level.levelgen.structure.BoundingBox;
import net.minecraft.world.level.levelgen.structure.PoolElementStructurePiece;
import net.minecraft.world.level.levelgen.structure.Structure;
import net.minecraft.world.level.levelgen.structure.StructureType;
import net.minecraft.world.level.levelgen.structure.pools.StructurePoolElement;
import net.minecraft.world.level.levelgen.structure.pools.StructureTemplatePool;
import net.minecraft.world.level.levelgen.structure.templatesystem.LiquidSettings;
import net.minecraft.world.level.levelgen.structure.templatesystem.StructureTemplateManager;

/**
 * Estructura de una sola pieza situada en la línea de costa. El jigsaw no ve el agua y gira al azar, así que aquí se
 * busca un punto con tierra detrás y mar delante (mapas de alturas de generación) y se gira la plantilla para que su
 * lado +z (la boca de la cueva) mire al mar, con la fila {@code sea_row} de la plantilla en el nivel del mar - 1.
 */
public final class FaroStructure extends Structure {
	public static final MapCodec<FaroStructure> CODEC = RecordCodecBuilder.mapCodec(i -> i.group(
			settingsCodec(i),
			StructureTemplatePool.CODEC.fieldOf("start_pool").forGetter(s -> s.startPool),
			Codec.intRange(0, 64).fieldOf("sea_row").forGetter(s -> s.seaRow)
	).apply(i, FaroStructure::new));

	/** Rejilla de candidatos alrededor del centro de la casilla (bloques) y paso de muestreo. */
	private static final int SEARCH = 24, STEP = 8;
	private static final List<int[]> CANDIDATES = new ArrayList<>();

	static {
		for (int dx = -SEARCH; dx <= SEARCH; dx += STEP) {
			for (int dz = -SEARCH; dz <= SEARCH; dz += STEP) {
				CANDIDATES.add(new int[]{dx, dz});
			}
		}
		CANDIDATES.sort(Comparator.<int[]>comparingInt(c -> c[0] * c[0] + c[1] * c[1]).thenComparingInt(c -> c[0]).thenComparingInt(c -> c[1]));
	}

	private final Holder<StructureTemplatePool> startPool;
	private final int seaRow;

	public FaroStructure(StructureSettings settings, Holder<StructureTemplatePool> startPool, int seaRow) {
		super(settings);
		this.startPool = startPool;
		this.seaRow = seaRow;
	}

	@Override
	public StructureType<?> type() {
		return Faro.TYPE;
	}

	@Override
	protected Optional<GenerationStub> findGenerationPoint(GenerationContext ctx) {
		ChunkGenerator gen = ctx.chunkGenerator();
		int sea = gen.getSeaLevel();
		int cx = ctx.chunkPos().getMiddleBlockX(), cz = ctx.chunkPos().getMiddleBlockZ();
		boolean forced = Generacion.forzada(ctx, biomes());
		Alturas heights = new Alturas(ctx);
		for (int[] c : CANDIDATES) {
			int px = cx + c[0], pz = cz + c[1];
			if (!forced && !Generacion.bioma(ctx, biomes(), px, sea, pz)) {
				continue;
			}
			for (Direction d : Direction.Plane.HORIZONTAL) {
				if (coast(heights, px, pz, d)) {
					return Optional.of(stub(ctx, px, pz, sea, d));
				}
			}
		}
		// /place structure acepta cualquier bioma: sin costa a la vista se coloca igualmente, para probar.
		return forced ? Optional.of(stub(ctx, cx, cz, sea, Direction.SOUTH)) : Optional.empty();
	}

	/** Tierra detrás (ni baja ni alta), mar con fondo delante y nada más alto que la cima en la huella. */
	private static boolean coast(Alturas h, int px, int pz, Direction d) {
		Direction e = d.getClockWise();
		for (int k = 8; k <= 16; k += 8) {
			for (int s = -8; s <= 8; s += 8) {
				int x = px - d.getStepX() * k + e.getStepX() * s, z = pz - d.getStepZ() * k + e.getStepZ() * s;
				int floor = h.floor(x, z);
				if (h.water(x, z) || floor < h.sea + 4 || floor > h.sea + 16) {
					return false;
				}
			}
		}
		int wet = 0;
		for (int k = 28; k <= 36; k += 8) {
			for (int s = -8; s <= 8; s += 8) {
				int x = px + d.getStepX() * k + e.getStepX() * s, z = pz + d.getStepZ() * k + e.getStepZ() * s;
				if (h.water(x, z) && h.floor(x, z) <= h.sea - 3) {
					wet++;
				}
			}
		}
		if (wet < 5) {
			return false;
		}
		for (int k = -24; k <= 16; k += 8) {
			for (int s = -16; s <= 16; s += 8) {
				if (h.floor(px + d.getStepX() * k + e.getStepX() * s, pz + d.getStepZ() * k + e.getStepZ() * s) > h.sea + 15) {
					return false;
				}
			}
		}
		return true;
	}

	private GenerationStub stub(GenerationContext ctx, int px, int pz, int sea, Direction seaward) {
		Rotation rotation = Rotation.NONE;
		for (Rotation r : Rotation.values()) {
			BlockPos v = new BlockPos(0, 0, 1).rotate(r);
			if (v.getX() == seaward.getStepX() && v.getZ() == seaward.getStepZ()) {
				rotation = r;
			}
		}
		StructureTemplateManager manager = ctx.structureTemplateManager();
		StructurePoolElement element = startPool.value().getRandomTemplate(ctx.random());
		BlockPos origin = new BlockPos(px, sea - 1 - seaRow, pz);
		BoundingBox box = element.getBoundingBox(manager, origin, rotation);
		PoolElementStructurePiece piece = new PoolElementStructurePiece(manager, element, origin, element.getGroundLevelDelta(),
				rotation, box, LiquidSettings.IGNORE_WATERLOGGING);
		piece.move(px - box.getCenter().getX(), 0, pz - box.getCenter().getZ());
		return new GenerationStub(new BlockPos(px, sea, pz), builder -> builder.addPiece(piece));
	}
}
