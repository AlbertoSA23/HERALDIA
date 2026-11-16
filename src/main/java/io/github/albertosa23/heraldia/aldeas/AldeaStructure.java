package io.github.albertosa23.heraldia.aldeas;

import com.mojang.serialization.Codec;
import com.mojang.serialization.MapCodec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.comun.Alturas;
import io.github.albertosa23.heraldia.comun.Generacion;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Optional;
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
 * no levante tierra bajo las tablas) que se colocan en la orilla más cercana a la plaza, con el muelle hacia el mar. La
 * orilla se busca en rayos desde el centro de la plaza en las cuatro direcciones (cada uno se corta en la primera agua),
 * solo con el fondo de generación ({@code OCEAN_FLOOR_WG}, con caché), y solo al crear la aldea (no en /locate ni en
 * los mapas). Si el sitio lo ocupan casas, se quitan (el puerto ocupa su lugar); si no hay orilla al alcance o choca
 * con la plaza, un edificio especial, una torre o una calle bajo el muelle, la aldea sale sin puerto (la avenida ya
 * tiene la posada).
 */
public final class AldeaStructure extends Structure {
	private static final Logger LOGGER = LoggerFactory.getLogger(Heraldia.MOD_ID);
	/** Paso de los rayos y desplazamientos laterales de cada rayo. */
	private static final int STEP = 16;
	private static final int[] LATERAL = {0, -16, 16};

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
		if (puerto.isEmpty() || stub.isEmpty()) {
			return stub;
		}
		GenerationStub village = stub.get();
		Puerto p = puerto.get();
		boolean forzada = Generacion.forzada(ctx, biomes());
		// El generador de piezas solo corre al crear la aldea de verdad: /locate y los mapas no pagan la búsqueda.
		return Optional.of(new GenerationStub(village.position(), builder -> {
			long t0 = System.nanoTime();
			List<StructurePiece> pieces = new ArrayList<>(village.getPiecesBuilder().build().pieces());
			long t1 = System.nanoTime();
			String result = addPort(ctx, p, village.position(), pieces);
			for (StructurePiece piece : pieces) {
				builder.addPiece(piece);
			}
			if (forzada) {   // solo con /place structure: la prueba de humo lo lee
				LOGGER.info("Heraldia: aldea de costa en {} {}: {} en {} µs (ensamblar la aldea: {} µs)", village.position().getX(),
						village.position().getZ(), result, (System.nanoTime() - t1) / 1000, (t1 - t0) / 1000);
			}
		}));
	}

	/** Orilla candidata: último punto de tierra baja antes del agua en un rayo, con la dirección hacia el mar. */
	private record Shore(int x, int z, int y, Direction sea, int dist) {
	}

	/**
	 * Casas, rellenos, torres y puertas del final de las calles y lo que va dentro (aldeanos, gólems, decoración): lo
	 * único que el puerto puede desplazar.
	 */
	private static boolean removable(StructurePiece piece) {
		if (!(piece instanceof PoolElementStructurePiece pe)) {
			return false;
		}
		String path = pe.getElement() instanceof SinglePoolElement e ? e.getTemplateLocation().getPath() : "";
		return path.contains("/houses/") || path.contains("/fillers/") || path.contains("/decor/") || path.contains("/terminators/")
				|| path.startsWith("villagers/") || path.equals("golem");
	}

	/**
	 * Piezas de la aldea que habría que quitar para poner el puerto en estas cajas, o null si choca con algo que no se
	 * quita (plaza, edificios especiales, torres). Las calles ({@code terrain_matching}) llegan a la orilla (sobre el agua
	 * el procesador de calle pone tablas): bajo la caseta no cuentan (la caseta, rígida y colocada después, las cubre),
	 * pero una calle cuya planta pisa la del muelle descarta la orilla (sus tablas quedarían bajo las del muelle, un bloque
	 * más abajo, y quitarla dejaría casas sin camino). Con cada casa se van las piezas que quedan dentro de ella (su
	 * aldeano, su cama).
	 */
	private static List<StructurePiece> displaced(List<StructurePiece> village, BoundingBox caseta, BoundingBox muelle) {
		List<StructurePiece> out = new ArrayList<>();
		for (StructurePiece piece : village) {
			BoundingBox b = piece.getBoundingBox();
			if (piece instanceof PoolElementStructurePiece pe
					&& pe.getElement().getProjection() == StructureTemplatePool.Projection.TERRAIN_MATCHING) {
				if (b.intersects(muelle.minX(), muelle.minZ(), muelle.maxX(), muelle.maxZ())) {
					return null;
				}
				continue;
			}
			if (!b.intersects(caseta) && !b.intersects(muelle)) {
				continue;
			}
			if (!removable(piece)) {
				return null;
			}
			out.add(piece);
		}
		for (StructurePiece piece : village) {
			for (int i = 0, n = out.size(); i < n && !out.contains(piece); i++) {
				BoundingBox house = out.get(i).getBoundingBox();
				BoundingBox b = piece.getBoundingBox();
				if (house.minX() <= b.minX() && b.maxX() <= house.maxX() && house.minZ() <= b.minZ() && b.maxZ() <= house.maxZ()
						&& house.minY() <= b.minY() && b.maxY() <= house.maxY()) {
					out.add(piece);
				}
			}
		}
		return out;
	}

	/** Busca la orilla y añade a {@code village} la caseta y el muelle (quitando las casas que ocupen su sitio). */
	private static String addPort(GenerationContext ctx, Puerto p, BlockPos center, List<StructurePiece> village) {
		Alturas h = new Alturas(ctx);
		List<Shore> shores = new ArrayList<>();
		for (Direction d : Direction.Plane.HORIZONTAL) {
			Direction e = d.getClockWise();
			for (int s : LATERAL) {
				int bx = center.getX() + e.getStepX() * s, bz = center.getZ() + e.getStepZ() * s;
				int land = -1;
				for (int r = STEP; r <= p.alcance(); r += STEP) {
					int f = h.floor(bx + d.getStepX() * r, bz + d.getStepZ() * r) - h.sea;
					if (f < 0) {           // agua: la orilla está entre la última tierra baja y aquí
						if (land >= 0) {
							Shore shore = refine(h, bx, bz, d, land, r);
							if (shore != null) {
								shores.add(shore);
							}
						}
						break;
					}
					land = f <= 4 ? r : -1;   // tierra baja (playa); un risco junto al agua no sirve
				}
			}
		}
		shores.sort(Comparator.comparingInt(Shore::dist));
		StructureTemplateManager manager = ctx.structureTemplateManager();
		int shallow = 0, blocked = 0;
		// primero las orillas libres; si no hay, las que solo ocupan casas (se quitan)
		for (int pass = 0; pass < 2; pass++) {
			for (Shore s : shores) {
				Direction sea = s.sea();
				// agua con fondo bajo la punta del muelle, agua a su mitad, más allá de la punta y a los lados (los botes):
				// mar abierto, no una ensenada que acabe en tierra
				int tx = s.x() + sea.getStepX() * p.largo(), tz = s.z() + sea.getStepZ() * p.largo();
				int mx = s.x() + sea.getStepX() * (p.largo() / 2), mz = s.z() + sea.getStepZ() * (p.largo() / 2);
				Direction side = sea.getClockWise();
				if (h.floor(tx, tz) > h.sea - 2 || h.floor(mx, mz) >= h.sea
						|| h.floor(tx + sea.getStepX() * 6, tz + sea.getStepZ() * 6) >= h.sea
						|| h.floor(tx + side.getStepX() * 7, tz + side.getStepZ() * 7) >= h.sea
						|| h.floor(tx - side.getStepX() * 7, tz - side.getStepZ() * 7) >= h.sea) {
					shallow += pass == 0 ? 1 : 0;
					continue;
				}
				Rotation rot = facing(sea);
				StructurePoolElement casetaEl = p.caseta().value().getRandomTemplate(ctx.random());
				StructurePoolElement muelleEl = p.muelle().value().getRandomTemplate(ctx.random());
				// la unión de la caseta (su cara hacia el mar) en la orilla; la del muelle, un bloque mar adentro
				BlockPos shore = new BlockPos(s.x(), s.y(), s.z());
				BlockPos casetaOrigin = shore.subtract(StructureTemplate.transform(p.unionCaseta(), Mirror.NONE, rot, BlockPos.ZERO));
				BlockPos muelleOrigin = shore.relative(sea).subtract(StructureTemplate.transform(p.unionMuelle(), Mirror.NONE, rot, BlockPos.ZERO));
				BoundingBox casetaBox = casetaEl.getBoundingBox(manager, casetaOrigin, rot);
				BoundingBox muelleBox = muelleEl.getBoundingBox(manager, muelleOrigin, rot);
				List<StructurePiece> gone = displaced(village, casetaBox, muelleBox);
				if (gone == null || (pass == 0 && !gone.isEmpty())) {
					blocked += pass == 0 && gone == null ? 1 : 0;
					continue;
				}
				village.removeAll(gone);
				village.add(new PoolElementStructurePiece(manager, casetaEl, casetaOrigin, casetaEl.getGroundLevelDelta(), rot,
						casetaBox, LiquidSettings.APPLY_WATERLOGGING));
				village.add(new PoolElementStructurePiece(manager, muelleEl, muelleOrigin, muelleEl.getGroundLevelDelta(), rot,
						muelleBox, LiquidSettings.APPLY_WATERLOGGING));
				return "muelle en " + s.x() + " " + s.z() + " hacia " + sea.getSerializedName() + ", punta " + tx + " " + tz
						+ " (" + shores.size() + " orillas, " + gone.size() + " piezas desplazadas)";
			}
		}
		return "sin orilla al alcance, sin puerto (" + shores.size() + " orillas: " + shallow + " sin fondo, " + blocked
				+ " junto a edificios que no se quitan o sobre una calle)";
	}

	/** Afina con paso 2 entre la última tierra baja (r0) y la primera agua (r1); null si no queda tierra baja. */
	private static Shore refine(Alturas h, int bx, int bz, Direction d, int r0, int r1) {
		Shore best = null;
		for (int r = r0; r < r1; r += 2) {
			int x = bx + d.getStepX() * r, z = bz + d.getStepZ() * r, floor = h.floor(x, z);
			if (floor < h.sea) {
				break;
			}
			if (floor - h.sea <= 4) {
				best = new Shore(x, z, floor, d, r);
			}
		}
		return best;
	}

	/** Giro que lleva el +z de las plantillas (de la caseta hacia el muelle) a la dirección dada. */
	private static Rotation facing(Direction d) {
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
