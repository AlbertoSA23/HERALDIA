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
 * Vanilla boss bar ({@link ServerBossEvent}, any client sees it) of each guardian in combat: with its name,
 * its health, the color of its phase and the players within {@link Phases#RADIUS} blocks. It starts on receiving or
 * dealing a hit and is removed on death, on unload or when no player is left within {@link Phases#OUTSIDE_RADIUS}.
 * In memory only (the server thread): after a restart, the next hit creates it again. It is swept once per
 * second and only if there are fights (the map is almost always empty).
 */
final class Bars {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	private static final int EVERY = 20;
	private static final Map<UUID, Combat> ACTIVE = new HashMap<>();

	private record Combat(Mob boss, ServerBossEvent bar) {
	}

	private Bars() {
	}

	/** The guardian enters (or stays) in combat: creates its bar if it has none and updates it. */
	static void combat(Mob boss) {
		Combat c = ACTIVE.get(boss.getUUID());
		if (c == null) {
			if (!(boss.level() instanceof ServerLevel level) || !Bosses.hasPlayers(level, boss, Phases.RADIUS)) {
				return;      // nobody would see it: it is not created (nor logged)
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
		// those who went to another dimension
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

	/** Yellow in phase 1, red in 2 and purple in 3. */
	static BossEvent.BossBarColor color(int phase) {
		return switch (phase) {
			case 1 -> BossEvent.BossBarColor.YELLOW;
			case 2 -> BossEvent.BossBarColor.RED;
			default -> BossEvent.BossBarColor.PURPLE;
		};
	}
}
