package io.github.albertosa23.heraldia.mixin;

import java.nio.file.Path;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.chunk.storage.RegionFileStorage;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Invoker;

/** Accessor (no code of its own): the path of a chunk's region file, computed by the game itself (IOWorkerMixin). */
@Mixin(RegionFileStorage.class)
public interface RegionFileStorageMixin {
	@Invoker("regionPath")
	Path heraldia$regionPath(ChunkPos pos);
}
