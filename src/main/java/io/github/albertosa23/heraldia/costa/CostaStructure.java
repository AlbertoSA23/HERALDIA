package io.github.albertosa23.heraldia.costa;

import com.mojang.serialization.Codec;
import com.mojang.serialization.MapCodec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import io.github.albertosa23.heraldia.comun.CacheAlturas;
import io.github.albertosa23.heraldia.comun.Generacion;
import io.github.albertosa23.heraldia.comun.Perfil;
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
 * Faro o naufragio de la costa (heraldia:costa, tools/gen/litoral): una sola plantilla que se pone en la orilla que busca
 * {@link Orilla} con la caché compartida de alturas de generación ({@link CacheAlturas}), girada para que su +z mire al
 * mar y con su ancla en el último bloque de tierra. El faro queda a la altura del terreno (la plataforma; sus cimientos y
 * pilotes bajan hasta el suelo con el procesador de la plantilla); el naufragio, con la fila {@code fila_mar} en el nivel
 * del mar - 1. El estilo es el del clima de esa costa: alguna de las parejas {@code climas} (bioma de la tierra en el
 * ancla y del mar 12 bloques mar adentro); el resto de estilos del structure_set no sale ahí. Con /place (que acepta
 * cualquier bioma) se coloca en la orilla que encuentre o, sin ella, en el centro mirando al sur.
 */
public final class CostaStructure extends Structure implements io.github.albertosa23.heraldia.minas.LocateParalelo.Precalculable {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	private static final AtomicInteger REGISTRADAS = new AtomicInteger(); // las primeras, en el registro (pruebas)
	private static final int LOGGED = 6, MAR_ADENTRO = 12;
	/** Con -Dheraldia.depurar.costa=true, cada sitio al log (tools/smoke/costa.py lo lee para saber dónde quedó cada una). */
	private static final boolean DEPURAR = Boolean.getBoolean("heraldia.depurar.costa");

	/** Pareja de clima: bioma de la tierra en la orilla y del mar de delante. */
	public record Clima(TagKey<Biome> tierra, TagKey<Biome> mar) {
		static final Codec<Clima> CODEC = RecordCodecBuilder.create(i -> i.group(
				TagKey.hashedCodec(Registries.BIOME).fieldOf("tierra").forGetter(Clima::tierra),
				TagKey.hashedCodec(Registries.BIOME).fieldOf("mar").forGetter(Clima::mar)
		).apply(i, Clima::new));
	}

	public static final MapCodec<CostaStructure> CODEC = RecordCodecBuilder.mapCodec(i -> i.group(
			settingsCodec(i),
			StructureTemplatePool.CODEC.fieldOf("start_pool").forGetter(s -> s.pool),
			Codec.STRING.fieldOf("modo").forGetter(s -> s.forma.modo().name().toLowerCase(java.util.Locale.ROOT)),
			Codec.INT.listOf(2, 2).fieldOf("ancla").forGetter(s -> List.of(s.anclaX, s.anclaZ)),
			Codec.INT.listOf(4, 4).fieldOf("tierra").forGetter(s -> lista(s.forma.tierra())),
			Codec.INT.listOf(4, 4).fieldOf("mar").forGetter(s -> lista(s.forma.mar())),
			Codec.intRange(-1, 64).fieldOf("fila_mar").forGetter(s -> s.filaMar),
			Clima.CODEC.listOf().fieldOf("climas").forGetter(s -> s.climas)
	).apply(i, CostaStructure::new));
	public static final StructureType<CostaStructure> TYPE = () -> CODEC;

	private final Holder<StructureTemplatePool> pool;
	private final Orilla.Forma forma;
	private final int anclaX, anclaZ, filaMar;
	private final List<Clima> climas;

	public CostaStructure(StructureSettings settings, Holder<StructureTemplatePool> pool, String modo, List<Integer> ancla,
			List<Integer> tierra, List<Integer> mar, int filaMar, List<Clima> climas) {
		super(settings);
		this.pool = pool;
		this.forma = new Orilla.Forma(Orilla.Modo.de(modo), array(tierra), array(mar));
		this.anclaX = ancla.get(0);
		this.anclaZ = ancla.get(1);
		this.filaMar = filaMar;
		this.climas = List.copyOf(climas);
	}

	private static int[] array(List<Integer> l) {
		return l.stream().mapToInt(Integer::intValue).toArray();
	}

	private static List<Integer> lista(int[] a) {
		return java.util.Arrays.stream(a).boxed().toList();
	}

	public Orilla.Forma forma() {
		return forma;
	}

	@Override
	protected Optional<GenerationStub> findGenerationPoint(GenerationContext ctx) {
		boolean forzada = Generacion.forzada(ctx, biomes());
		CacheAlturas c = CacheAlturas.de(ctx);
		int sea = ctx.chunkGenerator().getSeaLevel();
		int mx = ctx.chunkPos().getMiddleBlockX(), mz = ctx.chunkPos().getMiddleBlockZ();
		long t0 = System.nanoTime();
		Orilla.Sitio sitio = Orilla.buscar(terreno(c), sea, mx, mz, forma);
		Perfil.fin(Perfil.Tramo.COSTA_ORILLA, t0);
		if (sitio != null && !forzada && !clima(ctx, sitio, c, sea)) {
			return Optional.empty();                     // otro estilo del set: el de esta costa es otro
		}
		boolean sinOrilla = sitio == null;
		if (sitio == null) {
			if (!forzada) {
				return Optional.empty();
			}
			sitio = new Orilla.Sitio(mx, mz, Direction.SOUTH, Math.max(c.floor(mx, mz) - 1, sea), 0);
		}
		Rotation giro = giro(sitio.mar());
		int y = forma.modo() == Orilla.Modo.FARO ? sitio.y() : sea - 1 - filaMar;
		BlockPos a = new BlockPos(anclaX, 0, anclaZ).rotate(giro);
		BlockPos origen = new BlockPos(sitio.x() - a.getX(), y, sitio.z() - a.getZ());
		var manager = ctx.structureTemplateManager();
		StructurePoolElement element = pool.value().getRandomTemplate(ctx.random());
		BoundingBox box = element.getBoundingBox(manager, origen, giro);
		if (forzada || DEPURAR || REGISTRADAS.getAndIncrement() < LOGGED) {
			LOGGER.info("Heraldia: costa ({}) en {} {} {} hacia el {} (nota {}{}): orilla en {} µs", forma.modo().name().toLowerCase(java.util.Locale.ROOT),
					sitio.x(), y, sitio.z(), sitio.mar().getSerializedName(), sitio.nota(), sinOrilla ? ", sin orilla" : "",
					(System.nanoTime() - t0) / 1000);
		}
		PoolElementStructurePiece pieza = new PoolElementStructurePiece(manager, element, origen, element.getGroundLevelDelta(), giro, box,
				LiquidSettings.IGNORE_WATERLOGGING);
		return Optional.of(new GenerationStub(new BlockPos(sitio.x(), c.floor(sitio.x(), sitio.z()), sitio.z()), b -> b.addPiece(pieza)));
	}

	/**
	 * Lo que miraría {@link #findGenerationPoint} en ese chunk (la búsqueda de la orilla), solo para llenar la caché
	 * compartida de alturas: lo usa /locate desde otros hilos (minas/LocateParalelo). No crea nada ni escribe en el log.
	 */
	@Override
	public void precalcular(GenerationContext ctx) {
		long t0 = Perfil.inicio();
		Orilla.buscar(terreno(CacheAlturas.de(ctx)), ctx.chunkGenerator().getSeaLevel(), ctx.chunkPos().getMiddleBlockX(),
				ctx.chunkPos().getMiddleBlockZ(), forma);
		Perfil.fin(Perfil.Tramo.LADERA_ANTICIPADA, t0);
	}

	/** El giro que lleva el +z de la plantilla hacia d. */
	public static Rotation giro(Direction d) {
		for (Rotation r : Rotation.values()) {
			BlockPos v = new BlockPos(0, 0, 1).rotate(r);
			if (v.getX() == d.getStepX() && v.getZ() == d.getStepZ()) {
				return r;
			}
		}
		return Rotation.NONE;
	}

	/** ¿Es el clima de esta orilla uno de los del estilo? Dos lecturas del ruido de biomas (baratas: no evalúan terreno). */
	private boolean clima(GenerationContext ctx, Orilla.Sitio s, CacheAlturas c, int sea) {
		Holder<Biome> tierra = bioma(ctx, s.x(), c.floor(s.x(), s.z()), s.z());
		Holder<Biome> mar = bioma(ctx, s.x() + s.mar().getStepX() * MAR_ADENTRO, sea - 1, s.z() + s.mar().getStepZ() * MAR_ADENTRO);
		for (Clima k : climas) {
			if (tierra.is(k.tierra()) && mar.is(k.mar())) {
				return true;
			}
		}
		return false;
	}

	private static Holder<Biome> bioma(GenerationContext ctx, int x, int y, int z) {
		return ctx.biomeResolver().getNoiseBiome(QuartPos.fromBlock(x), QuartPos.fromBlock(y), QuartPos.fromBlock(z));
	}

	/** El terreno de la búsqueda sobre la caché compartida del mundo. */
	public static Orilla.Terreno terreno(CacheAlturas c) {
		return new Orilla.Terreno() {
			@Override
			public int suelo(int x, int z) {
				return c.floor(x, z);
			}

			@Override
			public boolean agua(int x, int z) {
				return c.water(x, z);
			}
		};
	}

	@Override
	public StructureType<?> type() {
		return TYPE;
	}
}
