package io.github.albertosa23.heraldia.bosses;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.mojang.serialization.JsonOps;
import java.util.List;
import net.minecraft.SharedConstants;
import net.minecraft.core.BlockPos;
import net.minecraft.core.HolderLookup;
import net.minecraft.core.RegistryAccess;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.server.Bootstrap;
import net.minecraft.util.ProblemReporter;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.entity.ChestBlockEntity;
import net.minecraft.world.level.block.entity.SpawnerBlockEntity;
import net.minecraft.world.level.storage.TagValueInput;
import net.minecraft.world.level.storage.TagValueOutput;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/**
 * Cleared uniques: the record (idempotency, pending spawners per chunk, the saved format) and turning a real spawner block
 * entity off (what it saves afterwards: no mob, no potentials).
 */
class ClearedSpawnersTest {
	private static final String CASTLE = ClearedUniques.key("heraldia:unicas/castillo", 42L);
	private static HolderLookup.Provider registries;

	@BeforeAll
	static void bootstrap() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
		registries = RegistryAccess.fromRegistryOfRegistries(BuiltInRegistries.REGISTRY);
	}

	@Test
	void recordIsIdempotent() {
		ClearedUniques a = ClearedUniques.EMPTY.with(CASTLE, List.of(1L, 2L));
		assertTrue(a.has(CASTLE));
		assertEquals(List.of(1L, 2L), a.pending());
		ClearedUniques b = a.with(CASTLE, List.of(3L));          // a second death in the same structure: nothing changes
		assertSame(a, b);
		assertEquals(List.of(1L, 2L), b.pending());
		ClearedUniques c = a.with(ClearedUniques.key("heraldia:unicas/castillo", 43L), List.of(2L, 4L));  // another castle
		assertEquals(List.of(1L, 2L, 4L), c.pending());          // no duplicates
		assertEquals(2, c.cleared().size());
		assertFalse(ClearedUniques.EMPTY.has(CASTLE));
	}

	@Test
	void pendingLeavesOnceHandled() {
		long inside = BlockPos.asLong(17, 64, -3), alsoInside = BlockPos.asLong(31, -10, -16), outside = BlockPos.asLong(32, 64, -3);
		ClearedUniques a = ClearedUniques.EMPTY.with(CASTLE, List.of(inside, outside, alsoInside));
		List<Long> here = a.pendingIn(1, -1, l -> BlockPos.getX(l) >> 4, l -> BlockPos.getZ(l) >> 4);
		assertEquals(List.of(inside, alsoInside), here);
		ClearedUniques b = a.without(here);
		assertEquals(List.of(outside), b.pending());
		assertTrue(b.has(CASTLE));                                // the structure stays cleared
		assertSame(b, b.without(List.of(inside)));                // handled twice: unchanged
		assertTrue(ClearedUniques.EMPTY.pendingIn(1, -1, l -> 0, l -> 0).isEmpty());
	}

	@Test
	void savedFormatRoundTrip() {
		ClearedUniques a = ClearedUniques.EMPTY.with(CASTLE, List.of(BlockPos.asLong(1, 2, 3)));
		var json = ClearedUniques.CODEC.encodeStart(JsonOps.INSTANCE, a).getOrThrow();
		assertTrue(json.getAsJsonObject().has("vencidas") && json.getAsJsonObject().has("pendientes"), json.toString());
		assertEquals(a, ClearedUniques.CODEC.parse(JsonOps.INSTANCE, json).getOrThrow());
		// a world without the attachment (or with an older, partial one) reads as empty lists
		assertEquals(ClearedUniques.EMPTY, ClearedUniques.CODEC.parse(JsonOps.INSTANCE, new com.google.gson.JsonObject()).getOrThrow());
	}

	@Test
	void turnsARealSpawnerOff() {
		BlockPos pos = new BlockPos(5, 70, 5);
		SpawnerBlockEntity spawner = new SpawnerBlockEntity(pos, Blocks.SPAWNER.defaultBlockState());
		CompoundTag zombie = new CompoundTag();
		zombie.putString("id", "minecraft:zombie");
		CompoundTag data = new CompoundTag();
		data.put("entity", zombie);
		CompoundTag nbt = new CompoundTag();
		nbt.put("SpawnData", data);
		spawner.getSpawner().load(null, pos, TagValueInput.create(ProblemReporter.DISCARDING, registries, nbt));
		assertEquals("minecraft:zombie", saved(spawner).getCompoundOrEmpty("SpawnData").getCompoundOrEmpty("entity").getStringOr("id", ""));

		assertTrue(ClearedSpawners.turnOff(null, registries, spawner));
		CompoundTag after = saved(spawner);
		assertTrue(after.getCompoundOrEmpty("SpawnData").getCompoundOrEmpty("entity").isEmpty(), after.toString());
		assertTrue(after.getListOrEmpty("SpawnPotentials").isEmpty(), after.toString());
		assertTrue(ClearedSpawners.turnOff(null, registries, spawner));      // again: still off
		assertEquals(after, saved(spawner));

		assertFalse(ClearedSpawners.turnOff(null, registries, null));        // broken by the player: nothing
		assertFalse(ClearedSpawners.turnOff(null, registries, new ChestBlockEntity(pos, Blocks.CHEST.defaultBlockState())));
	}

	private static CompoundTag saved(SpawnerBlockEntity spawner) {
		TagValueOutput out = TagValueOutput.createWithContext(ProblemReporter.DISCARDING, registries);
		spawner.getSpawner().save(out);
		return out.buildResult();
	}
}
