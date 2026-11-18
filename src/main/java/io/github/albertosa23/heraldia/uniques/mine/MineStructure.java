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
 * Mina perdida: la colonia (una plantilla grande) a una altura fija bajo tierra, el pozo maestro apilado encima en tramos
 * de 8 y de 1 bloques y el castillete en la superficie. Busca en una malla de 5 x 5 puntos (cada 16 bloques alrededor
 * del chunk candidato) el sitio donde el centro de la caverna y más puntos de muestra caen en el bioma (cuevas
 * exuberantes o de espeleotemas, a la altura de la caverna: solo lee el ruido de biomas) y, para los mejores, mira el
 * terreno sobre el pozo con el mapa de alturas de generación: seco, casi llano bajo el castillete y con un pozo de 0 a
 * pozo_max bloques. Si nada cumple no se genera; con /place (que acepta cualquier bioma) se usa el chunk tal cual.
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
	private static final AtomicInteger logged = new AtomicInteger(); // las primeras, en el registro (pruebas)

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
						continue;                       // el centro de la caverna tiene que caer en el bioma
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
		int ox = s.x() - c.getX(), oz = s.z() - c.getZ();                  // origen de la colonia
		BlockPos e = local(colonyAxis.getX(), colonyAxis.getZ(), rot);
		int ax = ox + e.getX(), az = oz + e.getZ();                        // eje del pozo
		int ground = heights.floor(ax, az), lo = ground, hi = ground;
		boolean water = heights.water(ax, az);
		for (int i = 0; i < 4; i++) {
			BlockPos q = local(footprint.get((i & 1) == 0 ? 0 : 2), footprint.get((i & 2) == 0 ? 1 : 3), rot);
			int h = heights.floor(ax + q.getX(), az + q.getZ());
			lo = Math.min(lo, h);
			hi = Math.max(hi, h);
			water |= heights.water(ax + q.getX(), az + q.getZ());
		}
		int base = colonyY + colonyAxis.getY();                         // primera capa del pozo
		int yc = ground - 1 - headframeAxis.getY();                       // origen del castillete (cimiento)
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

	/** Origen de una pieza cuyo eje local (x, z) cae en (ax, az) del mundo, con su capa 0 a la altura y. */
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
