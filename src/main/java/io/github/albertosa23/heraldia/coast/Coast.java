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
 * Faros y naufragios de la costa (heraldia:costa/&lt;tipo&gt;/&lt;estilo&gt;/&lt;variante&gt;, tools/gen/litoral, T42): un
 * structure_set por tipo con su rejilla heraldia:rejilla (grupo costa/&lt;tipo&gt;, opciones faros.* y naufragios.*) y el
 * tipo propio {@link CoastStructure}, que busca la orilla. La regla de colocación es la de las minas ({@link Mines#family}),
 * con su familia propia, y cede además a las minas:
 * <ul>
 * <li>nunca en la zona de una aldea o una única que sale (medianas.distancia_aldeas_unicas_bloques), junto a una
 * estructura vanilla o de otro mod que asoma (los naufragios y ruinas marinas vanilla incluidos) ni en la Atlántida;</li>
 * <li>a menos de medianas.distancia_minima.bloques de una mediana o una entrada a mina que sale (ceden siempre: ni las
 * medianas ni las minas saben de la costa, así que nada de lo ya hecho cambia de sitio);</li>
 * <li>entre un faro y un naufragio, esa misma distancia (la recursión por rangos de las únicas). Dos del mismo tipo los
 * separa su rejilla.</li>
 * </ul>
 * Los caminos no pasan por encima: su trazado salta las cajas de las estructuras de superficie. Solo corre en los chunks
 * candidatos (uno por tipo cada 48-64 chunks de lado, y solo en las playas).
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

	/** Tipo de estructura de los faros y naufragios. Una línea en Heraldia. */
	public static void register() {
		Registry.register(BuiltInRegistries.STRUCTURE_TYPE, Heraldia.id("costa"), CoastStructure.TYPE);
	}

	/** Barato: solo las heraldia:costa/* pasan de aquí. */
	public static boolean isCoast(Identifier id) {
		return id.getNamespace().equals(Heraldia.MOD_ID) && id.getPath().startsWith(PREFIX);
	}

	/** Prefijo de las opciones de un tipo («faros» o «naufragios»), o null si no es de la costa. */
	public static @Nullable String option(String type) {
		return switch (type) {
			case "faro" -> LIGHTHOUSES;
			case "naufragio" -> SHIPWRECKS;
			default -> null;
		};
	}

	/** Tipo de una estructura de la costa (heraldia:costa/&lt;tipo&gt;/...): «faro» o «naufragio». */
	public static String type(Identifier id) {
		return id.getPath().split("/")[1];
	}

	/** ¿Puede salir el tipo con la configuración en uso? */
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

	/** La regla de la familia (pruebas e /heraldia info). */
	public Mines family() {
		return family;
	}

	/** El faro o naufragio id con inicio en (chunkX, chunkZ) no sale (ver la clase). Solo para la costa; el resto, falso. */
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
