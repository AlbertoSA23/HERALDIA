package io.github.albertosa23.heraldia.command;

import com.google.gson.JsonPrimitive;
import com.mojang.brigadier.arguments.StringArgumentType;
import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.serialization.JavaOps;
import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.config.ConfigOption;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.config.Menus;
import io.github.albertosa23.heraldia.config.Profiles;
import io.github.albertosa23.heraldia.config.Reload;
import java.io.IOException;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import net.minecraft.ChatFormatting;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.SharedSuggestionProvider;
import net.minecraft.core.Holder;
import net.minecraft.network.chat.ClickEvent;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.dialog.ActionButton;
import net.minecraft.server.dialog.CommonButtonData;
import net.minecraft.server.dialog.CommonDialogData;
import net.minecraft.server.dialog.Dialog;
import net.minecraft.server.dialog.DialogAction;
import net.minecraft.server.dialog.Input;
import net.minecraft.server.dialog.MultiActionDialog;
import net.minecraft.server.dialog.NoticeDialog;
import net.minecraft.server.dialog.action.CommandTemplate;
import net.minecraft.server.dialog.action.ParsedTemplate;
import net.minecraft.server.dialog.action.StaticAction;
import net.minecraft.server.dialog.body.DialogBody;
import net.minecraft.server.dialog.body.PlainMessage;
import net.minecraft.server.dialog.input.BooleanInput;
import net.minecraft.server.dialog.input.InputControl;
import net.minecraft.server.dialog.input.NumberRangeInput;
import net.minecraft.server.dialog.input.SingleOptionInput;
import net.minecraft.server.level.ServerPlayer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Panel de configuración en el juego para clientes sin el mod (T46): /heraldia config (operadores) abre un diálogo vanilla
 * (Dialog API del servidor) con el perfil de juego arriba y un botón por submenú ({@link Menus}). Cada submenú lleva sus
 * opciones con una frase que las explica, el valor recomendado y, si hace falta, el aviso de que se aplican al reiniciar;
 * «Guardar» escribe config/heraldia.json y aplica con el mismo camino que /heraldia reload ({@link ReloadCommand#apply});
 * lo que no es recargable ({@link Reload}) queda guardado y se avisa de que espera al reinicio. Lo técnico que no está en
 * los submenús se cambia en el fichero (o con /heraldia config set &lt;opción&gt; &lt;valor&gt;, también desde la consola).
 * <p>Los botones ejecutan subcomandos de /heraldia config (en inglés, en {@code command/HeraldiaCommands}): menu, profile, save y
 * set. Nada por tick: el diálogo se construye al pedirlo.
 */
public final class ConfigPanel {
	private static final Logger LOGGER = LoggerFactory.getLogger(Heraldia.MOD_ID);
	static final String CMD = "heraldia config";
	static final int WIDTH = 300;

	private ConfigPanel() {
	}

	static LiteralArgumentBuilder<CommandSourceStack> node() {
		return Commands.literal("config")
				.requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))
				.executes(c -> open(c.getSource(), null))
				.then(Commands.literal("menu").then(Commands.argument("menu", StringArgumentType.word())
						.suggests((c, b) -> SharedSuggestionProvider.suggest(Menus.MENUS.stream().map(Menus.Menu::id), b))
						.executes(c -> open(c.getSource(), StringArgumentType.getString(c, "menu")))))
				.then(Commands.literal("profile").then(Commands.argument("profile", StringArgumentType.word())
						.suggests((c, b) -> SharedSuggestionProvider.suggest(Menus.PROFILES, b))
						.executes(c -> profile(c, StringArgumentType.getString(c, "profile")))))
				.then(Commands.literal("save").then(Commands.argument("menu", StringArgumentType.word())
						.then(Commands.argument("values", StringArgumentType.greedyString())
								.executes(c -> saveMenu(c, StringArgumentType.getString(c, "menu"), StringArgumentType.getString(c, "values"))))))
				.then(Commands.literal("set").then(Commands.argument("option", StringArgumentType.string())
						.suggests((c, b) -> SharedSuggestionProvider.suggest(HeraldiaConfig.options().stream().map(ConfigOption::key), b))
						.then(Commands.argument("value", StringArgumentType.greedyString())
								.executes(c -> setLanguage(c, StringArgumentType.getString(c, "option"), StringArgumentType.getString(c, "value"))))));
	}

	// ------------------------------------------------------------------ comandos

	private static int open(CommandSourceStack src, String menu) {
		Map<String, ConfigOption> options = options();
		Map<String, JsonPrimitive> optionValues = HeraldiaConfig.readValues(ReloadCommand.file());
		ServerPlayer p = src.getPlayer();
		Map<String, String> l = p != null ? Texts.language(p) : Texts.language(Texts.ES);
		Optional<Menus.Menu> m = menu == null ? Optional.empty() : Menus.menu(menu);
		if (menu != null && m.isEmpty()) {
			src.sendFailure(Texts.t(l, "heraldia.panel.no_existe", menu));
			return 0;
		}
		if (p == null) {           // consola: el mismo contenido en texto
			text(l, m.orElse(null), options, optionValues).forEach(t -> src.sendSystemMessage(t));
			return 1;
		}
		Dialog d = m.isPresent() ? submenu(l, m.get(), options, optionValues, HeraldiaConfig.get().profile().chosen())
				: main(l, optionValues.get(Profiles.CLAVE).getAsString(), HeraldiaConfig.get().profile().effective());
		p.openDialog(Holder.direct(d));
		LOGGER.info("Heraldia: panel de configuración abierto ({}, {})", p.getGameProfile().name(), m.map(Menus.Menu::id).orElse("principal"));
		return 1;
	}

	private static int profile(CommandContext<CommandSourceStack> ctx, String profile) {
		if (!Menus.PROFILES.contains(profile)) {
			ctx.getSource().sendFailure(Texts.t("heraldia.panel.no_existe", profile));
			return 0;
		}
		return save(ctx.getSource(), Map.of(Profiles.CLAVE, new JsonPrimitive(profile)), List.of(), null);
	}

	private static int saveMenu(CommandContext<CommandSourceStack> ctx, String menu, String optionValues) {
		Optional<Menus.Menu> m = Menus.menu(menu);
		if (m.isEmpty()) {
			ctx.getSource().sendFailure(Texts.t("heraldia.panel.no_existe", menu));
			return 0;
		}
		Map<String, JsonPrimitive> current = HeraldiaConfig.readValues(ReloadCommand.file());
		Menus.Loaded r = Menus.read(m.get(), Arrays.asList(optionValues.strip().split("\\s+")), options(), current);
		Map<String, JsonPrimitive> changes = new LinkedHashMap<>();
		r.optionValues().forEach((k, v) -> {
			if (!v.equals(current.get(k))) {
				changes.put(k, v);
			}
		});
		return save(ctx.getSource(), changes, r.invalid(), m.get());
	}

	private static int setLanguage(CommandContext<CommandSourceStack> ctx, String optionKey, String text) {
		ConfigOption o = options().get(optionKey);
		Map<String, JsonPrimitive> current = HeraldiaConfig.readValues(ReloadCommand.file());
		Optional<JsonPrimitive> v = o == null ? Optional.empty() : Menus.read(o, text, null);
		if (v.isEmpty()) {
			ctx.getSource().sendFailure(Texts.t("heraldia.panel.invalida", optionKey, text));
			return 0;
		}
		return save(ctx.getSource(), v.get().equals(current.get(optionKey)) ? Map.of() : Map.of(optionKey, v.get()), List.of(), null);
	}

	/**
	 * Escribe los cambios en el fichero (con lo que ya tenía) y los aplica como /heraldia reload. Al jugador le enseña el
	 * resultado en un aviso con un botón para volver; a la consola, en texto.
	 */
	private static int save(CommandSourceStack src, Map<String, JsonPrimitive> changes, List<String> invalid, Menus.Menu back) {
		ServerPlayer p = src.getPlayer();
		Map<String, String> l = p != null ? Texts.language(p) : Texts.language(Texts.ES);
		List<Component> lines = new ArrayList<>();
		invalid.forEach(k -> lines.add(Texts.t(l, "heraldia.panel.invalida", k, "?").withStyle(ChatFormatting.RED)));
		if (changes.isEmpty()) {
			lines.add(Texts.t(l, "heraldia.panel.sin_cambios").withStyle(ChatFormatting.GRAY));
		} else {
			Path file = ReloadCommand.file();
			Map<String, JsonPrimitive> optionValues = new LinkedHashMap<>(HeraldiaConfig.readValues(file));
			optionValues.putAll(changes);
			try {
				HeraldiaConfig.save(file, optionValues);
			} catch (IOException | IllegalArgumentException e) {
				src.sendFailure(Texts.t(l, "heraldia.panel.error", e.getMessage()));
				return 0;
			}
			changes.forEach((k, v) -> lines.add(Texts.t(l, Reload.reloadable(k) ? "heraldia.panel.guardada" : "heraldia.panel.guardada_reinicio",
					name(l, k), v.getAsString()).withStyle(Reload.reloadable(k) ? ChatFormatting.GREEN : ChatFormatting.YELLOW)));
			lines.addAll(ReloadCommand.apply(src.getServer()));
			LOGGER.info("Heraldia: panel de configuración: {} guardadas por {}", changes.keySet(), src.getTextName());
		}
		if (p == null) {
			lines.forEach(t -> src.sendSuccess(() -> t, true));
			return 1;
		}
		p.openDialog(Holder.direct(notice(l, lines, back)));
		return 1;
	}

	// ------------------------------------------------------------------ diálogos

	/**
	 * Diálogo principal: el perfil en uso, un botón por perfil (en el orden de {@link Menus#PROFILES}) y uno por submenú
	 * (en el de {@link Menus#MENUS}). Los botones, en {@link #mainActions()}.
	 */
	public static MultiActionDialog main(Map<String, String> l, String chosen, String effective) {
		List<DialogBody> body = List.of(
				new PlainMessage(Texts.t(l, "heraldia.panel.perfil", nameValue(l, Profiles.CLAVE, effective)), WIDTH),
				new PlainMessage(Texts.t(l, "heraldia.panel.ayuda").withStyle(ChatFormatting.GRAY), WIDTH));
		List<ActionButton> buttons = new ArrayList<>();
		for (String profile : Menus.PROFILES) {
			MutableComponent t = nameValue(l, Profiles.CLAVE, profile).copy();
			if (profile.equals(chosen)) {
				t = Component.literal("✔ ").append(t).withStyle(ChatFormatting.GREEN);
			}
			buttons.add(button(t, Texts.t(l, "heraldia.panel.perfil." + profile), CMD + " profile " + profile, 96));
		}
		for (Menus.Menu m : Menus.MENUS) {
			buttons.add(button(Texts.t(l, "heraldia.panel.menu." + m.id()), Texts.t(l, "heraldia.panel.menu." + m.id() + ".ayuda"),
					CMD + " menu " + m.id(), 96));
		}
		CommonDialogData c = new CommonDialogData(Texts.t(l, "heraldia.panel.titulo"), Optional.empty(), true, false,
				DialogAction.CLOSE, body, List.of());
		return new MultiActionDialog(c, buttons, Optional.of(new ActionButton(new CommonButtonData(Texts.t(l, "heraldia.panel.cerrar"), 96),
				Optional.empty())), 3);
	}

	/** Lo que ejecuta cada botón del diálogo principal, en orden (para los tests). */
	public static List<String> mainActions() {
		List<String> out = new ArrayList<>();
		Menus.PROFILES.forEach(p -> out.add(CMD + " profile " + p));
		Menus.MENUS.forEach(m -> out.add(CMD + " menu " + m.id()));
		return out;
	}

	/**
	 * Un submenú: una línea por opción (nombre, frase, valor recomendado y aviso de reinicio), un control por opción con
	 * su valor actual (claves o0, o1...) y los botones Guardar (manda los valores, en el orden del menú, a
	 * /heraldia config save) y Volver.
	 */
	public static MultiActionDialog submenu(Map<String, String> l, Menus.Menu m, Map<String, ConfigOption> options,
											Map<String, JsonPrimitive> optionValues, String profile) {
		List<DialogBody> body = new ArrayList<>();
		List<Input> entries = new ArrayList<>();
		StringBuilder template = new StringBuilder(CMD + " save " + m.id());
		for (int i = 0; i < m.keys().size(); i++) {
			String k = m.keys().get(i);
			ConfigOption o = options.get(k);
			JsonPrimitive v = optionValues.getOrDefault(k, o.defaultValue());
			MutableComponent line = Texts.t(l, "heraldia.panel.opcion", name(l, k), Texts.t(l, o.help(), o.args().toArray()),
					readableValue(l, o, recommended(o, profile)));
			if (!Reload.reloadable(k)) {
				line.append(" ").append(Texts.t(l, "heraldia.panel.reinicio").withStyle(ChatFormatting.GOLD));
			}
			body.add(new PlainMessage(line, WIDTH));
			String optionKey = "o" + i;
			entries.add(new Input(optionKey, control(l, o, v)));
			template.append(" $(").append(optionKey).append(")");
		}
		ParsedTemplate t = ParsedTemplate.CODEC.parse(JavaOps.INSTANCE, template.toString()).getOrThrow();
		List<ActionButton> buttons = List.of(
				new ActionButton(new CommonButtonData(Texts.t(l, "heraldia.panel.guardar"), Optional.of(Texts.t(l, "heraldia.panel.guardar.ayuda")), 140),
						Optional.of(new CommandTemplate(t))),
				button(Texts.t(l, "heraldia.panel.volver"), Texts.t(l, "heraldia.panel.volver.ayuda"), CMD, 140));
		CommonDialogData c = new CommonDialogData(Texts.t(l, "heraldia.panel.menu." + m.id()), Optional.empty(), true, false,
				DialogAction.CLOSE, body, entries);
		return new MultiActionDialog(c, buttons, Optional.of(button(Texts.t(l, "heraldia.panel.volver"), null, CMD, 140)), 2);
	}

	/** El resultado de guardar, con un botón para volver al submenú (o al principal). */
	static NoticeDialog notice(Map<String, String> l, List<Component> lines, Menus.Menu back) {
		List<DialogBody> body = new ArrayList<>();
		lines.forEach(t -> body.add(new PlainMessage(t, WIDTH)));
		CommonDialogData c = new CommonDialogData(Texts.t(l, "heraldia.panel.resultado"), Optional.empty(), true, false,
				DialogAction.CLOSE, body, List.of());
		return new NoticeDialog(c, button(Texts.t(l, "heraldia.panel.volver"), null, back == null ? CMD : CMD + " menu " + back.id(), 140));
	}

	/** El control de una opción con su valor actual: casilla, lista o deslizador (con el paso de {@link Menus#step}). */
	static InputControl control(Map<String, String> l, ConfigOption o, JsonPrimitive v) {
		Component tag = name(l, o.key());
		if (o.isBoolean()) {
			return new BooleanInput(tag, v.getAsBoolean(), "true", "false");
		}
		if (o.isChoice()) {
			List<SingleOptionInput.Entry> e = new ArrayList<>();
			for (int i = 0; i < o.values().size(); i++) {
				String id = o.values().get(i);
				e.add(new SingleOptionInput.Entry(id, Optional.of(Texts.t(l, o.valueNames().get(i))), id.equals(v.getAsString())));
			}
			return new SingleOptionInput(WIDTH - 100, e, tag, true);
		}
		return new NumberRangeInput(WIDTH - 100, tag, "options.generic_value",
				new NumberRangeInput.RangeInfo(o.min(), o.max(), Optional.of((float) Menus.adjust(o, v.getAsDouble())),
						Optional.of((float) Menus.step(o))));
	}

	/** El valor recomendado: el del perfil elegido para las opciones del perfil; el de por defecto para las demás. */
	static JsonPrimitive recommended(ConfigOption o, String profile) {
		Profiles ps = HeraldiaConfig.profiles();
		if (ps.keys().contains(o.key())) {
			JsonPrimitive v = ps.optionValues(Menus.PROFILES.contains(profile) ? profile : Profiles.STANDARD).get(o.key());
			if (v != null) {
				return v;
			}
		}
		return o.defaultValue();
	}

	/** Texto de un valor para leerlo: sí/no, el nombre de un valor de lista o el número. */
	static Component readableValue(Map<String, String> l, ConfigOption o, JsonPrimitive v) {
		if (o.isBoolean()) {
			return Texts.t(l, v.getAsBoolean() ? "heraldia.panel.si" : "heraldia.panel.no");
		}
		if (o.isChoice()) {
			int i = o.values().indexOf(v.getAsString());
			return i >= 0 ? Texts.t(l, o.valueNames().get(i)) : Component.literal(v.getAsString());
		}
		return Component.literal(v.getAsString());
	}

	/** Lo mismo que los diálogos, en líneas de texto (consola). */
	static List<Component> text(Map<String, String> l, Menus.Menu m, Map<String, ConfigOption> options, Map<String, JsonPrimitive> optionValues) {
		List<Component> out = new ArrayList<>();
		out.add(Texts.t(l, "heraldia.panel.titulo").withStyle(ChatFormatting.GOLD));
		out.add(Texts.t(l, "heraldia.panel.perfil", nameValue(l, Profiles.CLAVE, HeraldiaConfig.get().profile().effective())));
		for (Menus.Menu menu : m == null ? Menus.MENUS : List.of(m)) {
			out.add(Texts.t(l, "heraldia.panel.menu." + menu.id()).withStyle(ChatFormatting.YELLOW));
			for (String k : menu.keys()) {
				ConfigOption o = options.get(k);
				out.add(Component.literal(" - " + k + " = ").append(readableValue(l, o, optionValues.getOrDefault(k, o.defaultValue())))
						.append(Reload.reloadable(k) ? Component.empty() : Component.literal(" ").append(Texts.t(l, "heraldia.panel.reinicio"))));
			}
		}
		out.add(Texts.t(l, "heraldia.panel.consola").withStyle(ChatFormatting.GRAY));
		return out;
	}

	private static Map<String, ConfigOption> options() {
		Map<String, ConfigOption> m = new LinkedHashMap<>();
		HeraldiaConfig.options().forEach(o -> m.put(o.key(), o));
		return m;
	}

	private static Component name(Map<String, String> l, String optionKey) {
		ConfigOption o = options().get(optionKey);
		return o == null ? Component.literal(optionKey) : Texts.t(l, o.name(), o.args().toArray());
	}

	private static Component nameValue(Map<String, String> l, String optionKey, String value) {
		return Texts.t(l, "heraldia.config." + optionKey + "." + value);
	}

	private static ActionButton button(Component text, Component help, String cmd, int width) {
		return new ActionButton(new CommonButtonData(text, Optional.ofNullable(help), width),
				Optional.of(new StaticAction(new ClickEvent.RunCommand(cmd))));
	}
}
