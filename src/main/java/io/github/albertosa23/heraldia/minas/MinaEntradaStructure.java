package io.github.albertosa23.heraldia.minas;

import com.mojang.serialization.Codec;
import com.mojang.serialization.MapCodec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import io.github.albertosa23.heraldia.comun.Alturas;
import io.github.albertosa23.heraldia.comun.Generacion;
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
 * Entrada a mina de Heraldia (heraldia:mina_entrada, tools/gen/minas): una sola plantilla con el patio, la boca, la
 * bajada y la galería, colocada en una ladera que busca {@link Ladera} con el mapa de alturas de generación (con caché,
 * {@link Alturas}, y columnas en una malla de 4 bloques que comparten las muestras). Antes de buscar mira el bioma en el
 * centro del chunk (una columna): un structure_set con un estilo por bioma prueba sus entradas una a una, y las que no
 * son de ese bioma salen sin pagar la búsqueda. La boca (z = 0 de la plantilla) mira cuesta abajo; si nada sirve no se
 * genera, salvo con /place (que acepta cualquier bioma), que la coloca igualmente.
 */
public final class MinaEntradaStructure extends Structure {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	private static final AtomicInteger REGISTRADAS = new AtomicInteger(); // las primeras, en el registro (pruebas)
	private static final int LOGGED = 6;

	public static final MapCodec<MinaEntradaStructure> CODEC = RecordCodecBuilder.mapCodec(i -> i.group(
			settingsCodec(i),
			StructureTemplatePool.CODEC.fieldOf("start_pool").forGetter(s -> s.pool),
			BlockPos.CODEC.fieldOf("entrada").forGetter(s -> s.forma.entrada()),
			Codec.INT.listOf(4, 4).fieldOf("patio").forGetter(s -> List.of(s.forma.patioX0(), s.forma.patioZ0(), s.forma.patioX1(),
					s.forma.patioZ1())),
			Codec.INT.listOf(3, 3).listOf().fieldOf("techo").forGetter(s -> s.forma.techo().stream().map(a -> List.of(a[0], a[1], a[2])).toList())
	).apply(i, MinaEntradaStructure::new));
	public static final StructureType<MinaEntradaStructure> TYPE = () -> CODEC;

	private final Holder<StructureTemplatePool> pool;
	private final Ladera.Forma forma;

	public MinaEntradaStructure(StructureSettings settings, Holder<StructureTemplatePool> pool, BlockPos entrada, List<Integer> patio,
			List<List<Integer>> techo) {
		super(settings);
		this.pool = pool;
		this.forma = new Ladera.Forma(entrada, patio.get(0), patio.get(1), patio.get(2), patio.get(3),
				techo.stream().map(l -> new int[] {l.get(0), l.get(1), l.get(2)}).toList());
	}

	@Override
	protected Optional<GenerationStub> findGenerationPoint(GenerationContext ctx) {
		boolean forzada = Generacion.forzada(ctx, biomes());
		Alturas alturas = new Alturas(ctx);
		int mx = ctx.chunkPos().getMiddleBlockX(), mz = ctx.chunkPos().getMiddleBlockZ();
		Ladera.Terreno terreno = new Ladera.Terreno() {
			@Override
			public int suelo(int x, int z) {
				return alturas.floor(malla(x), malla(z));
			}

			@Override
			public boolean agua(int x, int z) {
				return alturas.water(malla(x), malla(z));
			}
		};
		if (!forzada && !Generacion.bioma(ctx, biomes(), mx, terreno.suelo(mx, mz), mz)) {
			return Optional.empty();                    // otro estilo del set: sin buscar nada
		}
		long t0 = System.nanoTime();
		Ladera.Sitio sitio = Ladera.buscar(terreno, mx, mz, forma, ctx.heightAccessor().getMinY(), forzada);
		if (sitio == null) {
			return Optional.empty();
		}
		var manager = ctx.structureTemplateManager();
		StructurePoolElement element = pool.value().getRandomTemplate(ctx.random());
		BlockPos e = forma.entrada().rotate(sitio.giro());
		BlockPos origen = new BlockPos(sitio.x() - e.getX(), sitio.pies() - 1 - e.getY(), sitio.z() - e.getZ());
		if (forzada || REGISTRADAS.getAndIncrement() < LOGGED) {
			LOGGER.info("Heraldia: entrada a mina en {} {} {} (giro {}, nota {}): ladera en {} µs", sitio.x(), sitio.pies(), sitio.z(),
					sitio.giro(), Math.round(sitio.nota()), (System.nanoTime() - t0) / 1000);
		}
		return Optional.of(new GenerationStub(new BlockPos(sitio.x(), sitio.pies(), sitio.z()), builder -> builder.addPiece(
				new PoolElementStructurePiece(manager, element, origen, element.getGroundLevelDelta(), sitio.giro(),
						element.getBoundingBox(manager, origen, sitio.giro()), LiquidSettings.IGNORE_WATERLOGGING))));
	}

	/** Columnas en una malla de 4 bloques (centro de cada celda): las muestras vecinas comparten caché. */
	private static int malla(int v) {
		return (v >> 2 << 2) + 2;
	}

	public Ladera.Forma forma() {
		return forma;
	}

	@Override
	public StructureType<?> type() {
		return TYPE;
	}
}
