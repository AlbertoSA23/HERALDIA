package io.github.albertosa23.heraldia.unicas.atlantida;

import com.mojang.serialization.Codec;
import com.mojang.serialization.MapCodec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import java.util.List;
import java.util.Optional;
import net.minecraft.core.BlockPos;
import net.minecraft.resources.Identifier;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.block.Rotation;
import net.minecraft.world.level.levelgen.structure.BoundingBox;
import net.minecraft.world.level.levelgen.structure.PoolElementStructurePiece;
import net.minecraft.world.level.levelgen.structure.Structure;
import net.minecraft.world.level.levelgen.structure.StructureType;
import net.minecraft.world.level.levelgen.structure.pools.StructurePoolElement;
import net.minecraft.world.level.levelgen.structure.pools.StructureTemplatePool;
import net.minecraft.world.level.levelgen.structure.templatesystem.LiquidSettings;

/**
 * heraldia:atlantida: una ciudad de plano fijo repartida en distritos. Cada distrito es un inicio de estructura propio
 * (un chunk solo ve inicios a ±8 chunks) y coloca, sin azar, las piezas del plano cuya esquina mínima cae en él,
 * después de la pieza base que despeja el agua, pavimenta y levanta la muralla. Coordenadas del plano: x, z relativas
 * al centro de la ciudad (esquina mínima del chunk ancla); y absoluta.
 */
public final class AtlantisStructure extends Structure {
	public record Piece(Identifier template, int x, int y, int z) {
		static final Codec<Piece> CODEC = RecordCodecBuilder.create(i -> i.group(
				Identifier.CODEC.fieldOf("plantilla").forGetter(Piece::template),
				Codec.INT.fieldOf("x").forGetter(Piece::x), Codec.INT.fieldOf("y").forGetter(Piece::y),
				Codec.INT.fieldOf("z").forGetter(Piece::z)).apply(i, Piece::new));
	}

	public static final MapCodec<AtlantisStructure> CODEC = RecordCodecBuilder.mapCodec(i -> i.group(
			settingsCodec(i),
			Codec.intRange(16, 384).fieldOf("radio").forGetter(s -> s.radius),
			Codec.INT.fieldOf("suelo").forGetter(s -> s.floor),
			Codec.INT.fieldOf("base").forGetter(s -> s.base),
			Codec.INT.fieldOf("techo").forGetter(s -> s.top),
			Piece.CODEC.listOf().fieldOf("piezas").forGetter(s -> s.pieces)
	).apply(i, AtlantisStructure::new));

	private final int radius, floor, base, top;
	private final List<Piece> pieces;

	private AtlantisStructure(StructureSettings settings, int radius, int floor, int base, int top, List<Piece> pieces) {
		super(settings);
		this.radius = radius;
		this.floor = floor;
		this.base = base;
		this.top = top;
		this.pieces = pieces;
	}

	/** Sin comprobación de bioma: el ancla ya se eligió en océano y, si no lo hubiera, la ciudad se genera igualmente entera. */
	@Override
	public Optional<GenerationStub> findValidGenerationPoint(GenerationContext context) {
		return findGenerationPoint(context);
	}

	@Override
	protected Optional<GenerationStub> findGenerationPoint(GenerationContext context) {
		ChunkPos chunk = context.chunkPos();
		ChunkPos anchor = AtlantisAnchor.get(context.seed());
		if (anchor == null || !AtlantisAnchor.isDistrictStart(context.seed(), chunk.x(), chunk.z())) {
			return Optional.empty();
		}
		int cx = anchor.getMinBlockX(), cz = anchor.getMinBlockZ(), half = AtlantisAnchor.DISTRICT_CHUNKS * 8;
		// caja del distrito en coordenadas del plano
		int x0 = chunk.getMinBlockX() - cx - half, z0 = chunk.getMinBlockZ() - cz - half, x1 = x0 + 2 * half - 1, z1 = z0 + 2 * half - 1;
		return Optional.of(new GenerationStub(new BlockPos(chunk.getMinBlockX(), floor, chunk.getMinBlockZ()), builder -> {
			builder.addPiece(new BasePiece(new BoundingBox(cx + x0, base - 40, cz + z0, cx + x1, top, cz + z1), cx, cz, radius, floor, base));
			for (Piece p : pieces) {
				if (p.x >= x0 && p.x <= x1 && p.z >= z0 && p.z <= z1) {
					StructurePoolElement element = StructurePoolElement.single(p.template.toString(), LiquidSettings.IGNORE_WATERLOGGING)
							.apply(StructureTemplatePool.Projection.RIGID);
					BlockPos pos = new BlockPos(cx + p.x, p.y, cz + p.z);
					builder.addPiece(new PoolElementStructurePiece(context.structureTemplateManager(), element, pos, 0, Rotation.NONE,
							element.getBoundingBox(context.structureTemplateManager(), pos, Rotation.NONE), LiquidSettings.IGNORE_WATERLOGGING));
				}
			}
		}));
	}

	@Override
	public StructureType<?> type() {
		return Atlantida.STRUCTURE;
	}
}
