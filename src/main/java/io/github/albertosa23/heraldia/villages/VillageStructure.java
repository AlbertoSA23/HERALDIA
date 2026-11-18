package io.github.albertosa23.heraldia.villages;

import com.mojang.serialization.Codec;
import com.mojang.serialization.MapCodec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.common.Heights;
import io.github.albertosa23.heraldia.common.Generation;
import io.github.albertosa23.heraldia.common.Profiler;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
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
import net.minecraft.world.level.levelgen.structure.BoundingBox;
import net.minecraft.world.level.levelgen.structure.PoolElementStructurePiece;
import net.minecraft.world.level.levelgen.structure.Structure;
import net.minecraft.world.level.levelgen.structure.StructurePiece;
import net.minecraft.world.level.levelgen.structure.StructureType;
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
 * ({@code aldeas.vida.tablon}), its piece is removed when the village is created; if not and there is no port, the stub is the jigsaw's.
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
		if ((port.isEmpty() && !noBoard) || stub.isEmpty()) {
			return stub;   // the normal case inland: the jigsaw's stub as is, at no extra cost
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
				|| path.startsWith("villagers/") || path.equals("golem");
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
