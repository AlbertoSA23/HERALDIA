package io.github.albertosa23.heraldia.comando;

import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.arena.Arena;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.config.Recarga;
import io.github.albertosa23.heraldia.dificultad.DificultadMobs;
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
 * /heraldia recargar (operador, nivel 2): vuelve a leer config/heraldia.json y aplica en caliente lo que no afecta a la
 * generación ({@link Recarga}); lo que sí la afecta se lista y no se aplica. Después de cambiar la configuración:
 * <ul>
 * <li>dificultad: se recalculan los modificadores de los mobs de Heraldia ya cargados (los demás, al cargarse);</li>
 * <li>gólems: se publican otra vez los límites al marcador de las funciones;</li>
 * <li>arena: incrementos, máximo de vivos, experiencia y si está activada (con una partida en marcha, se espera);</li>
 * <li>lo demás (jefes, botín y su reposición, Guía, tratos, cofre por jugador) se lee cada vez que se usa.</li>
 * </ul>
 * La pantalla de configuración del cliente usa el mismo camino ({@link #aplicar}) al guardar en un mundo abierto.
 */
public final class RecargarCommand {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");

	private RecargarCommand() {
	}

	static LiteralArgumentBuilder<CommandSourceStack> nodo() {
		return Commands.literal("recargar")
				.requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))
				.executes(ctx -> {
					List<Component> lines = aplicar(ctx.getSource().getServer());
					lines.forEach(l -> ctx.getSource().sendSuccess(() -> l, true));
					return lines.size();
				});
	}

	/** El fichero de configuración del servidor (el mismo que lee Heraldia.onInitialize). */
	public static Path fichero() {
		return FabricLoader.getInstance().getConfigDir().resolve("heraldia.json");
	}

	/**
	 * Recarga y aplica (en el hilo del servidor). Devuelve las líneas del informe, traducibles: lo aplicado, lo que espera
	 * al reinicio y lo recalculado.
	 */
	public static List<Component> aplicar(MinecraftServer server) {
		Path file = fichero();
		Recarga.Resultado r = HeraldiaConfig.recargar(file);
		HeraldiaConfig cfg = HeraldiaConfig.get();
		List<Component> out = new ArrayList<>();
		out.add(Textos.t("heraldia.recargar.titulo", file.getFileName().toString()).withStyle(ChatFormatting.GOLD));
		if (r.aplicadas().isEmpty()) {
			out.add(Textos.t("heraldia.recargar.nada").withStyle(ChatFormatting.GRAY));
		} else {
			out.add(Textos.t("heraldia.recargar.aplicadas", r.aplicadas().size()));
			for (String k : r.aplicadas()) {
				out.add(Textos.t("heraldia.recargar.aplicada", k, cfg.values().get(k).getAsString()).withStyle(ChatFormatting.GREEN));
			}
		}
		if (!r.pendientes().isEmpty()) {
			out.add(Textos.t("heraldia.recargar.pendientes", r.pendientes().size()).withStyle(ChatFormatting.YELLOW));
			for (Recarga.Pendiente p : r.pendientes()) {
				out.add(Textos.t("heraldia.recargar.pendiente", p.clave(), p.enUso().getAsString(), p.leido().getAsString())
						.withStyle(ChatFormatting.YELLOW));
			}
		}
		// Efectos de lo que se guarda fuera de la configuración: siempre (es barato y deja todo coherente).
		int mobs = recalcularMobs(server);
		out.add(Textos.t("heraldia.recargar.mobs", mobs).withStyle(ChatFormatting.GRAY));
		Heraldia.publishGolemSettings(server);
		if (!Arena.recargar(server)) {
			out.add(Textos.t("heraldia.recargar.arena_partida").withStyle(ChatFormatting.YELLOW));
		}
		LOGGER.info("Heraldia: /heraldia recargar: {} aplicadas, {} pendientes de reinicio, {} mobs recalculados",
				r.aplicadas().size(), r.pendientes().size(), mobs);
		return out;
	}

	/** Dificultad: los modificadores de la configuración nueva en todos los mobs de Heraldia ya cargados (una vez, no por tick). */
	static int recalcularMobs(MinecraftServer server) {
		int n = 0;
		for (ServerLevel level : server.getAllLevels()) {
			for (Entity e : level.getAllEntities()) {
				if (DificultadMobs.aplicar(e)) {
					n++;
				}
			}
		}
		return n;
	}
}
