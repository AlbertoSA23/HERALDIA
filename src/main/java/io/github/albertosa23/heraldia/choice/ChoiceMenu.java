package io.github.albertosa23.heraldia.choice;

import java.util.ArrayList;
import java.util.List;
import net.minecraft.ChatFormatting;
import net.minecraft.core.component.DataComponents;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.SimpleContainer;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.ChestMenu;
import net.minecraft.world.inventory.ContainerInput;
import net.minecraft.world.inventory.MenuType;
import net.minecraft.world.inventory.Slot;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.component.ItemLore;
import org.jspecify.annotations.Nullable;

/**
 * The container presentation of a {@link Choice} (server only; any client shows it, it is a vanilla two-row chest
 * window): the top row holds a sheet of paper with the speaker's name and lines, the bottom row one stained glass pane
 * per option (its colour), named with the option's text, its lore carrying the line (and the option's hint).
 * <p><b>Nothing ever moves.</b> {@link #clicked} never calls the vanilla click logic: every kind of click (pick up,
 * shift-click, number keys and offhand swap, middle-click clone, drop, drag, double-click collect) on any slot, the
 * window's or the player's own inventory, changes nothing; a left or right click on an option's slot only schedules the
 * pick (handled after the click packet, see {@link Choices#reply}). The client may have predicted a move: the click
 * handler's own resync (it compares the slots the client says it changed with the real ones) puts its view back, and
 * {@link #removed} has nothing to give back because nothing was ever carried. The display items exist only in this
 * window's own container, which is never saved or dropped.
 */
final class ChoiceMenu extends ChestMenu {
	static final int ROWS = 2, LINE_SLOT = 4, OPTION_ROW = 9, LORE_WIDTH = 40;
	private final ServerPlayer player;
	private final SimpleContainer shown;
	private int session;
	private Component title;
	private List<String> slots = List.of();

	private ChoiceMenu(int containerId, Inventory inventory, SimpleContainer shown, ServerPlayer player) {
		super(MenuType.GENERIC_9x2, containerId, inventory, shown, ROWS);
		this.player = player;
		this.shown = shown;
		this.title = Component.empty();
	}

	static ChoiceMenu create(int containerId, Inventory inventory, ServerPlayer player, int session, Choice.Prompt prompt) {
		ChoiceMenu m = new ChoiceMenu(containerId, inventory, new SimpleContainer(ROWS * 9), player);
		m.fill(session, prompt);
		return m;
	}

	int session() {
		return session;
	}

	Component shownTitle() {
		return title;
	}

	/** Puts a prompt in the window (the first one, or the next page of the same conversation without reopening it). */
	void fill(int session, Choice.Prompt prompt) {
		this.session = session;
		this.title = prompt.title();
		shown.clearContent();
		List<Component> said = lore(prompt.lines());
		shown.setItem(LINE_SLOT, item(Items.PAPER, prompt.title().copy().withStyle(ChatFormatting.GOLD), said));
		int[] row = Choice.row(prompt.options().size());
		List<String> ids = new ArrayList<>();
		for (int i = 0; i < ROWS * 9; i++) {
			ids.add(null);
		}
		for (int i = 0; i < row.length; i++) {
			Choice.Option o = prompt.options().get(i);
			List<Component> lore = new ArrayList<>(said);
			if (!o.hint().isEmpty()) {
				if (!lore.isEmpty()) {
					lore.add(Component.empty());
				}
				for (String s : Choice.wrap(o.hint(), LORE_WIDTH)) {
					lore.add(plain(s, Choice.GRAY, false));
				}
			}
			shown.setItem(OPTION_ROW + row[i], item(pane(o.color()), Component.literal(o.label())
					.withStyle(s -> s.withColor(o.color()).withItalic(false).withBold(true)), lore));
			ids.set(OPTION_ROW + row[i], o.id());
		}
		this.slots = ids;
		broadcastChanges();
	}

	/** The option id of a slot of the window, or null (an empty slot, the paper, the player's inventory). */
	@Nullable String option(int slot) {
		return slot >= 0 && slot < slots.size() ? slots.get(slot) : null;
	}

	@Override
	public void clicked(int slot, int button, ContainerInput input, Player p) {
		String id = option(slot);
		if (id != null && input == ContainerInput.PICKUP && (button == 0 || button == 1) && p == player) {
			Choices.menuPick(player, session, id);
		}
		// nothing else: no vanilla click logic at all, so no item can be taken, placed, swapped, cloned or dropped
	}

	@Override
	public ItemStack quickMoveStack(Player p, int slot) {
		return ItemStack.EMPTY;
	}

	@Override
	public boolean canTakeItemForPickAll(ItemStack stack, Slot slot) {
		return false;
	}

	@Override
	public boolean canDragTo(Slot slot) {
		return false;
	}

	@Override
	public boolean stillValid(Player p) {
		return p == player && Choices.stillValid(player, session);
	}

	@Override
	public void removed(Player p) {
		super.removed(p);
		shown.clearContent();
		if (p == player) {
			Choices.menuClosed(player, session);
		}
	}

	// --- the display items ---

	private static List<Component> lore(List<Choice.Line> lines) {
		List<Component> out = new ArrayList<>();
		for (Choice.Line l : lines) {
			for (String s : Choice.wrap(l.text(), LORE_WIDTH)) {
				out.add(plain(s, l.color(), l.italic()));
			}
		}
		return out.size() > ItemLore.MAX_LINES ? out.subList(0, ItemLore.MAX_LINES) : out;
	}

	private static MutableComponent plain(String s, int color, boolean italic) {
		return Component.literal(s).withStyle(st -> st.withColor(color).withItalic(italic));
	}

	private static ItemStack item(Item item, Component name, List<Component> lore) {
		ItemStack s = new ItemStack(item);
		s.set(DataComponents.CUSTOM_NAME, name.copy().withStyle(st -> st.withItalic(false)));
		s.set(DataComponents.LORE, new ItemLore(lore));
		return s;
	}

	/** A cheap, plain item of the option's colour (vanilla client: the colour is the only icon it needs). */
	static Item pane(int color) {
		return switch (color) {
			case Choice.AQUA -> Items.STAINED_GLASS_PANE.lightBlue();
			case Choice.PURPLE -> Items.STAINED_GLASS_PANE.magenta();
			case Choice.GREEN -> Items.STAINED_GLASS_PANE.lime();
			case Choice.GRAY -> Items.STAINED_GLASS_PANE.lightGray();
			case Choice.GOLD -> Items.STAINED_GLASS_PANE.orange();
			case Choice.RED -> Items.STAINED_GLASS_PANE.red();
			case Choice.YELLOW -> Items.STAINED_GLASS_PANE.yellow();
			default -> Items.STAINED_GLASS_PANE.white();
		};
	}
}
