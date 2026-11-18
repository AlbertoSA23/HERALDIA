package io.github.albertosa23.heraldia.command;

import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.arena.Arena;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.config.Reload;
import io.github.albertosa23.heraldia.difficulty.MobDifficulty;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import net.fabricmc.loader.api.FabricLoader;
import net.minecraft.ChatFormatting;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.Entity;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * /heraldia reload (operator, level 2): reads config/heraldia.json again and hot-applies what does not affect
 * generation ({@link Reload}); what does affect it is listed and not applied. After changing the configuration:
 * <ul>
 * <li>difficulty: the modifiers of the already loaded Heraldia mobs are recomputed (the others, when they load);</li>
 * <li>golems: the limits are published again to the functions' scoreboard;</li>
 * <li>arena: increments, max alive, experience and whether it is enabled (with a match running, it waits);</li>
 * <li>the rest (bosses, loot and its restocking, Guide, trades, per-player chest) is read on each use.</li>
 * </ul>
 * The client's configuration screen uses the same path ({@link #apply}) when saving with a world open.
 */
public final class ReloadCommand {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");

	private ReloadCommand() {
	}

	static LiteralArgumentBuilder<CommandSourceStack> node() {
		return Commands.literal("reload")
				.requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))
				.executes(ctx -> {
					List<Component> lines = apply(ctx.getSource().getServer());
					lines.forEach(l -> ctx.getSource().sendSuccess(() -> l, true));
					return lines.size();
				});
	}

	/** The server's configuration file (the same one Heraldia.onInitialize reads). */
	public static Path file() {
		return FabricLoader.getInstance().getConfigDir().resolve("heraldia.json");
	}

	/**
	 * Reloads and applies (on the server thread). Returns the report lines, translatable: what was applied, what waits
	 * for the restart and what was recomputed.
	 */
	public static List<Component> apply(MinecraftServer server) {
		Path file = file();
		Reload.Result r = HeraldiaConfig.reload(file);
		HeraldiaConfig cfg = HeraldiaConfig.get();
		List<Component> out = new ArrayList<>();
		out.add(Texts.t("heraldia.recargar.titulo", file.getFileName().toString()).withStyle(ChatFormatting.GOLD));
		if (r.applied().isEmpty()) {
			out.add(Texts.t("heraldia.recargar.nada").withStyle(ChatFormatting.GRAY));
		} else {
			out.add(Texts.t("heraldia.recargar.aplicadas", r.applied().size()));
			for (String k : r.applied()) {
				out.add(Texts.t("heraldia.recargar.aplicada", k, cfg.values().get(k).getAsString()).withStyle(ChatFormatting.GREEN));
			}
		}
		if (!r.pending().isEmpty()) {
			out.add(Texts.t("heraldia.recargar.pendientes", r.pending().size()).withStyle(ChatFormatting.YELLOW));
			for (Reload.Pending p : r.pending()) {
				out.add(Texts.t("heraldia.recargar.pendiente", p.key(), p.inUse().getAsString(), p.read().getAsString())
						.withStyle(ChatFormatting.YELLOW));
			}
		}
		// Effects of what is stored outside the configuration: always (it is cheap and keeps everything consistent).
		int mobs = recomputeMobs(server);
		out.add(Texts.t("heraldia.recargar.mobs", mobs).withStyle(ChatFormatting.GRAY));
		Heraldia.publishGolemSettings(server);
		if (!Arena.reload(server)) {
			out.add(Texts.t("heraldia.recargar.arena_partida").withStyle(ChatFormatting.YELLOW));
		}
		io.github.albertosa23.heraldia.maps.WebMaps.schedule();   // mapas_web.* (and the arena) on the web maps, if any
		LOGGER.info("Heraldia: /heraldia reload: {} aplicadas, {} pendientes de reinicio, {} mobs recalculados",
				r.applied().size(), r.pending().size(), mobs);
		return out;
	}

	/** Difficulty: the new configuration's modifiers on all already loaded Heraldia mobs (once, not per tick). */
	static int recomputeMobs(MinecraftServer server) {
		int n = 0;
		for (ServerLevel level : server.getAllLevels()) {
			for (Entity e : level.getAllEntities()) {
				if (MobDifficulty.apply(e)) {
					n++;
				}
			}
		}
		return n;
	}
}
