package io.github.albertosa23.heraldia.command;

import com.google.gson.JsonElement;
import com.google.gson.JsonParser;
import com.mojang.brigadier.arguments.IntegerArgumentType;
import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.arena.Arena;
import io.github.albertosa23.heraldia.roads.Roads;
import io.github.albertosa23.heraldia.common.MediumStructures;
import io.github.albertosa23.heraldia.config.ConfigOption;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.loot.WithoutLootrCondition;
import io.github.albertosa23.heraldia.coast.Coast;
import io.github.albertosa23.heraldia.mines.Mines;
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
 * /heraldia status [page] (any player; operators see more): version, Heraldia structures discovered
 * by some player against the total per type, guardians defeated, arena record, loot restocking, Lootr and,
 * for operators, the key options, what is left to discover and the other loaded mods.
 * <p>The advancements of online players are read from memory (on the server thread); the others', from their
 * files in the world folder, off the server thread ({@link State.Achievements#addFile}).
 */
public final class StatusCommand {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");

	private StatusCommand() {
	}

	static LiteralArgumentBuilder<CommandSourceStack> node() {
		return Commands.literal("status")
				.executes(ctx -> show(ctx.getSource(), 1))
				.then(Commands.argument("page", IntegerArgumentType.integer(1, 99))
						.executes(ctx -> show(ctx.getSource(), IntegerArgumentType.getInteger(ctx, "page"))));
	}

	/** What is counted, per structure kind: ids in order and the advancement (or criterion) that says whether someone discovered it. */
	private record Types(List<String> families, List<String> uniques, List<String> mediums, List<String> mines, List<String> coast,
						 List<String> guardians) {
	}

	private static int show(CommandSourceStack src, int page) {
		MinecraftServer server = src.getServer();
		boolean op = Commands.hasPermission(Commands.LEVEL_GAMEMASTERS).test(src);
		Types types = types(server);
		// on the server thread: the online ones (their files may be out of date)
		State.Achievements advancements = new State.Achievements();
		Set<UUID> online = new HashSet<>();
		List<AdvancementHolder> own = server.getAdvancements().getAllAdvancements().stream()
				.filter(a -> Heraldia.MOD_ID.equals(a.id().getNamespace())).toList();
		for (ServerPlayer p : server.getPlayerList().getPlayers()) {
			online.add(p.getUUID());
			advancements.player();
			for (AdvancementHolder a : own) {
				AdvancementProgress pr = p.getAdvancements().getOrStartProgress(a);
				if (pr.hasProgress()) {
					advancements.add(a.id().toString(), pr.isDone(), pr.getCompletedCriteria());
				}
			}
		}
		Path dir = server.getWorldPath(LevelResource.PLAYER_ADVANCEMENTS_DIR);
		CompletableFuture.runAsync(() -> readFiles(dir, online, advancements), Util.ioPool())
				.thenRunAsync(() -> send(src, server, op, types, advancements, page), server)
				.exceptionally(e -> {
					LOGGER.error("Heraldia: /heraldia status falló", e);
					src.sendFailure(Component.literal(String.valueOf(e.getMessage())));
					return null;
				});
		return 1;
	}

	/** Off the server thread: the advancement files of offline players. */
	public static void readFiles(Path dir, Set<UUID> online, State.Achievements advancements) {
		if (!Files.isDirectory(dir)) {
			return;
		}
		try (Stream<Path> files = Files.list(dir)) {
			for (Path f : files.filter(x -> x.getFileName().toString().endsWith(".json")).toList()) {
				String n = f.getFileName().toString();
				try {
					if (online.contains(UUID.fromString(n.substring(0, n.length() - ".json".length())))) {
						continue;
					}
					JsonElement e = JsonParser.parseString(Files.readString(f, StandardCharsets.UTF_8));
					if (e.isJsonObject()) {
						advancements.addFile(e.getAsJsonObject());
					}
				} catch (IOException | RuntimeException ignored) {
					// someone else's or broken file: does not count
				}
			}
		} catch (IOException e) {
			LOGGER.warn("Heraldia: /heraldia status: no se pudo leer {} ({})", dir, e.getMessage());
		}
	}

	private static Types types(MinecraftServer server) {
		Set<String> families = new LinkedHashSet<>(), uniques = new TreeSet<>(), mediums = new TreeSet<>(), mines = new LinkedHashSet<>();
		var styles = ReviewCommand.familyStyle(HeraldiaConfig.get());
		Set<String> ids = new TreeSet<>();
		server.registryAccess().lookupOrThrow(Registries.STRUCTURE).keySet().stream()
				.filter(id -> Heraldia.MOD_ID.equals(id.getNamespace())).forEach(id -> ids.add(id.getPath()));
		styles.forEach((style, fam) -> {
			if (ids.contains(style) || ids.contains(style + "_grande")) {
				families.add(fam);
			}
		});
		for (String p : ids) {
			String[] s = p.split("/");
			if (s[0].equals("unicas") && s.length >= 2) {
				uniques.add(s[1]);
			} else if (MediumStructures.isMedium(Heraldia.id(p)) && s.length >= 2) {
				mediums.add(s[1]);
			}
		}
		for (String t : Revision.SIZES) {
			if (ids.stream().anyMatch(p -> Mines.isMine(Heraldia.id(p)) && p.startsWith(Mines.PREFIX + t + "/"))) {
				mines.add(t);
			}
		}
		List<String> coast = Coast.TYPES.stream()
				.filter(c -> ids.stream().anyMatch(p -> p.startsWith(Coast.PREFIX + c + "/"))).toList();
		List<String> guardians = uniques.stream()
				.filter(u -> server.getAdvancements().get(Heraldia.id("unicas/" + u + "/guardian")) != null).toList();
		return new Types(List.copyOf(families), List.copyOf(uniques), List.copyOf(mediums), List.copyOf(mines), coast, guardians);
	}

	private static void send(CommandSourceStack src, MinecraftServer server, boolean op, Types t, State.Achievements l, int page) {
		HeraldiaConfig cfg = HeraldiaConfig.get();
		List<Component> lines = new ArrayList<>();
		if (op) {
			lines.add(Texts.t("heraldia.estado.dificultad", nameValue("dificultad.nivel", cfg.getString("dificultad.nivel")),
					InfoCommand.onOff(cfg.getBool("dificultad.escalar_por_jugadores")), InfoCommand.onOff(cfg.getBool("dificultad.escalar_botin"))));
			lines.add(Texts.t("heraldia.estado.generacion", cfg.getInt("aldeas.separacion_bloques"), cfg.getInt("aldeas.maximo"),
					InfoCommand.onOff(cfg.getBool(MediumStructures.ENABLED)), InfoCommand.onOff(cfg.getBool(Mines.ENABLED)),
					InfoCommand.onOff(cfg.getBool(Roads.ENABLED)),
					t.uniques().stream().filter(u -> InfoCommand.uniqueEnabled(cfg, u)).count(), t.uniques().size()));
		}
		lines.add(Texts.t("heraldia.estado.descubiertas", l.players()).withStyle(ChatFormatting.YELLOW));
		type(lines, op, "heraldia.estado.tipo.aldeas", State.count(t.families(), f -> l.done(State.NS + "aldeas/" + f)),
				f -> Texts.t("heraldia.familia." + f));
		type(lines, op, "heraldia.estado.tipo.unicas", State.count(t.uniques(), u -> l.done(State.NS + "unicas/" + u + "/descubrir")),
				InfoCommand::uniqueName);
		// one criterion per type in the walker advancement of its dimension (the Nether and End types are not in medianas/todas)
		type(lines, op, "heraldia.estado.tipo.medianas", State.count(t.mediums(), m -> l.criterion(State.NS + "medianas/todas", m)
						|| l.criterion(State.NS + "medianas/nether", m) || l.criterion(State.NS + "medianas/end", m)),
				InfoCommand::mediumName);
		type(lines, op, "heraldia.estado.tipo.minas", State.count(t.mines(), m -> l.done(State.NS + "minas/" + m)),
				m -> Texts.t("heraldia.minas." + m + ".nombre"));
		type(lines, op, "heraldia.estado.tipo.costa", State.count(t.coast(), c -> l.done(State.NS + "costa/" + c)),
				c -> Texts.t("heraldia.costa." + c + ".nombre"));
		type(lines, op, "heraldia.estado.guardianes", State.count(t.guardians(), u -> l.done(State.NS + "unicas/" + u + "/guardian")),
				InfoCommand::uniqueName);
		if (src.getPlayer() != null) {   // this is the server's summary; each player's own progress is in their journal
			lines.add(Journal.statusLine(Texts.language(src.getPlayer())));
		}
		boolean arena = cfg.getBool("arena.activado");
		lines.add(Texts.t("heraldia.estado.arena", Texts.t(!arena ? "heraldia.info.desactivada"
				: Arena.center() != null ? "heraldia.estado.arena.colocada" : "heraldia.estado.arena.sin_colocar"), Arena.record(server)));
		lines.addAll(io.github.albertosa23.heraldia.quests.Quests.state(server, src.getPlayer()));   // T38
		lines.addAll(io.github.albertosa23.heraldia.caravans.Caravans.state());                         // T39
		lines.addAll(io.github.albertosa23.heraldia.huts.Wizards.state());                                // T43
		lines.add(WithoutLootrCondition.LOOTR_LOADED
				? Texts.t("heraldia.estado.reponer.lootr")
				: cfg.getBool("botin.reponer.activado")
				? Texts.t("heraldia.estado.reponer", cfg.getInt("botin.reponer.dias"))
				: Texts.t("heraldia.estado.reponer.no"));
		lines.add(Texts.t("heraldia.estado.lootr", Texts.t(WithoutLootrCondition.LOOTR_LOADED ? "heraldia.info.cargado" : "heraldia.info.no_cargado")));
		if (op) {
			lines.add(Texts.t("heraldia.estado.jefes", InfoCommand.onOff(cfg.getBool("jefes.fases.activado")),
					InfoCommand.onOff(cfg.getBool("jefes.refuerzos.activado")), InfoCommand.onOff(cfg.getBool("jefes.barra.activado")),
					InfoCommand.onOff(cfg.getBool("guia.entregar_al_entrar"))));
			List<String> mods = otherMods();
			lines.add(Texts.t("heraldia.estado.mods", mods.size(), mods.isEmpty() ? "-" : String.join(", ", mods)));
		}
		int pages = State.pages(lines.size(), State.PER_PAGE);
		int p = Math.clamp(page, 1, pages);
		src.sendSuccess(() -> Texts.t("heraldia.estado.titulo", version(), p, pages).withStyle(ChatFormatting.GOLD), false);
		for (Component c : State.page(lines, p, State.PER_PAGE)) {
			src.sendSuccess(() -> c, false);
		}
		if (pages > 1) {
			MutableComponent nav = Component.empty();
			if (p > 1) {
				nav.append(button("heraldia.estado.anterior", "/heraldia status " + (p - 1))).append(" ");
			}
			if (p < pages) {
				nav.append(button("heraldia.estado.siguiente", "/heraldia status " + (p + 1)));
			}
			src.sendSuccess(() -> nav, false);
		}
	}

	/** A " - Type: n of m" line and, for operators, another with what is missing. */
	private static void type(List<Component> out, boolean op, String key, State.Tally c, Function<String, Component> name) {
		out.add(Texts.t(key, c.finished(), c.total()));
		if (op && !c.missing().isEmpty()) {
			out.add(Texts.t("heraldia.estado.faltan", ComponentUtils.formatList(c.missing(), Component.literal(", "), name))
					.withStyle(ChatFormatting.GRAY));
		}
	}

	private static Component button(String key, String order) {
		return Texts.t(key).withStyle(s -> s.withColor(ChatFormatting.AQUA).withClickEvent(new ClickEvent.RunCommand(order))
				.withHoverEvent(new HoverEvent.ShowText(Component.literal(order))));
	}

	/** Translated name of a list option's value (e.g. "Heroic"). */
	private static Component nameValue(String key, String value) {
		for (ConfigOption o : HeraldiaConfig.options()) {
			if (o.key().equals(key)) {
				int i = o.values().indexOf(value);
				if (i >= 0 && i < o.valueNames().size()) {
					return Texts.t(o.valueNames().get(i));
				}
			}
		}
		return Component.literal(value);
	}

	static String version() {
		return FabricLoader.getInstance().getModContainer(Heraldia.MOD_ID)
				.map(c -> c.getMetadata().getVersion().getFriendlyString()).orElse("?");
	}

	/** Loaded mods besides Heraldia, Minecraft, Java and Fabric (without those bundled inside another). */
	static List<String> otherMods() {
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
