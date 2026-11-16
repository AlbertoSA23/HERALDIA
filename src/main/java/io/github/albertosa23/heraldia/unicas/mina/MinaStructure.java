package io.github.albertosa23.heraldia.unicas.mina;

import com.mojang.serialization.Codec;
import com.mojang.serialization.MapCodec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import io.github.albertosa23.heraldia.comun.Alturas;
import io.github.albertosa23.heraldia.comun.Generacion;
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
public final class MinaStructure extends Structure {
	public static final MapCodec<MinaStructure> CODEC = RecordCodecBuilder.mapCodec(i -> i.group(
			settingsCodec(i),
			StructureTemplatePool.CODEC.fieldOf("start_pool").forGetter(s -> s.colonia),
			StructureTemplatePool.CODEC.fieldOf("pozo").forGetter(s -> s.pozo),
			StructureTemplatePool.CODEC.fieldOf("pozo_corto").forGetter(s -> s.pozoCorto),
			StructureTemplatePool.CODEC.fieldOf("castillete").forGetter(s -> s.castillete),
			Codec.INT.fieldOf("colonia_y").forGetter(s -> s.coloniaY),
			BlockPos.CODEC.fieldOf("eje_colonia").forGetter(s -> s.ejeColonia),
			BlockPos.CODEC.fieldOf("centro").forGetter(s -> s.centro),
			BlockPos.CODEC.listOf().fieldOf("muestras").forGetter(s -> s.muestras),
			BlockPos.CODEC.fieldOf("eje_pozo").forGetter(s -> s.ejePozo),
			Codec.intRange(1, 64).fieldOf("alto_pozo").forGetter(s -> s.altoPozo),
			BlockPos.CODEC.fieldOf("eje_castillete").forGetter(s -> s.ejeCastillete),
			Codec.INT.listOf(4, 4).fieldOf("huella").forGetter(s -> s.huella),
			Codec.intRange(0, 512).fieldOf("pozo_max").forGetter(s -> s.pozoMax)
	).apply(i, MinaStructure::new));
	public static final StructureType<MinaStructure> TYPE = () -> CODEC;

	private static final int STEP = 16, REACH = 32, TRIES = 3, MAX_SPREAD = 5, LOGGED = 8;
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	private static final AtomicInteger logged = new AtomicInteger(); // las primeras, en el registro (pruebas)

	private final Holder<StructureTemplatePool> colonia, pozo, pozoCorto, castillete;
	private final int coloniaY, altoPozo, pozoMax;
	private final BlockPos ejeColonia, centro, ejePozo, ejeCastillete;
	private final List<BlockPos> muestras;
	private final List<Integer> huella;

	public MinaStructure(StructureSettings settings, Holder<StructureTemplatePool> colonia, Holder<StructureTemplatePool> pozo,
			Holder<StructureTemplatePool> pozoCorto, Holder<StructureTemplatePool> castillete, int coloniaY, BlockPos ejeColonia,
			BlockPos centro, List<BlockPos> muestras, BlockPos ejePozo, int altoPozo, BlockPos ejeCastillete, List<Integer> huella,
			int pozoMax) {
		super(settings);
		this.colonia = colonia;
		this.pozo = pozo;
		this.pozoCorto = pozoCorto;
		this.castillete = castillete;
		this.coloniaY = coloniaY;
		this.ejeColonia = ejeColonia;
		this.centro = centro;
		this.muestras = muestras;
		this.ejePozo = ejePozo;
		this.altoPozo = altoPozo;
		this.ejeCastillete = ejeCastillete;
		this.huella = huella;
		this.pozoMax = pozoMax;
	}

	private record Sitio(int x, int z, int score, int dist) {
	}

	@Override
	protected Optional<GenerationStub> findGenerationPoint(GenerationContext ctx) {
		boolean forced = Generacion.forzada(ctx, biomes());
		Rotation rot = Rotation.getRandom(ctx.random());
		int mx = ctx.chunkPos().getMiddleBlockX(), mz = ctx.chunkPos().getMiddleBlockZ();
		int cy = coloniaY + centro.getY();
		List<Sitio> sitios = new ArrayList<>();
		for (int dx = -REACH; dx <= REACH; dx += STEP) {
			for (int dz = -REACH; dz <= REACH; dz += STEP) {
				if (forced && (dx != 0 || dz != 0)) {
					continue;
				}
				int x = mx + dx, z = mz + dz;
				int score = 0;
				if (!forced) {
					if (!Generacion.bioma(ctx, biomes(), x, cy, z)) {
						continue;                       // el centro de la caverna tiene que caer en el bioma
					}
					for (BlockPos m : muestras) {
						BlockPos r = local(m.getX() - centro.getX(), m.getZ() - centro.getZ(), rot);
						if (Generacion.bioma(ctx, biomes(), x + r.getX(), coloniaY + m.getY(), z + r.getZ())) {
							score++;
						}
					}
				}
				sitios.add(new Sitio(x, z, score, dx * dx + dz * dz));
			}
		}
		sitios.sort(Comparator.comparingInt(Sitio::score).reversed().thenComparingInt(Sitio::dist));
		Alturas alturas = new Alturas(ctx);
		for (int k = 0; k < Math.min(TRIES, sitios.size()); k++) {
			Optional<GenerationStub> stub = intentar(ctx, alturas, rot, sitios.get(k), cy, forced);
			if (stub.isPresent()) {
				return stub;
			}
		}
		return Optional.empty();
	}

	private Optional<GenerationStub> intentar(GenerationContext ctx, Alturas alturas, Rotation rot, Sitio s, int cy, boolean forced) {
		BlockPos c = local(centro.getX(), centro.getZ(), rot);
		int ox = s.x() - c.getX(), oz = s.z() - c.getZ();                  // origen de la colonia
		BlockPos e = local(ejeColonia.getX(), ejeColonia.getZ(), rot);
		int ax = ox + e.getX(), az = oz + e.getZ();                        // eje del pozo
		int suelo = alturas.floor(ax, az), lo = suelo, hi = suelo;
		boolean agua = alturas.water(ax, az);
		for (int i = 0; i < 4; i++) {
			BlockPos q = local(huella.get((i & 1) == 0 ? 0 : 2), huella.get((i & 2) == 0 ? 1 : 3), rot);
			int h = alturas.floor(ax + q.getX(), az + q.getZ());
			lo = Math.min(lo, h);
			hi = Math.max(hi, h);
			agua |= alturas.water(ax + q.getX(), az + q.getZ());
		}
		int base = coloniaY + ejeColonia.getY();                         // primera capa del pozo
		int yc = suelo - 1 - ejeCastillete.getY();                       // origen del castillete (cimiento)
		if (!forced && (agua || hi - lo > MAX_SPREAD || yc < base || yc - base > pozoMax)) {
			return Optional.empty();
		}
		yc = Math.max(yc, base);
		List<PoolElementStructurePiece> piezas = new ArrayList<>();
		piezas.add(pieza(ctx, colonia, new BlockPos(ox, coloniaY, oz), rot));
		int y = base;
		for (; y + altoPozo <= yc; y += altoPozo) {
			piezas.add(pieza(ctx, pozo, eje(ax, y, az, ejePozo, rot), rot));
		}
		for (; y < yc; y++) {
			piezas.add(pieza(ctx, pozoCorto, eje(ax, y, az, ejePozo, rot), rot));
		}
		piezas.add(pieza(ctx, castillete, eje(ax, yc, az, ejeCastillete, rot), rot));
		if (logged.getAndIncrement() < LOGGED) {
			LOGGER.info("Heraldia: mina perdida en el chunk {}, {}: eje del pozo en {}, {}, pozo de {} bloques de y = {} a {}, "
					+ "suelo del castillete a y = {}, giro {}", ctx.chunkPos().x(), ctx.chunkPos().z(), ax, az, yc - base, base, yc,
					yc + ejeCastillete.getY(), rot);
		}
		return Optional.of(new GenerationStub(new BlockPos(s.x(), cy, s.z()), (StructurePiecesBuilder b) -> piezas.forEach(b::addPiece)));
	}

	/** Origen de una pieza cuyo eje local (x, z) cae en (ax, az) del mundo, con su capa 0 a la altura y. */
	private static BlockPos eje(int ax, int y, int az, BlockPos local, Rotation rot) {
		BlockPos r = local(local.getX(), local.getZ(), rot);
		return new BlockPos(ax - r.getX(), y, az - r.getZ());
	}

	private static BlockPos local(int x, int z, Rotation rot) {
		return new BlockPos(x, 0, z).rotate(rot);
	}

	private static PoolElementStructurePiece pieza(GenerationContext ctx, Holder<StructureTemplatePool> pool, BlockPos origin, Rotation rot) {
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
