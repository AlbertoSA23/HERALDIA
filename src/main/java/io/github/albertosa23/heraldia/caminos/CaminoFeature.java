package io.github.albertosa23.heraldia.caminos;

import com.mojang.serialization.MapCodec;
import io.github.albertosa23.heraldia.comun.ZonaAjenas;
import java.util.ArrayList;
import java.util.List;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.Holder;
import net.minecraft.core.QuartPos;
import net.minecraft.core.component.DataComponentMap;
import net.minecraft.core.component.DataComponentPatch;
import net.minecraft.core.component.DataComponents;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.WorldGenRegion;
import net.minecraft.tags.BiomeTags;
import net.minecraft.tags.BlockTags;
import net.minecraft.tags.FluidTags;
import net.minecraft.util.RandomSource;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.StructureManager;
import net.minecraft.world.level.WorldGenLevel;
import net.minecraft.world.level.biome.Biome;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.StandingSignBlock;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.entity.SignBlockEntity;
import net.minecraft.world.level.block.entity.SignText;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;
import net.minecraft.world.level.chunk.ChunkGenerator;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.level.levelgen.feature.Feature;
import net.minecraft.world.level.levelgen.structure.BoundingBox;
import net.minecraft.world.level.levelgen.structure.StructurePiece;
import net.minecraft.world.level.levelgen.structure.StructureStart;

/**
 * heraldia:camino: pinta en el chunk que se genera los tramos de camino que lo cruzan ({@link Trazado}). Solo escribe
 * en su propio chunk y solo lee su chunk (alturas, bloques) y los inicios de estructura que ya conoce la generación.
 * <ul>
 * <li>Tierra: el bloque de la superficie pasa a camino de tierra (con algo de tierra gruesa y grava), losas de arenisca
 * en la arena, de arenisca roja en la arena roja y la terracota, grava y adoquín en la piedra y la nieve, barro compacto
 * en el barro. Lo que no es terreno natural (o tiene algo encima) se deja.</li>
 * <li>Agua: puente de tablas un bloque por encima del agua (con postes hasta el fondo) si el tramo es corto, pasarela a
 * ras si es poco hondo; si es largo y hondo, el camino se corta en la orilla. Nunca sobre lava.</li>
 * <li>Estructuras: ninguna columna dentro de la caja de una pieza (con margen) de una estructura que asoma a la superficie,
 * así que el camino se para al llegar a la aldea y no cruza otras estructuras.</li>
 * <li>Farolas (poste de valla con farol o con antorcha, según la ruta) y los carteles con el nombre de la aldea de destino
 * y la distancia, en tierra firme. Madera del bioma.</li>
 * </ul>
 */
@SuppressWarnings("deprecation") // WorldGenRegion.getLevel(): la vía de vanilla (ChunkStatusTasks) para su StructureManager
public record CaminoFeature() implements Feature {
	public static final MapCodec<CaminoFeature> CODEC = MapCodec.unit(CaminoFeature::new);
	private static final org.slf4j.Logger LOGGER = org.slf4j.LoggerFactory.getLogger("heraldia");
	private static final java.util.concurrent.atomic.AtomicInteger CARTELES = new java.util.concurrent.atomic.AtomicInteger();

	@Override
	public MapCodec<CaminoFeature> codec() {
		return CODEC;
	}

	@Override
	public boolean place(WorldGenLevel level, ChunkGenerator generator, RandomSource random, BlockPos origin) {
		if (!(level instanceof WorldGenRegion region)) {
			return false;
		}
		long t0 = System.nanoTime();
		Caminos.Contexto ctx = Caminos.de(region.getLevel(), generator);
		if (ctx == null || ctx.trazado() == null) {
			return false;
		}
		ChunkPos cp = region.getCenter();
		List<Trazado.Ruta> rutas = ctx.trazado().rutas(cp.x(), cp.z());
		boolean placed = false;
		if (!rutas.isEmpty()) {
			placed = pintar(region, ctx, cp, rutas);
		}
		long ns = System.nanoTime() - t0;
		long n = Caminos.CHUNKS.incrementAndGet();
		Caminos.CHUNKS_NS.addAndGet(ns);
		Caminos.medir(ns);
		if (!rutas.isEmpty()) {
			Caminos.CON_CAMINO.incrementAndGet();
			Caminos.CON_CAMINO_NS.addAndGet(ns);
		}
		if ((n & 0x3FFF) == 0) {
			Caminos.informe();
		}
		return placed;
	}

	private static boolean pintar(WorldGenRegion region, Caminos.Contexto ctx, ChunkPos cp, List<Trazado.Ruta> rutas) {
		Trazado t = ctx.trazado();
		Trazado.Celda[] celdas = t.pintar(rutas, cp.x(), cp.z(), ctx.ancho());
		List<Trazado.Marca> marcas = t.marcas(rutas, cp.x(), cp.z(), ctx.ancho());
		boolean any = !marcas.isEmpty();
		for (Trazado.Celda c : celdas) {
			any |= c != null;
		}
		if (!any) {
			return false;
		}
		List<BoundingBox> cajas = cajas(region, cp);
		int x0 = cp.getMinBlockX(), z0 = cp.getMinBlockZ();
		BlockPos.MutableBlockPos pos = new BlockPos.MutableBlockPos();
		Maderas maderas = new Maderas();
		int columnas = 0;
		for (int i = 0; i < 256; i++) {
			Trazado.Celda c = celdas[i];
			if (c != null && columna(region, ctx, maderas, c, x0 + i / 16, z0 + i % 16, cajas, pos)) {
				columnas++;
			}
		}
		for (Trazado.Marca m : marcas) {
			if (celdas[(m.x() - x0) * 16 + (m.z() - z0)] == null) { // nunca sobre otro camino
				columnas += marca(region, ctx, maderas, m, cajas, pos) ? 1 : 0;
			}
		}
		Caminos.COLUMNAS.addAndGet(columnas);
		return columnas > 0;
	}

	/** Cajas de las piezas de estructuras de superficie (las que el chunk referencia) que tocan el chunk, con margen. */
	private static List<BoundingBox> cajas(WorldGenRegion region, ChunkPos cp) {
		List<BoundingBox> out = new ArrayList<>();
		if (region.getChunk(cp.x(), cp.z()).getAllReferences().isEmpty()) {
			return out;
		}
		StructureManager manager = region.getLevel().structureManager().forWorldGenRegion(region);
		BoundingBox chunk = new BoundingBox(cp.getMinBlockX() - 3, region.getMinY(), cp.getMinBlockZ() - 3,
				cp.getMaxBlockX() + 3, region.getMaxY(), cp.getMaxBlockZ() + 3);
		for (StructureStart start : manager.startsForStructure(cp.x(), cp.z(), s -> ZonaAjenas.visible(s.step()))) {
			for (StructurePiece piece : start.getPieces()) {
				BoundingBox b = piece.getBoundingBox();
				if (b.intersects(chunk)) {
					out.add(b.inflatedBy(2, 3, 2));
				}
			}
		}
		return out;
	}

	private static boolean dentro(List<BoundingBox> cajas, int x, int y, int z) {
		for (BoundingBox b : cajas) {
			if (b.isInside(x, y, z)) {
				return true;
			}
		}
		return false;
	}

	/** Una columna del camino: tierra, puente, pasarela o nada. */
	private static boolean columna(WorldGenRegion region, Caminos.Contexto ctx, Maderas maderas, Trazado.Celda c, int x, int z,
								   List<BoundingBox> cajas, BlockPos.MutableBlockPos pos) {
		int surf = region.getHeight(Heightmap.Types.WORLD_SURFACE_WG, x, z); // primera altura libre
		int floor = region.getHeight(Heightmap.Types.OCEAN_FLOOR_WG, x, z);
		if (dentro(cajas, x, surf - 1, z)) {
			return false;
		}
		pos.set(x, surf - 1, z);
		BlockState top = region.getBlockState(pos);
		if (surf > floor) { // hay fluido encima del fondo
			if (!top.is(Blocks.WATER) || !top.getFluidState().is(FluidTags.WATER)) {
				return false; // lava, o algo que no es agua suelta
			}
			int depth = surf - floor, sea = ctx.sea();
			Trazado.Agua agua = c.ruta().agua(c.vertice(), ctx.fondo(), sea);
			boolean borde = c.dist() > ctx.ancho() / 2.0 - 1 && Math.floorMod((int) c.arco(), 5) == 0;
			if (agua == Trazado.Agua.PUENTE && surf == sea) {
				Madera m = maderas.de(ctx, c.ruta(), c.vertice(), surf);
				pos.set(x, surf, z); // tablero un bloque por encima del agua
				if (!region.getBlockState(pos).isAir()) {
					return false;
				}
				region.setBlock(pos, m.tablas, 2);
				if (borde) { // poste hasta el fondo
					BlockState poste = m.valla.setValue(BlockStateProperties.WATERLOGGED, true);
					for (int y = surf - 1; y >= floor; y--) {
						pos.set(x, y, z);
						if (!region.getBlockState(pos).is(Blocks.WATER)) {
							break;
						}
						region.setBlock(pos, poste, 2);
					}
				}
				return true;
			}
			if ((agua == Trazado.Agua.PASARELA && surf == sea && depth <= Trazado.PASARELA_PROFUNDIDAD)
					|| (agua == Trazado.Agua.TIERRA && depth <= 3)) {
				region.setBlock(pos, maderas.de(ctx, c.ruta(), c.vertice(), surf).tablas, 2); // pasarela a ras (marisma, charca, arroyo)
				return true;
			}
			return false; // tramo largo y hondo: se corta
		}
		pos.set(x, surf, z);
		if (!region.getBlockState(pos).isAir()) {
			return false;
		}
		pos.set(x, surf - 2, z);
		boolean firme = region.getBlockState(pos).isFaceSturdy(region, pos, Direction.UP);
		BlockState piso = suelo(top, Trazado.azar(region.getSeed(), Trazado.pack(x, z), 11), firme);
		if (piso == null) {
			return false;
		}
		pos.set(x, surf - 1, z);
		region.setBlock(pos, piso, 2);
		return true;
	}

	/** Material del camino según el bloque de la superficie, o null si no es terreno natural. Los bloques vanilla van
	 *  por nombre y los de otros mods por sus etiquetas (#dirt, #sand, #terracotta, #base_stone_overworld). */
	static BlockState suelo(BlockState top, double r, boolean firme) {
		BlockState grava = firme ? Blocks.GRAVEL.defaultBlockState() : Blocks.COBBLESTONE.defaultBlockState();
		if (top.is(Blocks.MUD) || top.is(Blocks.MUDDY_MANGROVE_ROOTS)) {
			return (r < 0.75 ? Blocks.PACKED_MUD : Blocks.MUD_BRICKS).defaultBlockState();
		}
		if (es(top, TIERRA) || top.is(BlockTags.DIRT)) {
			return r < 0.12 ? Blocks.COARSE_DIRT.defaultBlockState() : r < 0.17 ? grava : Blocks.DIRT_PATH.defaultBlockState();
		}
		if (top.is(Blocks.RED_SAND) || top.is(Blocks.TERRACOTTA) || top.is(BlockTags.TERRACOTTA)) {
			return (r < 0.6 ? Blocks.SMOOTH_RED_SANDSTONE : r < 0.85 ? Blocks.RED_SANDSTONE : Blocks.CUT_RED_SANDSTONE).defaultBlockState();
		}
		if (top.is(Blocks.SAND) || top.is(BlockTags.SAND)) {
			return (r < 0.6 ? Blocks.SMOOTH_SANDSTONE : r < 0.85 ? Blocks.SANDSTONE : Blocks.CUT_SANDSTONE).defaultBlockState();
		}
		if (es(top, PIEDRA) || top.is(BlockTags.BASE_STONE_OVERWORLD)) {
			return r < 0.55 ? grava : r < 0.85 ? Blocks.COBBLESTONE.defaultBlockState() : Blocks.STONE_BRICKS.defaultBlockState();
		}
		return null;
	}

	private static final Block[] TIERRA = {Blocks.GRASS_BLOCK, Blocks.DIRT, Blocks.COARSE_DIRT, Blocks.PODZOL, Blocks.MYCELIUM,
			Blocks.ROOTED_DIRT, Blocks.MOSS_BLOCK, Blocks.PALE_MOSS_BLOCK};
	private static final Block[] PIEDRA = {Blocks.STONE, Blocks.GRANITE, Blocks.DIORITE, Blocks.ANDESITE, Blocks.TUFF, Blocks.DEEPSLATE,
			Blocks.CALCITE, Blocks.GRAVEL, Blocks.SNOW_BLOCK, Blocks.POWDER_SNOW, Blocks.CLAY};

	private static boolean es(BlockState s, Block[] blocks) {
		for (Block b : blocks) {
			if (s.is(b)) {
				return true;
			}
		}
		return false;
	}

	/** Farola o cartel en tierra firme, fuera de las estructuras. */
	private static boolean marca(WorldGenRegion region, Caminos.Contexto ctx, Maderas maderas, Trazado.Marca m, List<BoundingBox> cajas,
								 BlockPos.MutableBlockPos pos) {
		int x = m.x(), z = m.z();
		int surf = region.getHeight(Heightmap.Types.WORLD_SURFACE_WG, x, z);
		if (surf != region.getHeight(Heightmap.Types.OCEAN_FLOOR_WG, x, z) || dentro(cajas, x, surf, z)) {
			return false; // agua o estructura
		}
		pos.set(x, surf - 1, z);
		BlockState top = region.getBlockState(pos);
		if (!top.isFaceSturdy(region, pos, Direction.UP) || suelo(top, 0.5, true) == null) {
			return false;
		}
		for (int y = surf; y < surf + 3; y++) {
			if (!region.getBlockState(pos.set(x, y, z)).isAir()) {
				return false;
			}
		}
		Madera w = maderas.de(ctx, m.ruta(), m.vertice(), surf);
		if (!m.cartel()) {
			region.setBlock(pos.set(x, surf, z), w.valla, 2);
			region.setBlock(pos.set(x, surf + 1, z), w.valla, 2);
			region.setBlock(pos.set(x, surf + 2, z), (m.ruta().farol ? Blocks.LANTERN : Blocks.TORCH).defaultBlockState(), 2);
			return true;
		}
		BlockState sign = w.cartel.setValue(StandingSignBlock.ROTATION, m.rotacion());
		pos.set(x, surf, z);
		region.setBlock(pos, sign, 2);
		BlockEntity be = region.getBlockEntity(pos);
		if (be instanceof SignBlockEntity) {
			String[] nombre = Nombres.de(region.getSeed(), Trazado.px(m.destino()), Trazado.pz(m.destino()));
			String n = String.valueOf(m.distancia());
			Component dist = m.derecha()
					? Component.translatableWithFallback("heraldia.camino.cartel.derecha", "%s bloques →", n)
					: Component.translatableWithFallback("heraldia.camino.cartel.izquierda", "← %s bloques", n);
			SignText text = SignText.EMPTY.asMutable()
					.setLine(0, Component.literal(nombre[0]))
					.setLine(1, Component.literal(nombre[1]))
					.setLine(2, dist)
					.asImmutable();
			// setText avisa al mundo (que en la generación no hay): el texto va como componente del bloque
			be.applyComponents(DataComponentMap.builder().set(DataComponents.SIGN_TEXT_FRONT, text).build(), DataComponentPatch.EMPTY);
			if (CARTELES.getAndIncrement() < 16) { // los primeros, al log (la prueba de servidor lee el letrero)
				LOGGER.info("Heraldia: cartel de camino en {} {} {}: «{} {}», {} bloques", x, surf, z, nombre[0], nombre[1], n);
			}
		}
		return true;
	}

	/** Tablas, valla y cartel de una madera. */
	record Madera(BlockState tablas, BlockState valla, BlockState cartel) {
		static Madera de(Block tablas, Block valla, Block cartel) {
			return new Madera(tablas.defaultBlockState(), valla.defaultBlockState(), cartel.defaultBlockState());
		}
	}

	static final Madera ROBLE = Madera.de(Blocks.OAK_PLANKS, Blocks.OAK_FENCE, Blocks.OAK_SIGN),
			ABETO = Madera.de(Blocks.SPRUCE_PLANKS, Blocks.SPRUCE_FENCE, Blocks.SPRUCE_SIGN),
			ABEDUL = Madera.de(Blocks.BIRCH_PLANKS, Blocks.BIRCH_FENCE, Blocks.BIRCH_SIGN),
			JUNGLA = Madera.de(Blocks.JUNGLE_PLANKS, Blocks.JUNGLE_FENCE, Blocks.JUNGLE_SIGN),
			ACACIA = Madera.de(Blocks.ACACIA_PLANKS, Blocks.ACACIA_FENCE, Blocks.ACACIA_SIGN),
			OSCURO = Madera.de(Blocks.DARK_OAK_PLANKS, Blocks.DARK_OAK_FENCE, Blocks.DARK_OAK_SIGN),
			MANGLE = Madera.de(Blocks.MANGROVE_PLANKS, Blocks.MANGROVE_FENCE, Blocks.MANGROVE_SIGN),
			CEREZO = Madera.de(Blocks.CHERRY_PLANKS, Blocks.CHERRY_FENCE, Blocks.CHERRY_SIGN),
			PALIDO = Madera.de(Blocks.PALE_OAK_PLANKS, Blocks.PALE_OAK_FENCE, Blocks.PALE_OAK_SIGN);

	/**
	 * Madera del bioma en un vértice (del ruido, a la altura del mar: la misma a los dos lados de una frontera de chunk),
	 * en memoria durante el chunk: unos pocos vértices por chunk, cada muestra del ruido cuesta unos 20 µs.
	 */
	static final class Maderas {
		private Trazado.Ruta ruta;
		private int vertice = -1;
		private Madera madera;

		Madera de(Caminos.Contexto ctx, Trazado.Ruta r, int v, int y) {
			if (r != ruta || v != vertice) {
				Holder<Biome> b = ctx.biomas().getNoiseBiome(QuartPos.fromBlock((int) r.x(v)), QuartPos.fromBlock(ctx.sea()), QuartPos.fromBlock((int) r.z(v)));
				ruta = r;
				vertice = v;
				madera = madera(b);
			}
			return madera;
		}
	}

	static Madera madera(Holder<Biome> b) {
		String path = b.unwrapKey().map(k -> k.identifier().getPath()).orElse("");
		if (b.is(BiomeTags.IS_JUNGLE)) {
			return JUNGLA;
		}
		if (b.is(BiomeTags.IS_SAVANNA)) {
			return ACACIA;
		}
		if (path.contains("mangrove")) {
			return MANGLE;
		}
		if (path.contains("cherry")) {
			return CEREZO;
		}
		if (path.contains("pale")) {
			return PALIDO;
		}
		if (path.contains("dark_forest") || path.contains("roofed")) {
			return OSCURO;
		}
		if (path.contains("birch")) {
			return ABEDUL;
		}
		if (b.is(BiomeTags.IS_TAIGA) || path.contains("snow") || path.contains("frozen") || path.contains("grove") || path.contains("slopes")
				|| path.contains("peaks") || path.contains("spruce") || path.contains("pine")) {
			return ABETO;
		}
		return ROBLE;
	}
}
