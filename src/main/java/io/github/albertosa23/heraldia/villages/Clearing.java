package io.github.albertosa23.heraldia.villages;

import java.util.ArrayList;
import java.util.List;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.StructureManager;
import net.minecraft.world.level.chunk.ChunkAccess;
import net.minecraft.world.level.levelgen.structure.BoundingBox;
import net.minecraft.world.level.levelgen.structure.StructurePiece;
import net.minecraft.world.level.levelgen.structure.StructureStart;

/**
 * The ground of a Heraldia village is kept clear of trees: while a chunk is decorated (its features placed, trees among
 * them), a tree, fallen tree or bamboo whose origin falls on a piece of a Heraldia village (its box and {@link #MARGIN}
 * blocks around it) is not placed. In a forest or a jungle the trunks and bushes otherwise grow between the houses, on
 * the edges of the streets and in front of the doors, and villagers cannot walk through them. Only the features placed
 * by world generation: saplings grow as always. The pieces are those of the starts that reach the chunk (the same ones
 * the terrain adaptation reads), kept per thread while the chunk is decorated.
 */
public final class Clearing {
	/** Blocks around each piece where trees do not grow either (a canopy still reaches over from further out). */
	public static final int MARGIN = 2;
	private static final ThreadLocal<List<BoundingBox>> BOXES = new ThreadLocal<>();

	private Clearing() {
	}

	/** Called when the chunk's decoration starts: the village pieces that reach it, inflated by the margin. */
	public static void begin(StructureManager structures, ChunkAccess chunk) {
		ChunkPos c = chunk.getPos();
		List<BoundingBox> out = null;
		for (StructureStart start : structures.startsForStructure(c.x(), c.z(), s -> s instanceof VillageStructure)) {
			for (StructurePiece piece : start.getPieces()) {
				BoundingBox b = piece.getBoundingBox();
				if (b.maxX() + MARGIN < c.getMinBlockX() || b.minX() - MARGIN > c.getMaxBlockX()
						|| b.maxZ() + MARGIN < c.getMinBlockZ() || b.minZ() - MARGIN > c.getMaxBlockZ()) {
					continue;
				}
				if (out == null) {
					out = new ArrayList<>();
				}
				out.add(b);
			}
		}
		BOXES.set(out);
	}

	/** Called when the chunk's decoration ends. */
	public static void end() {
		BOXES.remove();
	}

	/** Does a tree that starts at {@code pos} stay out (it is being decorated and falls on a village piece)? */
	public static boolean cleared(BlockPos pos) {
		List<BoundingBox> boxes = BOXES.get();
		return boxes != null && cleared(boxes, pos.getX(), pos.getZ());
	}

	static boolean cleared(List<BoundingBox> boxes, int x, int z) {
		for (BoundingBox b : boxes) {
			if (x >= b.minX() - MARGIN && x <= b.maxX() + MARGIN && z >= b.minZ() - MARGIN && z <= b.maxZ() + MARGIN) {
				return true;
			}
		}
		return false;
	}
}
