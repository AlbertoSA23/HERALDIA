package io.github.albertosa23.heraldia.common;

import java.util.List;
import java.util.Optional;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.levelgen.structure.PoolElementStructurePiece;
import net.minecraft.world.level.levelgen.structure.StructurePiece;
import net.minecraft.world.level.levelgen.structure.pools.SinglePoolElement;
import net.minecraft.world.level.levelgen.structure.templatesystem.StructurePlaceSettings;
import net.minecraft.world.level.levelgen.structure.templatesystem.StructureTemplate;

/**
 * The blocks a template put in the world: the blocks of {@code block} in the template of a pool piece, at their world position
 * (the same computation as when the piece was placed: its position and rotation, no mirror or pivot). Used by the restocking loot
 * (the original table of an already looted chest) and by the cleared uniques (where their spawners are, also in unloaded
 * chunks). What a processor changed when placing it is not known here: the caller checks the block that is really there.
 */
public final class TemplateBlocks {
	private TemplateBlocks() {
	}

	/** The blocks of {@code block} of a piece's template, at their world position; empty if the piece is not a single pool element. */
	public static List<StructureTemplate.StructureBlockInfo> of(ServerLevel level, StructurePiece piece, Block block) {
		if (!(piece instanceof PoolElementStructurePiece p) || !(p.getElement() instanceof SinglePoolElement e)) {
			return List.of();
		}
		Optional<StructureTemplate> t = level.getStructureTemplateManager().get(e.getTemplateLocation());
		if (t.isEmpty()) {
			return List.of();
		}
		StructurePlaceSettings s = new StructurePlaceSettings().setRotation(p.getRotation());
		return t.get().filterBlocks(p.getPosition(), s, block);
	}
}
