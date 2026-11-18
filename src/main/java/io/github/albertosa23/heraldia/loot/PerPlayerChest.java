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
 * Cofre de contenido fijo «por jugador» (opción unicas.&lt;id&gt;.cofre_unico_por_jugador, por defecto desactivada).
 * El generador marca el cofre con custom_data {heraldia_cofre_unico: "&lt;id&gt;"} en los componentes del bloque. Con la
 * opción activada, al abrirlo la primera vez su contenido pasa a ser la plantilla (el cofre queda vacío: romperlo o
 * vaciarlo con una tolva no duplica nada) y cada jugador abre su propia copia, guardada en el mismo cofre: la recibe
 * entera la primera vez y luego encuentra lo que dejó. Es lo que hace Lootr con los cofres de tabla (Lootr no toca este
 * porque no tiene tabla), así que con Lootr o sin él se comporta igual. Solo trabaja al usar un bloque: nada por tick.
 */
public final class PerPlayerChest {
	/** Misma clave que MARCA_POR_JUGADOR en tools/gen/unicas/atlantida/cosas.py. */
	public static final String MARK = "heraldia_cofre_unico";
	static final String TEMPLATE = "heraldia_plantilla", PLAYERS = "heraldia_jugadores";
	private static final int SIZE = 27;

	private PerPlayerChest() {
	}

	public static void register() {
		UseBlockCallback.EVENT.register(PerPlayerChest::use);
	}

	/** La clave de la opción que gobierna el cofre, o null si no es un cofre marcado. Barato: un mapa de componentes. */
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
			return InteractionResult.PASS; // la inmensa mayoría de los usos salen aquí
		}
		String key = option(chest);
		HeraldiaConfig cfg = HeraldiaConfig.get();
		if (key == null || !cfg.has(key)) {
			return InteractionResult.PASS;
		}
		if (!cfg.getBool(key)) { // opción desactivada (quizá después de usarla): el contenido vuelve al cofre, una vez
			CompoundTag data = data(chest);
			if (restore(data, chest, level.registryAccess().createSerializationContext(NbtOps.INSTANCE))) {
				store(chest, data);
			}
			return InteractionResult.PASS;
		}
		if (player.isSecondaryUseActive() && !(player.getMainHandItem().isEmpty() && player.getOffhandItem().isEmpty())) {
			return InteractionResult.PASS; // agachado con algo en la mano: colocar bloques, como en vanilla
		}
		if (!chest.canOpen(player)) { // la cerradura (llave en la mano) se respeta igual que en el cofre normal
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
	 * Contenido de la copia del jugador. La primera apertura con la opción activada captura el contenido del cofre como
	 * plantilla y lo vacía; un jugador sin copia recibe la plantilla entera y queda apuntado. Modifica data.
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
	 * Con la opción desactivada: si había plantilla y el cofre está vacío, la devuelve al cofre y la borra (vuelve a ser
	 * un cofre de contenido fijo normal; las copias de los jugadores se conservan por si se reactiva). Modifica data.
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

	/** Guarda la copia del jugador en data (al cerrar). */
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

	/** custom_data actual del cofre (se relee en cada operación: dos jugadores pueden tenerlo abierto a la vez). */
	private static CompoundTag data(ChestBlockEntity chest) {
		CustomData cd = chest.components().get(DataComponents.CUSTOM_DATA);
		return cd == null ? new CompoundTag() : cd.copyTag();
	}

	private static void store(ChestBlockEntity chest, CompoundTag data) {
		chest.setComponents(DataComponentMap.builder().addAll(chest.components()).set(DataComponents.CUSTOM_DATA, CustomData.of(data)).build());
		chest.setChanged();
	}

	/** Copia de un jugador abierta en un menú de cofre; al cerrarse se guarda en el cofre. */
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
