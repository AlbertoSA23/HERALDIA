package io.github.albertosa23.heraldia.villages;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.levelgen.structure.BoundingBox;
import org.junit.jupiter.api.Test;

/** No trees of world generation on a village's pieces ({@link Clearing}): which tree origins stay out. */
class ClearingTest {
	private static final List<BoundingBox> PIECES = List.of(new BoundingBox(0, 60, 0, 6, 70, 15), new BoundingBox(20, 60, 0, 28, 75, 8));

	@Test
	void onAPieceOrWithinTheMarginNoTree() {
		assertTrue(Clearing.cleared(PIECES, 3, 7));
		assertTrue(Clearing.cleared(PIECES, 24, 4));
		assertTrue(Clearing.cleared(PIECES, -Clearing.MARGIN, 0));
		assertTrue(Clearing.cleared(PIECES, 6 + Clearing.MARGIN, 15 + Clearing.MARGIN));
	}

	@Test
	void beyondTheMarginOrBetweenPiecesTreesGrow() {
		assertFalse(Clearing.cleared(PIECES, -Clearing.MARGIN - 1, 0));
		assertFalse(Clearing.cleared(PIECES, 13, 4));
		assertFalse(Clearing.cleared(PIECES, 24, 8 + Clearing.MARGIN + 1));
	}

	@Test
	void outsideAChunkBeingDecoratedEveryTreeGrows() {
		// saplings and other features placed outside the decoration of a chunk: no pieces known on this thread
		Clearing.end();
		assertFalse(Clearing.cleared(new BlockPos(3, 64, 7)));
	}
}
