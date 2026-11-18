package io.github.albertosa23.heraldia.treasure;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;
import java.util.Optional;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.NbtIo;
import net.minecraft.nbt.NbtAccounter;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import org.junit.jupiter.api.Test;

/** The chain saved in the item: round trip through NBT (also binary, as it is saved), steps and the chest only once. */
class ChainTest {
	static final Destination MEDIUM = new Destination(Destination.Type.MEDIUM, "heraldia:medianas/posada/llanuras", 400, -120, true, "minecraft:plains");
	static final Destination MINE = new Destination(Destination.Type.MINE, "heraldia:minas/pequena/taiga/a", 900, 300, false, "minecraft:taiga");
	static final Destination TREASURE = new Destination(Destination.Type.TREASURE, "", 980, 360, false, "minecraft:taiga");

	static Chain chain() {
		return Chain.fresh(-1234567890123L, 10, -20, List.of(MEDIUM, MINE, TREASURE));
	}

	@Test
	void nbtRoundTrip() throws IOException {
		Chain c = chain().advance();
		CompoundTag t = c.toTag();
		assertEquals(Optional.of(c), Chain.fromTag(t));
		ByteArrayOutputStream bytes = new ByteArrayOutputStream();
		NbtIo.write(t, new DataOutputStream(bytes));
		CompoundTag readBack = NbtIo.read(new DataInputStream(new ByteArrayInputStream(bytes.toByteArray())), NbtAccounter.unlimitedHeap());
		assertEquals(Optional.of(c), Chain.fromTag(readBack));
	}

	@Test
	void withChestAndMovedAreAlsoSaved() {
		Chain c = chain().advance().advance().withTreasure(new Destination(Destination.Type.TREASURE, "", 1000, 400, false, "minecraft:snowy_taiga"))
				.withChest(new BlockPos(1001, 70, 402));
		Chain readBack = Chain.fromTag(c.toTag()).orElseThrow();
		assertEquals(c, readBack);
		assertEquals(Optional.of(new BlockPos(1001, 70, 402)), readBack.chest());
		assertEquals(1, readBack.moved());
		assertTrue(readBack.completed());
	}

	@Test
	void undecipheredFragmentHasNoChain() {
		assertTrue(Chain.fromTag(Chain.fragment()).isEmpty());
		assertTrue(Chain.fromTag(new CompoundTag()).isEmpty());
		assertEquals(1, Chain.fragment().getIntOr("v", 0));
	}

	@Test
	void unreadableMarkDoesNotBreak() {
		CompoundTag t = chain().toTag();
		t.remove("destinos");   // without destinations: it does not end at the treasure
		assertTrue(Chain.fromTag(t).isEmpty());
		CompoundTag u = chain().toTag();
		u.putInt("paso", 9);
		assertTrue(Chain.fromTag(u).isEmpty());
	}

	@Test
	void advancesStepByStepAndChestOnlyOnce() {
		Chain c = chain();
		assertEquals(MEDIUM, c.actual());
		assertEquals(3, c.marks());
		assertEquals(10, c.from(0)[0]);
		c = c.advance();
		assertEquals(MINE, c.actual());
		assertEquals(MEDIUM.x(), c.from(1)[0]);
		c = c.advance();
		assertEquals(TREASURE, c.actual());
		Chain inTreasure = c;
		assertThrows(IllegalStateException.class, inTreasure::advance);
		c = c.withChest(new BlockPos(1, 2, 3));
		assertTrue(c.completed());
		Chain done = c;
		assertThrows(IllegalStateException.class, () -> done.withChest(new BlockPos(4, 5, 6)));
		assertThrows(IllegalStateException.class, done::advance);
		assertEquals(TREASURE, done.actual());
	}

	@Test
	void chestIsNotPlacedInAStructure() {
		assertThrows(IllegalStateException.class, () -> chain().withChest(BlockPos.ZERO));
	}

	@Test
	void mustEndAtTheTreasure() {
		assertThrows(IllegalArgumentException.class, () -> Chain.fresh(1, 0, 0, List.of(MEDIUM, MINE)));
		assertThrows(IllegalArgumentException.class, () -> Chain.fresh(1, 0, 0, List.of()));
		assertFalse(Chain.fresh(1, 0, 0, List.of(TREASURE)).completed());
	}

	@Test
	void destinationWithoutStructureDoesNotSaveField() {
		CompoundTag t = TREASURE.toTag();
		assertFalse(t.contains("estructura"));
		assertEquals(TREASURE, Destination.fromTag(t));
		assertEquals(MEDIUM, Destination.fromTag(MEDIUM.toTag()));
	}
}
