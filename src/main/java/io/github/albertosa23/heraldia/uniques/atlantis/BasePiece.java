package io.github.albertosa23.heraldia.uniques.atlantis;

import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.util.RandomSource;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.StructureManager;
import net.minecraft.world.level.WorldGenLevel;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.chunk.ChunkGenerator;
import net.minecraft.world.level.levelgen.structure.BoundingBox;
import net.minecraft.world.level.levelgen.structure.StructurePiece;
import net.minecraft.world.level.levelgen.structure.pieces.StructurePieceSerializationContext;
import net.minecraft.world.level.material.Fluids;

/**
 * Atlantis urban layout, by columns and without templates: inside the city circle it clears with water everything
 * that is above the ground, paves (cross avenues and inner ring road), fills the plinth down to the bed so that
 * nothing floats and raises the circular wall with its four gates and collapsed stretches. The same layout is in
 * tools/gen/uniques/atlantis/urban_layout.py for the plans and the audit: change both at once.
 */
public final class BasePiece extends StructurePiece {
	static final int WALL_THICKNESS = 4, WALL_HEIGHT = 13, GATE_HALF = 4, GATE_HEIGHT = 8, AVENUE_HALF = 6, RING_ROAD = 10;
	private static final BlockState WATER = Blocks.WATER.defaultBlockState(), BRICKS = Blocks.PRISMARINE_BRICKS.defaultBlockState(),
			PRISMARINE = Blocks.PRISMARINE.defaultBlockState(), DARK = Blocks.DARK_PRISMARINE.defaultBlockState(),
			LANTERN = Blocks.SEA_LANTERN.defaultBlockState(), STONE = Blocks.STONE.defaultBlockState(), GRAVEL = Blocks.GRAVEL.defaultBlockState();
	private final int cx, cz, radius, floor, base;

	BasePiece(BoundingBox box, int cx, int cz, int radius, int floor, int base) {
		super(Atlantis.BASE_PIECE, 0, box);
		this.cx = cx;
		this.cz = cz;
		this.radius = radius;
		this.floor = floor;
		this.base = base;
	}

	BasePiece(CompoundTag tag) {
		super(Atlantis.BASE_PIECE, tag);
		this.cx = tag.getIntOr("cx", 0);
		this.cz = tag.getIntOr("cz", 0);
		this.radius = tag.getIntOr("radio", 0);
		this.floor = tag.getIntOr("suelo", 0);
		this.base = tag.getIntOr("base", 0);
	}

	@Override
	protected void addAdditionalSaveData(StructurePieceSerializationContext context, CompoundTag tag) {
		tag.putInt("cx", cx);
		tag.putInt("cz", cz);
		tag.putInt("radio", radius);
		tag.putInt("suelo", floor);
		tag.putInt("base", base);
	}

	/** Deterministic integer scattering; identical to urbanismo.dispersion in Python. */
	static int hash(int x, int z, int salt) {
		int h = x * 374761393 + z * 668265263 + salt * 1013904223;
		h = (h ^ (h >>> 13)) * 1274126177;
		return (h ^ (h >>> 16)) & 0x7fffffff;
	}

	/** Height of the wall above the ground in this column (0 = gate opening at ground level is handled separately). */
	static int wallHeight(int x, int z) {
		int sector = (int) Math.floor(Math.atan2(z, x) * 24 / Math.PI); // 48 sectors of ~48 blocks of arc
		int roll = hash(sector, 7, 1) % 100;
		int height = roll < 18 ? 3 + hash(x >> 1, z >> 1, 2) % 5 : WALL_HEIGHT; // 18 % of the stretches, collapsed
		return height;
	}

	@Override
	public void postProcess(WorldGenLevel level, StructureManager structureManager, ChunkGenerator generator, RandomSource random,
							BoundingBox chunkBB, ChunkPos chunkPos, BlockPos referencePos) {
		BoundingBox box = getBoundingBox();
		BlockPos.MutableBlockPos pos = new BlockPos.MutableBlockPos();
		int top = box.maxY();
		for (int wx = Math.max(box.minX(), chunkBB.minX()); wx <= Math.min(box.maxX(), chunkBB.maxX()); wx++) {
			for (int wz = Math.max(box.minZ(), chunkBB.minZ()); wz <= Math.min(box.maxZ(), chunkBB.maxZ()); wz++) {
				int x = wx - cx, z = wz - cz;
				long d2 = (long) x * x + (long) z * z;
				if (d2 > (long) radius * radius) {
					continue;
				}
				double r = Math.sqrt(d2);
				boolean wall = r > radius - WALL_THICKNESS;
				boolean gate = wall && (Math.abs(x) <= GATE_HALF || Math.abs(z) <= GATE_HALF);
				int wallTop = wall ? floor + (gate ? WALL_HEIGHT : wallHeight(x, z)) : floor;
				if (wall && !gate && wallTop == floor + WALL_HEIGHT && r > radius - 1.5 && (hash(x, z, 3) & 1) == 0) {
					wallTop++; // battlements on the outer edge
				}
				// 1) water above the ground (or wall)
				for (int y = top; y > floor; y--) {
					pos.set(wx, y, wz);
					boolean solid = wall && y <= wallTop && !(gate && y <= floor + GATE_HEIGHT);
					BlockState want = solid ? (y == wallTop || (y - floor) % 5 == 0 ? DARK : BRICKS) : WATER;
					if (solid || level.getFluidState(pos).getType() != Fluids.WATER || !level.getBlockState(pos).is(Blocks.WATER)) {
						level.setBlock(pos, want, 2);
					}
				}
				// 2) paving
				level.setBlock(pos.set(wx, floor, wz), pavement(x, z, r), 2);
				// 3) plinth down to the bed
				for (int y = floor - 1; y >= box.minY(); y--) {
					pos.set(wx, y, wz);
					if (y < base && !replaceable(level.getBlockState(pos))) {
						break;
					}
					level.setBlock(pos, y >= base && r > radius - WALL_THICKNESS - 2 ? BRICKS : STONE, 2);
				}
			}
		}
	}

	private static boolean replaceable(BlockState state) {
		return state.isAir() || !state.getFluidState().isEmpty() || state.canBeReplaced();
	}

	private BlockState pavement(int x, int z, double r) {
		int ax = Math.abs(x), az = Math.abs(z);
		if (ax <= AVENUE_HALF || az <= AVENUE_HALF) {
			if ((ax == 0 && z % 8 == 0) || (az == 0 && x % 8 == 0)) {
				return LANTERN;
			}
			return ax == AVENUE_HALF || az == AVENUE_HALF ? BRICKS : DARK;
		}
		if (r > radius - WALL_THICKNESS - RING_ROAD) {
			return BRICKS;
		}
		int roll = hash(x, z, 4) % 100;
		return roll < 8 ? GRAVEL : roll < 30 ? BRICKS : PRISMARINE;
	}
}
