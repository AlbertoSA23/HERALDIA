package io.github.albertosa23.heraldia.arena;

import io.github.albertosa23.heraldia.command.Texts;
import net.minecraft.ChatFormatting;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.scores.DisplaySlot;
import net.minecraft.world.scores.Objective;
import net.minecraft.world.scores.ReadOnlyScoreInfo;
import net.minecraft.world.scores.ScoreAccess;
import net.minecraft.world.scores.ScoreHolder;
import net.minecraft.world.scores.Scoreboard;
import net.minecraft.world.scores.criteria.ObjectiveCriteria;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Récords de la arena en el marcador vanilla (lo guarda el juego con el mundo): el objetivo {@link #OBJECTIVE}, con la
 * oleada más alta superada por cada jugador y la del servidor ({@link #SERVER}: no puede ser el nombre de un jugador,
 * y se muestra con su nombre traducido). Se ve en la barra lateral mientras dura una partida, si nadie la usa para otra
 * cosa. Al batir el récord del servidor se anuncia en el chat; el personal, solo al jugador.
 */
final class ArenaScoreboard {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	static final String OBJECTIVE = "heraldia_arena";
	static final String SERVER = "-servidor-";

	private ArenaScoreboard() {
	}

	/** ¿Es un récord nuevo? (lógica pura) */
	static boolean improves(int previous, int cleared) {
		return cleared > previous;
	}

	static Objective target(MinecraftServer server) {
		Scoreboard board = server.getScoreboard();
		Objective obj = board.getObjective(OBJECTIVE);
		if (obj == null) {
			obj = board.addObjective(OBJECTIVE, ObjectiveCriteria.DUMMY, Texts.t("heraldia.arena.marcador").withStyle(ChatFormatting.GOLD),
					ObjectiveCriteria.RenderType.INTEGER, false, null);
		}
		return obj;
	}

	static int read(MinecraftServer server, String holder) {
		ReadOnlyScoreInfo info = server.getScoreboard().getPlayerScoreInfo(ScoreHolder.forNameOnly(holder), target(server));
		return info == null ? 0 : info.value();
	}

	static int record(MinecraftServer server) {
		return read(server, SERVER);
	}

	/** Un participante ha superado la oleada {@code n}: récord personal y del servidor. */
	static void cleared(MinecraftServer server, ServerPlayer p, int n) {
		Scoreboard board = server.getScoreboard();
		Objective obj = target(server);
		String name = p.getScoreboardName();
		if (improves(read(server, name), n)) {
			board.getOrCreatePlayerScore(ScoreHolder.forNameOnly(name), obj).set(n);
			if (!improves(read(server, SERVER), n)) {
				p.sendSystemMessage(Texts.t("heraldia.arena.record.personal", n).withStyle(ChatFormatting.AQUA));
			}
		}
		if (improves(read(server, SERVER), n)) {
			ScoreAccess s = board.getOrCreatePlayerScore(ScoreHolder.forNameOnly(SERVER), obj);
			s.set(n);
			s.display(Texts.t("heraldia.arena.marcador.servidor").withStyle(ChatFormatting.GOLD));
			Component announcement = Texts.t("heraldia.arena.record.servidor", p.getDisplayName(), n).withStyle(ChatFormatting.GOLD);
			server.getPlayerList().broadcastSystemMessage(announcement, false);
			LOGGER.info("Heraldia: arena: récord del servidor: {} en la oleada {}", p.getGameProfile().name(), n);
		}
	}

	/** Barra lateral con los récords, si está libre. */
	static void show(MinecraftServer server) {
		Scoreboard board = server.getScoreboard();
		if (board.getDisplayObjective(DisplaySlot.SIDEBAR) == null) {
			board.setDisplayObjective(DisplaySlot.SIDEBAR, target(server));
		}
	}

	/** Quita la barra lateral si es la de la arena. */
	static void hide(MinecraftServer server) {
		Scoreboard board = server.getScoreboard();
		Objective obj = board.getObjective(OBJECTIVE);
		if (obj != null && board.getDisplayObjective(DisplaySlot.SIDEBAR) == obj) {
			board.setDisplayObjective(DisplaySlot.SIDEBAR, null);
		}
	}
}
