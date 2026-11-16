package io.github.albertosa23.heraldia.loot;

import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import java.util.Optional;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.fabricmc.fabric.api.event.player.UseBlockCallback;
import net.minecraft.core.BlockPos;
import net.minecraft.core.component.DataComponentMap;
import net.minecraft.core.component.DataComponents;
import net.minecraft.core.registries.Registries;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.resources.Identifier;
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.component.CustomData;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.ChestBlock;
import net.minecraft.world.level.block.entity.RandomizableContainerBlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.ChestType;
import net.minecraft.world.level.levelgen.structure.PoolElementStructurePiece;
import net.minecraft.world.level.levelgen.structure.StructurePiece;
import net.minecraft.world.level.levelgen.structure.StructureStart;
import net.minecraft.world.level.levelgen.structure.pools.SinglePoolElement;
import net.minecraft.world.level.levelgen.structure.templatesystem.StructurePlaceSettings;
import net.minecraft.world.level.levelgen.structure.templatesystem.StructureTemplate;
import net.minecraft.world.level.storage.loot.LootTable;
import net.minecraft.world.phys.BlockHitResult;
import org.jspecify.annotations.Nullable;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Botín que se repone (botin.reponer.activado, por defecto desactivado). Perezoso: solo trabaja cuando un jugador usa un
 * contenedor con tabla de botín (cofre, cofre trampa, barril), nunca por tick ni recorriendo el mundo.
 * <ul>
 * <li>Un cofre de Heraldia que aún tiene su tabla: se apunta la tabla y el reloj del saqueo (el juego la abre en este
 * mismo uso).</li>
 * <li>Uno ya abierto antes de activar la opción (o vaciado por una tolva): su tabla original se busca una vez en la
 * plantilla de la pieza de la estructura de Heraldia que lo contiene ({@link #tablaDeLaPlantilla}) y la cuenta empieza
 * entonces.</li>
 * <li>Uno apuntado: si han pasado los días, no hay otro jugador a 32 bloques y tiene como mucho
 * {@link Reposicion#MAX_OCUPADAS} casillas ocupadas, se le vuelve a poner la tabla; el juego la abre al mostrar el cofre y
 * solo llena casillas libres, así que no se borra nada.</li>
 * </ul>
 * Con Lootr cargado no hace nada: Lootr convierte los cofres de tabla en cofres por jugador con su propia reposición. El
 * cofre premium de la Atlántida (contenido fijo, {@link CofrePorJugador#MARK}) y los trofeos no se reponen.
 */
public final class BotinRepuesto {
	private static final Logger LOGGER = LoggerFactory.getLogger(Heraldia.MOD_ID);

	private BotinRepuesto() {
	}

	public static void registrar() {
		UseBlockCallback.EVENT.register(BotinRepuesto::use);
		ServerLifecycleEvents.SERVER_STARTED.register(server -> {
			HeraldiaConfig cfg = HeraldiaConfig.get();
			if (cfg.getBool("botin.reponer.activado")) {
				LOGGER.info(WithoutLootrCondition.LOOTR_LOADED
						? "Heraldia: botín que se repone desactivado porque Lootr está cargado (Lootr ya da botín por jugador)"
						: "Heraldia: botín que se repone activado: cada {} días de juego", cfg.getInt("botin.reponer.dias"));
			}
		});
	}

	private static InteractionResult use(Player player, Level level, InteractionHand hand, BlockHitResult hit) {
		if (!(level instanceof ServerLevel server) || player.isSpectator()) {
			return InteractionResult.PASS;
		}
		BlockPos pos = hit.getBlockPos();
		if (!(level.getBlockEntity(pos) instanceof RandomizableContainerBlockEntity box)) {
			return InteractionResult.PASS; // la inmensa mayoría de los usos salen aquí
		}
		HeraldiaConfig cfg = HeraldiaConfig.get();
		if (!cfg.getBool("botin.reponer.activado") || WithoutLootrCondition.LOOTR_LOADED) {
			return InteractionResult.PASS;
		}
		if (player.isSecondaryUseActive() && !(player.getMainHandItem().isEmpty() && player.getOffhandItem().isEmpty())) {
			return InteractionResult.PASS; // agachado con algo en la mano: coloca un bloque, no abre
		}
		if (!box.canOpen(player)) {
			return InteractionResult.PASS; // cerrado con llave: no se abre, no se saquea
		}
		revisar(server, box, player, cfg);
		BlockState state = level.getBlockState(pos);
		if (state.getBlock() instanceof ChestBlock && state.getValue(ChestBlock.TYPE) != ChestType.SINGLE
				&& level.getBlockEntity(ChestBlock.getConnectedBlockPos(pos, state)) instanceof RandomizableContainerBlockEntity other) {
			revisar(server, other, player, cfg); // un cofre doble abre las dos mitades
		}
		return InteractionResult.PASS;
	}

	private static void revisar(ServerLevel level, RandomizableContainerBlockEntity box, Player player, HeraldiaConfig cfg) {
		CompoundTag data = customData(box);
		if (data.contains(CofrePorJugador.MARK)) {
			return; // contenido fijo (cofre premium de la Atlántida): tiene su propia opción
		}
		long ahora = level.getOverworldClockTime();
		ResourceKey<LootTable> pendiente = box.getLootTable();
		Optional<Reposicion.Registro> registro = Reposicion.registro(data);
		if (pendiente == null && registro.isEmpty()) {
			String original = tablaDeLaPlantilla(level, box.getBlockPos(), box.getBlockState());
			if (original != null && Reposicion.tablaRepone(original)) {
				guardar(box, Reposicion.conRegistro(data, new Reposicion.Registro(original, ahora)));
			}
			return;
		}
		Reposicion.Decision d = Reposicion.decidir(pendiente == null ? null : pendiente.identifier().toString(), registro, ahora,
				cfg.getInt("botin.reponer.dias"), otrosJugadores(level, box.getBlockPos(), player), ocupadas(box));
		switch (d) {
			case APUNTAR -> guardar(box, Reposicion.conRegistro(data, new Reposicion.Registro(pendiente.identifier().toString(), ahora)));
			case REINICIAR -> guardar(box, Reposicion.conRegistro(data, new Reposicion.Registro(registro.get().tabla(), ahora)));
			case REPONER -> {
				Identifier id = Identifier.tryParse(registro.get().tabla());
				if (id != null) {
					box.setLootTable(ResourceKey.create(Registries.LOOT_TABLE, id), level.getRandom().nextLong());
					guardar(box, Reposicion.conRegistro(data, new Reposicion.Registro(registro.get().tabla(), ahora)));
				}
			}
			case NADA, ESPERAR -> {
			}
		}
	}

	static int otrosJugadores(ServerLevel level, BlockPos pos, Player opener) {
		double r2 = Reposicion.RADIO_JUGADORES * Reposicion.RADIO_JUGADORES;
		int n = 0;
		for (Player p : level.players()) {
			if (p != opener && !p.isSpectator() && p.distanceToSqr(pos.getX() + 0.5, pos.getY() + 0.5, pos.getZ() + 0.5) <= r2) {
				n++;
			}
		}
		return n;
	}

	static int ocupadas(RandomizableContainerBlockEntity box) {
		int n = 0;
		for (int i = 0; i < box.getContainerSize(); i++) {
			if (!box.getItem(i).isEmpty()) {
				n++;
			}
		}
		return n;
	}

	/**
	 * Tabla de botín que la plantilla de Heraldia puso en esta posición (para los cofres abiertos antes de activar la
	 * opción, que ya no la tienen), o null. Busca la estructura de Heraldia con una pieza en la posición (las referencias
	 * del chunk, como /locate), y en su pieza de pool la plantilla con su giro: el mismo cálculo que al colocarla.
	 */
	static @Nullable String tablaDeLaPlantilla(ServerLevel level, BlockPos pos, BlockState state) {
		try {
			StructureStart start = level.structureManager().getStructureWithPieceAt(pos,
					h -> h.unwrapKey().map(k -> Heraldia.MOD_ID.equals(k.identifier().getNamespace())).orElse(false));
			if (!start.isValid()) {
				return null;
			}
			for (StructurePiece piece : start.getPieces()) {
				if (!(piece instanceof PoolElementStructurePiece p) || !p.getBoundingBox().isInside(pos)
						|| !(p.getElement() instanceof SinglePoolElement e)) {
					continue;
				}
				Optional<StructureTemplate> t = level.getStructureTemplateManager().get(e.getTemplateLocation());
				if (t.isEmpty()) {
					continue;
				}
				StructurePlaceSettings s = new StructurePlaceSettings().setRotation(p.getRotation());
				for (StructureTemplate.StructureBlockInfo info : t.get().filterBlocks(p.getPosition(), s, state.getBlock())) {
					if (info.pos().equals(pos) && info.nbt() != null) {
						String tabla = info.nbt().getStringOr("LootTable", "");
						return tabla.isEmpty() ? null : tabla;
					}
				}
			}
		} catch (RuntimeException ex) {
			LOGGER.debug("Heraldia: no se pudo leer la plantilla del cofre en {} ({})", pos, ex.toString());
		}
		return null;
	}

	private static CompoundTag customData(RandomizableContainerBlockEntity box) {
		CustomData cd = box.components().get(DataComponents.CUSTOM_DATA);
		return cd == null ? new CompoundTag() : cd.copyTag();
	}

	private static void guardar(RandomizableContainerBlockEntity box, CompoundTag data) {
		box.setComponents(DataComponentMap.builder().addAll(box.components()).set(DataComponents.CUSTOM_DATA, CustomData.of(data)).build());
		box.setChanged();
	}
}
