package io.github.albertosa23.heraldia.treasure;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.util.HashSet;
import java.util.Set;
import net.minecraft.core.BlockPos;
import org.junit.jupiter.api.Test;

/** Usar el mapa: lejos, en cada marca y en el tesoro; la cadena se completa una sola vez (también con copias). */
class AdvanceTest {
	@Test
	void farNearAndArrival() {
		Chain c = ChainTest.chain();
		Destination m = ChainTest.MEDIUM;
		assertEquals(Advance.Result.FAR, Advance.evaluateAt(c, 0, 0, Set.of()));
		assertEquals(Advance.Result.NEXT, Advance.evaluateAt(c, m.x() + Advance.STRUCTURE_ARRIVAL, m.z(), Set.of()));
		assertEquals(Advance.Result.FAR, Advance.evaluateAt(c, m.x() + Advance.STRUCTURE_ARRIVAL + 1, m.z(), Set.of()));
	}

	@Test
	void wholeRunAndOnlyOnce() {
		Set<Long> completed = new HashSet<>();
		Chain c = ChainTest.chain();
		Chain backup = c;   // una copia del mapa (mesa de cartografía) con la misma cadena
		int steps = 0;
		while (true) {
			Destination d = c.actual();
			Advance.Result r = Advance.evaluateAt(c, d.x(), d.z(), completed);
			if (r == Advance.Result.NEXT) {
				c = c.advance();
				steps++;
			} else {
				assertEquals(Advance.Result.CHEST, r);
				break;
			}
		}
		assertEquals(2, steps);
		completed.add(c.seed());
		c = c.withChest(new BlockPos(c.actual().x(), 63, c.actual().z()));
		assertEquals(Advance.Result.DONE, Advance.evaluateAt(c, c.actual().x(), c.actual().z(), completed));
		assertEquals(Advance.Result.DONE, Advance.evaluateAt(c, c.actual().x(), c.actual().z(), Set.of()), "completada por sí misma");
		Chain copyInTreasure = backup.advance().advance();
		assertEquals(Advance.Result.DONE, Advance.evaluateAt(copyInTreasure, copyInTreasure.actual().x(), copyInTreasure.actual().z(), completed),
				"la copia no da otro cofre");
		assertEquals(Advance.Result.DONE, Advance.evaluateAt(backup, 0, 0, completed), "ni lejos dice nada más");
	}

	@Test
	void treasureRequiresGettingCloser() {
		Chain c = ChainTest.chain().advance().advance();
		Destination t = c.actual();
		assertEquals(Advance.Result.CHEST, Advance.evaluateAt(c, t.x() + Advance.TREASURE_ARRIVAL, t.z(), Set.of()));
		assertEquals(Advance.Result.FAR, Advance.evaluateAt(c, t.x() + Advance.TREASURE_ARRIVAL + 1, t.z(), Set.of()));
	}

	@Test
	void approximateDistance() {
		Destination d = new Destination(Destination.Type.TREASURE, "", 0, 0, false, "minecraft:plains");
		assertEquals(120, Advance.approximateDistance(d, 123, 0));
		assertEquals(130, Advance.approximateDistance(d, 0, -126));
		assertEquals(0, Advance.approximateDistance(d, 2, 2));
	}
}
