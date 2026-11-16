package io.github.albertosa23.heraldia.aldeas;

import com.mojang.serialization.Codec;
import com.mojang.serialization.MapCodec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.comun.Alturas;
import io.github.albertosa23.heraldia.comun.Generacion;
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
 * Aldea de Heraldia: el jigsaw de siempre ({@code aldea}) más lo que el jigsaw no ve. Con {@code puerto} (aldeas de la
 * costa), el puerto va aparte: una caseta (rígida) y un muelle ({@code terrain_matching}, para que el ajuste del terreno
 * no levante tierra bajo las tablas) que se colocan en la orilla libre más cercana a la plaza, con el muelle hacia el mar.
 * La orilla se elige en {@link Orilla} entre todas las de una malla alrededor de la plaza, solo con el fondo de
 * generación ({@code OCEAN_FLOOR_WG}, con caché), y solo al crear la aldea (no en /locate ni en los mapas). Si el sitio
 * lo ocupan casas, rellenos o torres, se quitan (el puerto ocupa su lugar) cuando no hay ninguna orilla libre; las que
 * chocan con la plaza, un edificio especial o una calle bajo el muelle se descartan. Si no queda ninguna, la aldea sale
 * sin puerto (la avenida ya tiene la posada). Todas las aldeas usan este tipo: si el tablón de encargos está desactivado
 * ({@code aldeas.vida.tablon}), su pieza se quita al crear la aldea; si no y no hay puerto, el stub es el del jigsaw.
 */
public final class AldeaStructure extends Structure {
	private static final Logger LOGGER = LoggerFactory.getLogger(Heraldia.MOD_ID);
	/** Con {@code -Dheraldia.depurar.puerto=true} se registra el puerto de cada aldea de la costa (no solo con /place). */
	private static final boolean DEPURAR = Boolean.getBoolean("heraldia.depurar.puerto");

	/** Pools de la caseta y del muelle, posición de su jigsaw de unión en cada plantilla, largo del muelle y alcance. */
	public record Puerto(Holder<StructureTemplatePool> caseta, Holder<StructureTemplatePool> muelle, BlockPos unionCaseta,
			BlockPos unionMuelle, int largo, int alcance) {
		public static final Codec<Puerto> CODEC = RecordCodecBuilder.create(i -> i.group(
				StructureTemplatePool.CODEC.fieldOf("caseta").forGetter(Puerto::caseta),
				StructureTemplatePool.CODEC.fieldOf("muelle").forGetter(Puerto::muelle),
				BlockPos.CODEC.fieldOf("union_caseta").forGetter(Puerto::unionCaseta),
				BlockPos.CODEC.fieldOf("union_muelle").forGetter(Puerto::unionMuelle),
				Codec.intRange(4, 64).fieldOf("largo").forGetter(Puerto::largo),
				Codec.intRange(16, 96).fieldOf("alcance").forGetter(Puerto::alcance)).apply(i, Puerto::new));
	}

	public static final MapCodec<AldeaStructure> CODEC = RecordCodecBuilder.mapCodec(i -> i.group(
			settingsCodec(i),
			JigsawStructure.CODEC.codec().fieldOf("aldea").forGetter(s -> s.aldea),
			Puerto.CODEC.optionalFieldOf("puerto").forGetter(s -> s.puerto)).apply(i, AldeaStructure::new));
	public static final StructureType<AldeaStructure> TYPE = () -> CODEC;

	private final JigsawStructure aldea;
	private final Optional<Puerto> puerto;

	public AldeaStructure(Structure.StructureSettings settings, JigsawStructure aldea, Optional<Puerto> puerto) {
		super(settings);
		this.aldea = aldea;
		this.puerto = puerto;
	}

	public static void registrar() {
		Registry.register(BuiltInRegistries.STRUCTURE_TYPE, Heraldia.id("aldea"), TYPE);
	}

	@Override
	protected Optional<GenerationStub> findGenerationPoint(GenerationContext ctx) {
		Optional<GenerationStub> stub = aldea.findGenerationPoint(ctx);
		boolean sinTablon = !HeraldiaConfig.get().getBool(OPCION_TABLON);
		if ((puerto.isEmpty() && !sinTablon) || stub.isEmpty()) {
			return stub;   // lo normal tierra adentro: el stub del jigsaw tal cual, sin coste añadido
		}
		GenerationStub village = stub.get();
		boolean forzada = Generacion.forzada(ctx, biomes());
		// El generador de piezas solo corre al crear la aldea de verdad: /locate y los mapas no pagan la búsqueda.
		return Optional.of(new GenerationStub(village.position(), builder -> {
			long t0 = System.nanoTime();
			List<StructurePiece> pieces = new ArrayList<>(village.getPiecesBuilder().build().pieces());
			if (sinTablon) {
				pieces.removeIf(AldeaStructure::tablon);
			}
			long t1 = System.nanoTime();
			String result = puerto.isPresent() ? addPort(ctx, puerto.get(), pieces) : null;
			for (StructurePiece piece : pieces) {
				builder.addPiece(piece);
			}
			if ((forzada || DEPURAR) && result != null) {   // con /place structure (la prueba lo lee) o depurando
				LOGGER.info("Heraldia: aldea de costa en {} {}: {} en {} µs (ensamblar la aldea: {} µs)", village.position().getX(),
						village.position().getZ(), result, (System.nanoTime() - t1) / 1000, (t1 - t0) / 1000);
			}
		}));
	}

	/** Opción que pone el tablón de encargos en la plaza (si está desactivada, la pieza se quita al crear la aldea). */
	public static final String OPCION_TABLON = "aldeas.vida.tablon";

	/** Pieza del tablón de encargos (atril con su libro y el alguacil): plantilla {@code <estilo>/tablon}. */
	private static boolean tablon(StructurePiece piece) {
		return piece instanceof PoolElementStructurePiece pe && pe.getElement() instanceof SinglePoolElement e
				&& esTablon(e.getTemplateLocation().getPath());
	}

	/** Ruta de plantilla del tablón de encargos ({@code <estilo>/tablon}). */
	static boolean esTablon(String path) {
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
	 * abajo, y quitarla dejaría casas sin camino). Una pieza rígida en la planta de {@code mar} (el agua más allá de la
	 * punta y a los lados del muelle) también cuenta: el ajuste del terreno levanta tierra bajo ella y taparía la punta.
	 * Con cada casa se van las piezas que quedan dentro de ella (su aldeano, su cama).
	 */
	private static List<StructurePiece> displaced(List<StructurePiece> village, BoundingBox caseta, BoundingBox muelle,
												  BoundingBox mar) {
		return displaced(village, StructurePiece::getBoundingBox, AldeaStructure::street, AldeaStructure::removable, caseta, muelle, mar);
	}

	/** displaced sin piezas del juego (para las pruebas): caja, si es calle y si se puede quitar, de cada pieza. */
	static <P> List<P> displaced(List<P> village, Function<P, BoundingBox> box, Predicate<P> street, Predicate<P> removable,
								 BoundingBox caseta, BoundingBox muelle, BoundingBox mar) {
		List<P> out = new ArrayList<>();
		for (P piece : village) {
			BoundingBox b = box.apply(piece);
			if (street.test(piece)) {
				if (b.intersects(muelle.minX(), muelle.minZ(), muelle.maxX(), muelle.maxZ())) {
					return null;
				}
				continue;
			}
			if (!b.intersects(caseta) && !b.intersects(muelle) && !b.intersects(mar.minX(), mar.minZ(), mar.maxX(), mar.maxZ())) {
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

	/** Busca la orilla ({@link Orilla}) y añade a {@code village} la caseta y el muelle (quitando las casas que ocupen su sitio). */
	private static String addPort(GenerationContext ctx, Puerto p, List<StructurePiece> village) {
		Alturas h = new Alturas(ctx);
		StructureTemplateManager manager = ctx.structureTemplateManager();
		StructurePoolElement casetaEl = p.caseta().value().getRandomTemplate(ctx.random());
		StructurePoolElement muelleEl = p.muelle().value().getRandomTemplate(ctx.random());
		// cajas de las dos plantillas en cada giro, una sola vez: cada orilla probada solo las desplaza
		Plano[] planos = new Plano[4];
		for (Direction d : Direction.Plane.HORIZONTAL) {
			planos[d.get2DDataValue()] = plano(manager, p, casetaEl, muelleEl, d);
		}
		// la plaza es la primera pieza; la posición del inicio es una esquina de su chunk
		BlockPos center = village.get(0).getBoundingBox().getCenter();
		int x0 = ctx.chunkPos().getMinBlockX(), z0 = ctx.chunkPos().getMinBlockZ();
		Orilla.Eleccion<List<StructurePiece>> e = Orilla.elegir(h::floor, h.sea, center.getX(), center.getZ(), p.alcance(), p.largo(),
				s -> {
					Sitio sitio = planos[s.sea().get2DDataValue()].en(s);
					if (!enVentana(sitio.caseta(), x0, z0) || !enVentana(sitio.muelle(), x0, z0)) {
						return null;
					}
					return displaced(village, sitio.caseta(), sitio.muelle(), sitio.mar());
				}, List::isEmpty);
		String cuentas = e.candidatas() + " orillas: " + e.sinFondo() + " sin fondo, " + e.bloqueadas()
				+ " junto a edificios que no se quitan o sobre una calle; " + e.descartadas() + " direcciones descartadas por las piezas, "
				+ e.consultas() + " consultas del fondo";
		if (e.shore() == null) {
			return "sin orilla al alcance, sin puerto (" + cuentas + ")";
		}
		Orilla.Shore s = e.shore();
		Sitio sitio = planos[s.sea().get2DDataValue()].en(s);
		village.removeAll(e.gone());
		village.add(new PoolElementStructurePiece(manager, casetaEl, sitio.casetaOrigin(), casetaEl.getGroundLevelDelta(), sitio.rot(),
				sitio.caseta(), LiquidSettings.APPLY_WATERLOGGING));
		village.add(new PoolElementStructurePiece(manager, muelleEl, sitio.muelleOrigin(), muelleEl.getGroundLevelDelta(), sitio.rot(),
				sitio.muelle(), LiquidSettings.APPLY_WATERLOGGING));
		Direction sea = s.sea();
		return "muelle en " + s.x() + " " + s.z() + " hacia " + sea.getSerializedName() + ", punta " + (s.x() + sea.getStepX() * p.largo())
				+ " " + (s.z() + sea.getStepZ() * p.largo()) + " (" + e.gone().size() + " piezas desplazadas; " + cuentas + ")";
	}

	/**
	 * Giro, orígenes y cajas de la caseta y el muelle con la unión de la caseta en la orilla y el muelle hacia el mar, y
	 * el mar que debe quedar libre de piezas rígidas alrededor del muelle.
	 */
	private record Sitio(Rotation rot, BlockPos casetaOrigin, BlockPos muelleOrigin, BoundingBox caseta, BoundingBox muelle,
						 BoundingBox mar) {
	}

	/**
	 * Caseta y muelle girados hacia un lado del mar: giro, uniones giradas y cajas con el origen en 0, 0, 0 (se calculan
	 * una vez por aldea y giro; pedirlas a las plantillas en cada orilla probada era lo más caro de la búsqueda).
	 */
	private record Plano(Direction sea, Rotation rot, BlockPos unionCaseta, BlockPos unionMuelle, BoundingBox caseta,
						 BoundingBox muelle) {
		/** Sitio con la unión de la caseta (su cara hacia el mar) en la orilla y la del muelle un bloque mar adentro. */
		Sitio en(Orilla.Shore s) {
			BlockPos shore = new BlockPos(s.x(), s.y(), s.z());
			BlockPos co = shore.subtract(unionCaseta), mo = shore.relative(sea).subtract(unionMuelle);
			BoundingBox m = muelle.moved(mo.getX(), mo.getY(), mo.getZ());
			return new Sitio(rot, co, mo, caseta.moved(co.getX(), co.getY(), co.getZ()), m, marLibre(m, sea));
		}
	}

	private static Plano plano(StructureTemplateManager manager, Puerto p, StructurePoolElement casetaEl,
							   StructurePoolElement muelleEl, Direction sea) {
		Rotation rot = facing(sea);
		return new Plano(sea, rot, StructureTemplate.transform(p.unionCaseta(), Mirror.NONE, rot, BlockPos.ZERO),
				StructureTemplate.transform(p.unionMuelle(), Mirror.NONE, rot, BlockPos.ZERO),
				casetaEl.getBoundingBox(manager, BlockPos.ZERO, rot), muelleEl.getBoundingBox(manager, BlockPos.ZERO, rot));
	}

	/**
	 * Una pieza solo se coloca en los chunks a 8 o menos de su chunk de inicio (ChunkGenerator.createReferences): ¿cabe la
	 * caja entera? (x0, z0: primer bloque del chunk de inicio)
	 */
	static boolean enVentana(BoundingBox b, int x0, int z0) {
		int lo = -8 * 16, hi = 8 * 16 + 15;
		return b.minX() - x0 >= lo && b.maxX() - x0 <= hi && b.minZ() - z0 >= lo && b.maxZ() - z0 <= hi;
	}

	/** Agua que debe quedar libre de piezas rígidas: el muelle más {@link Orilla#MAS_ALLA} tras la punta y 4 a cada lado. */
	static BoundingBox marLibre(BoundingBox muelle, Direction sea) {
		int ax = sea.getAxis() == Direction.Axis.X ? 0 : 4, az = 4 - ax;
		int fx = sea.getStepX() * Orilla.MAS_ALLA, fz = sea.getStepZ() * Orilla.MAS_ALLA;
		return new BoundingBox(muelle.minX() - ax + Math.min(fx, 0), muelle.minY(), muelle.minZ() - az + Math.min(fz, 0),
				muelle.maxX() + ax + Math.max(fx, 0), muelle.maxY(), muelle.maxZ() + az + Math.max(fz, 0));
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
