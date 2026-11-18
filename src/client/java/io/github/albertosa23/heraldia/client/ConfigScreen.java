package io.github.albertosa23.heraldia.client;

import com.google.gson.JsonPrimitive;
import io.github.albertosa23.heraldia.config.ConfigOption;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.config.Profiles;
import java.io.IOException;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import net.fabricmc.api.EnvType;
import net.fabricmc.api.Environment;
import net.minecraft.ChatFormatting;
import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.client.gui.components.AbstractWidget;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.components.ContainerObjectSelectionList;
import net.minecraft.client.gui.components.CycleButton;
import net.minecraft.client.gui.components.EditBox;
import net.minecraft.client.gui.components.FocusableTextWidget;
import net.minecraft.client.gui.components.MultiLineTextWidget;
import net.minecraft.client.gui.components.StringWidget;
import net.minecraft.client.gui.components.events.GuiEventListener;
import net.minecraft.client.gui.components.toasts.SystemToast;
import net.minecraft.client.gui.layouts.HeaderAndFooterLayout;
import net.minecraft.client.gui.layouts.LinearLayout;
import net.minecraft.client.gui.narration.NarratableEntry;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.CommonComponents;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.util.FormattedCharSequence;
import org.jspecify.annotations.Nullable;

/**
 * Configuration screen (vanilla widgets, in the style of the game rules screen). It is built entirely from the .jar's
 * schema ({@link HeraldiaConfig#options()}): a new option in tools/gen/options.py shows up on its own, in its
 * section, with its range and its help. It edits this client's config/heraldia.json; it sends nothing to the server.
 * <p>Gameplay profile: when it changes, the profile options that had the previous profile's value take the new one's; the
 * ones that did not (set by hand) stay as they were, in gold, and override the profile. On save, the ones without the
 * profile's value are written as set by hand ({@link HeraldiaConfig#save(Path, Map)}).
 */
@Environment(EnvType.CLIENT)
public final class ConfigScreen extends Screen {
	private static final SystemToast.SystemToastId TOAST = new SystemToast.SystemToastId(8000L);
	private static final int VALID_COLOR = 0xFFE0E0E0;
	private static final int INVALID_COLOR = 0xFFFF5555;
	private static final int WIDGET_WIDTH = 44;
	private static final int FIXED_COLOR = 0xFFFFAA00;

	private final @Nullable Screen parent;
	private final Path file;
	private final HeaderAndFooterLayout layout;
	/** Valid values to be saved (a box with invalid text keeps the last valid one). */
	private final Map<String, JsonPrimitive> working;
	/** Text typed in each number box, kept while filtering even if it is not valid. */
	private final Map<String, String> typed = new HashMap<>();
	private final Set<String> invalid = new HashSet<>();
	private @Nullable OptionList list;
	private @Nullable EditBox search;
	private @Nullable Button saveButton;
	private @Nullable LinearLayout header;
	private final List<MultiLineTextWidget> notices = new ArrayList<>();

	public ConfigScreen(@Nullable Screen parent) {
		super(Component.translatable("heraldia.config.pantalla.titulo"));
		this.parent = parent;
		this.file = HeraldiaClient.configFile();
		this.working = new LinkedHashMap<>(HeraldiaConfig.readValues(file));
		this.layout = new HeaderAndFooterLayout(this, 0, 33);
	}

	@Override
	protected void init() {
		int textWidth = textWidth();
		LinearLayout header = this.layout.addToHeader(LinearLayout.vertical().spacing(4));
		this.header = header;
		header.defaultCellSetting().alignHorizontallyCenter();
		header.addChild(new StringWidget(this.title, this.font));
		header.addChild(notice(Component.translatable("heraldia.config.pantalla.aviso").withStyle(ChatFormatting.GRAY), textWidth));
		if (this.minecraft.getSingleplayerServer() != null) {
			header.addChild(notice(Component.translatable("heraldia.config.pantalla.aviso_mundo").withStyle(ChatFormatting.YELLOW), textWidth));
		} else if (this.minecraft.getConnection() != null) {
			header.addChild(notice(Component.translatable("heraldia.config.pantalla.aviso_servidor").withStyle(ChatFormatting.GOLD), textWidth));
		}
		this.search = header.addChild(new EditBox(this.font, 200, 15, Component.translatable("heraldia.config.pantalla.buscar")));
		this.search.setHint(Component.translatable("heraldia.config.pantalla.buscar").withStyle(EditBox.SEARCH_HINT_STYLE));
		this.search.setResponder(this::filter);
		fitHeader();

		this.list = this.layout.addToContents(new OptionList());
		LinearLayout footer = this.layout.addToFooter(LinearLayout.horizontal().spacing(8));
		this.saveButton = footer.addChild(Button.builder(Component.translatable("heraldia.config.pantalla.guardar"), b -> save()).width(100).build());
		footer.addChild(Button.builder(Component.translatable("heraldia.config.pantalla.restaurar"), b -> restoreDefaults()).width(100).build());
		footer.addChild(Button.builder(CommonComponents.GUI_CANCEL, b -> onClose()).width(100).build());
		this.layout.visitWidgets(this::addRenderableWidget);
		updateSaveButton();
		repositionElements();
	}

	private MultiLineTextWidget notice(Component text, int width) {
		MultiLineTextWidget w = new MultiLineTextWidget(text, this.font).setMaxWidth(width).setCentered(true);
		this.notices.add(w);
		return w;
	}

	private int textWidth() {
		return Math.min(360, this.width - 32);
	}

	private int rowWidth() {
		return Math.min(320, this.width - 40);
	}

	/** The header grows with the notices (more lines on narrow screens). */
	private void fitHeader() {
		if (this.header != null) {
			this.notices.forEach(n -> n.setMaxWidth(textWidth()));
			this.header.arrangeElements();
			this.layout.setHeaderHeight(this.header.getHeight() + 12);
		}
	}

	@Override
	protected void repositionElements() {
		fitHeader();
		this.layout.arrangeElements();
		if (this.list != null) {
			this.list.updateSize(this.width, this.layout);
		}
	}

	@Override
	protected void setInitialFocus() {
		if (this.search != null) {
			setInitialFocus(this.search);
		}
	}

	@Override
	public void onClose() {
		this.minecraft.gui.setScreen(this.parent);
	}

	private void filter(String text) {
		if (this.list != null) {
			this.list.populate(text);
			this.list.setScrollAmount(0.0);
			repositionElements();
		}
	}

	private void restoreDefaults() {
		this.working.clear();
		this.working.putAll(HeraldiaConfig.defaults());
		this.typed.clear();
		this.invalid.clear();
		filter(this.search == null ? "" : this.search.getValue());
		updateSaveButton();
	}

	private void save() {
		if (!this.invalid.isEmpty()) {
			return;
		}
		try {
			HeraldiaConfig.save(this.file, this.working);
		} catch (IOException | IllegalArgumentException e) {
			SystemToast.add(this.minecraft.gui.toastManager(), TOAST, this.title,
					Component.translatable("heraldia.config.pantalla.error", String.valueOf(e.getMessage())));
			return;
		}
		HeraldiaClient.applyIfIdle(this.minecraft);
		SystemToast.add(this.minecraft.gui.toastManager(), TOAST, Component.translatable("heraldia.config.pantalla.guardado"),
				Component.translatable("heraldia.config.pantalla.aviso"));
		onClose();
	}

	private void updateSaveButton() {
		if (this.saveButton != null) {
			this.saveButton.active = this.invalid.isEmpty();
		}
	}

	private String profile() {
		JsonPrimitive p = this.working.get(Profiles.KEY);
		return p != null ? p.getAsString() : Profiles.STANDARD;
	}

	/** Profile option with a value other than the chosen profile's? (it will be saved as set by hand) */
	private boolean fixedByHand(String key) {
		Map<String, JsonPrimitive> p = HeraldiaConfig.profiles().optionValues(profile());
		return p.containsKey(key) && !Profiles.CUSTOM.equals(profile()) && !p.get(key).equals(this.working.get(key));
	}

	/** Changes the profile: what had the previous profile's value takes the new one's; what was set by hand stays. */
	private void changeProfile(String profile) {
		Profiles ps = HeraldiaConfig.profiles();
		Map<String, JsonPrimitive> before = ps.optionValues(profile()), now = ps.optionValues(profile);
		for (String k : ps.keys()) {
			if (Profiles.CUSTOM.equals(profile()) || before.get(k).equals(this.working.get(k))) {
				this.working.put(k, Profiles.CUSTOM.equals(profile) ? this.working.get(k) : now.get(k));
				this.typed.remove(k);
				this.invalid.remove(k);
			}
		}
		this.working.put(Profiles.KEY, new JsonPrimitive(profile));
		filter(this.search == null ? "" : this.search.getValue());
		updateSaveButton();
	}

	/** Profile lines in an option's help: the value the profile gives and whether it is set by hand. */
	private List<FormattedCharSequence> profileLines(ConfigOption o) {
		List<FormattedCharSequence> out = new ArrayList<>();
		Profiles ps = HeraldiaConfig.profiles();
		if (o.key().equals(Profiles.KEY)) {
			List<String> distinct = ps.keys().stream().filter(this::fixedByHand).toList();
			Component effective = Component.translatable("heraldia.config.perfil." + (distinct.isEmpty() ? profile() : Profiles.CUSTOM));
			out.addAll(this.font.split(Component.translatable("heraldia.config.pantalla.perfil_efectivo", effective,
					distinct.isEmpty() ? "-" : String.join(", ", distinct)).withStyle(ChatFormatting.AQUA), 200));
		} else if (ps.keys().contains(o.key()) && !Profiles.CUSTOM.equals(profile())) {
			out.addAll(this.font.split(Component.translatable("heraldia.config.pantalla.perfil_valor",
					Component.translatable("heraldia.config.perfil." + profile()), ps.optionValues(profile()).get(o.key()).getAsString())
					.withStyle(ChatFormatting.AQUA), 200));
			if (fixedByHand(o.key())) {
				out.addAll(this.font.split(Component.translatable("heraldia.config.pantalla.fijada").withStyle(ChatFormatting.GOLD), 200));
			}
		}
		return out;
	}

	/** An option's name (with the family or structure name translated) and help, as translatable components. */
	private static Object[] args(ConfigOption o) {
		Object[] out = new Object[o.args().size()];
		for (int i = 0; i < out.length; i++) {
			String nameKey = i < o.argNames().size() ? o.argNames().get(i) : null;
			out[i] = nameKey != null ? Component.translatable(nameKey) : Component.literal(o.args().get(i));
		}
		return out;
	}

	private List<FormattedCharSequence> tooltip(ConfigOption o, MutableComponent help) {
		List<FormattedCharSequence> lines = new ArrayList<>();
		lines.add(Component.translatable("heraldia.config.pantalla.clave", o.key()).withStyle(ChatFormatting.YELLOW).getVisualOrderText());
		lines.addAll(this.font.split(help, 200));
		Component range = o.isChoice()
				? Component.translatable("heraldia.config.valores", Component.translatable(o.valueNames().get(o.values().indexOf(o.defaultValue().getAsString()))),
						Component.literal(String.join(", ", o.values())))
				: o.isBoolean()
				? Component.translatable("heraldia.config.si_no", o.defaultValue().getAsString())
				: Component.translatable("heraldia.config.rango", o.defaultValue().getAsString(), o.min(), o.max());
		lines.addAll(this.font.split(range.copy().withStyle(ChatFormatting.GRAY), 200));
		return List.copyOf(lines);
	}

	@Environment(EnvType.CLIENT)
	private final class OptionList extends ContainerObjectSelectionList<Row> {
		OptionList() {
			super(ConfigScreen.this.minecraft, ConfigScreen.this.width, ConfigScreen.this.layout.getContentHeight(),
					ConfigScreen.this.layout.getHeaderHeight(), 24);
			populate("");
		}

		void populate(String filter) {
			clearEntries();
			String f = filter.toLowerCase(Locale.ROOT).strip();
			Map<String, List<Row>> bySection = new LinkedHashMap<>();
			HeraldiaConfig.sections().keySet().forEach(s -> bySection.put(s, new ArrayList<>()));
			for (ConfigOption o : HeraldiaConfig.options()) {
				Object[] args = args(o);
				MutableComponent name = Component.translatable(o.name(), args);
				MutableComponent help = Component.translatable(o.help(), args);
				String sectionTitle = Component.translatable(HeraldiaConfig.sections().getOrDefault(o.section(), o.section())).getString();
				if (!f.isEmpty() && !(contains(o.key(), f) || contains(name.getString(), f) || contains(help.getString(), f)
						|| contains(sectionTitle, f))) {
					continue;
				}
				Row e = o.isChoice() ? new ChoiceEntry(o, name, tooltip(o, help))
						: o.isBoolean() ? new BooleanEntry(o, name, tooltip(o, help)) : new IntegerEntry(o, name, tooltip(o, help));
				bySection.computeIfAbsent(o.section(), k -> new ArrayList<>()).add(e);
			}
			bySection.forEach((section, entries) -> {
				if (!entries.isEmpty()) {
					String key = HeraldiaConfig.sections().getOrDefault(section, section);
					addEntry(new SectionEntry(Component.translatable(key).withStyle(ChatFormatting.BOLD, ChatFormatting.YELLOW, ChatFormatting.UNDERLINE)));
					entries.forEach(this::addEntry);
				}
			});
		}

		private static boolean contains(String text, String filter) {
			return text.toLowerCase(Locale.ROOT).contains(filter);
		}

		@Override
		public int getRowWidth() {
			return rowWidth();
		}

		@Override
		public void extractWidgetRenderState(GuiGraphicsExtractor graphics, int mouseX, int mouseY, float a) {
			super.extractWidgetRenderState(graphics, mouseX, mouseY, a);
			Row hovered = getHovered();
			if (hovered != null) {
				List<FormattedCharSequence> tip = hovered.tooltip();
				if (tip != null) {
					graphics.setTooltipForNextFrame(tip, mouseX, mouseY);
				}
			}
		}
	}

	@Environment(EnvType.CLIENT)
	private abstract static class Row extends ContainerObjectSelectionList.Entry<Row> {
		@Nullable List<FormattedCharSequence> tooltip() {
			return null;
		}
	}

	@Environment(EnvType.CLIENT)
	private final class SectionEntry extends Row {
		private final FocusableTextWidget widget;

		SectionEntry(Component label) {
			this.widget = FocusableTextWidget.builder(label, ConfigScreen.this.font)
					.alwaysShowBorder(false)
					.backgroundFill(FocusableTextWidget.BackgroundFill.ON_FOCUS)
					.build();
		}

		@Override
		public void extractContent(GuiGraphicsExtractor graphics, int mouseX, int mouseY, boolean hovered, float a) {
			this.widget.setPosition(getContentXMiddle() - this.widget.getWidth() / 2, getContentYMiddle() - this.widget.getHeight() / 2);
			this.widget.extractRenderState(graphics, mouseX, mouseY, a);
		}

		@Override
		public List<? extends GuiEventListener> children() {
			return List.of(this.widget);
		}

		@Override
		public List<? extends NarratableEntry> narratables() {
			return List.of(this.widget);
		}
	}

	@Environment(EnvType.CLIENT)
	private abstract class OptionEntry extends Row {
		protected final ConfigOption option;
		private final List<FormattedCharSequence> label;
		private final List<FormattedCharSequence> tooltip;

		OptionEntry(ConfigOption option, Component name, List<FormattedCharSequence> tooltip) {
			this.option = option;
			this.label = ConfigScreen.this.font.split(name, Math.max(60, rowWidth() - WIDGET_WIDTH - 8));
			this.tooltip = tooltip;
		}

		protected abstract AbstractWidget widget();

		@Override
		@Nullable List<FormattedCharSequence> tooltip() {
			List<FormattedCharSequence> extra = profileLines(this.option);
			if (extra.isEmpty()) {
				return this.tooltip;
			}
			List<FormattedCharSequence> out = new ArrayList<>(this.tooltip);
			out.addAll(extra);
			return out;
		}

		@Override
		public void extractContent(GuiGraphicsExtractor graphics, int mouseX, int mouseY, boolean hovered, float a) {
			int x = getContentX(), y = getContentY();
			int color = fixedByHand(this.option.key()) ? FIXED_COLOR : -1;
			if (this.label.size() == 1) {
				graphics.text(ConfigScreen.this.font, this.label.get(0), x, y + 5, color);
			} else if (this.label.size() >= 2) {
				graphics.text(ConfigScreen.this.font, this.label.get(0), x, y, color);
				graphics.text(ConfigScreen.this.font, this.label.get(1), x, y + 10, color);
			}
			AbstractWidget w = widget();
			w.setX(getContentRight() - WIDGET_WIDTH - 1);
			w.setY(y);
			w.extractRenderState(graphics, mouseX, mouseY, a);
		}

		@Override
		public List<? extends GuiEventListener> children() {
			return List.of(widget());
		}

		@Override
		public List<? extends NarratableEntry> narratables() {
			return List.of(widget());
		}
	}

	@Environment(EnvType.CLIENT)
	private final class BooleanEntry extends OptionEntry {
		private final CycleButton<Boolean> button;

		BooleanEntry(ConfigOption option, Component name, List<FormattedCharSequence> tooltip) {
			super(option, name, tooltip);
			this.button = CycleButton.onOffBuilder(ConfigScreen.this.working.get(option.key()).getAsBoolean())
					.displayOnlyValue()
					.create(0, 0, WIDGET_WIDTH, 20, name, (b, value) -> ConfigScreen.this.working.put(option.key(), new JsonPrimitive(value)));
		}

		@Override
		protected AbstractWidget widget() {
			return this.button;
		}
	}

	/** List option: a button that cycles through its values, each with its translated name. */
	@Environment(EnvType.CLIENT)
	private final class ChoiceEntry extends OptionEntry {
		private final CycleButton<String> button;

		ChoiceEntry(ConfigOption option, Component name, List<FormattedCharSequence> tooltip) {
			super(option, name, tooltip);
			this.button = CycleButton.<String>builder(v -> Component.translatable(option.valueNames().get(option.values().indexOf(v))),
							ConfigScreen.this.working.get(option.key()).getAsString())
					.withValues(option.values())
					.displayOnlyValue()
					.create(0, 0, WIDGET_WIDTH, 20, name, (b, value) -> {
						if (option.key().equals(Profiles.KEY)) {
							ConfigScreen.this.minecraft.schedule(() -> changeProfile(value)); // rebuild the list: after the click
						} else {
							ConfigScreen.this.working.put(option.key(), new JsonPrimitive(value));
						}
					});
		}

		@Override
		protected AbstractWidget widget() {
			return this.button;
		}
	}

	@Environment(EnvType.CLIENT)
	private final class IntegerEntry extends OptionEntry {
		private final EditBox input;
		private final List<FormattedCharSequence> invalidTooltip;

		IntegerEntry(ConfigOption option, Component name, List<FormattedCharSequence> tooltip) {
			super(option, name, tooltip);
			List<FormattedCharSequence> tip = new ArrayList<>(tooltip);
			tip.add(Component.translatable("heraldia.config.pantalla.invalido", option.min(), option.max())
					.withStyle(ChatFormatting.RED).getVisualOrderText());
			this.invalidTooltip = List.copyOf(tip);
			this.input = new EditBox(ConfigScreen.this.font, 0, 0, WIDGET_WIDTH, 20, name);
			this.input.setMaxLength(11);
			this.input.setValue(ConfigScreen.this.typed.getOrDefault(option.key(), ConfigScreen.this.working.get(option.key()).getAsString()));
			this.input.setTextColor(ConfigScreen.this.invalid.contains(option.key()) ? INVALID_COLOR : VALID_COLOR);
			this.input.setResponder(this::changed);
		}

		private void changed(String text) {
			String key = this.option.key();
			ConfigScreen.this.typed.put(key, text);
			var value = this.option.parse(text);
			if (value.isPresent()) {
				ConfigScreen.this.working.put(key, value.get());
				ConfigScreen.this.invalid.remove(key);
				this.input.setTextColor(VALID_COLOR);
			} else {
				ConfigScreen.this.invalid.add(key);
				this.input.setTextColor(INVALID_COLOR);
			}
			updateSaveButton();
		}

		@Override
		@Nullable List<FormattedCharSequence> tooltip() {
			return ConfigScreen.this.invalid.contains(this.option.key()) ? this.invalidTooltip : super.tooltip();
		}

		@Override
		protected AbstractWidget widget() {
			return this.input;
		}
	}
}
