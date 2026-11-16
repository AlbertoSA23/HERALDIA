package io.github.albertosa23.heraldia.arena;

import io.github.albertosa23.heraldia.comando.Textos;
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
 * Récords de la arena en el marcador vanilla (lo guarda el juego con el mundo): el objetivo {@link #OBJETIVO}, con la
 * oleada más alta superada por cada jugador y la del servidor ({@link #SERVIDOR}: no puede ser el nombre de un jugador,
 * y se muestra con su nombre traducido). Se ve en la barra lateral mientras dura una partida, si nadie la usa para otra
 * cosa. Al batir el récord del servidor se anuncia en el chat; el personal, solo al jugador.
 */
final class Marcador {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	static final String OBJETIVO = "heraldia_arena";
	static final String SERVIDOR = "-servidor-";

	private Marcador() {
	}

	/** ¿Es un récord nuevo? (lógica pura) */
	static boolean mejora(int previo, int superadas) {
		return superadas > previo;
	}

	static Objective objetivo(MinecraftServer server) {
		Scoreboard board = server.getScoreboard();
		Objective obj = board.getObjective(OBJETIVO);
		if (obj == null) {
			obj = board.addObjective(OBJETIVO, ObjectiveCriteria.DUMMY, Textos.t("heraldia.arena.marcador").withStyle(ChatFormatting.GOLD),
					ObjectiveCriteria.RenderType.INTEGER, false, null);
		}
		return obj;
	}

	static int leer(MinecraftServer server, String holder) {
		ReadOnlyScoreInfo info = server.getScoreboard().getPlayerScoreInfo(ScoreHolder.forNameOnly(holder), objetivo(server));
		return info == null ? 0 : info.value();
	}

	static int record(MinecraftServer server) {
		return leer(server, SERVIDOR);
	}

	/** Un participante ha superado la oleada {@code n}: récord personal y del servidor. */
	static void superada(MinecraftServer server, ServerPlayer p, int n) {
		Scoreboard board = server.getScoreboard();
		Objective obj = objetivo(server);
		String nombre = p.getScoreboardName();
		if (mejora(leer(server, nombre), n)) {
			board.getOrCreatePlayerScore(ScoreHolder.forNameOnly(nombre), obj).set(n);
			if (!mejora(leer(server, SERVIDOR), n)) {
				p.sendSystemMessage(Textos.t("heraldia.arena.record.personal", n).withStyle(ChatFormatting.AQUA));
			}
		}
		if (mejora(leer(server, SERVIDOR), n)) {
			ScoreAccess s = board.getOrCreatePlayerScore(ScoreHolder.forNameOnly(SERVIDOR), obj);
			s.set(n);
			s.display(Textos.t("heraldia.arena.marcador.servidor").withStyle(ChatFormatting.GOLD));
			Component anuncio = Textos.t("heraldia.arena.record.servidor", p.getDisplayName(), n).withStyle(ChatFormatting.GOLD);
			server.getPlayerList().broadcastSystemMessage(anuncio, false);
			LOGGER.info("Heraldia: arena: récord del servidor: {} en la oleada {}", p.getGameProfile().name(), n);
		}
	}

	/** Barra lateral con los récords, si está libre. */
	static void mostrar(MinecraftServer server) {
		Scoreboard board = server.getScoreboard();
		if (board.getDisplayObjective(DisplaySlot.SIDEBAR) == null) {
			board.setDisplayObjective(DisplaySlot.SIDEBAR, objetivo(server));
		}
	}

	/** Quita la barra lateral si es la de la arena. */
	static void ocultar(MinecraftServer server) {
		Scoreboard board = server.getScoreboard();
		Objective obj = board.getObjective(OBJETIVO);
		if (obj != null && board.getDisplayObjective(DisplaySlot.SIDEBAR) == obj) {
			board.setDisplayObjective(DisplaySlot.SIDEBAR, null);
		}
	}
}
