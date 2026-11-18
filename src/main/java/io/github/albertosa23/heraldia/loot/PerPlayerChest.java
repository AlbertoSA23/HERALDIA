package io.github.albertosa23.heraldia.loot;

import com.mojang.serialization.DynamicOps;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import net.fabricmc.fabric.api.event.player.UseBlockCallback;
import net.minecraft.core.BlockPos;
import net.minecraft.core.NonNullList;
import net.minecraft.core.component.DataComponentMap;
import net.minecraft.core.component.DataComponents;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.NbtOps;
import net.minecraft.nbt.Tag;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.Container;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.SimpleContainer;
import net.minecraft.world.SimpleMenuProvider;
import net.minecraft.world.entity.ContainerUser;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.ChestMenu;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.component.CustomData;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.entity.BaseContainerBlockEntity;
import net.minecraft.world.level.block.entity.ChestBlockEntity;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.Vec3;
import org.jspecify.annotations.Nullable;

/**
 * Fixed-content "per player" chest (option unicas.&lt;id&gt;.cofre_unico_por_jugador, disabled by default).
 * The generator marks the chest with custom_data {heraldia_cofre_unico: "&lt;id&gt;"} in the block's components. With the
 * option enabled, on the first opening its contents become the template (the chest is left empty: breaking it or
 * emptying it with a hopper duplicates nothing) and each player opens their own copy, stored in the same chest: they get it
 * whole the first time and then find what they left. It is what Lootr does with table chests (Lootr does not touch this one
 * because it has no table), so with or without Lootr it behaves the same. It only works when a block is used: nothing per tick.
 */
public final class PerPlayerChest {
	/** Same key as MARK_PER_PLAYER in tools/gen/uniques/atlantis/things.py. */
	public static final String MARK = "heraldia_cofre_unico";
	static final String TEMPLATE = "heraldia_plantilla", PLAYERS = "heraldia_jugadores";
	private static final int SIZE = 27;

	private PerPlayerChest() {
	}

	public static void register() {
		UseBlockCallback.EVENT.register(PerPlayerChest::use);
	}

	/** Key of the option that governs the chest, or null if it is not a marked chest. Cheap: a component map. */
	public static @Nullable String option(ChestBlockEntity chest) {
		CustomData cd = chest.components().get(DataComponents.CUSTOM_DATA);
		if (cd == null) {
			return null;
		}
		String owner = cd.copyTag().getStringOr(MARK, "");
		return owner.isEmpty() ? null : "unicas." + owner + ".cofre_unico_por_jugador";
	}

	private static InteractionResult use(Player player, Level level, InteractionHand hand, BlockHitResult hit) {
		if (level.isClientSide() || player.isSpectator() || !(player instanceof ServerPlayer sp)) {
			return InteractionResult.PASS;
		}
		BlockPos pos = hit.getBlockPos();
		if (!(level.getBlockEntity(pos) instanceof ChestBlockEntity chest)) {
			return InteractionResult.PASS; // the vast majority of uses exit here
		}
		String key = option(chest);
		HeraldiaConfig cfg = HeraldiaConfig.get();
		if (key == null || !cfg.has(key)) {
			return InteractionResult.PASS;
		}
		if (!cfg.getBool(key)) { // option disabled (maybe after using it): the contents go back to the chest, once
			CompoundTag data = data(chest);
			if (restore(data, chest, level.registryAccess().createSerializationContext(NbtOps.INSTANCE))) {
				store(chest, data);
			}
			return InteractionResult.PASS;
		}
		if (player.isSecondaryUseActive() && !(player.getMainHandItem().isEmpty() && player.getOffhandItem().isEmpty())) {
			return InteractionResult.PASS; // sneaking with something in hand: place blocks, as in vanilla
		}
		if (!chest.canOpen(player)) { // the lock (key in hand) is respected just like on a normal chest
			BaseContainerBlockEntity.sendChestLockedNotifications(Vec3.atCenterOf(pos), player, chest.getDisplayName());
			return InteractionResult.SUCCESS;
		}
		DynamicOps<Tag> ops = level.registryAccess().createSerializationContext(NbtOps.INSTANCE);
		String id = player.getUUID().toString();
		CompoundTag data = data(chest);
		NonNullList<ItemStack> items = open(data, chest, id, ops);
		store(chest, data);
		Copy copy = new Copy(chest, id, ops);
		for (int i = 0; i < SIZE; i++) {
			copy.setItem(i, items.get(i));
		}
		sp.openMenu(new SimpleMenuProvider((containerId, inventory, p) -> ChestMenu.threeRows(containerId, inventory, copy),
				chest.getDisplayName()));
		level.playSound(null, pos, SoundEvents.CHEST_OPEN, SoundSource.BLOCKS, 0.5F, 1.0F);
		return InteractionResult.SUCCESS;
	}

	/**
	 * Contents of the player's copy. The first opening with the option enabled captures the chest's contents as the
	 * template and empties it; a player without a copy gets the whole template and is recorded. Modifies data.
	 */
	static NonNullList<ItemStack> open(CompoundTag data, Container chest, String player, DynamicOps<Tag> ops) {
		if (!data.contains(TEMPLATE)) {
			NonNullList<ItemStack> template = NonNullList.withSize(SIZE, ItemStack.EMPTY);
			for (int i = 0; i < Math.min(SIZE, chest.getContainerSize()); i++) {
				template.set(i, chest.getItem(i).copy());
			}
			chest.clearContent();
			data.put(TEMPLATE, write(template, ops));
		}
		CompoundTag players = data.getCompoundOrEmpty(PLAYERS);
		NonNullList<ItemStack> items = read(players.contains(player) ? players.getListOrEmpty(player) : data.getListOrEmpty(TEMPLATE), ops);
		if (!players.contains(player)) {
			players.put(player, write(items, ops));
			data.put(PLAYERS, players);
		}
		return items;
	}

	/**
	 * With the option disabled: if there was a template and the chest is empty, it gives it back to the chest and deletes it (it becomes
	 * a normal fixed-content chest again; the players' copies are kept in case it is re-enabled). Modifies data.
	 */
	static boolean restore(CompoundTag data, Container chest, DynamicOps<Tag> ops) {
		if (!data.contains(TEMPLATE) || !chest.isEmpty()) {
			return false;
		}
		NonNullList<ItemStack> template = read(data.getListOrEmpty(TEMPLATE), ops);
		for (int i = 0; i < Math.min(SIZE, chest.getContainerSize()); i++) {
			chest.setItem(i, template.get(i));
		}
		data.remove(TEMPLATE);
		return true;
	}

	/** Saves the player's copy in data (on close). */
	static void save(CompoundTag data, String player, Container copy, DynamicOps<Tag> ops) {
		NonNullList<ItemStack> items = NonNullList.withSize(SIZE, ItemStack.EMPTY);
		for (int i = 0; i < SIZE; i++) {
			items.set(i, copy.getItem(i));
		}
		CompoundTag players = data.getCompoundOrEmpty(PLAYERS);
		players.put(player, write(items, ops));
		data.put(PLAYERS, players);
	}

	static ListTag write(NonNullList<ItemStack> items, DynamicOps<Tag> ops) {
		ListTag list = new ListTag();
		for (int i = 0; i < items.size(); i++) {
			ItemStack stack = items.get(i);
			if (!stack.isEmpty()) {
				CompoundTag entry = new CompoundTag();
				entry.putByte("Slot", (byte) i);
				entry.put("item", ItemStack.CODEC.encodeStart(ops, stack).getOrThrow());
				list.add(entry);
			}
		}
		return list;
	}

	static NonNullList<ItemStack> read(ListTag list, DynamicOps<Tag> ops) {
		NonNullList<ItemStack> items = NonNullList.withSize(SIZE, ItemStack.EMPTY);
		for (Tag t : list) {
			if (t instanceof CompoundTag entry && entry.get("item") != null) {
				int slot = entry.getByteOr("Slot", (byte) -1);
				if (slot >= 0 && slot < SIZE) {
					items.set(slot, ItemStack.CODEC.parse(ops, entry.get("item")).result().orElse(ItemStack.EMPTY));
				}
			}
		}
		return items;
	}

	/** The chest's current custom_data (re-read on every operation: two players can have it open at once). */
	private static CompoundTag data(ChestBlockEntity chest) {
		CustomData cd = chest.components().get(DataComponents.CUSTOM_DATA);
		return cd == null ? new CompoundTag() : cd.copyTag();
	}

	private static void store(ChestBlockEntity chest, CompoundTag data) {
		chest.setComponents(DataComponentMap.builder().addAll(chest.components()).set(DataComponents.CUSTOM_DATA, CustomData.of(data)).build());
		chest.setChanged();
	}

	/** A player's copy open in a chest menu; on close it is saved in the chest. */
	private static final class Copy extends SimpleContainer {
		private final ChestBlockEntity chest;
		private final String player;
		private final DynamicOps<Tag> ops;

		Copy(ChestBlockEntity chest, String player, DynamicOps<Tag> ops) {
			super(SIZE);
			this.chest = chest;
			this.player = player;
			this.ops = ops;
		}

		@Override
		public boolean stillValid(Player p) {
			return Container.stillValidBlockEntity(chest, p);
		}

		@Override
		public void stopOpen(ContainerUser user) {
			if (chest.isRemoved()) {
				return;
			}
			CompoundTag data = data(chest);
			save(data, player, this, ops);
			store(chest, data);
			Level level = chest.getLevel();
			if (level != null) {
				level.playSound(null, chest.getBlockPos(), SoundEvents.CHEST_CLOSE, SoundSource.BLOCKS, 0.5F, 1.0F);
			}
		}
	}
}
