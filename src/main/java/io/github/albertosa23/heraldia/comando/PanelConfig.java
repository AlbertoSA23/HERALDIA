package io.github.albertosa23.heraldia.comando;

import com.google.gson.JsonPrimitive;
import com.mojang.brigadier.arguments.StringArgumentType;
import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.serialization.JavaOps;
import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.config.ConfigOption;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.config.Menus;
import io.github.albertosa23.heraldia.config.Perfiles;
import io.github.albertosa23.heraldia.config.Recarga;
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
 * «Guardar» escribe config/heraldia.json y aplica con el mismo camino que /heraldia reload ({@link RecargarCommand#aplicar});
 * lo que no es recargable ({@link Recarga}) queda guardado y se avisa de que espera al reinicio. Lo técnico que no está en
 * los submenús se cambia en el fichero (o con /heraldia config set &lt;opción&gt; &lt;valor&gt;, también desde la consola).
 * <p>Los botones ejecutan subcomandos de /heraldia config (en inglés, en {@code comando/Comandos}): menu, profile, save y
 * set. Nada por tick: el diálogo se construye al pedirlo.
 */
public final class PanelConfig {
	private static final Logger LOGGER = LoggerFactory.getLogger(Heraldia.MOD_ID);
	static final String CMD = "heraldia config";
	static final int ANCHO = 300;

	private PanelConfig() {
	}

	static LiteralArgumentBuilder<CommandSourceStack> nodo() {
		return Commands.literal("config")
				.requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))
				.executes(c -> abrir(c.getSource(), null))
				.then(Commands.literal("menu").then(Commands.argument("menu", StringArgumentType.word())
						.suggests((c, b) -> SharedSuggestionProvider.suggest(Menus.MENUS.stream().map(Menus.Menu::id), b))
						.executes(c -> abrir(c.getSource(), StringArgumentType.getString(c, "menu")))))
				.then(Commands.literal("profile").then(Commands.argument("profile", StringArgumentType.word())
						.suggests((c, b) -> SharedSuggestionProvider.suggest(Menus.PERFILES, b))
						.executes(c -> perfil(c, StringArgumentType.getString(c, "profile")))))
				.then(Commands.literal("save").then(Commands.argument("menu", StringArgumentType.word())
						.then(Commands.argument("values", StringArgumentType.greedyString())
								.executes(c -> guardarMenu(c, StringArgumentType.getString(c, "menu"), StringArgumentType.getString(c, "values"))))))
				.then(Commands.literal("set").then(Commands.argument("option", StringArgumentType.string())
						.suggests((c, b) -> SharedSuggestionProvider.suggest(HeraldiaConfig.options().stream().map(ConfigOption::key), b))
						.then(Commands.argument("value", StringArgumentType.greedyString())
								.executes(c -> fijar(c, StringArgumentType.getString(c, "option"), StringArgumentType.getString(c, "value"))))));
	}

	// ------------------------------------------------------------------ comandos

	private static int abrir(CommandSourceStack src, String menu) {
		Map<String, ConfigOption> opciones = opciones();
		Map<String, JsonPrimitive> valores = HeraldiaConfig.readValues(RecargarCommand.fichero());
		ServerPlayer p = src.getPlayer();
		Map<String, String> l = p != null ? Textos.idioma(p) : Textos.idioma(Textos.ES);
		Optional<Menus.Menu> m = menu == null ? Optional.empty() : Menus.menu(menu);
		if (menu != null && m.isEmpty()) {
			src.sendFailure(Textos.t(l, "heraldia.panel.no_existe", menu));
			return 0;
		}
		if (p == null) {           // consola: el mismo contenido en texto
			texto(l, m.orElse(null), opciones, valores).forEach(t -> src.sendSystemMessage(t));
			return 1;
		}
		Dialog d = m.isPresent() ? submenu(l, m.get(), opciones, valores, HeraldiaConfig.get().profile().elegido())
				: principal(l, valores.get(Perfiles.CLAVE).getAsString(), HeraldiaConfig.get().profile().efectivo());
		p.openDialog(Holder.direct(d));
		LOGGER.info("Heraldia: panel de configuración abierto ({}, {})", p.getGameProfile().name(), m.map(Menus.Menu::id).orElse("principal"));
		return 1;
	}

	private static int perfil(CommandContext<CommandSourceStack> ctx, String perfil) {
		if (!Menus.PERFILES.contains(perfil)) {
			ctx.getSource().sendFailure(Textos.t("heraldia.panel.no_existe", perfil));
			return 0;
		}
		return guardar(ctx.getSource(), Map.of(Perfiles.CLAVE, new JsonPrimitive(perfil)), List.of(), null);
	}

	private static int guardarMenu(CommandContext<CommandSourceStack> ctx, String menu, String valores) {
		Optional<Menus.Menu> m = Menus.menu(menu);
		if (m.isEmpty()) {
			ctx.getSource().sendFailure(Textos.t("heraldia.panel.no_existe", menu));
			return 0;
		}
		Map<String, JsonPrimitive> actuales = HeraldiaConfig.readValues(RecargarCommand.fichero());
		Menus.Leidos r = Menus.leer(m.get(), Arrays.asList(valores.strip().split("\\s+")), opciones(), actuales);
		Map<String, JsonPrimitive> cambios = new LinkedHashMap<>();
		r.valores().forEach((k, v) -> {
			if (!v.equals(actuales.get(k))) {
				cambios.put(k, v);
			}
		});
		return guardar(ctx.getSource(), cambios, r.invalidas(), m.get());
	}

	private static int fijar(CommandContext<CommandSourceStack> ctx, String clave, String texto) {
		ConfigOption o = opciones().get(clave);
		Map<String, JsonPrimitive> actuales = HeraldiaConfig.readValues(RecargarCommand.fichero());
		Optional<JsonPrimitive> v = o == null ? Optional.empty() : Menus.leer(o, texto, null);
		if (v.isEmpty()) {
			ctx.getSource().sendFailure(Textos.t("heraldia.panel.invalida", clave, texto));
			return 0;
		}
		return guardar(ctx.getSource(), v.get().equals(actuales.get(clave)) ? Map.of() : Map.of(clave, v.get()), List.of(), null);
	}

	/**
	 * Escribe los cambios en el fichero (con lo que ya tenía) y los aplica como /heraldia reload. Al jugador le enseña el
	 * resultado en un aviso con un botón para volver; a la consola, en texto.
	 */
	private static int guardar(CommandSourceStack src, Map<String, JsonPrimitive> cambios, List<String> invalidas, Menus.Menu volver) {
		ServerPlayer p = src.getPlayer();
		Map<String, String> l = p != null ? Textos.idioma(p) : Textos.idioma(Textos.ES);
		List<Component> lineas = new ArrayList<>();
		invalidas.forEach(k -> lineas.add(Textos.t(l, "heraldia.panel.invalida", k, "?").withStyle(ChatFormatting.RED)));
		if (cambios.isEmpty()) {
			lineas.add(Textos.t(l, "heraldia.panel.sin_cambios").withStyle(ChatFormatting.GRAY));
		} else {
			Path file = RecargarCommand.fichero();
			Map<String, JsonPrimitive> valores = new LinkedHashMap<>(HeraldiaConfig.readValues(file));
			valores.putAll(cambios);
			try {
				HeraldiaConfig.save(file, valores);
			} catch (IOException | IllegalArgumentException e) {
				src.sendFailure(Textos.t(l, "heraldia.panel.error", e.getMessage()));
				return 0;
			}
			cambios.forEach((k, v) -> lineas.add(Textos.t(l, Recarga.recargable(k) ? "heraldia.panel.guardada" : "heraldia.panel.guardada_reinicio",
					nombre(l, k), v.getAsString()).withStyle(Recarga.recargable(k) ? ChatFormatting.GREEN : ChatFormatting.YELLOW)));
			lineas.addAll(RecargarCommand.aplicar(src.getServer()));
			LOGGER.info("Heraldia: panel de configuración: {} guardadas por {}", cambios.keySet(), src.getTextName());
		}
		if (p == null) {
			lineas.forEach(t -> src.sendSuccess(() -> t, true));
			return 1;
		}
		p.openDialog(Holder.direct(aviso(l, lineas, volver)));
		return 1;
	}

	// ------------------------------------------------------------------ diálogos

	/**
	 * Diálogo principal: el perfil en uso, un botón por perfil (en el orden de {@link Menus#PERFILES}) y uno por submenú
	 * (en el de {@link Menus#MENUS}). Los botones, en {@link #accionesPrincipal()}.
	 */
	public static MultiActionDialog principal(Map<String, String> l, String elegido, String efectivo) {
		List<DialogBody> cuerpo = List.of(
				new PlainMessage(Textos.t(l, "heraldia.panel.perfil", nombreValor(l, Perfiles.CLAVE, efectivo)), ANCHO),
				new PlainMessage(Textos.t(l, "heraldia.panel.ayuda").withStyle(ChatFormatting.GRAY), ANCHO));
		List<ActionButton> botones = new ArrayList<>();
		for (String perfil : Menus.PERFILES) {
			MutableComponent t = nombreValor(l, Perfiles.CLAVE, perfil).copy();
			if (perfil.equals(elegido)) {
				t = Component.literal("✔ ").append(t).withStyle(ChatFormatting.GREEN);
			}
			botones.add(boton(t, Textos.t(l, "heraldia.panel.perfil." + perfil), CMD + " profile " + perfil, 96));
		}
		for (Menus.Menu m : Menus.MENUS) {
			botones.add(boton(Textos.t(l, "heraldia.panel.menu." + m.id()), Textos.t(l, "heraldia.panel.menu." + m.id() + ".ayuda"),
					CMD + " menu " + m.id(), 96));
		}
		CommonDialogData c = new CommonDialogData(Textos.t(l, "heraldia.panel.titulo"), Optional.empty(), true, false,
				DialogAction.CLOSE, cuerpo, List.of());
		return new MultiActionDialog(c, botones, Optional.of(new ActionButton(new CommonButtonData(Textos.t(l, "heraldia.panel.cerrar"), 96),
				Optional.empty())), 3);
	}

	/** Lo que ejecuta cada botón del diálogo principal, en orden (para los tests). */
	public static List<String> accionesPrincipal() {
		List<String> out = new ArrayList<>();
		Menus.PERFILES.forEach(p -> out.add(CMD + " profile " + p));
		Menus.MENUS.forEach(m -> out.add(CMD + " menu " + m.id()));
		return out;
	}

	/**
	 * Un submenú: una línea por opción (nombre, frase, valor recomendado y aviso de reinicio), un control por opción con
	 * su valor actual (claves o0, o1...) y los botones Guardar (manda los valores, en el orden del menú, a
	 * /heraldia config save) y Volver.
	 */
	public static MultiActionDialog submenu(Map<String, String> l, Menus.Menu m, Map<String, ConfigOption> opciones,
											Map<String, JsonPrimitive> valores, String perfil) {
		List<DialogBody> cuerpo = new ArrayList<>();
		List<Input> entradas = new ArrayList<>();
		StringBuilder plantilla = new StringBuilder(CMD + " save " + m.id());
		for (int i = 0; i < m.claves().size(); i++) {
			String k = m.claves().get(i);
			ConfigOption o = opciones.get(k);
			JsonPrimitive v = valores.getOrDefault(k, o.defaultValue());
			MutableComponent linea = Textos.t(l, "heraldia.panel.opcion", nombre(l, k), Textos.t(l, o.help(), o.args().toArray()),
					valorLegible(l, o, recomendado(o, perfil)));
			if (!Recarga.recargable(k)) {
				linea.append(" ").append(Textos.t(l, "heraldia.panel.reinicio").withStyle(ChatFormatting.GOLD));
			}
			cuerpo.add(new PlainMessage(linea, ANCHO));
			String clave = "o" + i;
			entradas.add(new Input(clave, control(l, o, v)));
			plantilla.append(" $(").append(clave).append(")");
		}
		ParsedTemplate t = ParsedTemplate.CODEC.parse(JavaOps.INSTANCE, plantilla.toString()).getOrThrow();
		List<ActionButton> botones = List.of(
				new ActionButton(new CommonButtonData(Textos.t(l, "heraldia.panel.guardar"), Optional.of(Textos.t(l, "heraldia.panel.guardar.ayuda")), 140),
						Optional.of(new CommandTemplate(t))),
				boton(Textos.t(l, "heraldia.panel.volver"), Textos.t(l, "heraldia.panel.volver.ayuda"), CMD, 140));
		CommonDialogData c = new CommonDialogData(Textos.t(l, "heraldia.panel.menu." + m.id()), Optional.empty(), true, false,
				DialogAction.CLOSE, cuerpo, entradas);
		return new MultiActionDialog(c, botones, Optional.of(boton(Textos.t(l, "heraldia.panel.volver"), null, CMD, 140)), 2);
	}

	/** El resultado de guardar, con un botón para volver al submenú (o al principal). */
	static NoticeDialog aviso(Map<String, String> l, List<Component> lineas, Menus.Menu volver) {
		List<DialogBody> cuerpo = new ArrayList<>();
		lineas.forEach(t -> cuerpo.add(new PlainMessage(t, ANCHO)));
		CommonDialogData c = new CommonDialogData(Textos.t(l, "heraldia.panel.resultado"), Optional.empty(), true, false,
				DialogAction.CLOSE, cuerpo, List.of());
		return new NoticeDialog(c, boton(Textos.t(l, "heraldia.panel.volver"), null, volver == null ? CMD : CMD + " menu " + volver.id(), 140));
	}

	/** El control de una opción con su valor actual: casilla, lista o deslizador (con el paso de {@link Menus#paso}). */
	static InputControl control(Map<String, String> l, ConfigOption o, JsonPrimitive v) {
		Component etiqueta = nombre(l, o.key());
		if (o.isBoolean()) {
			return new BooleanInput(etiqueta, v.getAsBoolean(), "true", "false");
		}
		if (o.isChoice()) {
			List<SingleOptionInput.Entry> e = new ArrayList<>();
			for (int i = 0; i < o.values().size(); i++) {
				String id = o.values().get(i);
				e.add(new SingleOptionInput.Entry(id, Optional.of(Textos.t(l, o.valueNames().get(i))), id.equals(v.getAsString())));
			}
			return new SingleOptionInput(ANCHO - 100, e, etiqueta, true);
		}
		return new NumberRangeInput(ANCHO - 100, etiqueta, "options.generic_value",
				new NumberRangeInput.RangeInfo(o.min(), o.max(), Optional.of((float) Menus.ajustar(o, v.getAsDouble())),
						Optional.of((float) Menus.paso(o))));
	}

	/** El valor recomendado: el del perfil elegido para las opciones del perfil; el de por defecto para las demás. */
	static JsonPrimitive recomendado(ConfigOption o, String perfil) {
		Perfiles ps = HeraldiaConfig.profiles();
		if (ps.claves().contains(o.key())) {
			JsonPrimitive v = ps.valores(Menus.PERFILES.contains(perfil) ? perfil : Perfiles.ESTANDAR).get(o.key());
			if (v != null) {
				return v;
			}
		}
		return o.defaultValue();
	}

	/** Texto de un valor para leerlo: sí/no, el nombre de un valor de lista o el número. */
	static Component valorLegible(Map<String, String> l, ConfigOption o, JsonPrimitive v) {
		if (o.isBoolean()) {
			return Textos.t(l, v.getAsBoolean() ? "heraldia.panel.si" : "heraldia.panel.no");
		}
		if (o.isChoice()) {
			int i = o.values().indexOf(v.getAsString());
			return i >= 0 ? Textos.t(l, o.valueNames().get(i)) : Component.literal(v.getAsString());
		}
		return Component.literal(v.getAsString());
	}

	/** Lo mismo que los diálogos, en líneas de texto (consola). */
	static List<Component> texto(Map<String, String> l, Menus.Menu m, Map<String, ConfigOption> opciones, Map<String, JsonPrimitive> valores) {
		List<Component> out = new ArrayList<>();
		out.add(Textos.t(l, "heraldia.panel.titulo").withStyle(ChatFormatting.GOLD));
		out.add(Textos.t(l, "heraldia.panel.perfil", nombreValor(l, Perfiles.CLAVE, HeraldiaConfig.get().profile().efectivo())));
		for (Menus.Menu menu : m == null ? Menus.MENUS : List.of(m)) {
			out.add(Textos.t(l, "heraldia.panel.menu." + menu.id()).withStyle(ChatFormatting.YELLOW));
			for (String k : menu.claves()) {
				ConfigOption o = opciones.get(k);
				out.add(Component.literal(" - " + k + " = ").append(valorLegible(l, o, valores.getOrDefault(k, o.defaultValue())))
						.append(Recarga.recargable(k) ? Component.empty() : Component.literal(" ").append(Textos.t(l, "heraldia.panel.reinicio"))));
			}
		}
		out.add(Textos.t(l, "heraldia.panel.consola").withStyle(ChatFormatting.GRAY));
		return out;
	}

	private static Map<String, ConfigOption> opciones() {
		Map<String, ConfigOption> m = new LinkedHashMap<>();
		HeraldiaConfig.options().forEach(o -> m.put(o.key(), o));
		return m;
	}

	private static Component nombre(Map<String, String> l, String clave) {
		ConfigOption o = opciones().get(clave);
		return o == null ? Component.literal(clave) : Textos.t(l, o.name(), o.args().toArray());
	}

	private static Component nombreValor(Map<String, String> l, String clave, String valor) {
		return Textos.t(l, "heraldia.config." + clave + "." + valor);
	}

	private static ActionButton boton(Component texto, Component ayuda, String cmd, int ancho) {
		return new ActionButton(new CommonButtonData(texto, Optional.ofNullable(ayuda), ancho),
				Optional.of(new StaticAction(new ClickEvent.RunCommand(cmd))));
	}
}
