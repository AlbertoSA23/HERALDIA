package io.github.albertosa23.heraldia.bosses;

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
 * su vida, el color de su fase y los jugadores a menos de {@link Phases#RADIUS} bloques. Empieza al recibir o dar un
 * golpe y se quita al morir, al descargarse o cuando no queda ningún jugador a menos de {@link Phases#OUTSIDE_RADIUS}.
 * Solo en memoria (el hilo del servidor): tras un reinicio, el siguiente golpe la vuelve a crear. Se repasa una vez por
 * segundo y solo si hay combates (el mapa casi siempre está vacío).
 */
final class Bars {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	private static final int EVERY = 20;
	private static final Map<UUID, Combat> ACTIVE = new HashMap<>();

	private record Combat(Mob boss, ServerBossEvent bar) {
	}

	private Bars() {
	}

	/** El guardián entra (o sigue) en combate: crea su barra si no la tiene y la pone al día. */
	static void combat(Mob boss) {
		Combat c = ACTIVE.get(boss.getUUID());
		if (c == null) {
			if (!(boss.level() instanceof ServerLevel level) || !Bosses.hasPlayers(level, boss, Phases.RADIUS)) {
				return;      // nadie la vería: no se crea (ni se escribe en el log)
			}
			c = new Combat(boss, new ServerBossEvent(UUID.randomUUID(), boss.getDisplayName(), color(1),
					BossEvent.BossBarOverlay.NOTCHED_6));
			ACTIVE.put(boss.getUUID(), c);
		}
		update(c);
	}

	static void clear(Entity boss, String reason) {
		Combat c = ACTIVE.remove(boss.getUUID());
		if (c != null) {
			c.bar().removeAllPlayers();
			LOGGER.info("Heraldia: jefes: barra de {} quitada ({})", Bosses.name(boss), reason);
		}
	}

	static void everyTick(MinecraftServer server) {
		if (ACTIVE.isEmpty() || server.getTickCount() % EVERY != 0) {
			return;
		}
		for (Combat c : List.copyOf(ACTIVE.values())) {
			update(c);
		}
	}

	static void drain() {
		ACTIVE.values().forEach(c -> c.bar().removeAllPlayers());
		ACTIVE.clear();
	}

	private static void update(Combat c) {
		Mob boss = c.boss();
		if (boss.isRemoved() || boss.isDeadOrDying() || !(boss.level() instanceof ServerLevel level)) {
			clear(boss, boss.isDeadOrDying() ? "muerto" : "descargado");
			return;
		}
		ServerBossEvent bar = c.bar();
		bar.setProgress(Phases.progress(boss.getHealth(), boss.getMaxHealth()));
		bar.setColor(color(Phases.reached(boss.entityTags())));
		bar.setName(boss.getDisplayName());
		int before = bar.getPlayers().size();
		for (ServerPlayer p : level.players()) {
			Boolean sees = Phases.sees(p.distanceToSqr(boss));
			if (Boolean.TRUE.equals(sees)) {
				bar.addPlayer(p);
			} else if (Boolean.FALSE.equals(sees)) {
				bar.removePlayer(p);
			}
		}
		// los que se han ido a otra dimensión
		List<ServerPlayer> outside = new ArrayList<>();
		for (ServerPlayer p : bar.getPlayers()) {
			if (p.level() != level || p.isRemoved()) {
				outside.add(p);
			}
		}
		outside.forEach(bar::removePlayer);
		int now = bar.getPlayers().size();
		if (now == 0) {
			clear(boss, "sin jugadores cerca");
		} else if (now != before) {
			LOGGER.info("Heraldia: jefes: barra de {} para {} jugadores", Bosses.name(boss), now);
		}
	}

	/** Amarilla en la fase 1, roja en la 2 y morada en la 3. */
	static BossEvent.BossBarColor color(int phase) {
		return switch (phase) {
			case 1 -> BossEvent.BossBarColor.YELLOW;
			case 2 -> BossEvent.BossBarColor.RED;
			default -> BossEvent.BossBarColor.PURPLE;
		};
	}
}
