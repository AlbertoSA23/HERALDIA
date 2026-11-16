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
 * ¿Tiene ya un chunk guardado piezas de alguna estructura de superficie (aldeas, entradas de mina, únicas, estructuras
 * vanilla o de otros mods)? Lee solo las referencias del chunk en disco con el escáner de StructureCheck (como
 * /heraldia info cerca): seguro fuera del hilo del servidor, sin cargar ni generar chunks. Las subterráneas (minas
 * vanilla, fortalezas del End...) no cuentan: no asoman donde va la arena. Un chunk sin guardar no tiene nada.
 */
final class Estructuras {
	private Estructuras() {
	}

	static boolean ocupado(ServerLevel level, int chunkX, int chunkZ) {
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
		var registro = level.registryAccess().lookupOrThrow(Registries.STRUCTURE);
		boolean[] hay = {false};
		tag.getCompound("structures").flatMap(t -> t.getCompound("References")).ifPresent(refs -> refs.forEach((key, value) -> {
			Identifier id = Identifier.tryParse(key);
			Structure s = id == null ? null : registro.getValue(id);
			if (s != null && superficie(s.step())) {
				hay[0] = true;
			}
		}));
		return hay[0];
	}

	/** Pasos de generación de las estructuras que asoman (lógica pura). */
	static boolean superficie(GenerationStep.Decoration paso) {
		return paso != GenerationStep.Decoration.UNDERGROUND_STRUCTURES && paso != GenerationStep.Decoration.UNDERGROUND_DECORATION
				&& paso != GenerationStep.Decoration.STRONGHOLDS;
	}
}
