package io.github.albertosa23.heraldia.dimensiones;

import com.mojang.serialization.Codec;
import com.mojang.serialization.MapCodec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import io.github.albertosa23.heraldia.comun.Generacion;
import java.util.Optional;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Holder;
import net.minecraft.util.StringRepresentable;
import net.minecraft.world.level.NoiseColumn;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.level.levelgen.structure.Structure;
import net.minecraft.world.level.levelgen.structure.StructureType;
import net.minecraft.world.level.levelgen.structure.pools.DimensionPadding;
import net.minecraft.world.level.levelgen.structure.pools.JigsawPlacement;
import net.minecraft.world.level.levelgen.structure.pools.StructureTemplatePool;
import net.minecraft.world.level.levelgen.structure.pools.alias.PoolAliasLookup;
import net.minecraft.world.level.levelgen.structure.structures.JigsawStructure;
import net.minecraft.world.level.levelgen.structure.templatesystem.LiquidSettings;

/**
 * heraldia:dimension: una estructura de jigsaw (una pieza en las medianas, varias en las únicas) para el Nether o el End,
 * donde el {@code project_start_to_heightmap} del jigsaw vanilla no sirve (en el Nether da el techo de bedrock; en el
 * End, el vacío). La altura del inicio la decide {@link Suelo} con la columna de ruido del centro y de las cuatro
 * esquinas de la huella ({@code radio} bloques del centro): solo en los chunks candidatos de la rejilla, unas pocas
 * columnas por candidata. Sin sitio, no sale; con /place structure (que acepta cualquier bioma) se coloca en el centro a
 * y = 64 para poder probarla en cualquier sitio. La y del inicio es la primera libre sobre el suelo: con la pieza rígida
 * (getGroundLevelDelta = 1) la fila y = 0 de la plantilla queda a ras de suelo, como en el mundo principal.
 */
public final class DimensionStructure extends Structure {
	/** Dónde se apoya. */
	public enum Modo implements StringRepresentable {
		NETHER("nether"), END("end");
		public static final Codec<Modo> CODEC = StringRepresentable.fromEnum(Modo::values);
		private final String nombre;

		Modo(String nombre) {
			this.nombre = nombre;
		}

		@Override
		public String getSerializedName() {
			return nombre;
		}
	}

	public static final MapCodec<DimensionStructure> CODEC = RecordCodecBuilder.mapCodec(i -> i.group(
			settingsCodec(i),
			StructureTemplatePool.CODEC.fieldOf("start_pool").forGetter(s -> s.startPool),
			Codec.intRange(1, 20).fieldOf("size").forGetter(s -> s.size),
			Codec.intRange(1, 116).fieldOf("max_distance_from_center").forGetter(s -> s.maxDistance),
			Modo.CODEC.fieldOf("modo").forGetter(s -> s.modo),
			Codec.intRange(1, 64).fieldOf("radio").forGetter(s -> s.radio),
			Codec.intRange(2, 64).fieldOf("libre").forGetter(s -> s.libre)
	).apply(i, DimensionStructure::new));
	/** Altura del inicio con /place structure sin sitio a la vista (pruebas). */
	static final int Y_FORZADA = 64;

	private final Holder<StructureTemplatePool> startPool;
	private final int size, maxDistance, radio, libre;
	private final Modo modo;

	public DimensionStructure(StructureSettings settings, Holder<StructureTemplatePool> startPool, int size, int maxDistance,
							  Modo modo, int radio, int libre) {
		super(settings);
		this.startPool = startPool;
		this.size = size;
		this.maxDistance = maxDistance;
		this.modo = modo;
		this.radio = radio;
		this.libre = libre;
	}

	@Override
	public StructureType<?> type() {
		return Dimensiones.TYPE;
	}

	public Modo modo() {
		return modo;
	}

	@Override
	protected Optional<GenerationStub> findGenerationPoint(GenerationContext ctx) {
		int cx = ctx.chunkPos().getMiddleBlockX(), cz = ctx.chunkPos().getMiddleBlockZ();
		Sitio s = modo == Modo.NETHER
				? sitio((x, z) -> ctx.chunkGenerator().getBaseColumn(x, z, ctx.heightAccessor(), ctx.randomState()), null, cx, cz, radio, libre)
				: sitio(null, (x, z) -> ctx.chunkGenerator().getBaseHeight(x, z, Heightmap.Types.WORLD_SURFACE_WG, ctx.heightAccessor(),
				ctx.randomState()), cx, cz, radio, libre);
		if (s == null) {
			if (!Generacion.forzada(ctx, biomes())) {
				return Optional.empty();
			}
			s = new Sitio(cx, Y_FORZADA, cz);
		}
		return JigsawPlacement.addPieces(ctx, startPool, Optional.empty(), size, new BlockPos(s.x(), s.y(), s.z()), false, Optional.empty(),
				new JigsawStructure.MaxDistance(maxDistance), PoolAliasLookup.EMPTY, DimensionPadding.ZERO, LiquidSettings.IGNORE_WATERLOGGING);
	}

	/** Dónde va el inicio (la y es la primera libre sobre el suelo). */
	public record Sitio(int x, int y, int z) {
	}

	/** Puntos que se prueban alrededor del centro del chunk (bloques), en orden: el centro y una cruz a medio chunk. */
	static final int[][] PUNTOS = {{0, 0}, {8, 0}, {-8, 0}, {0, 8}, {0, -8}};
	/** Suelos de una misma columna del Nether que se prueban, de arriba abajo (cuevas superpuestas). */
	static final int SUELOS = 4;

	/**
	 * El primer sitio válido de {@link #PUNTOS} (Nether con {@code columnas}, End con {@code alturas}) o null. Solo en los
	 * chunks candidatos de la rejilla: como mucho 5 puntos x 5 columnas, y en el Nether cada columna se lee una vez.
	 */
	public static Sitio sitio(Columnas columnas, Alturas alturas, int cx, int cz, int radio, int libre) {
		java.util.Map<Long, NoiseColumn> leidas = new java.util.HashMap<>();
		Columnas memo = columnas == null ? null : (x, z) -> leidas.computeIfAbsent(BlockPos.asLong(x, 0, z), k -> columnas.en(x, z));
		for (int[] d : PUNTOS) {
			int x = cx + d[0], z = cz + d[1];
			int y = memo != null ? nether(memo, x, z, radio, libre) : end(alturas, x, z, radio);
			if (y != Suelo.NINGUNO) {
				return new Sitio(x, y, z);
			}
		}
		return null;
	}

	/** Columna de ruido de un punto (en el juego, ChunkGenerator.getBaseColumn: no carga ni genera chunks). */
	@FunctionalInterface
	public interface Columnas {
		NoiseColumn en(int x, int z);
	}

	/** Primera y libre de un punto según el heightmap WORLD_SURFACE_WG (en el juego, ChunkGenerator.getBaseHeight). */
	@FunctionalInterface
	public interface Alturas {
		int en(int x, int z);
	}

	/** Altura del inicio en el Nether (Suelo.nether en el centro, esquinas a ±DESNIVEL; hasta SUELOS suelos de arriba abajo) o Suelo.NINGUNO. Pública para las pruebas. */
	public static int nether(Columnas columnas, int x, int z, int radio, int libre) {
		NoiseColumn c = columnas.en(x, z);
		int desde = Suelo.NETHER_DESDE;
		for (int n = 0; n < SUELOS; n++) {
			int y = Suelo.nether(k -> solido(c.getBlock(k)), k -> aire(c.getBlock(k)), desde, Suelo.NETHER_HASTA, libre);
			if (y == Suelo.NINGUNO) {
				return y;
			}
			int[] esquinas = new int[4];
			int k = 0;
			for (int dx = -radio; dx <= radio; dx += 2 * radio) {
				for (int dz = -radio; dz <= radio; dz += 2 * radio) {
					NoiseColumn e = columnas.en(x + dx, z + dz);
					esquinas[k++] = Suelo.netherCerca(j -> solido(e.getBlock(j)), j -> aire(e.getBlock(j)), y);
				}
			}
			if (Suelo.llano(y, esquinas)) {
				return y;
			}
			desde = y - 2;                                   // el siguiente suelo, por debajo de este
		}
		return Suelo.NINGUNO;
	}

	/** Altura del inicio en el End (Suelo.end con el centro y las cuatro esquinas) o Suelo.NINGUNO. Pública para las pruebas. */
	public static int end(Alturas alturas, int x, int z, int radio) {
		return Suelo.end(x, z, alturas.en(x, z), alturas.en(x - radio, z - radio), alturas.en(x - radio, z + radio),
				alturas.en(x + radio, z - radio), alturas.en(x + radio, z + radio));
	}

	private static boolean solido(BlockState s) {
		return !s.isAir() && s.getFluidState().isEmpty();
	}

	private static boolean aire(BlockState s) {
		return s.isAir() && s.getFluidState().isEmpty();
	}
}
