package io.github.albertosa23.heraldia.roads;

import io.github.albertosa23.heraldia.common.ForeignZone;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.function.BiPredicate;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.tags.BlockTags;
import net.minecraft.tags.FluidTags;
import net.minecraft.world.item.DyeColor;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.LeavesBlock;
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
import org.jspecify.annotations.Nullable;

/**
 * Roads BUILT in a chunk that already exists (the Herald's House roads, herald/SpawnRoads): the columns of
 * {@link RoadLayout#paint} (with a whole edge), the plank bridges and walkways over water ({@link RoadLayout.Route#water}) and
 * the biome woods ({@link RoadFeature#wood}) of the roads between villages, but laid as one work: each road keeps a height
 * and a kind of ground along it ({@link RoadProfile}), its paving is one material with a kerb ({@link #deck}), the ground
 * is cut or filled to it, the air over it is cleared and the trees standing on it are felled whole. Nothing that is not
 * natural terrain or growth is ever touched (a player's block, a structure's piece: those columns are left as they are),
 * and nothing in a chunk that is not loaded is read or written. {@link #audit} looks at the result as it stands.
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

	/** What may be cleared over a bridge's deck or a lamp's post (plants, snow, leaves): nothing a player builds. */
	static boolean clearable(BlockState s) {
		return s.isAir() || (s.canBeReplaced() && s.getFluidState().isEmpty()) || s.is(BlockTags.LEAVES) || s.is(Blocks.SNOW);
	}

	/** Air over the paving (a tall player and a little more): nothing natural is left there. */
	static final int HEAD = 4;
	/** Air over the shoulder (the lamp posts stand on it). */
	static final int SHOULDER_HEAD = 3;
	/** At most this many blocks of ground cut away, or filled in, under the road to keep it level. */
	static final int CUT = 6, FILL = 6;
	/** A tree larger than this (logs) is not a tree: left as it is. */
	static final int MAX_LOGS = 320;
	/** Leaves looked at around a felled tree, at most (and at most {@link LeavesBlock#DECAY_DISTANCE} blocks from it). */
	static final int MAX_LEAVES = 12000;

	/** Natural growth over the ground, cleared from the road: trees (logs, leaves), plants, mushrooms, snow. */
	static boolean growth(BlockState s) {
		if (s.is(BlockTags.LEAVES) || s.is(Blocks.MANGROVE_ROOTS)) {
			return true;                            // waterlogged too (mangroves)
		}
		if (!s.getFluidState().isEmpty()) {
			return false;
		}
		return s.canBeReplaced() || s.is(BlockTags.LOGS) || s.is(BlockTags.FLOWERS) || s.is(BlockTags.SAPLINGS) || s.is(Blocks.SNOW)
				|| s.is(Blocks.BROWN_MUSHROOM_BLOCK) || s.is(Blocks.RED_MUSHROOM_BLOCK) || s.is(Blocks.MUSHROOM_STEM)
				|| s.is(Blocks.BAMBOO) || s.is(Blocks.BAMBOO_SAPLING) || s.is(Blocks.CACTUS) || s.is(Blocks.CACTUS_FLOWER)
				|| s.is(Blocks.SUGAR_CANE) || s.is(Blocks.SWEET_BERRY_BUSH) || s.is(Blocks.BEE_NEST) || s.is(Blocks.COCOA)
				|| s.is(Blocks.PUMPKIN) || s.is(Blocks.MELON) || s.is(Blocks.MOSS_CARPET) || s.is(Blocks.PALE_MOSS_CARPET)
				|| s.is(Blocks.PALE_HANGING_MOSS) || s.is(Blocks.CREAKING_HEART) || s.is(Blocks.BUSH) || s.is(Blocks.FIREFLY_BUSH)
				|| s.is(Blocks.LEAF_LITTER) || s.is(Blocks.SHORT_DRY_GRASS) || s.is(Blocks.AZALEA) || s.is(Blocks.FLOWERING_AZALEA)
				|| s.is(Blocks.BIG_DRIPLEAF) || s.is(Blocks.GLOW_LICHEN) || s.is(Blocks.BROWN_MUSHROOM) || s.is(Blocks.RED_MUSHROOM);
	}

	/** The kind of natural ground a block is (the paving of a built road counts as its own kind), or null. */
	public static RoadProfile.@Nullable Ground kind(BlockState s) {
		if (s.is(Blocks.MUD) || s.is(Blocks.MUDDY_MANGROVE_ROOTS) || s.is(Blocks.PACKED_MUD) || s.is(Blocks.MUD_BRICKS)) {
			return RoadProfile.Ground.MUD;
		}
		if (s.is(Blocks.DIRT_PATH) || s.is(Blocks.FARMLAND) || s.is(BlockTags.DIRT) || s.is(Blocks.GRASS_BLOCK) || s.is(Blocks.PODZOL)
				|| s.is(Blocks.MYCELIUM) || s.is(Blocks.MOSS_BLOCK) || s.is(Blocks.PALE_MOSS_BLOCK) || s.is(Blocks.COARSE_DIRT)
				|| s.is(Blocks.ROOTED_DIRT) || s.is(Blocks.DIRT)) {
			return RoadProfile.Ground.DIRT;
		}
		if (s.is(Blocks.RED_SAND) || s.is(Blocks.TERRACOTTA) || s.is(BlockTags.TERRACOTTA) || s.is(Blocks.RED_SANDSTONE)
				|| s.is(Blocks.SMOOTH_RED_SANDSTONE) || s.is(Blocks.CUT_RED_SANDSTONE)) {
			return RoadProfile.Ground.RED;
		}
		if (s.is(Blocks.SAND) || s.is(BlockTags.SAND) || s.is(Blocks.SANDSTONE) || s.is(Blocks.SMOOTH_SANDSTONE) || s.is(Blocks.CUT_SANDSTONE)) {
			return RoadProfile.Ground.SAND;
		}
		if (RoadFeature.ground(s, 0.5, true) != null || s.is(Blocks.COBBLESTONE) || s.is(Blocks.STONE_BRICKS)) {
			return RoadProfile.Ground.STONE;
		}
		return null;
	}

	/** Ground that may be cut away under a road: natural terrain and the ores near the surface. */
	static boolean terrain(BlockState s) {
		return kind(s) != null || s.is(BlockTags.IRON_ORES) || s.is(BlockTags.COPPER_ORES) || s.is(Blocks.COAL_ORE)
				|| s.is(Blocks.DEEPSLATE) || s.is(Blocks.SNOW_BLOCK) || s.is(Blocks.ICE) || s.is(Blocks.PACKED_ICE);
	}

	/**
	 * A built road's paving: one material for its whole width, and a kerb on its two edges (the outermost column of each
	 * side): a dirt path with coarse dirt edges, smooth sandstone with cut sandstone (red on red sand and terracotta),
	 * gravel with cobblestone on stone and snow, packed mud with mud bricks.
	 */
	public static BlockState deck(RoadProfile.Ground g, boolean edge) {
		return (switch (g) {
			case MUD -> edge ? Blocks.MUD_BRICKS : Blocks.PACKED_MUD;
			case DIRT -> edge ? Blocks.COARSE_DIRT : Blocks.DIRT_PATH;
			case RED -> edge ? Blocks.CUT_RED_SANDSTONE : Blocks.SMOOTH_RED_SANDSTONE;
			case SAND -> edge ? Blocks.CUT_SANDSTONE : Blocks.SMOOTH_SANDSTONE;
			case STONE -> edge ? Blocks.COBBLESTONE : Blocks.GRAVEL;
		}).defaultBlockState();
	}

	/** What fills the ground under a road (or a shoulder) raised over a dip. */
	static BlockState fill(RoadProfile.Ground g) {
		return (switch (g) {
			case MUD -> Blocks.PACKED_MUD;
			case DIRT -> Blocks.DIRT;
			case RED -> Blocks.RED_SANDSTONE;
			case SAND -> Blocks.SANDSTONE;
			case STONE -> Blocks.COBBLESTONE;
		}).defaultBlockState();
	}

	/** Every block a built road's paving may be (its land columns): what the server test checks. */
	public static boolean paving(BlockState s) {
		for (RoadProfile.Ground g : RoadProfile.Ground.values()) {
			if (s.is(deck(g, false).getBlock()) || s.is(deck(g, true).getBlock())) {
				return true;
			}
		}
		return false;
	}

	/**
	 * Blocks read in loaded chunks only: a built road never loads (or generates) a chunk to look beyond the one it paves.
	 * Null where the chunk is not loaded.
	 */
	static final class Loaded {
		private final ServerLevel level;
		private @Nullable LevelChunk last;
		private int lx = Integer.MIN_VALUE, lz = Integer.MIN_VALUE;
		private final BlockPos.MutableBlockPos pos = new BlockPos.MutableBlockPos();

		Loaded(ServerLevel level) {
			this.level = level;
		}

		@Nullable LevelChunk chunk(int x, int z) {
			if (x >> 4 != lx || z >> 4 != lz) {
				lx = x >> 4;
				lz = z >> 4;
				last = level.getChunkSource().getChunkNow(lx, lz);
			}
			return last;
		}

		@Nullable BlockState get(int x, int y, int z) {
			LevelChunk c = chunk(x, z);
			return c == null ? null : c.getBlockState(pos.set(x, y, z));
		}

		/** The natural ground's height (under any tree or plant) at a column of a loaded chunk. */
		int ground(LevelChunk c, int x, int z) {
			int y = c.getHeight(Heightmap.Types.MOTION_BLOCKING_NO_LEAVES, x & 15, z & 15);
			while (y > level.getMinY() && growth(c.getBlockState(pos.set(x, y, z)))) {
				y--;
			}
			return y;
		}

		/** The profile's sample at a column: its natural ground, or null if the chunk is not loaded. */
		RoadProfile.@Nullable Sample sample(int x, int z) {
			LevelChunk c = chunk(x, z);
			if (c == null) {
				return null;
			}
			int y = ground(c, x, z);
			BlockState s = c.getBlockState(pos.set(x, y, z));
			return new RoadProfile.Sample(s.getFluidState().isEmpty() ? kind(s) : null, y);
		}
	}

	/** What the painted chunk did: columns paved, bridged, left (not natural ground, a structure, the arena...), trees felled. */
	public record Painted(int paved, int bridged, int left, int trees) {
	}

	/**
	 * Paves the road columns of {@code routes} in this chunk, at the height and with the paving of each route's
	 * {@code profiles} (one per route), and tidies the one-block shoulder on each side. {@code skip}: columns never to
	 * touch (the town's footprint, the arena's box). {@code seabed}: the terrain's bottom height (noise: the vertices may
	 * lie in chunks not loaded). Returns the cells painted (x * 16 + z, null = no road) with the counts.
	 * <ul>
	 * <li>Land: the ground is cut or filled (at most {@link #CUT} / {@link #FILL} blocks) to the profile's height, the
	 * paving laid, and {@link #HEAD} blocks of air left over it: every trunk, leaf, plant or bump of ground in that space
	 * goes. A tree that stood on the road, or had a log in its air or on its shoulder, is felled whole: its logs and then
	 * the leaves no other tree holds.</li>
	 * <li>The shoulder (one block beyond each edge): its ground cut or filled to one block from the road at most, keeping
	 * its own surface (grass, sand...), and trees and leaves cleared up to {@link #SHOULDER_HEAD} blocks over it; its
	 * flowers and grass stay where its ground was not touched.</li>
	 * <li>Water: the plank bridges and walkways ({@link RoadLayout.Route#water}), as before.</li>
	 * </ul>
	 * Anything that is not natural (a player's block, a structure's piece) is never touched: its column is left.
	 */
	public static Painted pave(ServerLevel level, LevelChunk chunk, RoadLayout layout, List<RoadLayout.Route> routes,
			Map<RoadLayout.Route, RoadProfile> profiles, int width, RoadLayout.Seabed seabed, BiPredicate<Integer, Integer> skip,
			RoadLayout.Cell[] cells) {
		var cp = chunk.getPos();
		double half = Math.max(width / 2.0, RoadLayout.CORE);
		RoadLayout.Cell[] c = layout.paint(routes, cp.x(), cp.z(), width + 2, false);
		List<BoundingBox> boxes = boxes(level, chunk);
		Loaded loaded = new Loaded(level);
		RoadProfile.Sampler sampler = loaded::sample;
		List<BlockPos> felled = new ArrayList<>();
		BlockPos.MutableBlockPos pos = new BlockPos.MutableBlockPos();
		int paved = 0, bridged = 0, left = 0, sea = level.getSeaLevel();
		Arrays.fill(cells, null);
		for (int pass = 0; pass < 2; pass++) {    // the road first, then its shoulders (which look at the road's height)
			for (int i = 0; i < 256; i++) {
				RoadLayout.Cell cell = c[i];
				if (cell == null || (cell.dist() <= half) != (pass == 0)) {
					continue;
				}
				int x = cp.getMinBlockX() + i / 16, z = cp.getMinBlockZ() + i % 16;
				RoadProfile profile = profiles.get(cell.route());
				if (pass == 1) {
					if (profile != null && !skip.test(x, z)) {
						shoulder(level, chunk, loaded, profile, sampler, cell, x, z, boxes, felled, pos);
					}
					continue;
				}
				int r = column(level, chunk, loaded, profile, sampler, cell, x, z, cell.dist() > half - 0.75, width, seabed, sea,
						boxes, skip, felled, pos);
				if (r == 1) {
					paved++;
					cells[i] = cell;
				} else if (r == 2) {
					bridged++;
					cells[i] = cell;
				} else {
					left++;
				}
			}
		}
		int trees = fell(level, loaded, felled, skip, boxes);
		return new Painted(paved, bridged, left, trees);
	}

	/** One road column: 1 paved, 2 bridge or walkway, 0 left as it is. */
	private static int column(ServerLevel level, LevelChunk chunk, Loaded loaded, @Nullable RoadProfile profile,
			RoadProfile.Sampler sampler, RoadLayout.Cell c, int x, int z, boolean edge, int width, RoadLayout.Seabed seabed, int sea,
			List<BoundingBox> boxes, BiPredicate<Integer, Integer> skip, List<BlockPos> felled, BlockPos.MutableBlockPos pos) {
		if (skip.test(x, z)) {
			return 0;
		}
		int post = chunk.getHeight(Heightmap.Types.MOTION_BLOCKING_NO_LEAVES, x & 15, z & 15);
		if (lampPost(chunk, x, post, z, pos) && !inside(boxes, x, post, z)) {
			for (int y = post; y > post - 3; y--) {   // an earlier road's lamp post on this one (the arena road, built later)
				level.setBlock(pos.set(x, y, z), Blocks.AIR.defaultBlockState(), FLAGS);
			}
		}
		int g = loaded.ground(chunk, x, z);
		BlockState ground = chunk.getBlockState(pos.set(x, g, z));
		if (inside(boxes, x, g, z) || inside(boxes, x, g + 1, z)) {
			return 0;
		}
		if (!ground.getFluidState().isEmpty()) {
			return water(level, chunk, c, x, g, z, width, seabed, sea, felled, pos);
		}
		RoadProfile.Ground kind = kind(ground);
		if (kind == null) {
			return 0;                              // not natural ground (a player's block): left alone
		}
		int t = profile == null ? RoadProfile.MISSING : profile.height(c.arc(), sampler);
		t = t == RoadProfile.MISSING ? g : Math.clamp(t, g - CUT, g + FILL);
		RoadProfile.Ground k = profile == null ? null : profile.ground(c.arc(), sampler);
		if (k == null) {
			k = kind;
		}
		int top = Math.max(t + HEAD, g);
		for (int y = t + 1; y <= top; y++) {     // everything to clear must be natural (or an earlier road's sign)
			BlockState s = chunk.getBlockState(pos.set(x, y, z));
			if (!s.isAir() && (!growth(s) && !terrain(s) && !ourSign(chunk, s, pos) || inside(boxes, x, y, z))) {
				return 0;
			}
		}
		BlockState fill = fill(k);
		for (int y = t - 1; y >= t - FILL; y--) { // the dip filled, down to firm ground
			BlockState s = chunk.getBlockState(pos.set(x, y, z));
			if (!(s.isAir() || growth(s) || !s.getFluidState().isEmpty()) || inside(boxes, x, y, z)) {
				break;
			}
			level.setBlock(pos, fill, FLAGS);
		}
		level.setBlock(pos.set(x, t, z), deck(k, edge), FLAGS);
		clear(level, chunk, x, t + 1, top, z, felled, pos);
		return 1;
	}

	/** A lamp post of these roads with its lantern at y: a lantern on two fence posts of a wood, on the ground. */
	static boolean lampPost(LevelChunk chunk, int x, int y, int z, BlockPos.MutableBlockPos pos) {
		return chunk.getBlockState(pos.set(x, y, z)).is(Blocks.LANTERN) && chunk.getBlockState(pos.set(x, y - 1, z)).is(BlockTags.WOODEN_FENCES)
				&& chunk.getBlockState(pos.set(x, y - 2, z)).is(BlockTags.WOODEN_FENCES)
				&& !chunk.getBlockState(pos.set(x, y - 3, z)).is(BlockTags.WOODEN_FENCES);
	}

	/** A sign of these roads (a standing sign, waxed: {@link #sign}) at pos. */
	static boolean ourSign(LevelChunk chunk, BlockState s, BlockPos pos) {
		return s.is(BlockTags.STANDING_SIGNS) && chunk.getBlockEntity(pos) instanceof SignBlockEntity e && e.isWaxed();
	}

	/**
	 * Fells the trees whose logs were just removed at {@code felled} (by a hut's site, say), as a road does: the rest of
	 * their logs and the leaves no other log holds. Loaded chunks only. Returns the trees felled.
	 */
	public static int fell(ServerLevel level, List<BlockPos> felled, BiPredicate<Integer, Integer> skip) {
		return felled.isEmpty() ? 0 : fell(level, new Loaded(level), felled, skip, List.of());
	}

	/** Clears from y0 to y1 (natural blocks: checked), and then any growth standing on what was cleared (not leaves). */
	private static void clear(ServerLevel level, LevelChunk chunk, int x, int y0, int y1, int z, List<BlockPos> felled,
			BlockPos.MutableBlockPos pos) {
		for (int y = y0; y <= y1 + 32; y++) {
			BlockState s = chunk.getBlockState(pos.set(x, y, z));
			if (s.isAir() || y > y1 && (!growth(s) || s.is(BlockTags.LEAVES) || !s.getFluidState().isEmpty())) {
				if (y > y1) {
					break;
				}
				continue;
			}
			if (s.is(BlockTags.LOGS)) {
				felled.add(pos.immutable());
			}
			level.setBlock(pos, Blocks.AIR.defaultBlockState(), FLAGS);
		}
	}

	/** A road column over water (its surface at y): a plank bridge or walkway, or nothing (as {@link RoadFeature} does). */
	private static int water(ServerLevel level, LevelChunk chunk, RoadLayout.Cell c, int x, int y, int z, int width,
			RoadLayout.Seabed seabed, int sea, List<BlockPos> felled, BlockPos.MutableBlockPos pos) {
		BlockState top = chunk.getBlockState(pos.set(x, y, z));
		if (!top.is(Blocks.WATER) || !top.getFluidState().is(FluidTags.WATER)) {
			return 0;                              // lava, or something that is not loose water
		}
		int surf = y + 1, floor = y;
		while (floor > level.getMinY() && !chunk.getBlockState(pos.set(x, floor - 1, z)).getFluidState().isEmpty()) {
			floor--;
		}
		int depth = surf - floor;
		RoadLayout.Water water = c.route().water(c.vertex(), seabed, sea);
		RoadFeature.Wood w = RoadFeature.wood(level.getBiome(pos.set(x, surf, z)));
		boolean bridge = water == RoadLayout.Water.BRIDGE && surf == sea;
		boolean walkway = water == RoadLayout.Water.WALKWAY && surf == sea && depth <= RoadLayout.WALKWAY_DEPTH
				|| water == RoadLayout.Water.LAND && depth <= 3;
		if (!bridge && !walkway) {
			return 0;                              // a long, deep stretch: cut
		}
		int deck = bridge ? surf : y;
		for (int yy = deck + 1; yy <= deck + HEAD; yy++) {
			BlockState s = chunk.getBlockState(pos.set(x, yy, z));
			if (!s.isAir() && !growth(s)) {
				return 0;
			}
		}
		if (bridge && !growth(chunk.getBlockState(pos.set(x, surf, z))) && !chunk.getBlockState(pos).isAir()) {
			return 0;
		}
		level.setBlock(pos.set(x, deck, z), w.planks(), FLAGS);
		clear(level, chunk, x, deck + 1, deck + HEAD, z, felled, pos);
		if (bridge && c.dist() > width / 2.0 - 1 && Math.floorMod((int) c.arc(), 5) == 0) {
			BlockState post = w.fence().setValue(BlockStateProperties.WATERLOGGED, true);   // a post down to the bottom
			for (int yy = surf - 1; yy >= floor; yy--) {
				if (!chunk.getBlockState(pos.set(x, yy, z)).is(Blocks.WATER)) {
					break;
				}
				level.setBlock(pos, post, FLAGS);
			}
		}
		return 2;
	}

	/** A shoulder column: its ground within one block of the road's, trees and leaves cleared over it. */
	private static void shoulder(ServerLevel level, LevelChunk chunk, Loaded loaded, RoadProfile profile, RoadProfile.Sampler sampler,
			RoadLayout.Cell c, int x, int z, List<BoundingBox> boxes, List<BlockPos> felled, BlockPos.MutableBlockPos pos) {
		int g = loaded.ground(chunk, x, z);
		BlockState ground = chunk.getBlockState(pos.set(x, g, z));
		RoadProfile.Ground kind = kind(ground);
		int t = profile.height(c.arc(), sampler);
		if (kind == null || !ground.getFluidState().isEmpty() || t == RoadProfile.MISSING || inside(boxes, x, g + 1, z)) {
			return;
		}
		int s = Math.max(t + Math.clamp(g - t, -1, 1), g - CUT + 1);
		s = Math.min(s, g + FILL - 1);
		int top = Math.max(s + SHOULDER_HEAD, g);
		for (int y = Math.min(s, g) + 1; y <= top; y++) {
			BlockState b = chunk.getBlockState(pos.set(x, y, z));
			if (!b.isAir() && (!growth(b) && !terrain(b) || inside(boxes, x, y, z))) {
				return;                            // a player's block, a sign, a lamp: left alone
			}
		}
		if (s != g) {
			BlockState surface = ground.is(Blocks.DIRT_PATH) || ground.is(Blocks.FARMLAND) || ground.is(Blocks.DIRT)
					? Blocks.GRASS_BLOCK.defaultBlockState() : ground;
			BlockState fill = fill(kind);
			for (int y = g; y < s; y++) {
				level.setBlock(pos.set(x, y, z), fill, FLAGS);
			}
			level.setBlock(pos.set(x, s, z), surface, FLAGS);
			clear(level, chunk, x, s + 1, top, z, felled, pos);
			return;
		}
		for (int y = s + 1; y <= s + SHOULDER_HEAD; y++) {   // untouched ground: only trees go, its flowers stay
			BlockState b = chunk.getBlockState(pos.set(x, y, z));
			if (b.is(BlockTags.LOGS) || b.is(BlockTags.LEAVES)) {
				clear(level, chunk, x, y, y, z, felled, pos);
			}
		}
	}

	/**
	 * Fells the trees whose logs were cleared at {@code felled}: the logs joined to them (a tree: at most
	 * {@link #MAX_LOGS} and with natural leaves on it, else they stay), then the leaves that no log holds any more (as their
	 * decay would, at once, so none is left hanging), in loaded chunks only. Returns the trees felled.
	 */
	static int fell(ServerLevel level, Loaded loaded, List<BlockPos> felled, BiPredicate<Integer, Integer> skip, List<BoundingBox> boxes) {
		Set<Long> removed = new HashSet<>();
		for (BlockPos p : felled) {
			removed.add(p.asLong());
		}
		int trees = 0;
		Set<Long> done = new HashSet<>();
		for (BlockPos seed : felled) {
			if (!done.add(seed.asLong())) {
				continue;
			}
			Set<Long> logs = new HashSet<>();
			ArrayDeque<Long> queue = new ArrayDeque<>();
			queue.add(seed.asLong());
			boolean natural = false, large = false;
			while (!queue.isEmpty()) {
				long at = queue.poll();
				int ax = BlockPos.getX(at), ay = BlockPos.getY(at), az = BlockPos.getZ(at);
				for (int dx = -1; dx <= 1; dx++) {
					for (int dy = -1; dy <= 1; dy++) {
						for (int dz = -1; dz <= 1; dz++) {
							int x = ax + dx, y = ay + dy, z = az + dz;
							long key = BlockPos.asLong(x, y, z);
							if (logs.contains(key) || removed.contains(key) || done.contains(key)) {
								continue;
							}
							BlockState s = loaded.get(x, y, z);
							if (s == null) {
								continue;
							}
							if (s.is(BlockTags.LEAVES) && Math.abs(dx) + Math.abs(dy) + Math.abs(dz) == 1
									&& !s.getValue(LeavesBlock.PERSISTENT)) {
								natural = true;
							}
							if (s.is(BlockTags.LOGS) && !skip.test(x, z) && !inside(boxes, x, y, z)) {
								logs.add(key);
								queue.add(key);
								if (logs.size() > MAX_LOGS) {
									large = true;
									queue.clear();
								}
							}
						}
					}
				}
			}
			done.addAll(logs);
			if (large || !natural && !logs.isEmpty()) {
				continue;                          // too large, or no natural leaves on it: not a tree
			}
			BlockPos.MutableBlockPos pos = new BlockPos.MutableBlockPos();
			for (long l : logs) {
				level.setBlock(pos.set(l), Blocks.AIR.defaultBlockState(), FLAGS);
				removed.add(l);
			}
			trees++;
		}
		if (trees > 0 || !removed.isEmpty()) {
			leaves(level, loaded, removed, skip, boxes);
		}
		return trees;
	}

	private static final int[][] FACES = {{1, 0, 0}, {-1, 0, 0}, {0, 1, 0}, {0, -1, 0}, {0, 0, 1}, {0, 0, -1}};

	/**
	 * The leaves within {@link LeavesBlock#DECAY_DISTANCE} of the removed logs: their distance to a log worked out again
	 * (as vanilla's leaves do, through the leaves); those no log holds any more go, the rest keep their new distance.
	 */
	private static void leaves(ServerLevel level, Loaded loaded, Set<Long> removed, BiPredicate<Integer, Integer> skip,
			List<BoundingBox> boxes) {
		Map<Long, Integer> near = new HashMap<>();     // leaves near the removed logs -> steps from them
		ArrayDeque<Long> queue = new ArrayDeque<>(removed);
		for (long r : removed) {
			near.put(r, 0);
		}
		while (!queue.isEmpty() && near.size() < MAX_LEAVES) {
			long at = queue.poll();
			int d = near.get(at);
			if (d >= LeavesBlock.DECAY_DISTANCE) {
				continue;
			}
			for (int[] f : FACES) {
				long key = BlockPos.offset(at, f[0], f[1], f[2]);
				if (near.containsKey(key)) {
					continue;
				}
				int x = BlockPos.getX(key), y = BlockPos.getY(key), z = BlockPos.getZ(key);
				BlockState s = loaded.get(x, y, z);
				if (s != null && s.is(BlockTags.LEAVES) && !s.getValue(LeavesBlock.PERSISTENT) && !skip.test(x, z) && !inside(boxes, x, y, z)) {
					near.put(key, d + 1);
					queue.add(key);
				}
			}
		}
		for (long r : removed) {
			near.remove(r);
		}
		// the distance of each one to a log, through the leaves: from the logs and the leaves around that are not looked at
		Map<Long, Integer> dist = new HashMap<>();
		ArrayDeque<Long> wave = new ArrayDeque<>();
		for (long key : near.keySet()) {
			int best = LeavesBlock.DECAY_DISTANCE;
			for (int[] f : FACES) {
				long n = BlockPos.offset(key, f[0], f[1], f[2]);
				if (near.containsKey(n) || removed.contains(n)) {
					continue;
				}
				BlockState s = loaded.get(BlockPos.getX(n), BlockPos.getY(n), BlockPos.getZ(n));
				if (s == null || s.is(BlockTags.LOGS)) {
					best = 1;                      // a log (or a chunk not loaded: kept, to be safe)
				} else if (s.hasProperty(LeavesBlock.DISTANCE)) {
					best = Math.min(best, s.getValue(LeavesBlock.DISTANCE) + 1);
				}
			}
			dist.put(key, best);
			if (best < LeavesBlock.DECAY_DISTANCE) {
				wave.add(key);
			}
		}
		while (!wave.isEmpty()) {
			long at = wave.poll();
			int d = dist.get(at);
			for (int[] f : FACES) {
				long n = BlockPos.offset(at, f[0], f[1], f[2]);
				Integer dn = dist.get(n);
				if (dn != null && dn > d + 1) {
					dist.put(n, d + 1);
					wave.add(n);
				}
			}
		}
		BlockPos.MutableBlockPos pos = new BlockPos.MutableBlockPos();
		for (Map.Entry<Long, Integer> e : dist.entrySet()) {
			pos.set(e.getKey());
			BlockState s = loaded.get(pos.getX(), pos.getY(), pos.getZ());
			if (s == null) {
				continue;
			}
			if (e.getValue() >= LeavesBlock.DECAY_DISTANCE) {
				level.setBlock(pos, Blocks.AIR.defaultBlockState(), FLAGS);
			} else if (s.getValue(LeavesBlock.DISTANCE) != e.getValue()) {
				level.setBlock(pos, s.setValue(LeavesBlock.DISTANCE, e.getValue()), FLAGS);
			}
		}
	}

	/** What {@link #audit} found in a chunk's road columns. */
	public record Audit(int columns, int blocked, int unpaved, int steps, int orphans, List<String> examples) {
	}

	private static void example(List<String> out, String what, int x, int y, int z, BlockState s) {
		if (out.size() < 6) {
			out.add(what + " at " + x + " " + y + " " + z + " (" + BuiltInRegistries.BLOCK.getKey(s.getBlock()) + ")");
		}
	}

	/**
	 * Looks at the land columns of the roads in this chunk as they stand: {@code blocked} those with a trunk, leaves, a
	 * plant or ground on the paving or in the 3 blocks over it; {@code unpaved} those whose top is not the paving
	 * ({@link #paving}); {@code steps} the pairs of neighbouring road columns more than a block apart; {@code orphans} the
	 * natural leaves within 6 blocks of the road that no log holds (they would hang in the air). Water columns (bridges,
	 * walkways, a cut) and those of a structure or {@code skip} are not counted. Reads loaded chunks only.
	 */
	public static Audit audit(ServerLevel level, LevelChunk chunk, RoadLayout layout, List<RoadLayout.Route> routes, int width,
			BiPredicate<Integer, Integer> skip) {
		var cp = chunk.getPos();
		RoadLayout.Cell[] c = layout.paint(routes, cp.x(), cp.z(), width, false);
		List<BoundingBox> boxes = boxes(level, chunk);
		BlockPos.MutableBlockPos pos = new BlockPos.MutableBlockPos();
		int[] tops = new int[256];
		Arrays.fill(tops, Integer.MIN_VALUE);
		int columns = 0, blocked = 0, unpaved = 0, steps = 0, lo = Integer.MAX_VALUE, hi = Integer.MIN_VALUE;
		List<String> examples = new ArrayList<>();
		for (int i = 0; i < 256; i++) {
			int x = cp.getMinBlockX() + i / 16, z = cp.getMinBlockZ() + i % 16;
			if (c[i] == null || skip.test(x, z)) {
				continue;
			}
			int top = chunk.getHeight(Heightmap.Types.MOTION_BLOCKING_NO_LEAVES, x & 15, z & 15);
			if (inside(boxes, x, top, z) || inside(boxes, x, top + 1, z)) {
				continue;
			}
			int y = top;
			while (y > level.getMinY() && growth(chunk.getBlockState(pos.set(x, y, z)))) {
				y--;                               // under a trunk or a plant: the ground it stands on
			}
			BlockState s = chunk.getBlockState(pos.set(x, y, z));
			if (!s.getFluidState().isEmpty() || s.is(BlockTags.PLANKS)) {
				continue;                          // water: a bridge, a walkway, or cut
			}
			columns++;
			tops[i] = y;
			lo = Math.min(lo, y);
			hi = Math.max(hi, y);
			if (!paving(s)) {
				unpaved++;
				example(examples, "not paved", x, y, z, s);
			}
			for (int yy = y + 1; yy <= y + 3; yy++) {
				BlockState b = chunk.getBlockState(pos.set(x, yy, z));
				if (!b.isAir() && !b.is(Blocks.SNOW)) {
					blocked++;
					example(examples, "blocked", x, yy, z, b);
					break;
				}
			}
		}
		for (int i = 0; i < 256; i++) {
			if (tops[i] == Integer.MIN_VALUE) {
				continue;
			}
			int x = cp.getMinBlockX() + i / 16, z = cp.getMinBlockZ() + i % 16;
			if (i / 16 < 15 && tops[i + 16] != Integer.MIN_VALUE && Math.abs(tops[i + 16] - tops[i]) > 1) {
				steps++;
				example(examples, "step to " + tops[i + 16] + " east", x, tops[i], z, chunk.getBlockState(pos.set(x, tops[i], z)));
			}
			if (i % 16 < 15 && tops[i + 1] != Integer.MIN_VALUE && Math.abs(tops[i + 1] - tops[i]) > 1) {
				steps++;
				example(examples, "step to " + tops[i + 1] + " south", x, tops[i], z, chunk.getBlockState(pos.set(x, tops[i], z)));
			}
		}
		int orphans = columns == 0 ? 0 : orphans(level, chunk, c, lo - 12, hi + 24, examples, false);
		return new Audit(columns, blocked, unpaved, steps, orphans, examples);
	}

	/**
	 * Natural leaves within 6 blocks (across) of the road's columns in this chunk, between y0 and y1, with no log within
	 * {@link LeavesBlock#DECAY_DISTANCE} - 1 steps through the leaves (worked out from scratch, not from their state).
	 */
	private static int orphans(ServerLevel level, LevelChunk chunk, RoadLayout.Cell[] cells, int y0, int y1, List<String> examples,
			boolean remove) {
		var cp = chunk.getPos();
		int m = LeavesBlock.DECAY_DISTANCE + 6, x0 = cp.getMinBlockX() - m, z0 = cp.getMinBlockZ() - m, n = 16 + 2 * m, h = y1 - y0 + 1;
		Loaded loaded = new Loaded(level);
		BlockPos.MutableBlockPos pos = new BlockPos.MutableBlockPos();
		byte[] d = new byte[n * n * h];        // -1 neither, 0 a log (or beyond what is looked at), 1..6 held leaves, 8 not held (yet)
		ArrayDeque<Integer> wave = new ArrayDeque<>();
		for (int ix = 0; ix < n; ix++) {
			for (int iz = 0; iz < n; iz++) {
				LevelChunk ch = loaded.chunk(x0 + ix, z0 + iz);
				boolean side = ix == 0 || iz == 0 || ix == n - 1 || iz == n - 1;
				for (int iy = 0; iy < h; iy++) {
					boolean rim = side || iy == 0 || iy == h - 1;
					int idx = (ix * n + iz) * h + iy;
					BlockState s = ch == null ? null : ch.getBlockState(pos.set(x0 + ix, y0 + iy, z0 + iz));
					boolean leaf = s != null && s.is(BlockTags.LEAVES) && !s.getValue(LeavesBlock.PERSISTENT);
					if (s == null || s.is(BlockTags.LOGS) || leaf && rim) {
						d[idx] = 0;                    // a log; a chunk not loaded, or leaves on the rim: counted as holding
						wave.add(idx);
					} else {
						d[idx] = (byte) (leaf ? 8 : -1);
					}
				}
			}
		}
		while (!wave.isEmpty()) {
			int idx = wave.poll();
			int iy = idx % h, iz = (idx / h) % n, ix = idx / h / n, v = Math.max(d[idx], 0);
			if (v >= LeavesBlock.DECAY_DISTANCE - 1) {
				continue;
			}
			int[][] nb = {{ix + 1, iz, iy}, {ix - 1, iz, iy}, {ix, iz + 1, iy}, {ix, iz - 1, iy}, {ix, iz, iy + 1}, {ix, iz, iy - 1}};
			for (int[] q : nb) {
				if (q[0] < 0 || q[1] < 0 || q[2] < 0 || q[0] >= n || q[1] >= n || q[2] >= h) {
					continue;
				}
				int j = (q[0] * n + q[1]) * h + q[2];
				if (d[j] > v + 1) {
					d[j] = (byte) (v + 1);
					wave.add(j);
				}
			}
		}
		int out = 0;
		for (int ix = 0; ix < n; ix++) {
			for (int iz = 0; iz < n; iz++) {
				if (!nearRoad(cells, x0 + ix - cp.getMinBlockX(), z0 + iz - cp.getMinBlockZ(), 6)) {
					continue;
				}
				for (int iy = 0; iy < h; iy++) {
					if (d[(ix * n + iz) * h + iy] == 8) {
						out++;
						BlockState o = loaded.get(x0 + ix, y0 + iy, z0 + iz);
						if (o != null && remove) {
							level.setBlock(pos.set(x0 + ix, y0 + iy, z0 + iz), Blocks.AIR.defaultBlockState(), FLAGS);
						} else if (o != null) {
							example(examples, "hanging (distance " + o.getValue(LeavesBlock.DISTANCE) + ")", x0 + ix, y0 + iy, z0 + iz, o);
						}
					}
				}
			}
		}
		return out;
	}

	/**
	 * Takes away the natural leaves within 6 blocks of the road's columns in this chunk that no log holds any more (their
	 * distance worked out again from the logs, as their decay would): leaves of trees cut by anything that did not fell
	 * them whole (the town's blended margin, a hut's site, a template), left hanging over or beside the road. Loaded
	 * chunks only; leaves at the edge of what is looked at, or next to a chunk not loaded, stay. Returns how many went.
	 */
	public static int tidy(ServerLevel level, LevelChunk chunk, RoadLayout layout, List<RoadLayout.Route> routes, int width,
			BiPredicate<Integer, Integer> skip) {
		var cp = chunk.getPos();
		RoadLayout.Cell[] c = layout.paint(routes, cp.x(), cp.z(), width, false);
		int lo = Integer.MAX_VALUE, hi = Integer.MIN_VALUE;
		for (int i = 0; i < 256; i++) {
			int x = cp.getMinBlockX() + i / 16, z = cp.getMinBlockZ() + i % 16;
			if (c[i] == null || skip.test(x, z)) {
				c[i] = null;
				continue;
			}
			int top = chunk.getHeight(Heightmap.Types.MOTION_BLOCKING_NO_LEAVES, x & 15, z & 15);
			lo = Math.min(lo, top);
			hi = Math.max(hi, top);
		}
		return lo > hi ? 0 : orphans(level, chunk, c, lo - 12, hi + 24, new ArrayList<>(), true);
	}

	/** Is the column (lx, lz), local to the chunk (it may be outside it), within r blocks of one of its road cells? */
	private static boolean nearRoad(RoadLayout.Cell[] cells, int lx, int lz, int r) {
		for (int x = Math.max(0, lx - r); x <= Math.min(15, lx + r); x++) {
			for (int z = Math.max(0, lz - r); z <= Math.min(15, lz + r); z++) {
				if (cells[x * 16 + z] != null) {
					return true;
				}
			}
		}
		return false;
	}

	/**
	 * A lamp post (two fence posts of the biome's wood and a lantern) at (x, z) on firm natural ground; failing that (water,
	 * a tree, a player's block), one block farther out; failing that, on the road's own edge at (ex, ez): on its paving
	 * or on a bridge's deck. False if none fits.
	 */
	public static boolean lamp(ServerLevel level, int x, int z, int ex, int ez, BiPredicate<Integer, Integer> skip) {
		BlockPos.MutableBlockPos pos = new BlockPos.MutableBlockPos();
		int ox = Integer.signum(x - ex), oz = Integer.signum(z - ez);
		if (ground(level, pos, x, z, skip) || (ox != 0 || oz != 0) && ground(level, pos, x + ox, z + oz, skip)) {
			return true;
		}
		if (skip.test(ex, ez)) {
			return false;
		}
		LevelChunk chunk = level.getChunk(ex >> 4, ez >> 4);
		int top = chunk.getHeight(Heightmap.Types.MOTION_BLOCKING_NO_LEAVES, ex & 15, ez & 15);
		BlockState deck = level.getBlockState(pos.set(ex, top, ez));
		boolean bridge = deck.is(BlockTags.PLANKS) && level.getBlockState(pos.set(ex, top - 1, ez)).getFluidState().is(FluidTags.WATER);
		if (bridge && free(level, pos, ex, top + 1, ez)) {      // on land the shoulder (or one beyond) always fits
			post(level, pos, ex, top + 1, ez);
			return true;
		}
		return false;
	}

	/** A lamp post on firm natural ground (or a path) at (x, z), outside any structure. */
	private static boolean ground(ServerLevel level, BlockPos.MutableBlockPos pos, int x, int z, BiPredicate<Integer, Integer> skip) {
		if (skip.test(x, z)) {
			return false;
		}
		LevelChunk chunk = level.getChunk(x >> 4, z >> 4);
		int surf = chunk.getHeight(Heightmap.Types.MOTION_BLOCKING_NO_LEAVES, x & 15, z & 15) + 1;
		int floor = chunk.getHeight(Heightmap.Types.OCEAN_FLOOR, x & 15, z & 15) + 1;
		BlockState top = level.getBlockState(pos.set(x, surf - 1, z));
		if (surf == floor && !inside(boxes(level, chunk), x, surf, z) && top.isFaceSturdy(level, pos, Direction.UP)
				&& (RoadFeature.ground(top, 0.5, true) != null || top.is(Blocks.DIRT_PATH) || top.is(BlockTags.DIRT))
				&& free(level, pos, x, surf, z)) {
			post(level, pos, x, surf, z);
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
