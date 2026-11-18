package io.github.albertosa23.heraldia.arena;

import net.minecraft.core.registries.Registries;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.IntTag;
import net.minecraft.nbt.visitors.CollectFields;
import net.minecraft.nbt.visitors.FieldSelector;
import net.minecraft.resources.Identifier;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.levelgen.GenerationStep;
import net.minecraft.world.level.levelgen.structure.Structure;

/**
 * Does a saved chunk already have pieces of some surface structure (villages, mine entrances, uniques, vanilla
 * or other mods' structures)? It only reads the chunk's references on disk with StructureCheck's scanner (like
 * /heraldia info nearby): safe off the server thread, without loading or generating chunks. Underground ones (vanilla
 * mineshafts, End strongholds...) do not count: they do not show where the arena goes. An unsaved chunk has nothing.
 */
final class Structures {
	private Structures() {
	}

	static boolean occupied(ServerLevel level, int chunkX, int chunkZ) {
		CollectFields fields = new CollectFields(new FieldSelector(IntTag.TYPE, "DataVersion"),
				new FieldSelector("structures", CompoundTag.TYPE, "References"));
		try {
			level.getChunkSource().chunkScanner().scanChunk(new ChunkPos(chunkX, chunkZ), fields).join();
		} catch (RuntimeException e) {
			return false;
		}
		if (!(fields.getResult() instanceof CompoundTag tag)) {
			return false;
		}
		var ledger = level.registryAccess().lookupOrThrow(Registries.STRUCTURE);
		boolean[] there = {false};
		tag.getCompound("structures").flatMap(t -> t.getCompound("References")).ifPresent(refs -> refs.forEach((key, value) -> {
			Identifier id = Identifier.tryParse(key);
			Structure s = id == null ? null : ledger.getValue(id);
			if (s != null && surface(s.step())) {
				there[0] = true;
			}
		}));
		return there[0];
	}

	/** Generation steps of the structures that show above ground (pure logic). */
	static boolean surface(GenerationStep.Decoration step) {
		return step != GenerationStep.Decoration.UNDERGROUND_STRUCTURES && step != GenerationStep.Decoration.UNDERGROUND_DECORATION
				&& step != GenerationStep.Decoration.STRONGHOLDS;
	}
}
