package io.github.albertosa23.heraldia.loot;

import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.common.TemplateBlocks;
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
import net.minecraft.world.level.levelgen.structure.StructurePiece;
import net.minecraft.world.level.levelgen.structure.StructureStart;
import net.minecraft.world.level.levelgen.structure.templatesystem.StructureTemplate;
import net.minecraft.world.level.storage.loot.LootTable;
import net.minecraft.world.phys.BlockHitResult;
import org.jspecify.annotations.Nullable;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Restocking loot (botin.reponer.activado, disabled by default). Lazy: it only works when a player uses a
 * container with a loot table (chest, trapped chest, barrel), never per tick nor walking the world.
 * <ul>
 * <li>A Heraldia chest that still has its table: the table and the looting clock are recorded (the game opens it in this
 * same use).</li>
 * <li>One already opened before the option was enabled (or emptied by a hopper): its original table is looked up once in the
 * template of the piece of the Heraldia structure that contains it ({@link #templateTable}) and the count starts
 * then.</li>
 * <li>A recorded one: if the days have passed, there is no other player within 32 blocks and it has at most
 * {@link Restock#MAX_OCCUPIED} occupied slots, its table is set again; the game opens it when the chest is shown and
 * only fills free slots, so nothing is deleted.</li>
 * </ul>
 * With Lootr loaded it does nothing: Lootr turns table chests into per-player chests with its own restocking. The
 * Atlantis premium chest (fixed content, {@link PerPlayerChest#MARK}) and the trophies do not restock.
 */
public final class RestockedLoot {
	private static final Logger LOGGER = LoggerFactory.getLogger(Heraldia.MOD_ID);

	private RestockedLoot() {
	}

	public static void register() {
		UseBlockCallback.EVENT.register(RestockedLoot::use);
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
			return InteractionResult.PASS; // the vast majority of uses exit here
		}
		HeraldiaConfig cfg = HeraldiaConfig.get();
		if (!cfg.getBool("botin.reponer.activado") || WithoutLootrCondition.LOOTR_LOADED) {
			return InteractionResult.PASS;
		}
		if (player.isSecondaryUseActive() && !(player.getMainHandItem().isEmpty() && player.getOffhandItem().isEmpty())) {
			return InteractionResult.PASS; // sneaking with something in hand: places a block, does not open
		}
		if (!box.canOpen(player)) {
			return InteractionResult.PASS; // locked: does not open, is not looted
		}
		review(server, box, player, cfg);
		BlockState state = level.getBlockState(pos);
		if (state.getBlock() instanceof ChestBlock && state.getValue(ChestBlock.TYPE) != ChestType.SINGLE
				&& level.getBlockEntity(ChestBlock.getConnectedBlockPos(pos, state)) instanceof RandomizableContainerBlockEntity other) {
			review(server, other, player, cfg); // a double chest opens both halves
		}
		return InteractionResult.PASS;
	}

	private static void review(ServerLevel level, RandomizableContainerBlockEntity box, Player player, HeraldiaConfig cfg) {
		CompoundTag data = customData(box);
		if (data.contains(PerPlayerChest.MARK)) {
			return; // fixed content (Atlantis premium chest): it has its own option
		}
		long now = level.getOverworldClockTime();
		ResourceKey<LootTable> pending = box.getLootTable();
		Optional<Restock.Ledger> ledger = Restock.ledger(data);
		if (pending == null && ledger.isEmpty()) {
			String original = templateTable(level, box.getBlockPos(), box.getBlockState());
			if (original != null && Restock.tableRestocks(original)) {
				save(box, Restock.withLedger(data, new Restock.Ledger(original, now)));
			}
			return;
		}
		Restock.Decision d = Restock.decide(pending == null ? null : pending.identifier().toString(), ledger, now,
				cfg.getInt("botin.reponer.dias"), otherPlayers(level, box.getBlockPos(), player), occupied(box));
		switch (d) {
			case RECORD -> save(box, Restock.withLedger(data, new Restock.Ledger(pending.identifier().toString(), now)));
			case RESET -> save(box, Restock.withLedger(data, new Restock.Ledger(ledger.get().table(), now)));
			case RESTOCK -> {
				Identifier id = Identifier.tryParse(ledger.get().table());
				if (id != null) {
					box.setLootTable(ResourceKey.create(Registries.LOOT_TABLE, id), level.getRandom().nextLong());
					save(box, Restock.withLedger(data, new Restock.Ledger(ledger.get().table(), now)));
				}
			}
			case NOTHING, WAIT -> {
			}
		}
	}

	static int otherPlayers(ServerLevel level, BlockPos pos, Player opener) {
		double r2 = Restock.PLAYER_RADIUS * Restock.PLAYER_RADIUS;
		int n = 0;
		for (Player p : level.players()) {
			if (p != opener && !p.isSpectator() && p.distanceToSqr(pos.getX() + 0.5, pos.getY() + 0.5, pos.getZ() + 0.5) <= r2) {
				n++;
			}
		}
		return n;
	}

	static int occupied(RandomizableContainerBlockEntity box) {
		int n = 0;
		for (int i = 0; i < box.getContainerSize(); i++) {
			if (!box.getItem(i).isEmpty()) {
				n++;
			}
		}
		return n;
	}

	/**
	 * Loot table the Heraldia template put at this position (for chests opened before the
	 * option was enabled, which no longer have it), or null. It finds the Heraldia structure with a piece at the position (the
	 * chunk's references, like /locate), and in its pool piece the template with its rotation: the same computation as when it was placed.
	 */
	static @Nullable String templateTable(ServerLevel level, BlockPos pos, BlockState state) {
		try {
			StructureStart start = level.structureManager().getStructureWithPieceAt(pos,
					h -> h.unwrapKey().map(k -> Heraldia.MOD_ID.equals(k.identifier().getNamespace())).orElse(false));
			if (!start.isValid()) {
				return null;
			}
			for (StructurePiece piece : start.getPieces()) {
				if (!piece.getBoundingBox().isInside(pos)) {
					continue;
				}
				for (StructureTemplate.StructureBlockInfo info : TemplateBlocks.of(level, piece, state.getBlock())) {
					if (info.pos().equals(pos) && info.nbt() != null) {
						String table = info.nbt().getStringOr("LootTable", "");
						return table.isEmpty() ? null : table;
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

	private static void save(RandomizableContainerBlockEntity box, CompoundTag data) {
		box.setComponents(DataComponentMap.builder().addAll(box.components()).set(DataComponents.CUSTOM_DATA, CustomData.of(data)).build());
		box.setChanged();
	}
}
