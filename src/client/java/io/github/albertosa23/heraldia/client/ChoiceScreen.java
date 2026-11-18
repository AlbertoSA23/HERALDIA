package io.github.albertosa23.heraldia.client;

import com.mojang.blaze3d.platform.InputConstants;
import io.github.albertosa23.heraldia.choice.Choice;
import io.github.albertosa23.heraldia.choice.ChoicePayloads;
import java.util.ArrayList;
import java.util.List;
import net.fabricmc.api.EnvType;
import net.fabricmc.api.Environment;
import net.fabricmc.fabric.api.client.networking.v1.ClientPlayNetworking;
import net.minecraft.ChatFormatting;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.components.MultiLineTextWidget;
import net.minecraft.client.gui.components.Tooltip;
import net.minecraft.client.gui.layouts.FrameLayout;
import net.minecraft.client.gui.layouts.GridLayout;
import net.minecraft.client.gui.layouts.LinearLayout;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.client.input.KeyEvent;
import net.minecraft.client.renderer.RenderPipelines;
import net.minecraft.network.chat.CommonComponents;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.resources.Identifier;

/**
 * The mod's presentation of a choice (choice/Choice): a speech panel in the middle of the screen with the speaker's
 * name, their lines and the options as buttons stacked under them. Vanilla widgets and vanilla's own pop-up ninepatch
 * ({@code popup/background}): no texture or font of the mod's own.
 * <ul>
 * <li>Like a chest: the mouse is free, the world dims a little behind the panel and the game does not pause (in single
 * player the world keeps running, as with any container).</li>
 * <li>Mouse, or keyboard: the number keys pick an option (1 to 9, also on the numeric keypad), the arrow keys and Tab
 * move between the buttons, Enter or Space presses the one selected (the first, when it opens) and Escape leaves.</li>
 * <li>The texts come from the server already in the player's language (the same strings the container menu shows); the
 * title is a text component the client translates (a villager's profession).</li>
 * <li>After a pick the buttons wait (greyed out) until the server sends the next page or closes the window: the server
 * decides everything and checks the pick (choice/Choices#reply).</li>
 * <li>Sized for the GUI: at most 300 wide, narrower on a small window; when the panel would not fit the height (GUI scale
 * 4 on a short window), the buttons go in two columns.</li>
 * </ul>
 */
@Environment(EnvType.CLIENT)
public final class ChoiceScreen extends Screen {
	private static final Identifier BACKGROUND = Identifier.withDefaultNamespace("popup/background");
	private static final int BORDER = 14, MARGIN = 8, MAX_WIDTH = 300, BUTTON_HEIGHT = 20, GAP = 3;
	private int session;
	private Choice.Prompt prompt;
	private boolean waiting;
	private final List<Button> buttons = new ArrayList<>();
	private LinearLayout layout = LinearLayout.vertical();

	private ChoiceScreen(int session, Choice.Prompt prompt) {
		super(prompt.title());
		this.session = session;
		this.prompt = prompt;
	}

	/** The receivers, from HeraldiaClient (they register this protocol's channels: that is what the server sees). */
	static void register() {
		ClientPlayNetworking.registerGlobalReceiver(ChoicePayloads.Open.TYPE, (payload, ctx) -> open(ctx.client(), payload));
		ClientPlayNetworking.registerGlobalReceiver(ChoicePayloads.Close.TYPE, (payload, ctx) -> {
			if (ctx.client().gui.screen() instanceof ChoiceScreen s && s.session == payload.session()) {
				ctx.client().gui.setScreen(null);
			}
		});
	}

	private static void open(Minecraft minecraft, ChoicePayloads.Open payload) {
		if (minecraft.gui.screen() instanceof ChoiceScreen s) {
			s.session = payload.session();      // the next page in the same panel
			s.prompt = payload.prompt();
			s.waiting = false;
			s.rebuildWidgets();
			s.setInitialFocus();
			return;
		}
		minecraft.gui.setScreen(new ChoiceScreen(payload.session(), payload.prompt()));
	}

	@Override
	protected void init() {
		buttons.clear();
		int contentWidth = Math.max(120, Math.min(MAX_WIDTH, this.width - 2 * (BORDER + MARGIN)));
		layout = LinearLayout.vertical();
		layout.spacing(6).defaultCellSetting().alignHorizontallyCenter();
		layout.addChild(new MultiLineTextWidget(prompt.title().copy().withStyle(ChatFormatting.GOLD, ChatFormatting.BOLD), this.font)
				.setMaxWidth(contentWidth).setCentered(true));
		int linesHeight = 0;
		for (Choice.Line l : prompt.lines()) {
			MutableComponent text = Component.literal(l.text()).withStyle(s -> s.withColor(l.color()).withItalic(l.italic()));
			MultiLineTextWidget w = new MultiLineTextWidget(text, this.font).setMaxWidth(contentWidth).setCentered(true);
			linesHeight += w.getHeight() + 6;
			layout.addChild(w);
		}
		int n = prompt.options().size();
		int oneColumn = n * BUTTON_HEIGHT + Math.max(0, n - 1) * GAP;
		int fixed = this.font.lineHeight + 6 + linesHeight + 2 * BORDER + 2 * MARGIN;
		boolean twoColumns = n > 2 && fixed + oneColumn > this.height;
		int columns = twoColumns ? 2 : 1;
		int buttonWidth = twoColumns ? (contentWidth - GAP) / 2 : Math.min(contentWidth, 220);
		GridLayout grid = new GridLayout().columnSpacing(GAP).rowSpacing(GAP);
		GridLayout.RowHelper rows = grid.createRowHelper(columns);
		for (int i = 0; i < n; i++) {
			Choice.Option o = prompt.options().get(i);
			int index = i;
			MutableComponent label = Component.empty();
			if (n > 1 && i < 9) {
				label.append(Component.literal((i + 1) + "  ").withStyle(ChatFormatting.DARK_GRAY));
			}
			label.append(Component.literal(o.label()).withStyle(s -> s.withColor(o.color())));
			Button.Builder b = Button.builder(label, btn -> pick(index)).width(buttonWidth);
			if (!o.hint().isEmpty()) {
				b.tooltip(Tooltip.create(Component.literal(o.hint())));
			}
			Button button = b.build();
			button.active = !waiting;
			buttons.add(rows.addChild(button));
		}
		layout.addChild(grid, s -> s.paddingTop(4));
		layout.visitWidgets(this::addRenderableWidget);
		repositionElements();
	}

	@Override
	protected void repositionElements() {
		layout.arrangeElements();
		FrameLayout.centerInRectangle(layout, this.getRectangle());
	}

	@Override
	protected void setInitialFocus() {
		if (!buttons.isEmpty() && !waiting) {
			setInitialFocus(buttons.get(0));
		}
	}

	private void pick(int index) {
		if (waiting || index < 0 || index >= prompt.options().size()) {
			return;
		}
		waiting = true;
		buttons.forEach(b -> b.active = false);
		ClientPlayNetworking.send(new ChoicePayloads.Pick(session, prompt.options().get(index).id()));
	}

	@Override
	public boolean keyPressed(KeyEvent event) {
		int key = event.key();
		int index = key >= InputConstants.KEY_1 && key <= InputConstants.KEY_9 ? key - InputConstants.KEY_1
				: key >= InputConstants.KEY_NUMPAD1 && key <= InputConstants.KEY_NUMPAD9 ? key - InputConstants.KEY_NUMPAD1 : -1;
		if (index >= 0 && index < prompt.options().size()) {
			pick(index);
			return true;
		}
		return super.keyPressed(event);
	}

	@Override
	public void onClose() {
		ClientPlayNetworking.send(new ChoicePayloads.Pick(session, Choice.CLOSED));
		super.onClose();
	}

	@Override
	public void extractBackground(GuiGraphicsExtractor graphics, int mouseX, int mouseY, float a) {
		super.extractBackground(graphics, mouseX, mouseY, a);
		graphics.blitSprite(RenderPipelines.GUI_TEXTURED, BACKGROUND, layout.getX() - BORDER, layout.getY() - BORDER,
				layout.getWidth() + 2 * BORDER, layout.getHeight() + 2 * BORDER);
	}

	@Override
	public Component getNarrationMessage() {
		List<Component> parts = new ArrayList<>();
		parts.add(this.title);
		prompt.lines().forEach(l -> parts.add(Component.literal(l.text())));
		return CommonComponents.joinForNarration(parts.toArray(Component[]::new));
	}

	@Override
	public boolean isPauseScreen() {
		return false;
	}

	@Override
	public boolean isInGameUi() {
		return true;
	}
}
