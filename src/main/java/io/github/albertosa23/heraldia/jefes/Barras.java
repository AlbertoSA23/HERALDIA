package io.github.albertosa23.heraldia.jefes;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerBossEvent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.BossEvent;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.Mob;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Barra de jefe vanilla ({@link ServerBossEvent}, la ve cualquier cliente) de cada guardián en combate: con su nombre,
 * su vida, el color de su fase y los jugadores a menos de {@link Fases#RADIO} bloques. Empieza al recibir o dar un
 * golpe y se quita al morir, al descargarse o cuando no queda ningún jugador a menos de {@link Fases#RADIO_FUERA}.
 * Solo en memoria (el hilo del servidor): tras un reinicio, el siguiente golpe la vuelve a crear. Se repasa una vez por
 * segundo y solo si hay combates (el mapa casi siempre está vacío).
 */
final class Barras {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	private static final int CADA = 20;
	private static final Map<UUID, Combate> ACTIVAS = new HashMap<>();

	private record Combate(Mob jefe, ServerBossEvent barra) {
	}

	private Barras() {
	}

	/** El guardián entra (o sigue) en combate: crea su barra si no la tiene y la pone al día. */
	static void combate(Mob jefe) {
		Combate c = ACTIVAS.get(jefe.getUUID());
		if (c == null) {
			if (!(jefe.level() instanceof ServerLevel level) || !Jefes.hayJugadores(level, jefe, Fases.RADIO)) {
				return;      // nadie la vería: no se crea (ni se escribe en el log)
			}
			c = new Combate(jefe, new ServerBossEvent(UUID.randomUUID(), jefe.getDisplayName(), color(1),
					BossEvent.BossBarOverlay.NOTCHED_6));
			ACTIVAS.put(jefe.getUUID(), c);
		}
		actualizar(c);
	}

	static void quitar(Entity jefe, String motivo) {
		Combate c = ACTIVAS.remove(jefe.getUUID());
		if (c != null) {
			c.barra().removeAllPlayers();
			LOGGER.info("Heraldia: jefes: barra de {} quitada ({})", Jefes.nombre(jefe), motivo);
		}
	}

	static void cadaTick(MinecraftServer server) {
		if (ACTIVAS.isEmpty() || server.getTickCount() % CADA != 0) {
			return;
		}
		for (Combate c : List.copyOf(ACTIVAS.values())) {
			actualizar(c);
		}
	}

	static void vaciar() {
		ACTIVAS.values().forEach(c -> c.barra().removeAllPlayers());
		ACTIVAS.clear();
	}

	private static void actualizar(Combate c) {
		Mob jefe = c.jefe();
		if (jefe.isRemoved() || jefe.isDeadOrDying() || !(jefe.level() instanceof ServerLevel level)) {
			quitar(jefe, jefe.isDeadOrDying() ? "muerto" : "descargado");
			return;
		}
		ServerBossEvent barra = c.barra();
		barra.setProgress(Fases.progreso(jefe.getHealth(), jefe.getMaxHealth()));
		barra.setColor(color(Fases.alcanzada(jefe.entityTags())));
		barra.setName(jefe.getDisplayName());
		int antes = barra.getPlayers().size();
		for (ServerPlayer p : level.players()) {
			Boolean ve = Fases.ve(p.distanceToSqr(jefe));
			if (Boolean.TRUE.equals(ve)) {
				barra.addPlayer(p);
			} else if (Boolean.FALSE.equals(ve)) {
				barra.removePlayer(p);
			}
		}
		// los que se han ido a otra dimensión
		List<ServerPlayer> fuera = new ArrayList<>();
		for (ServerPlayer p : barra.getPlayers()) {
			if (p.level() != level || p.isRemoved()) {
				fuera.add(p);
			}
		}
		fuera.forEach(barra::removePlayer);
		int ahora = barra.getPlayers().size();
		if (ahora == 0) {
			quitar(jefe, "sin jugadores cerca");
		} else if (ahora != antes) {
			LOGGER.info("Heraldia: jefes: barra de {} para {} jugadores", Jefes.nombre(jefe), ahora);
		}
	}

	/** Amarilla en la fase 1, roja en la 2 y morada en la 3. */
	static BossEvent.BossBarColor color(int fase) {
		return switch (fase) {
			case 1 -> BossEvent.BossBarColor.YELLOW;
			case 2 -> BossEvent.BossBarColor.RED;
			default -> BossEvent.BossBarColor.PURPLE;
		};
	}
}
