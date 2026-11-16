package io.github.albertosa23.heraldia.arena;

import com.mojang.serialization.Codec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import io.github.albertosa23.heraldia.Heraldia;
import java.util.Optional;
import net.fabricmc.fabric.api.attachment.v1.AttachmentRegistry;
import net.fabricmc.fabric.api.attachment.v1.AttachmentType;
import net.minecraft.core.BlockPos;

/**
 * Lo que se guarda de la arena en el mundo principal (adjunto persistente de Fabric API en el {@code ServerLevel}): el
 * origen de la arena colocada (si hay) y si ya se decidió generarla sola (en un mundo nuevo) o no (en uno existente),
 * para no volver a decidirlo en cada arranque.
 */
public record Guardada(Optional<BlockPos> origen, boolean decidida) {
	public static final Codec<Guardada> CODEC = RecordCodecBuilder.create(i -> i.group(
			BlockPos.CODEC.optionalFieldOf("origen").forGetter(Guardada::origen),
			Codec.BOOL.optionalFieldOf("decidida", false).forGetter(Guardada::decidida)).apply(i, Guardada::new));
	public static final Guardada VACIA = new Guardada(Optional.empty(), false);

	public Guardada conOrigen(BlockPos o) {
		return new Guardada(Optional.ofNullable(o), true);
	}

	public Guardada decidir() {
		return new Guardada(origen, true);
	}

	/** El adjunto, aparte para que los tests no registren nada al cargar la clase. */
	static final class Tipo {
		static final AttachmentType<Guardada> ARENA = AttachmentRegistry.create(Heraldia.id("arena"), b -> b.persistent(CODEC));
		/** En el jugador que cae en el ruedo: conserva su inventario y su experiencia al reaparecer (se guarda con él). */
		static final AttachmentType<Boolean> CONSERVAR = AttachmentRegistry.create(Heraldia.id("arena_conservar"),
				b -> b.persistent(Codec.BOOL));

		private Tipo() {
		}
	}
}
