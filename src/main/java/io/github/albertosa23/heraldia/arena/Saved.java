package io.github.albertosa23.heraldia.arena;

import com.mojang.serialization.Codec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import io.github.albertosa23.heraldia.Heraldia;
import java.util.Optional;
import net.fabricmc.fabric.api.attachment.v1.AttachmentRegistry;
import net.fabricmc.fabric.api.attachment.v1.AttachmentType;
import net.minecraft.core.BlockPos;

/**
 * What is saved of the arena in the overworld (Fabric API persistent attachment on the {@code ServerLevel}): the
 * origin of the placed arena (if any) and whether it was already decided to generate it on its own (in a new world) or
 * not (in an existing one), so it is not decided again on every startup.
 */
public record Saved(Optional<BlockPos> origin, boolean decided) {
	public static final Codec<Saved> CODEC = RecordCodecBuilder.create(i -> i.group(
			BlockPos.CODEC.optionalFieldOf("origen").forGetter(Saved::origin),
			Codec.BOOL.optionalFieldOf("decidida", false).forGetter(Saved::decided)).apply(i, Saved::new));
	public static final Saved EMPTY = new Saved(Optional.empty(), false);

	public Saved withOrigin(BlockPos o) {
		return new Saved(Optional.ofNullable(o), true);
	}

	public Saved decide() {
		return new Saved(origin, true);
	}

	/** The attachment, kept apart so the tests register nothing when the class loads. */
	static final class Type {
		static final AttachmentType<Saved> ARENA = AttachmentRegistry.create(Heraldia.id("arena"), b -> b.persistent(CODEC));
		/** On the player who falls in the ring: keeps their inventory and experience on respawn (saved with them). */
		static final AttachmentType<Boolean> KEEP = AttachmentRegistry.create(Heraldia.id("arena_conservar"),
				b -> b.persistent(Codec.BOOL));

		private Type() {
		}
	}
}
