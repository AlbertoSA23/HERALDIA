package io.github.albertosa23.heraldia.roads;

import com.mojang.serialization.MapCodec;
import io.github.albertosa23.heraldia.common.Profiler;
import io.github.albertosa23.heraldia.common.ForeignZone;
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
 * heraldia:camino: paints in the chunk being generated the road segments that cross it ({@link RoadLayout}). It only writes
 * into its own chunk and only reads its own chunk (heights, blocks) and the structure starts generation already knows.
 * <ul>
 * <li>Land: the surface block becomes a dirt path (with some coarse dirt and gravel), sandstone slabs
 * on sand, red sandstone on red sand and terracotta, gravel and cobblestone on stone and snow, packed mud
 * on mud. Whatever is not natural terrain (or has something on top) is left.</li>
 * <li>Water: a plank bridge one block above the water (with posts down to the bottom) if the stretch is short, a
 * walkway flush with it if it is shallow; if it is long and deep, the road is cut at the shore. Never over lava.</li>
 * <li>Structures: no column inside the box of a piece (with a margin) of a structure that shows above ground,
 * so the road stops when it reaches the village and does not cross other structures.</li>
 * <li>Lamp posts (fence post with a lantern or a torch, depending on the route) and the signs with the destination
 * village's name and the distance, on firm ground. Wood of the biome.</li>
 * </ul>
 */
@SuppressWarnings("deprecation") // WorldGenRegion.getLevel(): vanilla's way (ChunkStatusTasks) to its StructureManager
public record RoadFeature() implements Feature {
	public static final MapCodec<RoadFeature> CODEC = MapCodec.unit(RoadFeature::new);
	private static final org.slf4j.Logger LOGGER = org.slf4j.LoggerFactory.getLogger("heraldia");
	private static final java.util.concurrent.atomic.AtomicInteger SIGNS = new java.util.concurrent.atomic.AtomicInteger();

	@Override
	public MapCodec<RoadFeature> codec() {
		return CODEC;
	}

	@Override
	public boolean place(WorldGenLevel level, ChunkGenerator generator, RandomSource random, BlockPos origin) {
		if (!(level instanceof WorldGenRegion region)) {
			return false;
		}
		long t0 = System.nanoTime();
		Roads.Context ctx = Roads.of(region.getLevel(), generator);
		if (ctx == null || ctx.layout() == null) {
			return false;
		}
		ChunkPos cp = region.getCenter();
		List<RoadLayout.Route> routes = ctx.layout().routes(cp.x(), cp.z());
		boolean placed = false;
		if (!routes.isEmpty()) {
			placed = paint(region, ctx, cp, routes);
		}
		long ns = System.nanoTime() - t0;
		Profiler.counters().recordSample(Profiler.Segment.ROADS, ns);
		long n = Roads.CHUNKS.incrementAndGet();
		Roads.CHUNKS_NS.addAndGet(ns);
		Roads.measure(ns);
		if (!routes.isEmpty()) {
			Roads.WITH_ROAD.incrementAndGet();
			Roads.WITH_ROAD_NS.addAndGet(ns);
		}
		if ((n & 0x3FFF) == 0) {
			Roads.report();
		}
		return placed;
	}

	private static boolean paint(WorldGenRegion region, Roads.Context ctx, ChunkPos cp, List<RoadLayout.Route> routes) {
		RoadLayout t = ctx.layout();
		RoadLayout.Cell[] cells = t.paint(routes, cp.x(), cp.z(), ctx.width());
		List<RoadLayout.Mark> marks = t.marks(routes, cp.x(), cp.z(), ctx.width());
		boolean any = !marks.isEmpty();
		for (RoadLayout.Cell c : cells) {
			any |= c != null;
		}
		if (!any) {
			return false;
		}
		List<BoundingBox> boxes = boxes(region, cp);
		int x0 = cp.getMinBlockX(), z0 = cp.getMinBlockZ();
		BlockPos.MutableBlockPos pos = new BlockPos.MutableBlockPos();
		Woods woods = new Woods();
		int columns = 0;
		for (int i = 0; i < 256; i++) {
			RoadLayout.Cell c = cells[i];
			if (c != null && column(region, ctx, woods, c, x0 + i / 16, z0 + i % 16, boxes, pos)) {
				columns++;
			}
		}
		for (RoadLayout.Mark m : marks) {
			if (cells[(m.x() - x0) * 16 + (m.z() - z0)] == null) { // never over another road
				columns += mark(region, ctx, woods, m, boxes, pos) ? 1 : 0;
			}
		}
		Roads.COLUMNS.addAndGet(columns);
		return columns > 0;
	}

	/** Boxes of the surface structure pieces (those the chunk references) that touch the chunk, with a margin. */
	private static List<BoundingBox> boxes(WorldGenRegion region, ChunkPos cp) {
		List<BoundingBox> out = new ArrayList<>();
		if (region.getChunk(cp.x(), cp.z()).getAllReferences().isEmpty()) {
			return out;
		}
		StructureManager manager = region.getLevel().structureManager().forWorldGenRegion(region);
		BoundingBox chunk = new BoundingBox(cp.getMinBlockX() - 3, region.getMinY(), cp.getMinBlockZ() - 3,
				cp.getMaxBlockX() + 3, region.getMaxY(), cp.getMaxBlockZ() + 3);
		for (StructureStart start : manager.startsForStructure(cp.x(), cp.z(), s -> ForeignZone.visible(s.step()))) {
			for (StructurePiece piece : start.getPieces()) {
				BoundingBox b = piece.getBoundingBox();
				if (b.intersects(chunk)) {
					out.add(b.inflatedBy(2, 3, 2));
				}
			}
		}
		return out;
	}

	private static boolean inside(List<BoundingBox> boxes, int x, int y, int z) {
		for (BoundingBox b : boxes) {
			if (b.isInside(x, y, z)) {
				return true;
			}
		}
		return false;
	}

	/** A road column: land, bridge, walkway or nothing. */
	private static boolean column(WorldGenRegion region, Roads.Context ctx, Woods woods, RoadLayout.Cell c, int x, int z,
								   List<BoundingBox> boxes, BlockPos.MutableBlockPos pos) {
		int surf = region.getHeight(Heightmap.Types.WORLD_SURFACE_WG, x, z); // first free height
		int floor = region.getHeight(Heightmap.Types.OCEAN_FLOOR_WG, x, z);
		if (inside(boxes, x, surf - 1, z)) {
			return false;
		}
		pos.set(x, surf - 1, z);
		BlockState top = region.getBlockState(pos);
		if (surf > floor) { // there is fluid above the bottom
			if (!top.is(Blocks.WATER) || !top.getFluidState().is(FluidTags.WATER)) {
				return false; // lava, or something that is not loose water
			}
			int depth = surf - floor, sea = ctx.sea();
			RoadLayout.Water water = c.route().water(c.vertex(), ctx.depth(), sea);
			boolean edge = c.dist() > ctx.width() / 2.0 - 1 && Math.floorMod((int) c.arc(), 5) == 0;
			if (water == RoadLayout.Water.BRIDGE && surf == sea) {
				Wood m = woods.of(ctx, c.route(), c.vertex(), surf);
				pos.set(x, surf, z); // deck one block above the water
				if (!region.getBlockState(pos).isAir()) {
					return false;
				}
				region.setBlock(pos, m.planks, 2);
				if (edge) { // post down to the bottom
					BlockState post = m.fence.setValue(BlockStateProperties.WATERLOGGED, true);
					for (int y = surf - 1; y >= floor; y--) {
						pos.set(x, y, z);
						if (!region.getBlockState(pos).is(Blocks.WATER)) {
							break;
						}
						region.setBlock(pos, post, 2);
					}
				}
				return true;
			}
			if ((water == RoadLayout.Water.WALKWAY && surf == sea && depth <= RoadLayout.WALKWAY_DEPTH)
					|| (water == RoadLayout.Water.LAND && depth <= 3)) {
				region.setBlock(pos, woods.of(ctx, c.route(), c.vertex(), surf).planks, 2); // flush walkway (marsh, pond, stream)
				return true;
			}
			return false; // long and deep stretch: it is cut
		}
		pos.set(x, surf, z);
		if (!region.getBlockState(pos).isAir()) {
			return false;
		}
		pos.set(x, surf - 2, z);
		boolean firm = region.getBlockState(pos).isFaceSturdy(region, pos, Direction.UP);
		BlockState deck = ground(top, RoadLayout.rng(region.getSeed(), RoadLayout.pack(x, z), 11), firm);
		if (deck == null) {
			return false;
		}
		pos.set(x, surf - 1, z);
		region.setBlock(pos, deck, 2);
		return true;
	}

	/** Road material for the surface block, or null if it is not natural terrain. Vanilla blocks go
	 *  by name and other mods' by their tags (#dirt, #sand, #terracotta, #base_stone_overworld). */
	static BlockState ground(BlockState top, double r, boolean firm) {
		BlockState gravel = firm ? Blocks.GRAVEL.defaultBlockState() : Blocks.COBBLESTONE.defaultBlockState();
		if (top.is(Blocks.MUD) || top.is(Blocks.MUDDY_MANGROVE_ROOTS)) {
			return (r < 0.75 ? Blocks.PACKED_MUD : Blocks.MUD_BRICKS).defaultBlockState();
		}
		if (es(top, LAND) || top.is(BlockTags.DIRT)) {
			return r < 0.12 ? Blocks.COARSE_DIRT.defaultBlockState() : r < 0.17 ? gravel : Blocks.DIRT_PATH.defaultBlockState();
		}
		if (top.is(Blocks.RED_SAND) || top.is(Blocks.TERRACOTTA) || top.is(BlockTags.TERRACOTTA)) {
			return (r < 0.6 ? Blocks.SMOOTH_RED_SANDSTONE : r < 0.85 ? Blocks.RED_SANDSTONE : Blocks.CUT_RED_SANDSTONE).defaultBlockState();
		}
		if (top.is(Blocks.SAND) || top.is(BlockTags.SAND)) {
			return (r < 0.6 ? Blocks.SMOOTH_SANDSTONE : r < 0.85 ? Blocks.SANDSTONE : Blocks.CUT_SANDSTONE).defaultBlockState();
		}
		if (es(top, STONE) || top.is(BlockTags.BASE_STONE_OVERWORLD)) {
			return r < 0.55 ? gravel : r < 0.85 ? Blocks.COBBLESTONE.defaultBlockState() : Blocks.STONE_BRICKS.defaultBlockState();
		}
		return null;
	}

	private static final Block[] LAND = {Blocks.GRASS_BLOCK, Blocks.DIRT, Blocks.COARSE_DIRT, Blocks.PODZOL, Blocks.MYCELIUM,
			Blocks.ROOTED_DIRT, Blocks.MOSS_BLOCK, Blocks.PALE_MOSS_BLOCK};
	private static final Block[] STONE = {Blocks.STONE, Blocks.GRANITE, Blocks.DIORITE, Blocks.ANDESITE, Blocks.TUFF, Blocks.DEEPSLATE,
			Blocks.CALCITE, Blocks.GRAVEL, Blocks.SNOW_BLOCK, Blocks.POWDER_SNOW, Blocks.CLAY};

	private static boolean es(BlockState s, Block[] blocks) {
		for (Block b : blocks) {
			if (s.is(b)) {
				return true;
			}
		}
		return false;
	}

	/** Lamp post or sign on firm ground, outside the structures. */
	private static boolean mark(WorldGenRegion region, Roads.Context ctx, Woods woods, RoadLayout.Mark m, List<BoundingBox> boxes,
								 BlockPos.MutableBlockPos pos) {
		int x = m.x(), z = m.z();
		int surf = region.getHeight(Heightmap.Types.WORLD_SURFACE_WG, x, z);
		if (surf != region.getHeight(Heightmap.Types.OCEAN_FLOOR_WG, x, z) || inside(boxes, x, surf, z)) {
			return false; // water or structure
		}
		pos.set(x, surf - 1, z);
		BlockState top = region.getBlockState(pos);
		if (!top.isFaceSturdy(region, pos, Direction.UP) || ground(top, 0.5, true) == null) {
			return false;
		}
		for (int y = surf; y < surf + 3; y++) {
			if (!region.getBlockState(pos.set(x, y, z)).isAir()) {
				return false;
			}
		}
		Wood w = woods.of(ctx, m.route(), m.vertex(), surf);
		if (!m.signpost()) {
			region.setBlock(pos.set(x, surf, z), w.fence, 2);
			region.setBlock(pos.set(x, surf + 1, z), w.fence, 2);
			region.setBlock(pos.set(x, surf + 2, z), (m.route().lantern ? Blocks.LANTERN : Blocks.TORCH).defaultBlockState(), 2);
			return true;
		}
		BlockState sign = w.signpost.setValue(StandingSignBlock.ROTATION, m.rotation());
		pos.set(x, surf, z);
		region.setBlock(pos, sign, 2);
		BlockEntity be = region.getBlockEntity(pos);
		if (be instanceof SignBlockEntity) {
			String[] name = Names.of(region.getSeed(), RoadLayout.px(m.destination()), RoadLayout.pz(m.destination()));
			String n = String.valueOf(m.distance());
			Component dist = m.right()
					? Component.translatableWithFallback("heraldia.camino.cartel.derecha", "%s bloques →", n)
					: Component.translatableWithFallback("heraldia.camino.cartel.izquierda", "← %s bloques", n);
			SignText text = SignText.EMPTY.asMutable()
					.setLine(0, Component.literal(name[0]))
					.setLine(1, Component.literal(name[1]))
					.setLine(2, dist)
					.asImmutable();
			// setText notifies the world (which does not exist during generation): the text goes as a block component
			be.applyComponents(DataComponentMap.builder().set(DataComponents.SIGN_TEXT_FRONT, text).build(), DataComponentPatch.EMPTY);
			if (SIGNS.getAndIncrement() < 16) { // the first ones, to the log (the server test reads the sign)
				LOGGER.info("Heraldia: cartel de camino en {} {} {}: «{} {}», {} bloques", x, surf, z, name[0], name[1], n);
			}
		}
		return true;
	}

	/** Planks, fence and sign of a wood. */
	record Wood(BlockState planks, BlockState fence, BlockState signpost) {
		static Wood of(Block planks, Block fence, Block signpost) {
			return new Wood(planks.defaultBlockState(), fence.defaultBlockState(), signpost.defaultBlockState());
		}
	}

	static final Wood OAK = Wood.of(Blocks.OAK_PLANKS, Blocks.OAK_FENCE, Blocks.OAK_SIGN),
			SPRUCE = Wood.of(Blocks.SPRUCE_PLANKS, Blocks.SPRUCE_FENCE, Blocks.SPRUCE_SIGN),
			BIRCH = Wood.of(Blocks.BIRCH_PLANKS, Blocks.BIRCH_FENCE, Blocks.BIRCH_SIGN),
			JUNGLE = Wood.of(Blocks.JUNGLE_PLANKS, Blocks.JUNGLE_FENCE, Blocks.JUNGLE_SIGN),
			ACACIA = Wood.of(Blocks.ACACIA_PLANKS, Blocks.ACACIA_FENCE, Blocks.ACACIA_SIGN),
			DARK_OAK = Wood.of(Blocks.DARK_OAK_PLANKS, Blocks.DARK_OAK_FENCE, Blocks.DARK_OAK_SIGN),
			MANGROVE = Wood.of(Blocks.MANGROVE_PLANKS, Blocks.MANGROVE_FENCE, Blocks.MANGROVE_SIGN),
			CHERRY = Wood.of(Blocks.CHERRY_PLANKS, Blocks.CHERRY_FENCE, Blocks.CHERRY_SIGN),
			PALE_OAK = Wood.of(Blocks.PALE_OAK_PLANKS, Blocks.PALE_OAK_FENCE, Blocks.PALE_OAK_SIGN);

	/**
	 * Wood of the biome at a vertex (from the noise, at sea level: the same on both sides of a chunk border),
	 * memoized during the chunk: a few vertices per chunk, each noise sample costs about 20 µs.
	 */
	static final class Woods {
		private RoadLayout.Route route;
		private int vertex = -1;
		private Wood wood;

		Wood of(Roads.Context ctx, RoadLayout.Route r, int v, int y) {
			if (r != route || v != vertex) {
				Holder<Biome> b = ctx.biomes().getNoiseBiome(QuartPos.fromBlock((int) r.x(v)), QuartPos.fromBlock(ctx.sea()), QuartPos.fromBlock((int) r.z(v)));
				route = r;
				vertex = v;
				wood = wood(b);
			}
			return wood;
		}
	}

	static Wood wood(Holder<Biome> b) {
		String path = b.unwrapKey().map(k -> k.identifier().getPath()).orElse("");
		if (b.is(BiomeTags.IS_JUNGLE)) {
			return JUNGLE;
		}
		if (b.is(BiomeTags.IS_SAVANNA)) {
			return ACACIA;
		}
		if (path.contains("mangrove")) {
			return MANGROVE;
		}
		if (path.contains("cherry")) {
			return CHERRY;
		}
		if (path.contains("pale")) {
			return PALE_OAK;
		}
		if (path.contains("dark_forest") || path.contains("roofed")) {
			return DARK_OAK;
		}
		if (path.contains("birch")) {
			return BIRCH;
		}
		if (b.is(BiomeTags.IS_TAIGA) || path.contains("snow") || path.contains("frozen") || path.contains("grove") || path.contains("slopes")
				|| path.contains("peaks") || path.contains("spruce") || path.contains("pine")) {
			return SPRUCE;
		}
		return OAK;
	}
}
