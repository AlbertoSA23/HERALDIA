package io.github.albertosa23.heraldia.tesoro;

import io.github.albertosa23.heraldia.comando.InfoCommand;
import io.github.albertosa23.heraldia.comun.Medianas;
import io.github.albertosa23.heraldia.config.UniqueSeparation;
import io.github.albertosa23.heraldia.minas.Minas;
import java.util.ArrayList;
import java.util.List;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Holder;
import net.minecraft.core.QuartPos;
import net.minecraft.core.RegistryAccess;
import net.minecraft.core.SectionPos;
import net.minecraft.resources.Identifier;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.biome.BiomeResolver;
import net.minecraft.world.level.biome.Climate;
import net.minecraft.world.level.chunk.ChunkGenerator;
import net.minecraft.world.level.chunk.ChunkGeneratorStructureState;
import net.minecraft.world.level.chunk.storage.ChunkScanAccess;
import net.minecraft.world.level.levelgen.RandomState;
import net.minecraft.world.level.levelgen.densityfunction.SamplerContext;
import net.minecraft.world.level.levelgen.structure.Structure;
import net.minecraft.world.level.levelgen.structure.StructureStart;
import net.minecraft.world.level.chunk.LevelChunk;
import net.minecraft.world.level.levelgen.structure.placement.RandomSpreadStructurePlacement;

/**
 * Las candidatas de {@link Planificador}, buscadas FUERA del hilo del servidor con las mismas reglas que
 * /heraldia info nearby ({@link InfoCommand}): por cada rejilla de medianas o de minas, las casillas a menos del radio de
 * la más cercana a la más lejana; una casilla vale si su chunk guardado tiene el inicio (generada) o si la generación la
 * pondría ahí (prevista: isStructureChunk, bioma, terreno y las reglas de medianas y minas). No carga ni genera chunks:
 * lee el disco con el escáner de StructureCheck; las previstas en chunks ya cargados se confirman en el hilo del servidor
 * ({@link #confirmar}). Se para tras {@value #POR_GRUPO} por rejilla (las más cercanas).
 * Se crea y se usa en un solo hilo (el muestreador de clima es de ese hilo).
 */
final class Busqueda implements Planificador.Buscador, Planificador.Biomas {
	static final int POR_GRUPO = 3;
	private final ServerLevel level;
	private final List<InfoCommand.Group> medianas = new ArrayList<>(), minas = new ArrayList<>();
	private final ChunkGenerator generator;
	private final RandomState randomState;
	private final ChunkGeneratorStructureState state;
	private final ChunkScanAccess scanner;
	private final long seed;
	private final RegistryAccess access;
	private final Climate.Sampler sampler;
	private final BiomeResolver biomas;
	private final UniqueSeparation sep;
	private final UniqueSeparation.Viability viability;
	int celdas;   // casillas miradas (para el log)

	/** {@code grupos}: InfoCommand.groups(level), sacado en el hilo del servidor. */
	Busqueda(ServerLevel level, List<InfoCommand.Group> grupos) {
		this.level = level;
		for (InfoCommand.Group g : grupos) {
			Identifier id = g.structures().getFirst().unwrapKey().orElseThrow().identifier();
			if (Medianas.esMediana(id)) {
				medianas.add(g);
			} else if (Minas.esMina(id)) {
				minas.add(g);
			}
		}
		generator = level.getChunkSource().getGenerator();
		randomState = level.getChunkSource().randomState();
		state = level.getChunkSource().getGeneratorState();
		scanner = level.getChunkSource().chunkScanner();
		seed = state.getLevelSeed();
		access = level.registryAccess();
		sampler = randomState.createClimateSampler(SamplerContext.builder().enableCaches().build());
		biomas = generator.getBiomeSource().createResolver(sampler);
		sep = UniqueSeparation.of(access);
		viability = sep.viability(access, generator, generator.getBiomeSource(), sampler, randomState, level.getStructureTemplateManager(),
				seed, level, level.dimension());
	}

	@Override
	public List<Planificador.Candidata> buscar(Destino.Tipo tipo, int x, int z, int radio) {
		List<Hallada> hits = new ArrayList<>();
		int cx = SectionPos.blockToSectionCoord(x), cz = SectionPos.blockToSectionCoord(z), reach = radio / 16 + 1;
		long radiusSq = (long) radio * radio;
		for (InfoCommand.Group g : tipo == Destino.Tipo.MINA ? minas : medianas) {
			RandomSpreadStructurePlacement p = g.placement();
			int s = p.spacing(), ox = UniqueSeparation.offsetX(p), oz = UniqueSeparation.offsetZ(p);
			record Celda(ChunkPos c, BlockPos at, long d) {
			}
			List<Celda> cells = new ArrayList<>();
			for (int gx = Math.floorDiv(cx - reach - ox, s), gxMax = Math.floorDiv(cx + reach - ox, s); gx <= gxMax; gx++) {
				for (int gz = Math.floorDiv(cz - reach - oz, s), gzMax = Math.floorDiv(cz + reach - oz, s); gz <= gzMax; gz++) {
					ChunkPos c = p.getPotentialStructureChunk(seed, gx * s + ox, gz * s + oz);
					BlockPos at = p.getLocatePos(c);
					long dx = at.getX() - x, dz = at.getZ() - z, d = dx * dx + dz * dz;
					if (d <= radiusSq && p.isStructureChunk(state, c.x(), c.z())) {
						cells.add(new Celda(c, at, d));
					}
				}
			}
			cells.sort((a, b) -> Long.compare(a.d(), b.d()));
			int hallados = 0;
			for (Celda cell : cells) {
				if (hallados >= POR_GRUPO) {
					break;
				}
				celdas++;
				InfoCommand.Stored stored = InfoCommand.stored(scanner, cell.c());
				Holder<Structure> h = null;
				if (stored != null) {
					for (Holder<Structure> cand : g.structures()) {
						if (stored.starts().contains(cand.unwrapKey().orElseThrow().identifier())) {
							h = cand;
							break;
						}
					}
				} else {
					h = InfoCommand.firstViable(g, cell.c(), seed, level, access, generator, randomState, sampler, sep, viability);
				}
				if (h != null) {
					hallados++;
					hits.add(new Hallada(g, h, cell.c(), new Planificador.Candidata(tipo, h.unwrapKey().orElseThrow().identifier().toString(),
							cell.at().getX(), cell.at().getZ(), stored != null)));
				}
			}
		}
		return confirmar(hits);
	}

	record Hallada(InfoCommand.Group grupo, Holder<Structure> estructura, ChunkPos chunk, Planificador.Candidata candidata) {
	}

	/**
	 * Las previstas cuyo chunk ya está cargado (generado y quizá aún sin guardar, como los del spawn) se miran en el hilo
	 * del servidor, como hace /heraldia info nearby: si tiene el inicio de alguna estructura de la rejilla, es esa y
	 * generada; si no, se quita. Una sola tarea en el hilo del servidor por búsqueda, barata (solo chunks cargados); este
	 * hilo la espera.
	 */
	private List<Planificador.Candidata> confirmar(List<Hallada> hits) {
		if (hits.stream().allMatch(x -> x.candidata().generada())) {
			return hits.stream().map(Hallada::candidata).toList();
		}
		java.util.function.Supplier<List<Planificador.Candidata>> tarea = () -> {
			List<Planificador.Candidata> out = new ArrayList<>();
			for (Hallada x : hits) {
				LevelChunk ch = x.candidata().generada() ? null : level.getChunkSource().getChunkNow(x.chunk().x(), x.chunk().z());
				if (ch == null) {
					out.add(x.candidata());
					continue;
				}
				for (Holder<Structure> h : x.grupo().structures()) {
					StructureStart st = level.structureManager().getStartForStructure(h.value(), ch);
					if (st != null && st.isValid()) {
						Planificador.Candidata c = x.candidata();
						out.add(new Planificador.Candidata(c.tipo(), h.unwrapKey().orElseThrow().identifier().toString(), c.x(), c.z(), true));
						break;
					}
				}
			}
			return out;
		};
		if (level.getServer().isSameThread()) {
			return tarea.get();
		}
		try {   // con un tope: si el servidor se está parando, no se queda esperando para siempre
			return level.getServer().submit(tarea).get(10, java.util.concurrent.TimeUnit.SECONDS);
		} catch (InterruptedException e) {
			Thread.currentThread().interrupt();
			return hits.stream().map(Hallada::candidata).toList();
		} catch (java.util.concurrent.ExecutionException | java.util.concurrent.TimeoutException e) {
			return hits.stream().map(Hallada::candidata).toList();
		}
	}

	@Override
	public String en(int x, int z) {
		return biomas.getNoiseBiome(QuartPos.fromBlock(x), QuartPos.fromBlock(generator.getSeaLevel()), QuartPos.fromBlock(z))
				.unwrapKey().map(k -> k.identifier().toString()).orElse("minecraft:plains");
	}

	/** Solo los biomas (para mover el tesoro, en el hilo del servidor: un muestreo de ruido, sin chunks). */
	static final class Simple implements Planificador.Biomas {
		private final BiomeResolver biomas;
		private final int mar;

		Simple(ServerLevel level) {
			ChunkGenerator g = level.getChunkSource().getGenerator();
			biomas = g.getBiomeSource().createResolver(level.getChunkSource().randomState().createClimateSampler(SamplerContext.EMPTY_UNCACHED));
			mar = g.getSeaLevel();
		}

		@Override
		public String en(int x, int z) {
			return biomas.getNoiseBiome(QuartPos.fromBlock(x), QuartPos.fromBlock(mar), QuartPos.fromBlock(z))
					.unwrapKey().map(k -> k.identifier().toString()).orElse("minecraft:plains");
		}
	}
}
