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
 * Aldea de Heraldia: el jigsaw de siempre ({@code theVillage}) más lo que el jigsaw no ve. Con {@code port} (aldeas de la
 * costa), el puerto va aparte: una caseta (rígida) y un muelle ({@code terrain_matching}, para que el ajuste del terreno
 * no levante tierra bajo las tablas) que se colocan en la orilla libre más cercana a la plaza, con el muelle hacia el mar.
 * La orilla se elige en {@link Shoreline} entre todas las de una malla alrededor de la plaza, solo con el fondo de
 * generación ({@code OCEAN_FLOOR_WG}, con caché), y solo al crear la aldea (no en /locate ni en los mapas). Si el sitio
 * lo ocupan casas, rellenos o torres, se quitan (el puerto ocupa su lugar) cuando no hay ninguna orilla libre; las que
 * chocan con la plaza, un edificio especial o una calle bajo el muelle se descartan. Si no queda ninguna, la aldea sale
 * sin puerto (la avenida ya tiene la posada). Todas las aldeas usan este tipo: si el tablón de encargos está desactivado
 * ({@code villages.health.board}), su pieza se quita al crear la aldea; si no y no hay puerto, el stub es el del jigsaw.
 */
public final class VillageStructure extends Structure {
	private static final Logger LOGGER = LoggerFactory.getLogger(Heraldia.MOD_ID);
	/** Con {@code -Dheraldia.depurar.port=true} se registra el puerto de cada aldea de la costa (no solo con /place). */
	private static final boolean DEBUG = Boolean.getBoolean("heraldia.depurar.puerto");

	/** Pools de la caseta y del muelle, posición de su jigsaw de unión en cada plantilla, largo del muelle y alcance. */
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
			return stub;   // lo normal tierra adentro: el stub del jigsaw tal cual, sin coste añadido
		}
		GenerationStub village = stub.get();
		boolean forced = Generation.forced(ctx, biomes());
		// El generador de piezas solo corre al crear la aldea de verdad: /locate y los mapas no pagan la búsqueda.
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
			if ((forced || DEBUG) && result != null) {   // con /place structure (la prueba lo lee) o depurando
				LOGGER.info("Heraldia: aldea de costa en {} {}: {} en {} µs (ensamblar la aldea: {} µs)", village.position().getX(),
						village.position().getZ(), result, (System.nanoTime() - t1) / 1000, (t1 - t0) / 1000);
			}
		}));
	}

	/** Opción que pone el tablón de encargos en la plaza (si está desactivada, la pieza se quita al crear la aldea). */
	public static final String BOARD_OPTION = "aldeas.vida.tablon";

	/** Pieza del tablón de encargos (atril con su libro y el alguacil): plantilla {@code <style>/board}. */
	private static boolean board(StructurePiece piece) {
		return piece instanceof PoolElementStructurePiece pe && pe.getElement() instanceof SinglePoolElement e
				&& isBoard(e.getTemplateLocation().getPath());
	}

	/** Ruta de plantilla del tablón de encargos ({@code <style>/board}). */
	static boolean isBoard(String path) {
		return path.endsWith("/tablon");
	}

	/**
	 * Casas, rellenos, torres y puertas del final de las calles y lo que va dentro (aldeanos, gólems, decoración): lo
	 * único que el puerto puede desplazar.
	 */
	private static boolean removable(StructurePiece piece) {
		if (!(piece instanceof PoolElementStructurePiece pe)) {
			return false;
		}
		return removable(pe.getElement() instanceof SinglePoolElement e ? e.getTemplateLocation().getPath() : "");
	}

	/** Lo mismo por la ruta de la plantilla (sin la pieza): lo único que decide. */
	static boolean removable(String path) {
		return path.contains("/houses/") || path.contains("/fillers/") || path.contains("/decor/") || path.contains("/terminators/")
				|| path.startsWith("villagers/") || path.equals("golem");
	}

	/** Calle o avenida: pieza de pool que se adapta al terreno (terrain_matching). */
	private static boolean street(StructurePiece piece) {
		return piece instanceof PoolElementStructurePiece pe
				&& pe.getElement().getProjection() == StructureTemplatePool.Projection.TERRAIN_MATCHING;
	}

	/**
	 * Piezas de la aldea que habría que quitar para poner el puerto en estas cajas, o null si choca con algo que no se
	 * quita (plaza, edificios especiales). Las calles ({@code terrain_matching}) llegan a la orilla (sobre el agua el
	 * procesador de calle pone tablas): bajo la caseta no cuentan (la caseta, rígida y colocada después, las cubre), pero
	 * una calle cuya planta pisa la del muelle descarta la orilla (sus tablas quedarían bajo las del muelle, un bloque más
	 * abajo, y quitarla dejaría casas sin camino). Una pieza rígida en la planta de {@code seaSide} (el agua más allá de la
	 * punta y a los lados del muelle) también cuenta: el ajuste del terreno levanta tierra bajo ella y taparía la punta.
	 * Con cada casa se van las piezas que quedan dentro de ella (su aldeano, su cama).
	 */
	private static List<StructurePiece> displaced(List<StructurePiece> village, BoundingBox shed, BoundingBox pier,
												  BoundingBox seaSide) {
		return displaced(village, StructurePiece::getBoundingBox, VillageStructure::street, VillageStructure::removable, shed, pier, seaSide);
	}

	/** displaced sin piezas del juego (para las pruebas): caja, si es calle y si se puede quitar, de cada pieza. */
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

	/** Busca la orilla ({@link Shoreline}) y añade a {@code village} la caseta y el muelle (quitando las casas que ocupen su sitio). */
	private static String addPort(GenerationContext ctx, Port p, List<StructurePiece> village) {
		Heights h = new Heights(ctx);
		StructureTemplateManager manager = ctx.structureTemplateManager();
		StructurePoolElement shedEl = p.shed().value().getRandomTemplate(ctx.random());
		StructurePoolElement pierEl = p.pier().value().getRandomTemplate(ctx.random());
		// cajas de las dos plantillas en cada giro, una sola vez: cada orilla probada solo las desplaza
		Blueprint[] blueprints = new Blueprint[4];
		for (Direction d : Direction.Plane.HORIZONTAL) {
			blueprints[d.get2DDataValue()] = plan(manager, p, shedEl, pierEl, d);
		}
		// la plaza es la primera pieza; la posición del inicio es una esquina de su chunk
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
		village.add(new PoolElementStructurePiece(manager, shedEl, site.shedOrigin(), shedEl.getGroundLevelDelta(), site.rot(),
				site.shed(), LiquidSettings.APPLY_WATERLOGGING));
		village.add(new PoolElementStructurePiece(manager, pierEl, site.pierOrigin(), pierEl.getGroundLevelDelta(), site.rot(),
				site.pier(), LiquidSettings.APPLY_WATERLOGGING));
		Direction sea = s.sea();
		return "muelle en " + s.x() + " " + s.z() + " hacia " + sea.getSerializedName() + ", punta " + (s.x() + sea.getStepX() * p.length())
				+ " " + (s.z() + sea.getStepZ() * p.length()) + " (" + e.gone().size() + " piezas desplazadas; " + tallies + ")";
	}

	/**
	 * Giro, orígenes y cajas de la caseta y el muelle con la unión de la caseta en la orilla y el muelle hacia el mar, y
	 * el mar que debe quedar libre de piezas rígidas alrededor del muelle.
	 */
	private record Site(Rotation rot, BlockPos shedOrigin, BlockPos pierOrigin, BoundingBox shed, BoundingBox pier,
						 BoundingBox seaSide) {
	}

	/**
	 * Caseta y muelle girados hacia un lado del mar: giro, uniones giradas y cajas con el origen en 0, 0, 0 (se calculan
	 * una vez por aldea y giro; pedirlas a las plantillas en cada orilla probada era lo más caro de la búsqueda).
	 */
	private record Blueprint(Direction sea, Rotation rot, BlockPos shedJoint, BlockPos pierJoint, BoundingBox shed,
						 BoundingBox pier) {
		/** Sitio con la unión de la caseta (su cara hacia el mar) en la orilla y la del muelle un bloque mar adentro. */
		Site en(Shoreline.Shore s) {
			BlockPos shore = new BlockPos(s.x(), s.y(), s.z());
			BlockPos co = shore.subtract(shedJoint), mo = shore.relative(sea).subtract(pierJoint);
			BoundingBox m = pier.moved(mo.getX(), mo.getY(), mo.getZ());
			return new Site(rot, co, mo, shed.moved(co.getX(), co.getY(), co.getZ()), m, openSea(m, sea));
		}
	}

	private static Blueprint plan(StructureTemplateManager manager, Port p, StructurePoolElement shedEl,
							   StructurePoolElement pierEl, Direction sea) {
		Rotation rot = facing(sea);
		return new Blueprint(sea, rot, StructureTemplate.transform(p.shedJoint(), Mirror.NONE, rot, BlockPos.ZERO),
				StructureTemplate.transform(p.pierJoint(), Mirror.NONE, rot, BlockPos.ZERO),
				shedEl.getBoundingBox(manager, BlockPos.ZERO, rot), pierEl.getBoundingBox(manager, BlockPos.ZERO, rot));
	}

	/**
	 * Una pieza solo se coloca en los chunks a 8 o menos de su chunk de inicio (ChunkGenerator.createReferences): ¿cabe la
	 * caja entera? (x0, z0: primer bloque del chunk de inicio)
	 */
	static boolean inWindow(BoundingBox b, int x0, int z0) {
		int lo = -8 * 16, hi = 8 * 16 + 15;
		return b.minX() - x0 >= lo && b.maxX() - x0 <= hi && b.minZ() - z0 >= lo && b.maxZ() - z0 <= hi;
	}

	/** Agua que debe quedar libre de piezas rígidas: el muelle más {@link Shoreline#BEYOND} tras la punta y 4 a cada lado. */
	static BoundingBox openSea(BoundingBox pier, Direction sea) {
		int ax = sea.getAxis() == Direction.Axis.X ? 0 : 4, az = 4 - ax;
		int fx = sea.getStepX() * Shoreline.BEYOND, fz = sea.getStepZ() * Shoreline.BEYOND;
		return new BoundingBox(pier.minX() - ax + Math.min(fx, 0), pier.minY(), pier.minZ() - az + Math.min(fz, 0),
				pier.maxX() + ax + Math.max(fx, 0), pier.maxY(), pier.maxZ() + az + Math.max(fz, 0));
	}

	/** Giro que lleva el +z de las plantillas (de la caseta hacia el muelle) a la dirección dada. */
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
