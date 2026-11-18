package io.github.albertosa23.heraldia.mixin;

import io.github.albertosa23.heraldia.common.UnwrittenRegions;
import java.util.concurrent.CompletableFuture;
import java.util.function.Supplier;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.StreamTagVisitor;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.chunk.storage.IOWorker;
import net.minecraft.world.level.chunk.storage.RegionFileStorage;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/**
 * Mixin (last resort: the round trip to the storage thread is inside vanilla): a scan of a chunk that is surely not on
 * disk ({@link UnwrittenRegions}) answers "no data" right away, the same answer the storage thread would give. The
 * structure searches scan every candidate chunk they walk (StructureCheck); a /locate that finds nothing spent 1.4 s of its
 * 1.6 s on those round trips. Cheap early exit: one set lookup per scan, and one file check per region not yet seen.
 */
@Mixin(IOWorker.class)
abstract class IOWorkerMixin {
	@Shadow
	@Final
	private RegionFileStorage storage;

	@Unique
	private volatile UnwrittenRegions heraldia$regions;

	@Unique
	private UnwrittenRegions heraldia$regions() {
		UnwrittenRegions r = heraldia$regions;
		if (r == null) {
			synchronized (this) {
				r = heraldia$regions;
				if (r == null) {
					RegionFileStorageMixin s = (RegionFileStorageMixin) (Object) storage;
					r = new UnwrittenRegions(s::heraldia$regionPath);
					heraldia$regions = r;
				}
			}
		}
		return r;
	}

	/** Every store goes through here (the one with a CompoundTag calls this one). */
	@Inject(method = "store(Lnet/minecraft/world/level/ChunkPos;Ljava/util/function/Supplier;)Ljava/util/concurrent/CompletableFuture;", at = @At("HEAD"))
	private void heraldia$storeLater(ChunkPos pos, Supplier<CompoundTag> tag, CallbackInfoReturnable<CompletableFuture<Void>> cir) {
		heraldia$regions().written(pos);
	}

	@Inject(method = "scanChunk", at = @At("HEAD"), cancellable = true)
	private void heraldia$scan(ChunkPos pos, StreamTagVisitor visitor, CallbackInfoReturnable<CompletableFuture<Void>> cir) {
		if (heraldia$regions().absent(pos)) {
			cir.setReturnValue(CompletableFuture.completedFuture(null));
		}
	}
}
