package io.github.albertosa23.heraldia.config;

import com.mojang.serialization.Codec;
import com.mojang.serialization.MapCodec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashSet;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import net.minecraft.core.Vec3i;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.chunk.ChunkGeneratorStructureState;
import net.minecraft.world.level.levelgen.structure.placement.AbstractSpreadingStructurePlacement;
import net.minecraft.world.level.levelgen.structure.placement.RandomSpreadStructurePlacement;
import net.minecraft.world.level.levelgen.structure.placement.RandomSpreadType;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * heraldia:rejilla: un random_spread cuya separación, activación, máximo de casillas y zona de exclusión salen de
 * config/heraldia.json. Los valores del JSON del datapack (spacing, separation, exclusion_zone) son los de por defecto
 * y marcan la proporción; el grupo ("aldeas" o "unicas/&lt;id&gt;") dice qué opciones se aplican. Todo se calcula al
 * leer el datapack y queda inmutable. Hereda de random_spread para que /locate la recorra como a las vanilla.
 */
@SuppressWarnings("deprecation") // ExclusionZone está marcada obsoleta en vanilla, pero es la que usan sus aldeas
public final class GridPlacement extends RandomSpreadStructurePlacement {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	public static final MapCodec<GridPlacement> CODEC = RecordCodecBuilder.mapCodec(i -> i.group(
			Codec.STRING.fieldOf("grupo").forGetter(p -> p.group),
			Codec.intRange(1, 4096).fieldOf("spacing").forGetter(p -> p.baseSpacing),
			Codec.intRange(0, 4095).fieldOf("separation").forGetter(p -> p.baseSeparation),
			Codec.INT.fieldOf("salt").forGetter(p -> p.baseSalt),
			AbstractSpreadingStructurePlacement.ExclusionZone.CODEC.optionalFieldOf("exclusion_zone").forGetter(p -> p.baseExclusion)
	).apply(i, GridPlacement::create));

	private final String group;
	private final int baseSpacing, baseSeparation, baseSalt;
	private final Optional<AbstractSpreadingStructurePlacement.ExclusionZone> baseExclusion;
	private final boolean enabled;
	private final Set<Long> cells; // null = sin límite

	private GridPlacement(String group, int baseSpacing, int baseSeparation, int salt,
						  Optional<AbstractSpreadingStructurePlacement.ExclusionZone> baseExclusion, Settings s) {
		super(Vec3i.ZERO, AbstractSpreadingStructurePlacement.FrequencyReductionMethod.DEFAULT, 1.0F, salt, s.exclusion,
				s.spacing, s.separation, RandomSpreadType.LINEAR);
		this.group = group;
		this.baseSpacing = baseSpacing;
		this.baseSeparation = baseSeparation;
		this.baseSalt = salt;
		this.baseExclusion = baseExclusion;
		this.enabled = s.enabled;
		this.cells = s.maxCells < 0 ? null : Set.copyOf(nearestCells(s.maxCells));
	}

	private record Settings(boolean enabled, int spacing, int separation, int maxCells,
							Optional<AbstractSpreadingStructurePlacement.ExclusionZone> exclusion) {
	}

	private static GridPlacement create(String group, int spacing, int separation, int salt,
										Optional<AbstractSpreadingStructurePlacement.ExclusionZone> exclusion) {
		HeraldiaConfig cfg = HeraldiaConfig.get();
		Settings s;
		if (group.equals("aldeas")) {
			int sp = chunks(cfg.getInt("aldeas.separacion_bloques"));
			int distance = cfg.getInt("aldeas.distancia_aldeas_vanilla_bloques");
			Optional<AbstractSpreadingStructurePlacement.ExclusionZone> ex = distance == 0 ? Optional.empty()
					: exclusion.map(z -> new AbstractSpreadingStructurePlacement.ExclusionZone(z.otherSet(), Math.clamp((distance + 15) / 16, 1, 16)));
			s = new Settings(true, sp, scaled(sp, spacing, separation), cfg.getInt("aldeas.maximo"), ex);
		} else if (group.startsWith("unicas/") && cfg.has(group.replace('/', '.') + ".separacion_bloques")) {
			String key = group.replace('/', '.');
			int sp = chunks(cfg.getInt(key + ".separacion_bloques"));
			s = new Settings(cfg.getBool(key + ".activada"), sp, scaled(sp, spacing, separation), -1, exclusion);
		} else {
			LOGGER.warn("Heraldia: grupo de colocación sin opciones {}; se usan los valores del datapack", group);
			s = new Settings(true, spacing, Math.min(separation, spacing - 1), -1, exclusion);
		}
		LOGGER.info("Heraldia: rejilla {}: {}, cada {} chunks (separación mínima {}), {}, exclusión {}", group,
				s.enabled ? "activada" : "desactivada", s.spacing, s.separation,
				s.maxCells < 0 ? "sin máximo" : "máximo " + s.maxCells + " casillas",
				s.exclusion.map(z -> z.chunkCount() + " chunks").orElse("ninguna"));
		return new GridPlacement(group, spacing, separation, salt, exclusion, s);
	}

	private static int chunks(int blocks) {
		return Math.clamp(Math.round(blocks / 16.0F), 2, 4096);
	}

	/** Separación mínima con la misma proporción que la del datapack (62/94 en las aldeas). */
	private static int scaled(int spacing, int baseSpacing, int baseSeparation) {
		return Math.clamp(Math.round((float) spacing * baseSeparation / baseSpacing), 0, spacing - 1);
	}

	/** Las n casillas cuyo centro está más cerca del 0,0 (empates por z y luego x): deterministas, sin datos guardados. */
	private static Set<Long> nearestCells(int n) {
		int r = (int) Math.ceil(Math.sqrt(n)) + 1;
		List<int[]> all = new ArrayList<>();
		for (int x = -r; x < r; x++) {
			for (int z = -r; z < r; z++) {
				all.add(new int[]{x, z});
			}
		}
		all.sort(Comparator.<int[]>comparingDouble(c -> (c[0] + 0.5) * (c[0] + 0.5) + (c[1] + 0.5) * (c[1] + 0.5))
				.thenComparingInt(c -> c[1]).thenComparingInt(c -> c[0]));
		Set<Long> out = new HashSet<>();
		for (int i = 0; i < n; i++) {
			out.add(ChunkPos.pack(all.get(i)[0], all.get(i)[1]));
		}
		return out;
	}

	private boolean allowed(int chunkX, int chunkZ) {
		return enabled && (cells == null || cells.contains(ChunkPos.pack(Math.floorDiv(chunkX, spacing()), Math.floorDiv(chunkZ, spacing()))));
	}

	@Override
	protected boolean isPlacementChunk(ChunkGeneratorStructureState state, int chunkX, int chunkZ) {
		return allowed(chunkX, chunkZ) && super.isPlacementChunk(state, chunkX, chunkZ);
	}

	/** /locate no pasa por isPlacementChunk sino por aquí: así no señala casillas desactivadas o fuera del máximo. */
	@Override
	public boolean applyAdditionalChunkRestrictions(int chunkX, int chunkZ, long seed) {
		return allowed(chunkX, chunkZ) && super.applyAdditionalChunkRestrictions(chunkX, chunkZ, seed);
	}

	@Override
	@SuppressWarnings("unchecked")
	public MapCodec<RandomSpreadStructurePlacement> codec() {
		return (MapCodec<RandomSpreadStructurePlacement>) (MapCodec<?>) CODEC;
	}
}
