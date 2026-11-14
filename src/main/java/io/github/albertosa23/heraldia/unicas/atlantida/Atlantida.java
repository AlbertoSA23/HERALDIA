package io.github.albertosa23.heraldia.unicas.atlantida;

import io.github.albertosa23.heraldia.Heraldia;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLevelEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.minecraft.core.Registry;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.world.level.levelgen.structure.StructureType;
import net.minecraft.world.level.levelgen.structure.pieces.StructurePieceType;

/** La Atlántida: una sola por mundo. Aquí se registra lo que los datos no pueden expresar (ver docs/unicas/atlantida.md). */
public final class Atlantida {
	public static final StructureType<AtlantisStructure> STRUCTURE = () -> AtlantisStructure.CODEC;
	public static final StructurePieceType BASE_PIECE = (StructurePieceType.ContextlessType) BasePiece::new;

	private Atlantida() {
	}

	public static void register() {
		Registry.register(BuiltInRegistries.STRUCTURE_PLACEMENT, Heraldia.id("mundial"), WorldPlacement.CODEC);
		Registry.register(BuiltInRegistries.STRUCTURE_TYPE, Heraldia.id("atlantida"), STRUCTURE);
		Registry.register(BuiltInRegistries.STRUCTURE_PIECE, Heraldia.id("atlantida_base"), BASE_PIECE);
		ServerLevelEvents.LOAD.register(AtlantisAnchor::onLevelLoad);
		ServerLifecycleEvents.SERVER_STOPPED.register(server -> AtlantisAnchor.clear());
	}
}
