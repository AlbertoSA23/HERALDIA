package io.github.albertosa23.heraldia.uniques.atlantis;

import io.github.albertosa23.heraldia.Heraldia;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLevelEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.minecraft.core.Registry;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.world.level.levelgen.structure.StructureType;
import net.minecraft.world.level.levelgen.structure.pieces.StructurePieceType;

/** Atlantis: only one per world. This registers what the data cannot express (see docs/unicas/atlantida.md). */
public final class Atlantis {
	public static final StructureType<AtlantisStructure> STRUCTURE = () -> AtlantisStructure.CODEC;
	public static final StructurePieceType BASE_PIECE = (StructurePieceType.ContextlessType) BasePiece::new;

	private Atlantis() {
	}

	public static void register() {
		Registry.register(BuiltInRegistries.STRUCTURE_PLACEMENT, Heraldia.id("mundial"), WorldPlacement.CODEC);
		Registry.register(BuiltInRegistries.STRUCTURE_TYPE, Heraldia.id("atlantida"), STRUCTURE);
		Registry.register(BuiltInRegistries.STRUCTURE_PIECE, Heraldia.id("atlantida_base"), BASE_PIECE);
		ServerLevelEvents.LOAD.register(AtlantisAnchor::onLevelLoad);
		ServerLifecycleEvents.SERVER_STOPPED.register(server -> AtlantisAnchor.clear());
	}
}
