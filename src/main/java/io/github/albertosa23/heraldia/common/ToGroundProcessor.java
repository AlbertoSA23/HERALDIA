package io.github.albertosa23.heraldia.common;

import com.mojang.serialization.Codec;
import com.mojang.serialization.MapCodec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import io.github.albertosa23.heraldia.Heraldia;
import java.util.ArrayList;
import java.util.List;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Registry;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.tags.BlockTags;
import net.minecraft.world.level.ServerLevelAccessor;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.levelgen.structure.BoundingBox;
import net.minecraft.world.level.levelgen.structure.templatesystem.StructurePlaceSettings;
import net.minecraft.world.level.levelgen.structure.templatesystem.StructureProcessor;
import net.minecraft.world.level.levelgen.structure.templatesystem.StructureTemplate.StructureBlockInfo;

/**
 * Prolonga hacia abajo, hasta el suelo firme (atraviesa aire, agua y plantas), los bloques indicados de la fila inferior
 * de la plantilla: así los pilares del acueducto, los cimientos de las casas de las aldeas en ladera y los pilotes del
 * muelle llegan siempre al terreno. La fila inferior se mira en la plantilla (lista {@code original}, alineada con
 * {@code processed} mientras los procesadores anteriores solo añaden al final), así que vale también para piezas
 * {@code terrain_matching}, cuyos bloques ya bajó la gravedad. Solo lee y escribe dentro del chunk que se está generando.
 * Id publicado {@code heraldia:acueducto_hasta_el_suelo} (no se renombra).
 */
public record ToGroundProcessor(List<Block> blocks, int maxDepth) implements StructureProcessor {
	public static final MapCodec<ToGroundProcessor> CODEC = RecordCodecBuilder.mapCodec(i -> i.group(
			BuiltInRegistries.BLOCK.byNameCodec().listOf().fieldOf("bloques").forGetter(ToGroundProcessor::blocks),
			Codec.intRange(1, 128).optionalFieldOf("profundidad_maxima", 64).forGetter(ToGroundProcessor::maxDepth)
	).apply(i, ToGroundProcessor::new));

	public static void register() {
		Registry.register(BuiltInRegistries.STRUCTURE_PROCESSOR, Heraldia.id("acueducto_hasta_el_suelo"), CODEC);
	}

	@Override
	public MapCodec<? extends StructureProcessor> codec() {
		return CODEC;
	}

	@Override
	public List<StructureBlockInfo> finalizeProcessing(ServerLevelAccessor level, BlockPos offset, BlockPos pivot,
			List<StructureBlockInfo> original, List<StructureBlockInfo> processed, StructurePlaceSettings settings) {
		BoundingBox box = settings.getBoundingBox();
		List<StructureBlockInfo> out = new ArrayList<>(processed);
		int n = Math.min(original.size(), processed.size());
		for (int i = 0; i < n; i++) {
			StructureBlockInfo info = processed.get(i);
			BlockPos pos = info.pos();
			if (original.get(i).pos().getY() != 0 || !blocks.contains(info.state().getBlock())
					|| (box != null && !box.isInside(pos))) {
				continue;
			}
			for (int d = 1; d <= maxDepth && pos.getY() - d >= level.getMinY(); d++) {
				BlockPos p = pos.below(d);
				if (isGround(level.getBlockState(p))) {
					break;
				}
				out.add(new StructureBlockInfo(p, info.state(), null));
			}
		}
		return out;
	}

	private static boolean isGround(BlockState s) {
		return !s.isAir() && s.getFluidState().isEmpty() && !s.canBeReplaced() && !s.is(BlockTags.LEAVES);
	}
}
