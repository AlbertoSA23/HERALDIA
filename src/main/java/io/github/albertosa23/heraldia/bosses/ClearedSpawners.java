package io.github.albertosa23.heraldia.bosses;

import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.common.TemplateBlocks;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import java.util.ArrayList;
import java.util.List;
import net.fabricmc.fabric.api.attachment.v1.AttachmentRegistry;
import net.fabricmc.fabric.api.attachment.v1.AttachmentType;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerChunkEvents;
import net.minecraft.core.BlockPos;
import net.minecraft.core.HolderLookup;
import net.minecraft.core.registries.Registries;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.resources.Identifier;
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.level.ChunkHolder;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.util.ProblemReporter;
import net.minecraft.util.Util;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.entity.SpawnerBlockEntity;
import net.minecraft.world.level.chunk.LevelChunk;
import net.minecraft.world.level.levelgen.structure.Structure;
import net.minecraft.world.level.levelgen.structure.StructurePiece;
import net.minecraft.world.level.levelgen.structure.StructureStart;
import net.minecraft.world.level.levelgen.structure.templatesystem.StructureTemplate;
import net.minecraft.world.level.storage.TagValueInput;
import org.jspecify.annotations.Nullable;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Cleared uniques (option jefes.apagar_generadores, on by default): when the final guardian of a unique structure dies, the
 * spawners of that structure are turned off, so the place is left clean and safe to live in (and is not an endless experience
 * farm). Nothing runs per tick: it hangs from the guardian's death (Bosses, {@code AFTER_DEATH}) and, for the spawners that
 * were in unloaded chunks, from the loading of their chunk ({@code CHUNK_LOAD}, with an early exit when nothing is pending).
 * <ul>
 * <li><b>Which structure:</b> the start of {@code heraldia:unicas/<id>} (the id of the guardian's tag
 * {@code heraldia_guardian.<id>}) that reaches the guardian's chunk, that is, the whole structure the player conquered (all its
 * pieces, also the dungeons far from the guardian's room), and not a radius: a vanilla dungeon or a player's spawner next to
 * it is never touched.</li>
 * <li><b>Which spawners:</b> the ones its templates placed ({@link TemplateBlocks}), at their world position, if a spawner is
 * still there. So they are known also in unloaded chunks without loading them; one the player broke is skipped.</li>
 * <li><b>Turned off:</b> the spawner stays (an empty cage, as a relic of the fight) but without a mob: no SpawnData entity and
 * no SpawnPotentials. It spawns nothing again; a vanilla spawn egg can fill it again like any empty spawner.</li>
 * <li><b>Idempotent:</b> each cleared start is recorded ({@link ClearedUniques}, attachment {@code heraldia:unicas_vencidas}
 * of its dimension); a second death in it does nothing, and a pending spawner leaves the list once handled.</li>
 * </ul>
 * A structure placed with {@code /place structure} does not save its start (see LESSONS): its spawners are not turned off.
 * A unique whose guardian died before this version is not recorded: it stays as it was (see CONTENT, "Cleared uniques").
 * The clear is recorded also with the option off (then without touching any spawner): the restocking loot reads it
 * ({@link #isCleared}, option botin.reponer.premium_vencido_modesto).
 */
public final class ClearedSpawners {
	private static final Logger LOGGER = LoggerFactory.getLogger(Heraldia.MOD_ID);
	public static final String OPTION = "jefes.apagar_generadores";

	private ClearedSpawners() {
	}

	/** The attachment, kept apart so the tests register nothing when the class loads. */
	static final class Type {
		static final AttachmentType<ClearedUniques> CLEARED = AttachmentRegistry.create(Heraldia.id("unicas_vencidas"),
				b -> b.persistent(ClearedUniques.CODEC));

		private Type() {
		}
	}

	static void register() {
		Type.CLEARED.identifier();   // registers the attachment at startup: otherwise the saved record is dropped when the world loads
		ServerChunkEvents.CHUNK_LOAD.register(ClearedSpawners::onChunkLoad);
	}

	/** A final guardian has died (it carries {@link Phases#GUARDIAN}): its structure's spawners are turned off. */
	static void guardianDied(LivingEntity guardian) {
		if (!(guardian.level() instanceof ServerLevel level)) {
			return;
		}
		String sid = Phases.unique(guardian.entityTags());
		if (sid == null) {
			return;
		}
		long t0 = System.nanoTime();
		StructureStart start = startOf(level, sid, guardian.blockPosition());
		if (start == null) {
			LOGGER.info("Heraldia: bosses: {} defeated outside any saved structure heraldia:unicas/{} (placed with /place?): no spawner turned off",
					Bosses.name(guardian), sid);
			return;
		}
		String key = ClearedUniques.key(Heraldia.MOD_ID + ":unicas/" + sid, start.getChunkPos().pack());
		ClearedUniques saved = level.getAttachedOrElse(Type.CLEARED, ClearedUniques.EMPTY);
		if (saved.has(key)) {
			return;
		}
		if (!HeraldiaConfig.get().getBool(OPTION)) {
			// spawners left as they are, but the structure is still recorded as cleared (its premium chest's refills, RestockedLoot)
			level.setAttached(Type.CLEARED, saved.with(key, List.of()));
			LOGGER.info("Heraldia: bosses: {} defeated: {} cleared (jefes.apagar_generadores off: spawners left on)", Bosses.name(guardian), key);
			return;
		}
		List<Long> pending = new ArrayList<>();
		List<BlockPos> off = new ArrayList<>();
		for (StructurePiece piece : start.getPieces()) {
			for (StructureTemplate.StructureBlockInfo info : TemplateBlocks.of(level, piece, Blocks.SPAWNER)) {
				BlockPos p = info.pos();
				LevelChunk chunk = level.getChunkSource().getChunkNow(p.getX() >> 4, p.getZ() >> 4);
				if (chunk != null) {
					if (turnOff(level, level.registryAccess(), chunk.getBlockEntity(p))) {
						off.add(p);   // (the spawner itself sends the change to the clients that see it)
					}
					continue;
				}
				LevelChunk cached = cached(level, p);
				if (cached == null) {
					pending.add(p.asLong());
				} else if (turnOff(null, level.registryAccess(), cached.getBlockEntity(p))) {
					cached.markUnsaved();
					off.add(p);
				}
			}
		}
		level.setAttached(Type.CLEARED, saved.with(key, pending));
		LOGGER.info("Heraldia: bosses: {} defeated: {} cleared, {} spawners turned off, {} pending until their chunk loads ({} ms): {}",
				Bosses.name(guardian), key, off.size(), pending.size(), (System.nanoTime() - t0) / 1_000_000, text(off, pending));
	}

	/**
	 * A chunk still in memory but no longer accessible (its ticket dropped below full; it has not been unloaded yet), or
	 * null. It has to be handled now: when it becomes full again it is not loaded again, so no {@code CHUNK_LOAD} comes
	 * (seen on a dedicated server). It is only touched through the chunk itself, never asking the level for it.
	 */
	private static @Nullable LevelChunk cached(ServerLevel level, BlockPos p) {
		ChunkHolder holder = level.getChunkSource().chunkMap.getUpdatingChunkIfPresent(ChunkPos.pack(p.getX() >> 4, p.getZ() >> 4));
		return holder != null && holder.getLatestChunk() instanceof LevelChunk c ? c : null;
	}

	/**
	 * Has the guardian of the unique structure {@code heraldia:unicas/<sid>} that reaches {@code pos} fallen (since cleared uniques
	 * are recorded)? Used by the restocking loot for the premium chest; only called when such a chest is due, so it is rare.
	 */
	public static boolean isCleared(ServerLevel level, String sid, BlockPos pos) {
		ClearedUniques saved = level.getAttached(Type.CLEARED);
		if (saved == null || saved.cleared().isEmpty()) {
			return false;
		}
		StructureStart start = startOf(level, sid, pos);
		return start != null && saved.has(ClearedUniques.key(Heraldia.MOD_ID + ":unicas/" + sid, start.getChunkPos().pack()));
	}

	/** The start of heraldia:unicas/&lt;sid&gt; that reaches the guardian's chunk (the guardian may have chased someone out of its piece), or null. */
	private static @Nullable StructureStart startOf(ServerLevel level, String sid, BlockPos pos) {
		Identifier id = Heraldia.id("unicas/" + sid);
		Structure structure = level.registryAccess().lookupOrThrow(Registries.STRUCTURE).getValue(ResourceKey.create(Registries.STRUCTURE, id));
		if (structure == null) {
			return null;
		}
		for (StructureStart s : level.structureManager().startsForStructure(pos.getX() >> 4, pos.getZ() >> 4, structure)) {
			if (s.isValid()) {
				return s;
			}
		}
		return null;
	}

	/** A cleared structure's spawners that were in this chunk are turned off now that it loads. */
	private static void onChunkLoad(ServerLevel level, LevelChunk chunk, boolean generated) {
		ClearedUniques saved = level.getAttached(Type.CLEARED);
		if (saved == null || saved.pending().isEmpty() || !HeraldiaConfig.get().getBool(OPTION)) {
			return;    // almost always: nothing pending (with the option off, they wait until it is on again)
		}
		List<Long> here = saved.pendingIn(chunk.getPos().x(), chunk.getPos().z(), l -> BlockPos.getX(l) >> 4, l -> BlockPos.getZ(l) >> 4);
		if (here.isEmpty()) {
			return;
		}
		int off = 0;
		for (long l : here) {
			if (turnOff(null, level.registryAccess(), chunk.getBlockEntity(BlockPos.of(l)))) {
				off++;
			}
		}
		if (off > 0) {
			chunk.markUnsaved();
		}
		level.setAttached(Type.CLEARED, saved.without(here));
		LOGGER.info("Heraldia: bosses: {} pending spawners turned off when chunk {} loaded: {}", off, chunk.getPos(),
				text(here.stream().map(BlockPos::of).toList(), List.of()));
	}

	/**
	 * Turns a spawner off in place: no mob to spawn (empty SpawnData entity, no SpawnPotentials); the cage stays. False if
	 * there is no spawner there any more. Only the block entity is touched. With {@code level} null (while its chunk loads:
	 * asking the level for that chunk then could wait for itself) the clients are not told and the block entity is not marked
	 * as changed: the caller marks the chunk.
	 */
	static boolean turnOff(@Nullable Level level, HolderLookup.Provider registries, @Nullable BlockEntity be) {
		if (!(be instanceof SpawnerBlockEntity spawner)) {
			return false;
		}
		spawner.getSpawner().load(level, be.getBlockPos(), TagValueInput.create(ProblemReporter.DISCARDING, registries, OFF.copy()));
		if (level != null) {
			be.setChanged();
		}
		return true;
	}

	/** What a turned-off spawner loads: a SpawnData without entity and no SpawnPotentials (the rest, the vanilla defaults). */
	static final CompoundTag OFF = Util.make(new CompoundTag(), t -> {
		CompoundTag data = new CompoundTag();
		data.put("entity", new CompoundTag());
		t.put("SpawnData", data);
		t.put("SpawnPotentials", new ListTag());
	});

	private static String text(List<BlockPos> off, List<Long> pending) {
		StringBuilder b = new StringBuilder();
		for (BlockPos p : off) {
			b.append(b.isEmpty() ? "" : "; ").append(p.getX()).append(' ').append(p.getY()).append(' ').append(p.getZ());
		}
		for (long l : pending) {
			b.append(b.isEmpty() ? "" : "; ").append("pending ").append(BlockPos.getX(l)).append(' ').append(BlockPos.getY(l)).append(' ').append(BlockPos.getZ(l));
		}
		return b.toString();
	}
}
