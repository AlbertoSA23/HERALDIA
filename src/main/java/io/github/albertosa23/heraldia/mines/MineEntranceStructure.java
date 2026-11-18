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
 * Entrada a mina de Heraldia (heraldia:mina_entrada, tools/gen/minas): una sola plantilla con el patio, la boca, la
 * bajada y la galería, colocada en una ladera que busca {@link Hillside} con el mapa de alturas de generación (con caché,
 * {@link Heights}, y columnas en una malla de 4 bloques que comparten las muestras). Antes de buscar mira el bioma en el
 * centro del chunk (una columna): un structure_set con un estilo por bioma prueba sus entradas una a una, y las que no
 * son de ese bioma salen sin pagar la búsqueda. La boca (z = 0 de la plantilla) mira cuesta abajo; si nada sirve no se
 * genera, salvo con /place (que acepta cualquier bioma), que la coloca igualmente.
 */
public final class MineEntranceStructure extends Structure implements ParallelLocate.Precomputable {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	private static final AtomicInteger REGISTERED = new AtomicInteger(); // las primeras, en el registro (pruebas)
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
			return Optional.empty();                    // otro estilo del set: sin buscar nada
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
	 * Precalcula lo que miraría {@link #findGenerationPoint} en ese chunk (el bioma del centro y, si es el suyo, la
	 * búsqueda de ladera): solo llena la caché compartida de alturas, sin crear nada ni escribir en el log. Lo usa
	 * {@link ParallelLocate} desde otros hilos para que /locate encuentre las columnas ya calculadas.
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
	 * El terreno de la búsqueda sobre la caché compartida del mundo ({@link HeightCache}): los estilos y variantes del
	 * structure_set, /locate y la regla de colocación miran las mismas columnas y ya no las vuelven a calcular. Mismos
	 * valores que con una caché por búsqueda ({@link Heights}, lo de antes): lo comprueba MinasDeterminismoTest.
	 */
	public static Hillside.Terrain terrain(HeightCache c) {
		return terrain(c::floor, c::water);
	}

	/** Lo de antes (una caché por búsqueda): solo para comparar en las pruebas. */
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

	/** Columnas en una malla de 4 bloques (centro de cada celda): las muestras vecinas comparten caché. */
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
