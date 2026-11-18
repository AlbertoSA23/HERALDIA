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
 * Arena records on the vanilla scoreboard (the game saves it with the world): the {@link #OBJECTIVE} objective, with the
 * highest wave cleared by each player and the server's ({@link #SERVER}: it cannot be a player name, and it is shown with
 * its translated name). It shows in the sidebar while a match lasts, if nobody uses it for something else. Beating the
 * server record is announced in the chat; a personal one, only to the player.
 */
final class ArenaScoreboard {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	static final String OBJECTIVE = "heraldia_arena";
	static final String SERVER = "-servidor-";

	private ArenaScoreboard() {
	}

	/** Is it a new record? (pure logic) */
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

	/** A participant has cleared wave {@code n}: personal and server record. */
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

	/** Sidebar with the records, if it is free. */
	static void show(MinecraftServer server) {
		Scoreboard board = server.getScoreboard();
		if (board.getDisplayObjective(DisplaySlot.SIDEBAR) == null) {
			board.setDisplayObjective(DisplaySlot.SIDEBAR, target(server));
		}
	}

	/** Removes the sidebar if it is the arena's. */
	static void hide(MinecraftServer server) {
		Scoreboard board = server.getScoreboard();
		Objective obj = board.getObjective(OBJECTIVE);
		if (obj != null && board.getDisplayObjective(DisplaySlot.SIDEBAR) == obj) {
			board.setDisplayObjective(DisplaySlot.SIDEBAR, null);
		}
	}
}
