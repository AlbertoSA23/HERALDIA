package io.github.albertosa23.heraldia.roads;

import io.github.albertosa23.heraldia.common.ForeignZone;
import java.util.ArrayList;
import java.util.List;
import java.util.function.BiPredicate;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.tags.BlockTags;
import net.minecraft.tags.FluidTags;
import net.minecraft.world.item.DyeColor;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.StandingSignBlock;
import net.minecraft.world.level.block.entity.SignBlockEntity;
import net.minecraft.world.level.block.entity.SignText;
import net.minecraft.world.level.block.entity.SignTextSlot;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;
import net.minecraft.world.level.chunk.LevelChunk;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.level.levelgen.structure.BoundingBox;
import net.minecraft.world.level.levelgen.structure.StructurePiece;
import net.minecraft.world.level.levelgen.structure.StructureStart;

/**
 * Roads BUILT in a chunk that already exists (the Herald's House roads, herald/SpawnRoads), with the look of the roads
 * between villages that generation paints ({@link RoadFeature}): the same columns ({@link RoadLayout#paint}), the same
 * paving for each kind of ground ({@link RoadFeature#ground}), the same plank bridges and walkways over water
 * ({@link RoadLayout.Route#water}) and the same biome woods ({@link RoadFeature#wood}). What changes is that the chunk is a
 * real one: grass, flowers, snow and low leaves over the road are cleared, and nothing that is not natural terrain is
 * ever touched (a player's block, a structure's piece: those columns are left as they are).
 */
public final class BuiltRoads {
	/** No neighbour updates and no drops (as the town's building). */
	public static final int FLAGS = Block.UPDATE_CLIENTS | Block.UPDATE_KNOWN_SHAPE | Block.UPDATE_SUPPRESS_DROPS;

	private BuiltRoads() {
	}

	/** The boxes (with a margin) of the pieces of the surface structures this chunk references. */
	public static List<BoundingBox> boxes(ServerLevel level, LevelChunk chunk) {
		List<BoundingBox> out = new ArrayList<>();
		if (chunk.getAllReferences().isEmpty()) {
			return out;
		}
		var cp = chunk.getPos();
		BoundingBox near = new BoundingBox(cp.getMinBlockX() - 3, level.getMinY(), cp.getMinBlockZ() - 3, cp.getMaxBlockX() + 3,
				level.getMaxY(), cp.getMaxBlockZ() + 3);
		for (StructureStart start : level.structureManager().startsForStructure(cp.x(), cp.z(), s -> ForeignZone.visible(s.step()))) {
			for (StructurePiece piece : start.getPieces()) {
				BoundingBox b = piece.getBoundingBox();
				if (b.intersects(near)) {
					out.add(b.inflatedBy(2, 3, 2));
				}
			}
		}
		return out;
	}

	static boolean inside(List<BoundingBox> boxes, int x, int y, int z) {
		for (BoundingBox b : boxes) {
			if (b.isInside(x, y, z)) {
				return true;
			}
		}
		return false;
	}

	/** What may be cleared over a road (plants, snow, leaves): nothing a player builds. */
	static boolean clearable(BlockState s) {
		return s.isAir() || (s.canBeReplaced() && s.getFluidState().isEmpty()) || s.is(BlockTags.LEAVES) || s.is(Blocks.SNOW);
	}

	/** What the painted chunk did: columns paved, bridged, left (not natural ground, a structure, the arena...). */
	public record Painted(int paved, int bridged, int left) {
	}

	/**
	 * Paves the road columns of {@code routes} in this chunk. {@code skip}: columns never to touch (the town's footprint,
	 * the arena's box). {@code seabed}: the terrain's bottom height (noise: the vertices may lie in chunks not loaded).
	 * Returns the cells painted (x * 16 + z, null = no road) with the counts.
	 */
	public static Painted pave(ServerLevel level, LevelChunk chunk, RoadLayout layout, List<RoadLayout.Route> routes, int width,
			RoadLayout.Seabed seabed, BiPredicate<Integer, Integer> skip, RoadLayout.Cell[] cells) {
		var cp = chunk.getPos();
		RoadLayout.Cell[] c = layout.paint(routes, cp.x(), cp.z(), width);
		System.arraycopy(c, 0, cells, 0, 256);
		List<BoundingBox> boxes = boxes(level, chunk);
		BlockPos.MutableBlockPos pos = new BlockPos.MutableBlockPos();
		int paved = 0, bridged = 0, left = 0, sea = level.getSeaLevel();
		for (int i = 0; i < 256; i++) {
			RoadLayout.Cell cell = c[i];
			if (cell == null) {
				continue;
			}
			int x = cp.getMinBlockX() + i / 16, z = cp.getMinBlockZ() + i % 16;
			int r = column(level, chunk, cell, x, z, width, seabed, sea, boxes, skip, pos);
			if (r == 1) {
				paved++;
			} else if (r == 2) {
				bridged++;
			} else {
				left++;
				cells[i] = null;
			}
		}
		return new Painted(paved, bridged, left);
	}

	/** One column: 1 paved, 2 bridge or walkway, 0 left as it is. */
	private static int column(ServerLevel level, LevelChunk chunk, RoadLayout.Cell c, int x, int z, int width, RoadLayout.Seabed seabed,
			int sea, List<BoundingBox> boxes, BiPredicate<Integer, Integer> skip, BlockPos.MutableBlockPos pos) {
		if (skip.test(x, z)) {
			return 0;
		}
		int surf = chunk.getHeight(Heightmap.Types.MOTION_BLOCKING_NO_LEAVES, x & 15, z & 15) + 1;   // first free height
		int floor = chunk.getHeight(Heightmap.Types.OCEAN_FLOOR, x & 15, z & 15) + 1;
		if (inside(boxes, x, surf - 1, z)) {
			return 0;
		}
		BlockState top = level.getBlockState(pos.set(x, surf - 1, z));
		if (surf > floor) {                       // fluid above the bottom
			if (!top.is(Blocks.WATER) || !top.getFluidState().is(FluidTags.WATER)) {
				return 0;                          // lava, or something that is not loose water
			}
			int depth = surf - floor;
			RoadLayout.Water water = c.route().water(c.vertex(), seabed, sea);
			RoadFeature.Wood w = RoadFeature.wood(level.getBiome(pos.set(x, surf, z)));
			if (water == RoadLayout.Water.BRIDGE && surf == sea) {
				if (!clearable(level.getBlockState(pos.set(x, surf, z)))) {
					return 0;
				}
				level.setBlock(pos, w.planks(), FLAGS);
				boolean edge = c.dist() > width / 2.0 - 1 && Math.floorMod((int) c.arc(), 5) == 0;
				if (edge) {                        // a post down to the bottom
					BlockState post = w.fence().setValue(BlockStateProperties.WATERLOGGED, true);
					for (int y = surf - 1; y >= floor; y--) {
						if (!level.getBlockState(pos.set(x, y, z)).is(Blocks.WATER)) {
							break;
						}
						level.setBlock(pos, post, FLAGS);
					}
				}
				return 2;
			}
			if (water == RoadLayout.Water.WALKWAY && surf == sea && depth <= RoadLayout.WALKWAY_DEPTH
					|| water == RoadLayout.Water.LAND && depth <= 3) {
				level.setBlock(pos.set(x, surf - 1, z), w.planks(), FLAGS);   // a walkway flush with the water
				return 2;
			}
			return 0;                              // a long, deep stretch: cut
		}
		for (int y = surf; y <= surf + 1; y++) {
			if (!clearable(level.getBlockState(pos.set(x, y, z)))) {
				return 0;                          // something over the ground that is not a plant: left alone
			}
		}
		boolean firm = level.getBlockState(pos.set(x, surf - 2, z)).isFaceSturdy(level, pos, Direction.UP);
		BlockState deck = RoadFeature.ground(top, RoadLayout.rng(level.getSeed(), RoadLayout.pack(x, z), 11), firm);
		if (deck == null) {
			return 0;
		}
		for (int y = surf; y <= surf + 1; y++) {
			if (!level.getBlockState(pos.set(x, y, z)).isAir()) {
				level.setBlock(pos, Blocks.AIR.defaultBlockState(), FLAGS);
			}
		}
		level.setBlock(pos.set(x, surf - 1, z), deck, FLAGS);
		return 1;
	}

	/**
	 * A lamp post (two fence posts of the biome's wood and a lantern) at (x, z) on firm natural ground, or, if that
	 * column is water beside a bridge, on the bridge's edge at (ex, ez). False if neither fits.
	 */
	public static boolean lamp(ServerLevel level, int x, int z, int ex, int ez, BiPredicate<Integer, Integer> skip) {
		BlockPos.MutableBlockPos pos = new BlockPos.MutableBlockPos();
		if (!skip.test(x, z)) {
			LevelChunk chunk = level.getChunk(x >> 4, z >> 4);
			List<BoundingBox> boxes = boxes(level, chunk);
			int surf = chunk.getHeight(Heightmap.Types.MOTION_BLOCKING_NO_LEAVES, x & 15, z & 15) + 1;
			int floor = chunk.getHeight(Heightmap.Types.OCEAN_FLOOR, x & 15, z & 15) + 1;
			BlockState top = level.getBlockState(pos.set(x, surf - 1, z));
			if (surf == floor && !inside(boxes, x, surf, z) && top.isFaceSturdy(level, pos, Direction.UP)
					&& (RoadFeature.ground(top, 0.5, true) != null || top.is(Blocks.DIRT_PATH)) && free(level, pos, x, surf, z)) {
				post(level, pos, x, surf, z);
				return true;
			}
		}
		if (skip.test(ex, ez)) {
			return false;
		}
		LevelChunk chunk = level.getChunk(ex >> 4, ez >> 4);
		int surf = chunk.getHeight(Heightmap.Types.MOTION_BLOCKING_NO_LEAVES, ex & 15, ez & 15);
		BlockState deck = level.getBlockState(pos.set(ex, surf, ez));
		if (deck.is(BlockTags.PLANKS) && level.getBlockState(pos.set(ex, surf - 1, ez)).getFluidState().is(FluidTags.WATER)
				&& free(level, pos, ex, surf + 1, ez)) {
			post(level, pos, ex, surf + 1, ez);
			return true;
		}
		return false;
	}

	private static boolean free(ServerLevel level, BlockPos.MutableBlockPos pos, int x, int y, int z) {
		for (int yy = y; yy < y + 3; yy++) {
			if (!clearable(level.getBlockState(pos.set(x, yy, z)))) {
				return false;
			}
		}
		return true;
	}

	private static void post(ServerLevel level, BlockPos.MutableBlockPos pos, int x, int y, int z) {
		RoadFeature.Wood w = RoadFeature.wood(level.getBiome(pos.set(x, y, z)));
		level.setBlock(pos.set(x, y, z), w.fence(), Block.UPDATE_ALL);
		level.setBlock(pos.set(x, y + 1, z), w.fence(), Block.UPDATE_ALL);
		level.setBlock(pos.set(x, y + 2, z), Blocks.LANTERN.defaultBlockState(), Block.UPDATE_ALL);
	}

	/** A standing sign of the biome's wood at (x, z) on firm ground, facing {@code rotation} (0-15), with two lines. */
	public static boolean sign(ServerLevel level, int x, int z, int rotation, Component first, Component second,
			BiPredicate<Integer, Integer> skip) {
		if (skip.test(x, z)) {
			return false;
		}
		LevelChunk chunk = level.getChunk(x >> 4, z >> 4);
		int surf = chunk.getHeight(Heightmap.Types.MOTION_BLOCKING_NO_LEAVES, x & 15, z & 15) + 1;
		BlockPos.MutableBlockPos pos = new BlockPos.MutableBlockPos();
		BlockState top = level.getBlockState(pos.set(x, surf - 1, z));
		if (!top.isFaceSturdy(level, pos, Direction.UP) || !top.getFluidState().isEmpty() || !free(level, pos, x, surf, z)
				|| inside(boxes(level, chunk), x, surf, z)) {
			return false;
		}
		RoadFeature.Wood w = RoadFeature.wood(level.getBiome(pos.set(x, surf, z)));
		BlockPos at = new BlockPos(x, surf, z);
		level.setBlock(at, w.signpost().setValue(StandingSignBlock.ROTATION, Math.floorMod(rotation, 16)), Block.UPDATE_ALL);
		if (level.getBlockEntity(at) instanceof SignBlockEntity s) {
			List<Component> lines = List.of(first, second, Component.empty(), Component.empty());
			s.setText(new SignText(lines, lines, DyeColor.BLACK, false), SignTextSlot.FRONT);
			s.setWaxed(true);
			s.setChanged();
		}
		return true;
	}

	/** The sign rotation (0-15) of a sign whose text faces the direction (fx, fz), as {@link RoadLayout#marks} computes it. */
	public static int rotation(double fx, double fz) {
		return Math.floorMod((int) Math.round(Math.toDegrees(Math.atan2(-fx, fz)) / 22.5), 16);
	}
}
