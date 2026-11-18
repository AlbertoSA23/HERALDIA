package io.github.albertosa23.heraldia.coast;

import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.common.MediumStructures;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.mines.Mines;
import java.util.List;
import net.minecraft.core.Registry;
import net.minecraft.core.RegistryAccess;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.Identifier;
import net.minecraft.resources.ResourceKey;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.LevelHeightAccessor;
import net.minecraft.world.level.biome.BiomeSource;
import net.minecraft.world.level.biome.Climate;
import net.minecraft.world.level.chunk.ChunkGenerator;
import net.minecraft.world.level.levelgen.RandomState;
import net.minecraft.world.level.levelgen.structure.StructureSet;
import net.minecraft.world.level.levelgen.structure.templatesystem.StructureTemplateManager;
import org.jspecify.annotations.Nullable;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Lighthouses and shipwrecks on the coast (heraldia:costa/&lt;type&gt;/&lt;style&gt;/&lt;variant&gt;, tools/gen/shore, T42): one
 * structure_set per type with its heraldia:rejilla grid (group costa/&lt;type&gt;, options faros.* and naufragios.*) and the
 * own type {@link CoastStructure}, which looks for the shore. The placement rule is the mines' one ({@link Mines#family}),
 * with its own family, and it also yields to the mines:
 * <ul>
 * <li>never in the zone of a village or a unique that wins (medianas.distancia_aldeas_unicas_bloques), next to a
 * vanilla or other mod's structure that shows above ground (vanilla shipwrecks and ocean ruins included) nor in Atlantis;</li>
 * <li>within medianas.distancia_minima.bloques of a medium structure or a mine entrance that wins (they always yield: neither
 * the mediums nor the mines know about the coast, so nothing already made changes place);</li>
 * <li>between a lighthouse and a shipwreck, that same distance (the uniques' range recursion). Two of the same type are
 * kept apart by their grid.</li>
 * </ul>
 * Roads do not run over them: their layout skips the boxes of surface structures. It only runs in the candidate chunks
 * (one per type every 48-64 chunks per side, and only on beaches).
 */
public final class Coast {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	public static final String PREFIX = "costa/";
	public static final List<String> TYPES = List.of("faro", "naufragio");
	public static final String LIGHTHOUSES = "faros", SHIPWRECKS = "naufragios";
	private static volatile @Nullable Coast cached;

	private final Object source;
	private final Mines family;

	private Coast(Object source, Mines family) {
		this.source = source;
		this.family = family;
	}

	/** Structure type of the lighthouses and shipwrecks. One line in Heraldia. */
	public static void register() {
		Registry.register(BuiltInRegistries.STRUCTURE_TYPE, Heraldia.id("costa"), CoastStructure.TYPE);
	}

	/** Cheap: only heraldia:costa/* get past here. */
	public static boolean isCoast(Identifier id) {
		return id.getNamespace().equals(Heraldia.MOD_ID) && id.getPath().startsWith(PREFIX);
	}

	/** Prefix of a type's options ("faros" or "naufragios"), or null if it is not a coast one. */
	public static @Nullable String option(String type) {
		return switch (type) {
			case "faro" -> LIGHTHOUSES;
			case "naufragio" -> SHIPWRECKS;
			default -> null;
		};
	}

	/** Type of a coast structure (heraldia:costa/&lt;type&gt;/...): "faro" or "naufragio". */
	public static String type(Identifier id) {
		return id.getPath().split("/")[1];
	}

	/** Can the type spawn with the configuration in use? */
	public static boolean enabled(HeraldiaConfig cfg, String type) {
		String o = option(type);
		return o != null && cfg.getBool(o + ".activado");
	}

	public static Coast of(RegistryAccess access) {
		Registry<StructureSet> sets = access.lookupOrThrow(Registries.STRUCTURE_SET);
		Coast t = cached;
		if (t == null || t.source != sets) {
			HeraldiaConfig cfg = HeraldiaConfig.get();
			int distance = cfg.getInt(MediumStructures.DISTANCE);
			t = new Coast(sets, Mines.family(sets, access, PREFIX, distance));
			LOGGER.info("Heraldia: costa: faros {} cada {} bloques, naufragios {} cada {} bloques; {} tipos, a {} bloques de aldeas y "
							+ "únicas y a {} de las medianas, las minas y entre ellos", cfg.getBool(LIGHTHOUSES + ".activado") ? "activados" : "desactivados",
					cfg.getInt(LIGHTHOUSES + ".separacion_bloques"), cfg.getBool(SHIPWRECKS + ".activado") ? "activados" : "desactivados",
					cfg.getInt(SHIPWRECKS + ".separacion_bloques"), t.family.types(), cfg.getInt(MediumStructures.ZONE), distance);
			cached = t;
		}
		return t;
	}

	/** The family's rule (tests and /heraldia info). */
	public Mines family() {
		return family;
	}

	/** The lighthouse or shipwreck id starting at (chunkX, chunkZ) does not win (see the class). Only for the coast; the rest, false. */
	public boolean rejects(Identifier id, int chunkX, int chunkZ, long seed, RegistryAccess access, ChunkGenerator generator,
						   BiomeSource biomeSource, Climate.Sampler sampler, RandomState randomState, StructureTemplateManager templates,
						   LevelHeightAccessor height, ResourceKey<Level> dimension) {
		int i = family.type(id);
		if (i < 0 || dimension != Level.OVERWORLD) {
			return false;
		}
		MediumStructures med = MediumStructures.of(access);
		MediumStructures.Context c = med.context(id, access, generator, biomeSource, sampler, randomState, templates, seed, height, dimension);
		Mines mines = Mines.of(access);
		int distance = family.distance();
		MediumStructures.Zone mediums = (x, z) -> med.near(x, z, distance, seed, c);
		MediumStructures.Styles ofMines = mines.styles(access, generator, biomeSource, sampler, randomState, templates, seed, height);
		MediumStructures.Zone near = (x, z) -> mediums.occupied(x, z)
				|| mines.near(x, z, distance, seed, c.zone(), ofMines, c.atlantis(), mediums);
		return family.rejects(i, chunkX, chunkZ, seed, c.zone(),
				family.styles(access, generator, biomeSource, sampler, randomState, templates, seed, height), c.atlantis(), near);
	}
}
