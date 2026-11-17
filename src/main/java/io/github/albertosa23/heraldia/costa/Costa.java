package io.github.albertosa23.heraldia.costa;

import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.comun.Medianas;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.minas.Minas;
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
 * Faros y naufragios de la costa (heraldia:costa/&lt;tipo&gt;/&lt;estilo&gt;/&lt;variante&gt;, tools/gen/costa, T42): un
 * structure_set por tipo con su rejilla heraldia:rejilla (grupo costa/&lt;tipo&gt;, opciones faros.* y naufragios.*) y el
 * tipo propio {@link CostaStructure}, que busca la orilla. La regla de colocación es la de las minas ({@link Minas#familia}),
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
public final class Costa {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	public static final String PREFIJO = "costa/";
	public static final List<String> TIPOS = List.of("faro", "naufragio");
	public static final String FAROS = "faros", NAUFRAGIOS = "naufragios";
	private static volatile @Nullable Costa cached;

	private final Object source;
	private final Minas familia;

	private Costa(Object source, Minas familia) {
		this.source = source;
		this.familia = familia;
	}

	/** Tipo de estructura de los faros y naufragios. Una línea en Heraldia. */
	public static void registrar() {
		Registry.register(BuiltInRegistries.STRUCTURE_TYPE, Heraldia.id("costa"), CostaStructure.TYPE);
	}

	/** Barato: solo las heraldia:costa/* pasan de aquí. */
	public static boolean esCosta(Identifier id) {
		return id.getNamespace().equals(Heraldia.MOD_ID) && id.getPath().startsWith(PREFIJO);
	}

	/** Prefijo de las opciones de un tipo («faros» o «naufragios»), o null si no es de la costa. */
	public static @Nullable String opcion(String tipo) {
		return switch (tipo) {
			case "faro" -> FAROS;
			case "naufragio" -> NAUFRAGIOS;
			default -> null;
		};
	}

	/** Tipo de una estructura de la costa (heraldia:costa/&lt;tipo&gt;/...): «faro» o «naufragio». */
	public static String tipo(Identifier id) {
		return id.getPath().split("/")[1];
	}

	/** ¿Puede salir el tipo con la configuración en uso? */
	public static boolean activado(HeraldiaConfig cfg, String tipo) {
		String o = opcion(tipo);
		return o != null && cfg.getBool(o + ".activado");
	}

	public static Costa of(RegistryAccess access) {
		Registry<StructureSet> sets = access.lookupOrThrow(Registries.STRUCTURE_SET);
		Costa t = cached;
		if (t == null || t.source != sets) {
			HeraldiaConfig cfg = HeraldiaConfig.get();
			int distancia = cfg.getInt(Medianas.DISTANCIA);
			t = new Costa(sets, Minas.familia(sets, access, PREFIJO, distancia));
			LOGGER.info("Heraldia: costa: faros {} cada {} bloques, naufragios {} cada {} bloques; {} tipos, a {} bloques de aldeas y "
							+ "únicas y a {} de las medianas, las minas y entre ellos", cfg.getBool(FAROS + ".activado") ? "activados" : "desactivados",
					cfg.getInt(FAROS + ".separacion_bloques"), cfg.getBool(NAUFRAGIOS + ".activado") ? "activados" : "desactivados",
					cfg.getInt(NAUFRAGIOS + ".separacion_bloques"), t.familia.tipos(), cfg.getInt(Medianas.ZONA), distancia);
			cached = t;
		}
		return t;
	}

	/** La regla de la familia (pruebas e /heraldia info). */
	public Minas familia() {
		return familia;
	}

	/** El faro o naufragio id con inicio en (chunkX, chunkZ) no sale (ver la clase). Solo para la costa; el resto, falso. */
	public boolean rechaza(Identifier id, int chunkX, int chunkZ, long seed, RegistryAccess access, ChunkGenerator generator,
						   BiomeSource biomeSource, Climate.Sampler sampler, RandomState randomState, StructureTemplateManager templates,
						   LevelHeightAccessor height, ResourceKey<Level> dimension) {
		int i = familia.tipo(id);
		if (i < 0 || dimension != Level.OVERWORLD) {
			return false;
		}
		Medianas med = Medianas.of(access);
		Medianas.Contexto c = med.contexto(id, access, generator, biomeSource, sampler, randomState, templates, seed, height, dimension);
		Minas minas = Minas.of(access);
		int distancia = familia.distancia();
		Medianas.Zona medianas = (x, z) -> med.cerca(x, z, distancia, seed, c);
		Medianas.Estilos deMinas = minas.estilos(access, generator, biomeSource, sampler, randomState, templates, seed, height);
		Medianas.Zona cerca = (x, z) -> medianas.ocupada(x, z)
				|| minas.cerca(x, z, distancia, seed, c.zona(), deMinas, c.atlantida(), medianas);
		return familia.rechaza(i, chunkX, chunkZ, seed, c.zona(),
				familia.estilos(access, generator, biomeSource, sampler, randomState, templates, seed, height), c.atlantida(), cerca);
	}
}
