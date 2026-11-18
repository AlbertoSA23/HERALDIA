package io.github.albertosa23.heraldia.treasure;

import io.github.albertosa23.heraldia.command.InfoCommand;
import io.github.albertosa23.heraldia.common.MediumStructures;
import io.github.albertosa23.heraldia.config.UniqueSeparation;
import io.github.albertosa23.heraldia.mines.Mines;
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
 * The candidates for {@link Planner}, searched OFF the server thread with the same rules as
 * /heraldia info nearby ({@link InfoCommand}): for each medium or mine grid, the cells within the radius from
 * nearest to farthest; a cell is valid if its saved chunk has the start (generated) or if generation would put
 * it there (expected: isStructureChunk, biome, terrain and the mediums' and mines' rules). It neither loads nor generates chunks:
 * it reads the disk with StructureCheck's scanner; the expected ones in already loaded chunks are confirmed on the server thread
 * ({@link #confirm}). It stops after {@value #PER_GROUP} per grid (the nearest ones).
 * It is created and used on a single thread (the climate sampler belongs to that thread).
 */
final class Search implements Planner.Finder, Planner.Biomes {
	static final int PER_GROUP = 3;
	private final ServerLevel level;
	private final List<InfoCommand.Group> mediums = new ArrayList<>(), mines = new ArrayList<>();
	private final ChunkGenerator generator;
	private final RandomState randomState;
	private final ChunkGeneratorStructureState state;
	private final ChunkScanAccess scanner;
	private final long seed;
	private final RegistryAccess access;
	private final Climate.Sampler sampler;
	private final BiomeResolver biomes;
	private final UniqueSeparation sep;
	private final UniqueSeparation.Viability viability;
	int cellsVisited;   // cells checked (for the log)

	/** {@code groups}: InfoCommand.groups(level), taken on the server thread. */
	Search(ServerLevel level, List<InfoCommand.Group> groups) {
		this.level = level;
		for (InfoCommand.Group g : groups) {
			Identifier id = g.structures().getFirst().unwrapKey().orElseThrow().identifier();
			if (MediumStructures.isMedium(id)) {
				mediums.add(g);
			} else if (Mines.isMine(id)) {
				mines.add(g);
			}
		}
		generator = level.getChunkSource().getGenerator();
		randomState = level.getChunkSource().randomState();
		state = level.getChunkSource().getGeneratorState();
		scanner = level.getChunkSource().chunkScanner();
		seed = state.getLevelSeed();
		access = level.registryAccess();
		sampler = randomState.createClimateSampler(SamplerContext.builder().enableCaches().build());
		biomes = generator.getBiomeSource().createResolver(sampler);
		sep = UniqueSeparation.of(access);
		viability = sep.viability(access, generator, generator.getBiomeSource(), sampler, randomState, level.getStructureTemplateManager(),
				seed, level, level.dimension());
	}

	@Override
	public List<Planner.Candidate> search(Destination.Type type, int x, int z, int radius) {
		List<Found> hits = new ArrayList<>();
		int cx = SectionPos.blockToSectionCoord(x), cz = SectionPos.blockToSectionCoord(z), reach = radius / 16 + 1;
		long radiusSq = (long) radius * radius;
		for (InfoCommand.Group g : type == Destination.Type.MINE ? mines : mediums) {
			RandomSpreadStructurePlacement p = g.placement();
			int s = p.spacing(), ox = UniqueSeparation.offsetX(p), oz = UniqueSeparation.offsetZ(p);
			record Cell(ChunkPos c, BlockPos at, long d) {
			}
			List<Cell> cells = new ArrayList<>();
			for (int gx = Math.floorDiv(cx - reach - ox, s), gxMax = Math.floorDiv(cx + reach - ox, s); gx <= gxMax; gx++) {
				for (int gz = Math.floorDiv(cz - reach - oz, s), gzMax = Math.floorDiv(cz + reach - oz, s); gz <= gzMax; gz++) {
					ChunkPos c = p.getPotentialStructureChunk(seed, gx * s + ox, gz * s + oz);
					BlockPos at = p.getLocatePos(c);
					long dx = at.getX() - x, dz = at.getZ() - z, d = dx * dx + dz * dz;
					if (d <= radiusSq && p.isStructureChunk(state, c.x(), c.z())) {
						cells.add(new Cell(c, at, d));
					}
				}
			}
			cells.sort((a, b) -> Long.compare(a.d(), b.d()));
			int found = 0;
			for (Cell cell : cells) {
				if (found >= PER_GROUP) {
					break;
				}
				cellsVisited++;
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
					found++;
					hits.add(new Found(g, h, cell.c(), new Planner.Candidate(type, h.unwrapKey().orElseThrow().identifier().toString(),
							cell.at().getX(), cell.at().getZ(), stored != null)));
				}
			}
		}
		return confirm(hits);
	}

	record Found(InfoCommand.Group group, Holder<Structure> structure, ChunkPos chunk, Planner.Candidate candidate) {
	}

	/**
	 * The expected ones whose chunk is already loaded (generated and maybe not saved yet, like the spawn's) are checked on the
	 * server thread, as /heraldia info nearby does: if it has the start of some structure of the grid, it is that one and
	 * generated; otherwise, it is removed. A single task on the server thread per search, cheap (only loaded chunks); this
	 * thread waits for it.
	 */
	private List<Planner.Candidate> confirm(List<Found> hits) {
		if (hits.stream().allMatch(x -> x.candidate().generated())) {
			return hits.stream().map(Found::candidate).toList();
		}
		java.util.function.Supplier<List<Planner.Candidate>> task = () -> {
			List<Planner.Candidate> out = new ArrayList<>();
			for (Found x : hits) {
				LevelChunk ch = x.candidate().generated() ? null : level.getChunkSource().getChunkNow(x.chunk().x(), x.chunk().z());
				if (ch == null) {
					out.add(x.candidate());
					continue;
				}
				for (Holder<Structure> h : x.group().structures()) {
					StructureStart st = level.structureManager().getStartForStructure(h.value(), ch);
					if (st != null && st.isValid()) {
						Planner.Candidate c = x.candidate();
						out.add(new Planner.Candidate(c.type(), h.unwrapKey().orElseThrow().identifier().toString(), c.x(), c.z(), true));
						break;
					}
				}
			}
			return out;
		};
		if (level.getServer().isSameThread()) {
			return task.get();
		}
		try {   // with a cap: if the server is stopping, it does not wait forever
			return level.getServer().submit(task).get(10, java.util.concurrent.TimeUnit.SECONDS);
		} catch (InterruptedException e) {
			Thread.currentThread().interrupt();
			return hits.stream().map(Found::candidate).toList();
		} catch (java.util.concurrent.ExecutionException | java.util.concurrent.TimeoutException e) {
			return hits.stream().map(Found::candidate).toList();
		}
	}

	@Override
	public String en(int x, int z) {
		return biomes.getNoiseBiome(QuartPos.fromBlock(x), QuartPos.fromBlock(generator.getSeaLevel()), QuartPos.fromBlock(z))
				.unwrapKey().map(k -> k.identifier().toString()).orElse("minecraft:plains");
	}

	/** Only the biomes (to move the treasure, on the server thread: a noise sample, no chunks). */
	static final class Simple implements Planner.Biomes {
		private final BiomeResolver biomes;
		private final int seaSide;

		Simple(ServerLevel level) {
			ChunkGenerator g = level.getChunkSource().getGenerator();
			biomes = g.getBiomeSource().createResolver(level.getChunkSource().randomState().createClimateSampler(SamplerContext.EMPTY_UNCACHED));
			seaSide = g.getSeaLevel();
		}

		@Override
		public String en(int x, int z) {
			return biomes.getNoiseBiome(QuartPos.fromBlock(x), QuartPos.fromBlock(seaSide), QuartPos.fromBlock(z))
					.unwrapKey().map(k -> k.identifier().toString()).orElse("minecraft:plains");
		}
	}
}
