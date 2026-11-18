package io.github.albertosa23.heraldia.villages;

import com.mojang.serialization.Codec;
import com.mojang.serialization.MapCodec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.common.HeightCache;
import io.github.albertosa23.heraldia.common.Heights;
import io.github.albertosa23.heraldia.common.Generation;
import io.github.albertosa23.heraldia.common.Profiler;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import it.unimi.dsi.fastutil.longs.Long2IntOpenHashMap;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.function.Function;
import java.util.function.Predicate;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.Holder;
import net.minecraft.core.Registry;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.world.level.block.Mirror;
import net.minecraft.world.level.block.Rotation;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.level.levelgen.structure.BoundingBox;
import net.minecraft.world.level.levelgen.structure.PoolElementStructurePiece;
import net.minecraft.world.level.levelgen.structure.Structure;
import net.minecraft.world.level.levelgen.structure.StructurePiece;
import net.minecraft.world.level.levelgen.structure.StructureType;
import net.minecraft.world.level.levelgen.structure.pools.JigsawJunction;
import net.minecraft.world.level.levelgen.structure.pools.SinglePoolElement;
import net.minecraft.world.level.levelgen.structure.pools.StructurePoolElement;
import net.minecraft.world.level.levelgen.structure.pools.StructureTemplatePool;
import net.minecraft.world.level.levelgen.structure.structures.JigsawStructure;
import net.minecraft.world.level.levelgen.structure.templatesystem.LiquidSettings;
import net.minecraft.world.level.levelgen.structure.templatesystem.StructureTemplate;
import net.minecraft.world.level.levelgen.structure.templatesystem.StructureTemplateManager;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Heraldia village: the usual jigsaw ({@code theVillage}) plus what the jigsaw does not see. With {@code port} (coastal
 * villages), the port goes separately: a shed (rigid) and a pier ({@code terrain_matching}, so the terrain adaptation
 * does not raise dirt under the planks) placed on the free shore nearest to the plaza, with the pier towards the sea.
 * The shore is chosen in {@link Shoreline} among all those of a grid around the plaza, using only the generation
 * bottom ({@code OCEAN_FLOOR_WG}, cached), and only when the village is created (not in /locate or the maps). If the spot
 * is taken by houses, fillers or towers, they are removed (the port takes their place) when there is no free shore; those that
 * collide with the plaza, a special building or a street under the pier are discarded. If none is left, the village spawns
 * without a port (the avenue already has the inn). All villages use this type: if the quest board is disabled
 * ({@code aldeas.vida.tablon}), its piece is removed when the village is created, and so are the traces of work in progress
 * ({@code <style>/traces/<kind>}, on their plots) if {@code aldeas.vida.rastros} is disabled; if neither and there is no port,
 * the stub is the jigsaw's.
 */
public final class VillageStructure extends Structure {
	private static final Logger LOGGER = LoggerFactory.getLogger(Heraldia.MOD_ID);
	/** With {@code -Dheraldia.depurar.puerto=true} the port of each coastal village is logged (not only with /place). */
	private static final boolean DEBUG = Boolean.getBoolean("heraldia.depurar.puerto");

	/** Pools of the shed and the pier, position of their joining jigsaw in each template, pier length and reach. */
	public record Port(Holder<StructureTemplatePool> shed, Holder<StructureTemplatePool> pier, BlockPos shedJoint,
			BlockPos pierJoint, int length, int reach) {
		public static final Codec<Port> CODEC = RecordCodecBuilder.create(i -> i.group(
				StructureTemplatePool.CODEC.fieldOf("caseta").forGetter(Port::shed),
				StructureTemplatePool.CODEC.fieldOf("muelle").forGetter(Port::pier),
				BlockPos.CODEC.fieldOf("union_caseta").forGetter(Port::shedJoint),
				BlockPos.CODEC.fieldOf("union_muelle").forGetter(Port::pierJoint),
				Codec.intRange(4, 64).fieldOf("largo").forGetter(Port::length),
				Codec.intRange(16, 96).fieldOf("alcance").forGetter(Port::reach)).apply(i, Port::new));
	}

	public static final MapCodec<VillageStructure> CODEC = RecordCodecBuilder.mapCodec(i -> i.group(
			settingsCodec(i),
			JigsawStructure.CODEC.codec().fieldOf("aldea").forGetter(s -> s.theVillage),
			Port.CODEC.optionalFieldOf("puerto").forGetter(s -> s.port)).apply(i, VillageStructure::new));
	public static final StructureType<VillageStructure> TYPE = () -> CODEC;

	private final JigsawStructure theVillage;
	private final Optional<Port> port;

	public VillageStructure(Structure.StructureSettings settings, JigsawStructure theVillage, Optional<Port> port) {
		super(settings);
		this.theVillage = theVillage;
		this.port = port;
	}

	public static void register() {
		Registry.register(BuiltInRegistries.STRUCTURE_TYPE, Heraldia.id("aldea"), TYPE);
	}

	@Override
	protected Optional<GenerationStub> findGenerationPoint(GenerationContext ctx) {
		long tp = Profiler.start();
		Optional<GenerationStub> stub = theVillage.findGenerationPoint(ctx);
		Profiler.end(Profiler.Segment.VILLAGE, tp);
		boolean noBoard = !HeraldiaConfig.get().getBool(BOARD_OPTION);
		boolean noTraces = !HeraldiaConfig.get().getBool(TRACES_OPTION);
		if (stub.isEmpty()) {
			return stub;
		}
		GenerationStub village = stub.get();
		boolean forced = Generation.forced(ctx, biomes());
		// The piece generator only runs when the village is really created: /locate and the maps do not pay for the search.
		return Optional.of(new GenerationStub(village.position(), builder -> {
			long t0 = System.nanoTime();
			List<StructurePiece> pieces = new ArrayList<>(village.getPiecesBuilder().build().pieces());
			if (noBoard) {
				pieces.removeIf(VillageStructure::board);
			}
			if (noTraces) {
				pieces.removeIf(VillageStructure::trace);
			}
			long tf = Profiler.start();
			String fit = fitTerrain(ctx, pieces);
			Profiler.end(Profiler.Segment.VILLAGE_TERRAIN, tf);
			if (forced || DEBUG) {
				LOGGER.info("Heraldia: aldea en {} {}: terrain fit: {}", village.position().getX(), village.position().getZ(), fit);
			}
			long t1 = System.nanoTime();
			String result = port.isPresent() ? addPort(ctx, port.get(), pieces) : null;
			if (port.isPresent()) {
				Profiler.end(Profiler.Segment.SHORE, t1);
			}
			for (StructurePiece piece : pieces) {
				builder.addPiece(piece);
			}
			if ((forced || DEBUG) && result != null) {   // with /place structure (the test reads it) or when debugging
				LOGGER.info("Heraldia: aldea de costa en {} {}: {} en {} µs (ensamblar la aldea: {} µs)", village.position().getX(),
						village.position().getZ(), result, (System.nanoTime() - t1) / 1000, (t1 - t0) / 1000);
			}
		}));
	}

	/**
	 * Fits the village to the terrain ({@link TerrainFit}): reads the parent of each piece from the jigsaw junctions,
	 * decides with the generation heights, removes the dropped pieces and the junctions that pointed at them (so the terrain
	 * adaptation does not shape the ground for a piece that is no longer there) and gives each graded street its grading
	 * points as junctions, which the terrain adaptation of the new chunks follows (with /place, which does not adapt the
	 * terrain, they change nothing). Junctions are saved with the structure start. Returns the summary.
	 */
	static String fitTerrain(GenerationContext ctx, List<StructurePiece> pieces) {
		List<TerrainFit.Part> parts = parts(pieces);
		TerrainFit.Result r = TerrainFit.fit(parts, new Ground(ctx));
		List<BoundingBox> gone = new ArrayList<>();
		List<StructurePiece> kept = new ArrayList<>();
		for (int i = 0; i < pieces.size(); i++) {
			if (r.kept(i)) {
				kept.add(pieces.get(i));
				// a graded street: the terrain adaptation (beard_thin) blends the ground towards each of its points
				if (pieces.get(i) instanceof PoolElementStructurePiece pe) {
					for (int[] q : r.grades().get(i)) {
						pe.addJunction(new JigsawJunction(q[0], q[1], q[2], 0, StructureTemplatePool.Projection.TERRAIN_MATCHING));
					}
				}
			} else {
				gone.add(pieces.get(i).getBoundingBox());
			}
		}
		if (!gone.isEmpty()) {
			for (StructurePiece piece : kept) {
				if (piece instanceof PoolElementStructurePiece pe) {
					pe.getJunctions().removeIf(j -> gone.stream().anyMatch(b -> inside(b, j.getSourceX(), j.getSourceZ()))
							&& !inside(pe.getBoundingBox(), j.getSourceX(), j.getSourceZ()));
				}
			}
			pieces.clear();
			pieces.addAll(kept);
		}
		return r.summary();
	}

	/** The pieces as {@link TerrainFit.Part}s: kind by template path and parent and joint from the junctions. */
	static List<TerrainFit.Part> parts(List<StructurePiece> pieces) {
		List<BoundingBox> boxes = new ArrayList<>();
		List<List<int[]>> junctions = new ArrayList<>();
		for (StructurePiece piece : pieces) {
			boxes.add(piece.getBoundingBox());
			List<int[]> js = new ArrayList<>();
			if (piece instanceof PoolElementStructurePiece pe) {
				for (JigsawJunction j : pe.getJunctions()) {
					js.add(new int[] {j.getSourceX(), j.getSourceZ()});
				}
			}
			junctions.add(js);
		}
		List<TerrainFit.Part> out = new ArrayList<>();
		for (int i = 0; i < pieces.size(); i++) {
			int[] link = parent(boxes, junctions, i);
			out.add(TerrainFit.Part.of(boxes.get(i), kind(pieces.get(i), i), link == null ? -1 : link[0],
					link == null ? 0 : link[1], link == null ? 0 : link[2]));
		}
		return out;
	}

	/**
	 * The piece that piece {@code i} hangs from and the joint between them: {parent, x, z}, or null. The jigsaw places a
	 * parent before its children and gives both a junction at the other's jigsaw block, so the parent is the latest earlier
	 * piece whose footprint holds one of the child's junctions while the child's footprint holds one of the parent's.
	 */
	static int[] parent(List<BoundingBox> boxes, List<List<int[]>> junctions, int i) {
		for (int j = i - 1; j >= 0; j--) {
			for (int[] mine : junctions.get(i)) {
				if (!inside(boxes.get(j), mine[0], mine[1])) {
					continue;
				}
				for (int[] theirs : junctions.get(j)) {
					if (inside(boxes.get(i), theirs[0], theirs[1])) {
						return new int[] {j, mine[0], mine[1]};
					}
				}
			}
		}
		return null;
	}

	private static boolean inside(BoundingBox b, int x, int z) {
		return x >= b.minX() && x <= b.maxX() && z >= b.minZ() && z <= b.maxZ();
	}

	private static TerrainFit.Kind kind(StructurePiece piece, int i) {
		if (i == 0) {
			return TerrainFit.Kind.ROOT;
		}
		if (street(piece)) {
			return TerrainFit.Kind.STREET;
		}
		String path = piece instanceof PoolElementStructurePiece pe && pe.getElement() instanceof SinglePoolElement e
				? e.getTemplateLocation().getPath() : "";
		return kind(path);
	}

	/** Kind of a rigid piece by its template path: buildings that hang from streets; the rest goes with its parent. */
	static TerrainFit.Kind kind(String path) {
		return path.contains("/houses/") || path.contains("/fillers/") || path.contains("/specials/")
				|| path.contains("/terminators/") ? TerrainFit.Kind.BUILDING : TerrainFit.Kind.CONTENT;
	}

	/**
	 * Generation heights of one village: first free height counting water, asked of the generator only on a grid of
	 * {@link #CELL} blocks and interpolated in between. A height costs a whole noise column (~0.2 ms) and a village reads
	 * thousands of columns; the terrain's density is interpolated over cells of 4 blocks anyway, so its surface between
	 * two grid points is close to a straight line (a fit asking every column took 1.6 s per village; on the grid, about a
	 * sixteenth).
	 */
	static final class Ground implements TerrainFit.Ground {
		static final int CELL = 4;
		private final HeightCache.Source source;
		private final Long2IntOpenHashMap grid = new Long2IntOpenHashMap();

		Ground(GenerationContext ctx) {
			this((x, z, type) -> ctx.chunkGenerator().getBaseHeight(x, z, type, ctx.heightAccessor(), ctx.randomState()));
		}

		Ground(HeightCache.Source source) {
			this.source = source;
		}

		private int corner(int gx, int gz) {
			long key = BlockPos.asLong(gx, 0, gz);
			if (grid.containsKey(key)) {
				return grid.get(key);
			}
			int h = source.height(gx * CELL, gz * CELL, Heightmap.Types.WORLD_SURFACE_WG);
			grid.put(key, h);
			return h;
		}

		@Override
		public int surface(int x, int z) {
			int gx = Math.floorDiv(x, CELL), gz = Math.floorDiv(z, CELL);
			double fx = (x - gx * CELL) / (double) CELL, fz = (z - gz * CELL) / (double) CELL;
			double top = corner(gx, gz) * (1 - fx) + corner(gx + 1, gz) * fx;
			double bottom = corner(gx, gz + 1) * (1 - fx) + corner(gx + 1, gz + 1) * fx;
			return (int) Math.round(top * (1 - fz) + bottom * fz);
		}
	}

	/** Option that puts the quest board in the plaza (if disabled, the piece is removed when the village is created). */
	public static final String BOARD_OPTION = "aldeas.vida.tablon";

	/** Quest board piece (lectern with its book and the bailiff): template {@code <style>/tablon}. */
	private static boolean board(StructurePiece piece) {
		return piece instanceof PoolElementStructurePiece pe && pe.getElement() instanceof SinglePoolElement e
				&& isBoard(e.getTemplateLocation().getPath());
	}

	/** Template path of the quest board ({@code <style>/tablon}). */
	static boolean isBoard(String path) {
		return path.endsWith("/tablon");
	}

	/** Option that puts the traces of work in progress on their plots (if disabled, they are removed when the village is created). */
	public static final String TRACES_OPTION = "aldeas.vida.rastros";

	/** Trace of work in progress (blocks only, on its plot): template {@code <style>/traces/<kind>}. */
	private static boolean trace(StructurePiece piece) {
		return piece instanceof PoolElementStructurePiece pe && pe.getElement() instanceof SinglePoolElement e
				&& isTrace(e.getTemplateLocation().getPath());
	}

	/** Template path of a trace of work in progress ({@code <style>/traces/<kind>}). */
	static boolean isTrace(String path) {
		return path.contains("/traces/");
	}

	/**
	 * Houses, fillers, towers and gates at the end of the streets and what goes inside them (villagers, golems, decoration): the
	 * only thing the port can displace.
	 */
	private static boolean removable(StructurePiece piece) {
		if (!(piece instanceof PoolElementStructurePiece pe)) {
			return false;
		}
		return removable(pe.getElement() instanceof SinglePoolElement e ? e.getTemplateLocation().getPath() : "");
	}

	/** The same by template path (without the piece): the only thing that decides. */
	static boolean removable(String path) {
		return path.contains("/houses/") || path.contains("/fillers/") || path.contains("/decor/") || path.contains("/terminators/")
				|| isTrace(path) || path.startsWith("villagers/") || path.equals("golem");
	}

	/** Street or avenue: a pool piece that adapts to the terrain (terrain_matching). */
	private static boolean street(StructurePiece piece) {
		return piece instanceof PoolElementStructurePiece pe
				&& pe.getElement().getProjection() == StructureTemplatePool.Projection.TERRAIN_MATCHING;
	}

	/**
	 * Village pieces that would have to be removed to put the port in these boxes, or null if it collides with something that is not
	 * removed (plaza, special buildings). The streets ({@code terrain_matching}) reach the shore (over water the
	 * street processor places planks): under the shed they do not count (the shed, rigid and placed afterwards, covers them), but
	 * a street whose footprint overlaps the pier's discards the shore (its planks would sit under the pier's, one block
	 * lower, and removing it would leave houses without a path). A rigid piece in the footprint of {@code seaSide} (the water beyond the
	 * tip and on the sides of the pier) also counts: the terrain adaptation raises dirt under it and would cover the tip.
	 * Along with each house go the pieces inside it (its villager, its bed).
	 */
	private static List<StructurePiece> displaced(List<StructurePiece> village, BoundingBox shed, BoundingBox pier,
												  BoundingBox seaSide) {
		return displaced(village, StructurePiece::getBoundingBox, VillageStructure::street, VillageStructure::removable, shed, pier, seaSide);
	}

	/** displaced without game pieces (for the tests): box, whether it is a street and whether it can be removed, for each piece. */
	static <P> List<P> displaced(List<P> village, Function<P, BoundingBox> box, Predicate<P> street, Predicate<P> removable,
								 BoundingBox shed, BoundingBox pier, BoundingBox seaSide) {
		List<P> out = new ArrayList<>();
		for (P piece : village) {
			BoundingBox b = box.apply(piece);
			if (street.test(piece)) {
				if (b.intersects(pier.minX(), pier.minZ(), pier.maxX(), pier.maxZ())) {
					return null;
				}
				continue;
			}
			if (!b.intersects(shed) && !b.intersects(pier) && !b.intersects(seaSide.minX(), seaSide.minZ(), seaSide.maxX(), seaSide.maxZ())) {
				continue;
			}
			if (!removable.test(piece)) {
				return null;
			}
			out.add(piece);
		}
		for (P piece : village) {
			for (int i = 0, n = out.size(); i < n && !out.contains(piece); i++) {
				BoundingBox house = box.apply(out.get(i));
				BoundingBox b = box.apply(piece);
				if (house.minX() <= b.minX() && b.maxX() <= house.maxX() && house.minZ() <= b.minZ() && b.maxZ() <= house.maxZ()
						&& house.minY() <= b.minY() && b.maxY() <= house.maxY()) {
					out.add(piece);
				}
			}
		}
		return out;
	}

	/** Looks for the shore ({@link Shoreline}) and adds the shed and the pier to {@code village} (removing the houses in their way). */
	private static String addPort(GenerationContext ctx, Port p, List<StructurePiece> village) {
		Heights h = new Heights(ctx);
		StructureTemplateManager manager = ctx.structureTemplateManager();
		StructurePoolElement shedElement = p.shed().value().getRandomTemplate(ctx.random());
		StructurePoolElement pierElement = p.pier().value().getRandomTemplate(ctx.random());
		// boxes of both templates in each rotation, only once: each tried shore only shifts them
		Blueprint[] blueprints = new Blueprint[4];
		for (Direction d : Direction.Plane.HORIZONTAL) {
			blueprints[d.get2DDataValue()] = plan(manager, p, shedElement, pierElement, d);
		}
		// the plaza is the first piece; the start position is a corner of its chunk
		BlockPos center = village.get(0).getBoundingBox().getCenter();
		int x0 = ctx.chunkPos().getMinBlockX(), z0 = ctx.chunkPos().getMinBlockZ();
		Shoreline.Choice<List<StructurePiece>> e = Shoreline.choose(h::floor, h.sea, center.getX(), center.getZ(), p.reach(), p.length(),
				s -> {
					Site site = blueprints[s.sea().get2DDataValue()].en(s);
					if (!inWindow(site.shed(), x0, z0) || !inWindow(site.pier(), x0, z0)) {
						return null;
					}
					return displaced(village, site.shed(), site.pier(), site.seaSide());
				}, List::isEmpty);
		String tallies = e.candidates() + " orillas: " + e.noSeabed() + " sin fondo, " + e.blocked()
				+ " junto a edificios que no se quitan o sobre una calle; " + e.discarded() + " direcciones descartadas por las piezas, "
				+ e.queries() + " consultas del fondo";
		if (e.shore() == null) {
			return "sin orilla al alcance, sin puerto (" + tallies + ")";
		}
		Shoreline.Shore s = e.shore();
		Site site = blueprints[s.sea().get2DDataValue()].en(s);
		village.removeAll(e.gone());
		village.add(new PoolElementStructurePiece(manager, shedElement, site.shedOrigin(), shedElement.getGroundLevelDelta(), site.rot(),
				site.shed(), LiquidSettings.APPLY_WATERLOGGING));
		village.add(new PoolElementStructurePiece(manager, pierElement, site.pierOrigin(), pierElement.getGroundLevelDelta(), site.rot(),
				site.pier(), LiquidSettings.APPLY_WATERLOGGING));
		Direction sea = s.sea();
		return "muelle en " + s.x() + " " + s.z() + " hacia " + sea.getSerializedName() + ", punta " + (s.x() + sea.getStepX() * p.length())
				+ " " + (s.z() + sea.getStepZ() * p.length()) + " (" + e.gone().size() + " piezas desplazadas; " + tallies + ")";
	}

	/**
	 * Rotation, origins and boxes of the shed and the pier with the shed's joint on the shore and the pier towards the sea, and
	 * the sea that must be free of rigid pieces around the pier.
	 */
	private record Site(Rotation rot, BlockPos shedOrigin, BlockPos pierOrigin, BoundingBox shed, BoundingBox pier,
						 BoundingBox seaSide) {
	}

	/**
	 * Shed and pier rotated towards one side of the sea: rotation, rotated joints and boxes with the origin at 0, 0, 0 (computed
	 * once per village and rotation; asking the templates for them on each tried shore was the most expensive part of the search).
	 */
	private record Blueprint(Direction sea, Rotation rot, BlockPos shedJoint, BlockPos pierJoint, BoundingBox shed,
						 BoundingBox pier) {
		/** Spot with the shed's joint (its face towards the sea) on the shore and the pier's one block offshore. */
		Site en(Shoreline.Shore s) {
			BlockPos shore = new BlockPos(s.x(), s.y(), s.z());
			BlockPos co = shore.subtract(shedJoint), mo = shore.relative(sea).subtract(pierJoint);
			BoundingBox m = pier.moved(mo.getX(), mo.getY(), mo.getZ());
			return new Site(rot, co, mo, shed.moved(co.getX(), co.getY(), co.getZ()), m, openSea(m, sea));
		}
	}

	private static Blueprint plan(StructureTemplateManager manager, Port p, StructurePoolElement shedElement,
							   StructurePoolElement pierElement, Direction sea) {
		Rotation rot = facing(sea);
		return new Blueprint(sea, rot, StructureTemplate.transform(p.shedJoint(), Mirror.NONE, rot, BlockPos.ZERO),
				StructureTemplate.transform(p.pierJoint(), Mirror.NONE, rot, BlockPos.ZERO),
				shedElement.getBoundingBox(manager, BlockPos.ZERO, rot), pierElement.getBoundingBox(manager, BlockPos.ZERO, rot));
	}

	/**
	 * A piece is only placed in the chunks within 8 of its start chunk (ChunkGenerator.createReferences): does the whole
	 * box fit? (x0, z0: first block of the start chunk)
	 */
	static boolean inWindow(BoundingBox b, int x0, int z0) {
		int lo = -8 * 16, hi = 8 * 16 + 15;
		return b.minX() - x0 >= lo && b.maxX() - x0 <= hi && b.minZ() - z0 >= lo && b.maxZ() - z0 <= hi;
	}

	/** Water that must stay free of rigid pieces: the pier plus {@link Shoreline#BEYOND} past the tip and 4 to each side. */
	static BoundingBox openSea(BoundingBox pier, Direction sea) {
		int ax = sea.getAxis() == Direction.Axis.X ? 0 : 4, az = 4 - ax;
		int fx = sea.getStepX() * Shoreline.BEYOND, fz = sea.getStepZ() * Shoreline.BEYOND;
		return new BoundingBox(pier.minX() - ax + Math.min(fx, 0), pier.minY(), pier.minZ() - az + Math.min(fz, 0),
				pier.maxX() + ax + Math.max(fx, 0), pier.maxY(), pier.maxZ() + az + Math.max(fz, 0));
	}

	/** Rotation that turns the templates' +z (from the shed towards the pier) to the given direction. */
	static Rotation facing(Direction d) {
		for (Rotation r : Rotation.values()) {
			BlockPos v = new BlockPos(0, 0, 1).rotate(r);
			if (v.getX() == d.getStepX() && v.getZ() == d.getStepZ()) {
				return r;
			}
		}
		return Rotation.NONE;
	}

	@Override
	public StructureType<?> type() {
		return TYPE;
	}
}
