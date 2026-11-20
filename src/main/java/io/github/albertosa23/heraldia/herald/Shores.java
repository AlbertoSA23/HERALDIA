package io.github.albertosa23.heraldia.herald;

import io.github.albertosa23.heraldia.roads.BuiltRoads;
import io.github.albertosa23.heraldia.roads.RoadProfile;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.function.BiPredicate;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.FallingBlock;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.chunk.LevelChunk;
import net.minecraft.world.level.levelgen.Heightmap;

/**
 * No still water standing in the air where the Herald's House was built (its footprint, its margin and its grounds).
 * Water placed by world generation has no fluid tick: when the ground that held a pond is cut away (the town's margin
 * blended down, the grounds levelled, a lake that the town's template cut in two), its water stays where it was, a wall
 * of it with nothing beside it, for good. Building and Outskirts look at every column they shaped once they are done
 * (a step per chunk) and settle any such water as a real one would have:
 * <ul>
 * <li>a pond small enough ({@link #POND} blocks at most, all of it in loaded chunks) drains: its water down to the lowest
 * place where it touched the air goes, as it would have run out; what lies lower stays, held by the ground round it;</li>
 * <li>a bigger body (a lake, a river, the sea) is contained instead: each of its blocks with air beside or under it
 * becomes ground (a bank: the fill of the ground under the water, with its surface on top), so the rest stays held.</li>
 * </ul>
 * Only still water counts (a source block: flowing water has, or had, its tick and runs on its own), from the column's
 * top down (a cave's water underground is left alone), never a waterlogged block. Loaded chunks only: what lies in one
 * that is not loaded counts as holding the water. In the town's own footprint, water its template does not have (a pond
 * or a lake beside it that ran in when the template's edge was placed) goes first ({@link #clear}).
 */
final class Shores {
	/** The most blocks a pond may have to be drained; a bigger body of water is banked instead. */
	static final int POND = 4096;
	/** How deep a column's water is looked at from its top. */
	static final int DEPTH = 64;
	private static final Direction[] AROUND = {Direction.NORTH, Direction.SOUTH, Direction.EAST, Direction.WEST, Direction.DOWN};

	/** What was settled: ponds drained (and their blocks), water blocks banked. */
	record Settled(int ponds, int drained, int banked) {
		Settled plus(Settled o) {
			return new Settled(ponds + o.ponds, drained + o.drained, banked + o.banked);
		}
	}

	static final Settled NONE = new Settled(0, 0, 0);

	private Shores() {
	}

	/** Is the block water, not a waterlogged one? */
	static boolean water(BlockState s) {
		return s.is(Blocks.WATER);
	}

	/** Still water: a source block. */
	static boolean still(BlockState s) {
		return s.is(Blocks.WATER) && s.getFluidState().isSource();
	}

	/** The water of one chunk's columns ({@code in}) that is not the template's ({@code own}): removed. Returns how many blocks. */
	static int clear(ServerLevel level, LevelChunk chunk, BiPredicate<Integer, Integer> in, Set<BlockPos> own, int minY, int maxY) {
		var cp = chunk.getPos();
		BlockPos.MutableBlockPos pos = new BlockPos.MutableBlockPos();
		int out = 0;
		for (int lx = 0; lx < 16; lx++) {
			for (int lz = 0; lz < 16; lz++) {
				int x = cp.getMinBlockX() + lx, z = cp.getMinBlockZ() + lz;
				if (!in.test(x, z)) {
					continue;
				}
				for (int y = minY; y <= maxY; y++) {
					if (water(chunk.getBlockState(pos.set(x, y, z))) && !own.contains(pos)) {
						level.setBlock(pos, Blocks.AIR.defaultBlockState(), BuiltRoads.FLAGS);
						out++;
					}
				}
			}
		}
		return out;
	}

	/** Would water beside it run into it (air, or a plant or snow it would wash away)? Unloaded: no. */
	private static boolean open(ServerLevel level, BlockPos p) {
		LevelChunk c = level.getChunkSource().getChunkNow(p.getX() >> 4, p.getZ() >> 4);
		if (c == null) {
			return false;
		}
		BlockState s = c.getBlockState(p);
		return s.isAir() || s.getFluidState().isEmpty() && s.canBeReplaced();
	}

	/** A water block with air (or something it would wash away) beside it or under it: it would run if it had a tick. */
	static boolean standing(ServerLevel level, BlockPos p, BlockPos.MutableBlockPos q) {
		for (Direction d : AROUND) {
			if (open(level, q.setWithOffset(p, d))) {
				return true;
			}
		}
		return false;
	}

	/** The water blocks of one chunk's columns ({@code in}) that stand in the air: from each column's top down. */
	static List<BlockPos> standing(ServerLevel level, LevelChunk chunk, BiPredicate<Integer, Integer> in) {
		List<BlockPos> out = new ArrayList<>();
		var cp = chunk.getPos();
		BlockPos.MutableBlockPos pos = new BlockPos.MutableBlockPos(), q = new BlockPos.MutableBlockPos();
		for (int lx = 0; lx < 16; lx++) {
			for (int lz = 0; lz < 16; lz++) {
				int x = cp.getMinBlockX() + lx, z = cp.getMinBlockZ() + lz;
				if (!in.test(x, z)) {
					continue;
				}
				int top = chunk.getHeight(Heightmap.Types.WORLD_SURFACE, lx, lz);
				for (int y = top; y > top - DEPTH && y > level.getMinY() && water(chunk.getBlockState(pos.set(x, y, z))); y--) {
					if (still(chunk.getBlockState(pos)) && standing(level, pos, q)) {
						out.add(pos.immutable());
					}
				}
			}
		}
		return out;
	}

	/** Settles the standing water of one chunk's columns ({@code in}): small ponds drained, the rest banked. */
	static Settled settle(ServerLevel level, LevelChunk chunk, BiPredicate<Integer, Integer> in) {
		List<BlockPos> found = standing(level, chunk, in);
		if (found.isEmpty()) {
			return NONE;
		}
		Settled out = NONE;
		BlockPos.MutableBlockPos q = new BlockPos.MutableBlockPos();
		for (BlockPos p : found) {
			if (!water(level.getBlockState(p)) || !standing(level, p, q)) {
				continue;                          // drained with an earlier block's pond, or no longer open
			}
			Set<BlockPos> pond = pond(level, p);
			if (pond != null) {
				out = out.plus(drain(level, pond));
			} else {
				out = out.plus(new Settled(0, 0, bank(level, p) ? 1 : 0));
			}
		}
		return out;
	}

	/** The body of water the block belongs to (6-connected), or null if it has more than {@link #POND} blocks or reaches an unloaded chunk. */
	static @org.jspecify.annotations.Nullable Set<BlockPos> pond(ServerLevel level, BlockPos start) {
		Set<BlockPos> seen = new HashSet<>();
		ArrayDeque<BlockPos> todo = new ArrayDeque<>();
		seen.add(start);
		todo.add(start);
		while (!todo.isEmpty()) {
			BlockPos p = todo.poll();
			for (Direction d : Direction.values()) {
				BlockPos o = p.relative(d);
				if (seen.contains(o)) {
					continue;
				}
				LevelChunk c = level.getChunkSource().getChunkNow(o.getX() >> 4, o.getZ() >> 4);
				if (c == null) {
					return null;
				}
				if (water(c.getBlockState(o))) {
					if (seen.size() >= POND) {
						return null;
					}
					seen.add(o);
					todo.add(o);
				}
			}
		}
		return seen;
	}

	/**
	 * Drains a pond as it would have run out: while any of its blocks stands in the air, every block of it as high as
	 * the lowest of those, or higher, goes; what is lower stays, held by the ground.
	 */
	static Settled drain(ServerLevel level, Set<BlockPos> pond) {
		BlockPos.MutableBlockPos q = new BlockPos.MutableBlockPos();
		Set<BlockPos> left = new HashSet<>(pond);
		int drained = 0;
		while (!left.isEmpty()) {
			int lowest = Integer.MAX_VALUE;
			for (BlockPos p : left) {
				if (p.getY() < lowest && still(level.getBlockState(p)) && standing(level, p, q)) {
					lowest = p.getY();
				}
			}
			if (lowest == Integer.MAX_VALUE) {
				break;
			}
			List<BlockPos> gone = new ArrayList<>();
			for (BlockPos p : left) {
				if (p.getY() >= lowest) {
					gone.add(p);
				}
			}
			for (BlockPos p : gone) {
				level.setBlock(p, Blocks.AIR.defaultBlockState(), BuiltRoads.FLAGS);
				left.remove(p);
				drained++;
			}
		}
		return new Settled(1, drained, 0);
	}

	/** A water block made into its bank: the fill of the ground under its water (its surface, if open to the sky). */
	static boolean bank(ServerLevel level, BlockPos p) {
		BlockPos.MutableBlockPos q = new BlockPos.MutableBlockPos().set(p);
		BlockState bed = Blocks.DIRT.defaultBlockState();
		for (int k = 0; k < DEPTH && q.getY() > level.getMinY(); k++) {
			BlockState s = level.getBlockState(q.move(Direction.DOWN));
			if (!water(s)) {
				bed = s;
				break;
			}
		}
		RoadProfile.Ground kind = BuiltRoads.kind(bed);
		BlockState fill = kind == null ? Blocks.DIRT.defaultBlockState() : BuiltRoads.fill(kind);
		BlockState s = fill;
		if (level.getBlockState(p.above()).isAir()) {
			BlockState top = kind == RoadProfile.Ground.DIRT ? Blocks.GRASS_BLOCK.defaultBlockState() : bed;
			s = top.getBlock() instanceof FallingBlock || kind == null ? fill : top;
		}
		level.setBlock(p, s, BuiltRoads.FLAGS);
		return true;
	}
}
