package io.github.albertosa23.heraldia.comando;

import com.google.gson.JsonElement;
import com.google.gson.JsonParser;
import com.mojang.brigadier.arguments.IntegerArgumentType;
import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.arena.Arena;
import io.github.albertosa23.heraldia.caminos.Caminos;
import io.github.albertosa23.heraldia.comun.Medianas;
import io.github.albertosa23.heraldia.config.ConfigOption;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.loot.WithoutLootrCondition;
import io.github.albertosa23.heraldia.minas.Minas;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import java.util.TreeSet;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.function.Function;
import java.util.stream.Stream;
import net.fabricmc.loader.api.FabricLoader;
import net.fabricmc.loader.api.ModContainer;
import net.minecraft.ChatFormatting;
import net.minecraft.advancements.AdvancementHolder;
import net.minecraft.advancements.AdvancementProgress;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.chat.ClickEvent;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.ComponentUtils;
import net.minecraft.network.chat.HoverEvent;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.util.Util;
import net.minecraft.world.level.storage.LevelResource;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * /heraldia status [page] (cualquier jugador; los operadores ven más): versión, estructuras de Heraldia descubiertas
 * por algún jugador frente al total por tipo, guardianes vencidos, récord de la arena, reposición del botín, Lootr y,
 * para los operadores, las opciones clave, lo que falta por descubrir y los otros mods cargados.
 * <p>Los logros de los jugadores conectados se leen de memoria (en el hilo del servidor); los de los demás, de sus
 * ficheros en la carpeta del mundo, fuera del hilo del servidor ({@link Estado.Logros#sumarFichero}).
 */
public final class EstadoCommand {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");

	private EstadoCommand() {
	}

	static LiteralArgumentBuilder<CommandSourceStack> nodo() {
		return Commands.literal("status")
				.executes(ctx -> mostrar(ctx.getSource(), 1))
				.then(Commands.argument("page", IntegerArgumentType.integer(1, 99))
						.executes(ctx -> mostrar(ctx.getSource(), IntegerArgumentType.getInteger(ctx, "page"))));
	}

	/** Lo que se cuenta, por clase de estructura: ids en orden y el logro (o criterio) que dice si alguien la descubrió. */
	private record Tipos(List<String> familias, List<String> unicas, List<String> medianas, List<String> minas, List<String> guardianes) {
	}

	private static int mostrar(CommandSourceStack src, int pagina) {
		MinecraftServer server = src.getServer();
		boolean op = Commands.hasPermission(Commands.LEVEL_GAMEMASTERS).test(src);
		Tipos tipos = tipos(server);
		// en el hilo del servidor: los conectados (sus ficheros pueden estar atrasados)
		Estado.Logros logros = new Estado.Logros();
		Set<UUID> conectados = new HashSet<>();
		List<AdvancementHolder> propios = server.getAdvancements().getAllAdvancements().stream()
				.filter(a -> Heraldia.MOD_ID.equals(a.id().getNamespace())).toList();
		for (ServerPlayer p : server.getPlayerList().getPlayers()) {
			conectados.add(p.getUUID());
			logros.jugador();
			for (AdvancementHolder a : propios) {
				AdvancementProgress pr = p.getAdvancements().getOrStartProgress(a);
				if (pr.hasProgress()) {
					logros.sumar(a.id().toString(), pr.isDone(), pr.getCompletedCriteria());
				}
			}
		}
		Path dir = server.getWorldPath(LevelResource.PLAYER_ADVANCEMENTS_DIR);
		CompletableFuture.runAsync(() -> leerFicheros(dir, conectados, logros), Util.ioPool())
				.thenRunAsync(() -> enviar(src, server, op, tipos, logros, pagina), server)
				.exceptionally(e -> {
					LOGGER.error("Heraldia: /heraldia status falló", e);
					src.sendFailure(Component.literal(String.valueOf(e.getMessage())));
					return null;
				});
		return 1;
	}

	/** Fuera del hilo del servidor: los ficheros de logros de los jugadores no conectados. */
	public static void leerFicheros(Path dir, Set<UUID> conectados, Estado.Logros logros) {
		if (!Files.isDirectory(dir)) {
			return;
		}
		try (Stream<Path> files = Files.list(dir)) {
			for (Path f : files.filter(x -> x.getFileName().toString().endsWith(".json")).toList()) {
				String n = f.getFileName().toString();
				try {
					if (conectados.contains(UUID.fromString(n.substring(0, n.length() - ".json".length())))) {
						continue;
					}
					JsonElement e = JsonParser.parseString(Files.readString(f, StandardCharsets.UTF_8));
					if (e.isJsonObject()) {
						logros.sumarFichero(e.getAsJsonObject());
					}
				} catch (IOException | RuntimeException ignored) {
					// fichero ajeno o roto: no cuenta
				}
			}
		} catch (IOException e) {
			LOGGER.warn("Heraldia: /heraldia status: no se pudo leer {} ({})", dir, e.getMessage());
		}
	}

	private static Tipos tipos(MinecraftServer server) {
		Set<String> familias = new LinkedHashSet<>(), unicas = new TreeSet<>(), medianas = new TreeSet<>(), minas = new LinkedHashSet<>();
		var estilos = RevisarCommand.estiloFamilia(HeraldiaConfig.get());
		Set<String> ids = new TreeSet<>();
		server.registryAccess().lookupOrThrow(Registries.STRUCTURE).keySet().stream()
				.filter(id -> Heraldia.MOD_ID.equals(id.getNamespace())).forEach(id -> ids.add(id.getPath()));
		estilos.forEach((estilo, fam) -> {
			if (ids.contains(estilo) || ids.contains(estilo + "_grande")) {
				familias.add(fam);
			}
		});
		for (String p : ids) {
			String[] s = p.split("/");
			if (s[0].equals("unicas") && s.length >= 2) {
				unicas.add(s[1]);
			} else if (Medianas.esMediana(Heraldia.id(p)) && s.length >= 2) {
				medianas.add(s[1]);
			}
		}
		for (String t : Revision.TAMANOS) {
			if (ids.stream().anyMatch(p -> Minas.esMina(Heraldia.id(p)) && p.startsWith(Minas.PREFIJO + t + "/"))) {
				minas.add(t);
			}
		}
		List<String> guardianes = unicas.stream()
				.filter(u -> server.getAdvancements().get(Heraldia.id("unicas/" + u + "/guardian")) != null).toList();
		return new Tipos(List.copyOf(familias), List.copyOf(unicas), List.copyOf(medianas), List.copyOf(minas), guardianes);
	}

	private static void enviar(CommandSourceStack src, MinecraftServer server, boolean op, Tipos t, Estado.Logros l, int pagina) {
		HeraldiaConfig cfg = HeraldiaConfig.get();
		List<Component> lineas = new ArrayList<>();
		if (op) {
			lineas.add(Textos.t("heraldia.estado.dificultad", nombreValor("dificultad.nivel", cfg.getString("dificultad.nivel")),
					InfoCommand.onOff(cfg.getBool("dificultad.escalar_por_jugadores")), InfoCommand.onOff(cfg.getBool("dificultad.escalar_botin"))));
			lineas.add(Textos.t("heraldia.estado.generacion", cfg.getInt("aldeas.separacion_bloques"), cfg.getInt("aldeas.maximo"),
					InfoCommand.onOff(cfg.getBool(Medianas.ACTIVADAS)), InfoCommand.onOff(cfg.getBool(Minas.ACTIVADO)),
					InfoCommand.onOff(cfg.getBool(Caminos.ACTIVADO)),
					t.unicas().stream().filter(u -> InfoCommand.uniqueEnabled(cfg, u)).count(), t.unicas().size()));
		}
		lineas.add(Textos.t("heraldia.estado.descubiertas", l.jugadores()).withStyle(ChatFormatting.YELLOW));
		tipo(lineas, op, "heraldia.estado.tipo.aldeas", Estado.contar(t.familias(), f -> l.hecho(Estado.NS + "aldeas/" + f)),
				f -> Textos.t("heraldia.familia." + f));
		tipo(lineas, op, "heraldia.estado.tipo.unicas", Estado.contar(t.unicas(), u -> l.hecho(Estado.NS + "unicas/" + u + "/descubrir")),
				InfoCommand::uniqueName);
		tipo(lineas, op, "heraldia.estado.tipo.medianas", Estado.contar(t.medianas(), m -> l.criterio(Estado.NS + "medianas/todas", m)),
				InfoCommand::mediumName);
		tipo(lineas, op, "heraldia.estado.tipo.minas", Estado.contar(t.minas(), m -> l.hecho(Estado.NS + "minas/" + m)),
				m -> Textos.t("heraldia.minas." + m + ".nombre"));
		tipo(lineas, op, "heraldia.estado.guardianes", Estado.contar(t.guardianes(), u -> l.hecho(Estado.NS + "unicas/" + u + "/guardian")),
				InfoCommand::uniqueName);
		boolean arena = cfg.getBool("arena.activado");
		lineas.add(Textos.t("heraldia.estado.arena", Textos.t(!arena ? "heraldia.info.desactivada"
				: Arena.centro() != null ? "heraldia.estado.arena.colocada" : "heraldia.estado.arena.sin_colocar"), Arena.record(server)));
		lineas.addAll(io.github.albertosa23.heraldia.encargos.Encargos.estado(server, src.getPlayer()));   // T38
		lineas.addAll(io.github.albertosa23.heraldia.caravanas.Caravanas.estado());                         // T39
		lineas.addAll(io.github.albertosa23.heraldia.chozas.Magos.estado());                                // T43
		lineas.add(WithoutLootrCondition.LOOTR_LOADED
				? Textos.t("heraldia.estado.reponer.lootr")
				: cfg.getBool("botin.reponer.activado")
				? Textos.t("heraldia.estado.reponer", cfg.getInt("botin.reponer.dias"))
				: Textos.t("heraldia.estado.reponer.no"));
		lineas.add(Textos.t("heraldia.estado.lootr", Textos.t(WithoutLootrCondition.LOOTR_LOADED ? "heraldia.info.cargado" : "heraldia.info.no_cargado")));
		if (op) {
			lineas.add(Textos.t("heraldia.estado.jefes", InfoCommand.onOff(cfg.getBool("jefes.fases.activado")),
					InfoCommand.onOff(cfg.getBool("jefes.refuerzos.activado")), InfoCommand.onOff(cfg.getBool("jefes.barra.activado")),
					InfoCommand.onOff(cfg.getBool("guia.entregar_al_entrar"))));
			List<String> mods = otrosMods();
			lineas.add(Textos.t("heraldia.estado.mods", mods.size(), mods.isEmpty() ? "-" : String.join(", ", mods)));
		}
		int paginas = Estado.paginas(lineas.size(), Estado.POR_PAGINA);
		int p = Math.clamp(pagina, 1, paginas);
		src.sendSuccess(() -> Textos.t("heraldia.estado.titulo", version(), p, paginas).withStyle(ChatFormatting.GOLD), false);
		for (Component c : Estado.pagina(lineas, p, Estado.POR_PAGINA)) {
			src.sendSuccess(() -> c, false);
		}
		if (paginas > 1) {
			MutableComponent nav = Component.empty();
			if (p > 1) {
				nav.append(boton("heraldia.estado.anterior", "/heraldia status " + (p - 1))).append(" ");
			}
			if (p < paginas) {
				nav.append(boton("heraldia.estado.siguiente", "/heraldia status " + (p + 1)));
			}
			src.sendSuccess(() -> nav, false);
		}
	}

	/** Una línea « - Tipo: n de m» y, para los operadores, otra con lo que falta. */
	private static void tipo(List<Component> out, boolean op, String clave, Estado.Cuenta c, Function<String, Component> nombre) {
		out.add(Textos.t(clave, c.hechos(), c.total()));
		if (op && !c.faltan().isEmpty()) {
			out.add(Textos.t("heraldia.estado.faltan", ComponentUtils.formatList(c.faltan(), Component.literal(", "), nombre))
					.withStyle(ChatFormatting.GRAY));
		}
	}

	private static Component boton(String key, String orden) {
		return Textos.t(key).withStyle(s -> s.withColor(ChatFormatting.AQUA).withClickEvent(new ClickEvent.RunCommand(orden))
				.withHoverEvent(new HoverEvent.ShowText(Component.literal(orden))));
	}

	/** Nombre traducido de un valor de una opción de lista (p. ej. «Heroica»). */
	private static Component nombreValor(String clave, String valor) {
		for (ConfigOption o : HeraldiaConfig.options()) {
			if (o.key().equals(clave)) {
				int i = o.values().indexOf(valor);
				if (i >= 0 && i < o.valueNames().size()) {
					return Textos.t(o.valueNames().get(i));
				}
			}
		}
		return Component.literal(valor);
	}

	static String version() {
		return FabricLoader.getInstance().getModContainer(Heraldia.MOD_ID)
				.map(c -> c.getMetadata().getVersion().getFriendlyString()).orElse("?");
	}

	/** Mods cargados además de Heraldia, Minecraft, Java y Fabric (sin los que van dentro de otro). */
	static List<String> otrosMods() {
		List<String> out = new ArrayList<>();
		for (ModContainer m : FabricLoader.getInstance().getAllMods()) {
			String id = m.getMetadata().getId();
			if (m.getContainingMod().isPresent() || id.equals(Heraldia.MOD_ID) || id.equals("minecraft") || id.equals("java")
					|| id.startsWith("fabric") || id.equals("mixinextras")) {
				continue;
			}
			out.add(m.getMetadata().getName() + " " + m.getMetadata().getVersion().getFriendlyString());
		}
		out.sort(String.CASE_INSENSITIVE_ORDER);
		return out;
	}
}
