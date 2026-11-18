package io.github.albertosa23.heraldia.arena;

import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.command.KeyCommand;
import io.github.albertosa23.heraldia.command.Texts;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.difficulty.MobDifficulty;
import io.github.albertosa23.heraldia.bosses.Phases;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import net.minecraft.ChatFormatting;
import net.minecraft.advancements.AdvancementHolder;
import net.minecraft.core.BlockPos;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.chat.Component;
import net.minecraft.network.protocol.game.ClientboundSetSubtitleTextPacket;
import net.minecraft.network.protocol.game.ClientboundSetTitleTextPacket;
import net.minecraft.network.protocol.game.ClientboundSetTitlesAnimationPacket;
import net.minecraft.resources.Identifier;
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerBossEvent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.BossEvent;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntitySpawnReason;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.storage.loot.LootParams;
import net.minecraft.world.level.storage.loot.LootTable;
import net.minecraft.world.level.storage.loot.parameters.LootContextParamSets;
import net.minecraft.world.level.storage.loot.parameters.LootContextParams;
import net.minecraft.world.phys.AABB;
import org.jspecify.annotations.Nullable;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * La partida en marcha: mueve la {@link Match} cada tick (salida temprana si no hay ninguna), saca los mobs por
 * tandas en los puntos de aparición, los mantiene en el ruedo, lleva la barra de jefe, los títulos, los récords
 * ({@link ArenaScoreboard}), las recompensas y los logros, y cierra y abre la puerta del ruedo. Los mobs de la arena llevan la
 * etiqueta {@link Arena#TAG}; solo cuentan los de esta partida (en memoria): los demás se quitan al cargarse.
 */
final class Game {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	/** Modificadores propios (se suman a los de la dificultad y los jefes sin pisarlos). */
	static final Identifier HEALTH = Heraldia.id("arena_vida"), DAMAGE = Heraldia.id("arena_dano"),
			BOSS_HEALTH = Heraldia.id("arena_jefe_vida"), BOSS_DAMAGE = Heraldia.id("arena_jefe_dano");
	private static final int SPAWN_EVERY = 10, SWEEP_EVERY = 20, BAR_RADIUS = 24;
	private static final Set<String> NO_SUN = Set.of("minecraft:husk", "minecraft:creeper", "minecraft:spider",
			"minecraft:cave_spider", "minecraft:vindicator", "minecraft:witch", "minecraft:wither_skeleton");

	private static Match match = new Match(50);
	private static final Map<UUID, Mob> MOBS = new HashMap<>();
	/** Jugadores que reaparecen en la arena (cayeron en el ruedo); en memoria, se usa en el mismo tick. */
	private static final Set<UUID> RESPAWN = new HashSet<>();
	private static @Nullable ServerBossEvent bar;
	private static int leftPlayers;
	/** Experiencia de la oleada en curso: la que daría vanilla y la que se da (para el log). */
	private static long xpVanilla, xpGiven;
	private static int mobsPct = 50, statsPct = 10, maxAlive = 20, xpPct = 15;
	/** Modos activados (arena.modos.*) y oleadas del contrarreloj (arena.modos.oleadas_contrarreloj). */
	private static java.util.EnumSet<Mode> modes = java.util.EnumSet.allOf(Mode.class);
	private static int timeTrialWaves = 10;
	/** Nombre de cada participante de la partida en curso (para su marca aunque se desconecte). */
	private static final Map<UUID, String> NAMES = new HashMap<>();

	private Game() {
	}

	/** Lee la configuración (al arrancar) y deja la arena sin partida. */
	static void configure(HeraldiaConfig cfg) {
		mobsPct = cfg.getInt("arena.oleada.mobs_incremento");
		int requested = cfg.getInt("arena.oleada.stats_incremento");
		statsPct = Waves.effectiveStats(mobsPct, requested);
		if (statsPct != requested) {
			LOGGER.warn("Heraldia: arena: arena.oleada.stats_incremento={} es mayor que mobs_incremento={}: se usa {} "
					+ "(los mobs crecen más que su vida y daño)", requested, mobsPct, statsPct);
		}
		maxAlive = cfg.getInt("arena.max_mobs_vivos");
		xpPct = cfg.getInt("arena.experiencia_porcentaje");
		java.util.EnumSet<Mode> m = java.util.EnumSet.noneOf(Mode.class);
		for (Mode x : Mode.values()) {
			if (cfg.getBool(x.option())) {
				m.add(x);
			}
		}
		modes = m;
		timeTrialWaves = cfg.getInt("arena.modos.oleadas_contrarreloj");
		match = new Match(mobsPct);
		MOBS.clear();
		NAMES.clear();
	}

	/** Modos activados, en orden (cooperativo, contrarreloj, supervivencia). */
	static java.util.List<Mode> modes() {
		return List.copyOf(modes);
	}

	static boolean enabled(Mode m) {
		return modes.contains(m);
	}

	static int timeTrialWaves() {
		return timeTrialWaves;
	}

	static Match match() {
		return match;
	}

	static int experiencePct() {
		return xpPct;
	}

	static void addExperience(int vanilla, int given) {
		xpVanilla += vanilla;
		xpGiven += given;
	}

	// --- empezar y acabar ---

	/**
	 * Alguien toca la campana: con un solo modo activado empieza su cuenta atrás (como siempre); con varios, le ofrece en
	 * el chat un botón por modo (/heraldia arena start &lt;modo&gt;, que puede usar cualquiera desde el ruedo).
	 */
	static void bell(ServerPlayer p, Zone z) {
		if (match.state() != Match.State.FREE) {
			p.sendOverlayMessage(Texts.t("heraldia.arena.en_marcha"));
			return;
		}
		List<Mode> active = modes();
		if (active.isEmpty()) {
			p.sendOverlayMessage(Texts.t("heraldia.arena.modo.ninguno").withStyle(ChatFormatting.RED));
			return;
		}
		if (active.size() == 1) {
			start((ServerLevel) p.level(), z, p.getGameProfile().name(), active.get(0));
			return;
		}
		menu(p);
	}

	/** El menú de modos en el chat: un botón por modo activado (lo escribe en el log para las pruebas). */
	static void menu(ServerPlayer p) {
		java.util.Map<String, String> texts = Texts.language(p);
		net.minecraft.network.chat.MutableComponent line = Component.empty();
		for (Mode m : modes()) {
			String order = "/heraldia arena start " + m.id();
			line.append(Component.literal("[").append(Texts.t(texts, m.text())).append("]").withStyle(s -> s
					.withColor(ChatFormatting.GREEN).withBold(true)
					.withClickEvent(new net.minecraft.network.chat.ClickEvent.RunCommand(order))
					.withHoverEvent(new net.minecraft.network.chat.HoverEvent.ShowText(
							Texts.t(texts, m.text() + ".ayuda", timeTrialWaves)))));
			line.append(" ");
		}
		p.sendSystemMessage(Texts.t(texts, "heraldia.arena.modo.elige").withStyle(ChatFormatting.GOLD));
		p.sendSystemMessage(line);
		LOGGER.info("Heraldia: arena: {} elige modo ({})", p.getGameProfile().name(),
				String.join(", ", modes().stream().map(Mode::id).toList()));
	}

	/** Empieza la cuenta atrás de una partida cooperativa (/heraldia arena start sin modo). */
	static boolean start(ServerLevel level, Zone z, String who) {
		return start(level, z, who, Mode.COOP);
	}

	/** Empieza la cuenta atrás (con la campana o con /heraldia arena start [modo]). Falso si ya hay partida. */
	static boolean start(ServerLevel level, Zone z, String who, Mode mode) {
		if (!match.start(mode, timeTrialWaves)) {
			return false;
		}
		NAMES.clear();
		gate(level, z, true);
		LOGGER.info("Heraldia: arena: cuenta atrás (la empieza {}, modo {}{})", who, mode.id(),
				mode == Mode.TIME_TRIAL ? ", " + match.target() + " oleadas" : "");
		for (ServerPlayer p : inRing(level, z)) {
			title(p, Component.literal(String.valueOf(match.seconds())).withStyle(ChatFormatting.GOLD),
					Texts.t("heraldia.arena.cuenta"));
		}
		level.playSound(null, z.centerX(), z.minY() + 2, z.centerZ(), SoundEvents.RAID_HORN.value(), SoundSource.HOSTILE, 2f, 1f);
		return true;
	}

	/** Acaba la partida: quita sus mobs, abre la puerta, quita la barra y avisa. */
	static void finish(@Nullable ServerLevel level, @Nullable Zone z, String reason) {
		if (match.state() == Match.State.FREE) {
			return;
		}
		int cleared = match.cleared();
		Mode mode = match.mode();
		boolean completed = match.completed();
		long time = match.clearedTicks();
		MinecraftServer server = level != null ? level.getServer() : Arena.arenaServer();
		if (match.inGame() && server != null) {
			for (UUID u : match.participants()) {
				mark(server, u);                 // los que siguen en el ruedo (los que salieron ya tienen la suya)
			}
		}
		for (Mob m : MOBS.values()) {
			m.discard();
		}
		MOBS.clear();
		if (level != null && z != null) {
			// también los que se hubieran quedado fuera de la cuenta (refuerzos, mobs recargados)
			for (Mob m : level.getEntitiesOfClass(Mob.class, box(z), m -> m.entityTags().contains(Arena.TAG))) {
				m.discard();
			}
			gate(level, z, false);
			Component end = (completed ? Texts.t("heraldia.arena.fin.contrarreloj", cleared, Marks.time(time))
					: mode == Mode.TIME_TRIAL ? Texts.t("heraldia.arena.fin.contrarreloj.no", cleared, match.target())
					: Texts.t("heraldia.arena.fin", cleared)).withStyle(ChatFormatting.GOLD);
			for (ServerPlayer p : level.players()) {
				if (z.near(p.getBlockX(), p.getBlockY(), p.getBlockZ(), BAR_RADIUS)) {
					p.sendSystemMessage(end);
				}
			}
			ArenaScoreboard.hide(level.getServer());
		}
		if (bar != null) {
			bar.removeAllPlayers();
			bar = null;
		}
		match.finish();
		NAMES.clear();
		LOGGER.info("Heraldia: arena: partida terminada ({}) con {} oleadas superadas (modo {}, {} ticks)", reason, cleared,
				mode.id(), time);
	}

	/**
	 * La marca de un participante al acabar su partida (al caer, salir o terminarse): oleadas superadas y su tiempo, a la
	 * clasificación de la semana ({@link Fame}); sus logros del modo. Nada si no superó ninguna.
	 */
	private static void mark(MinecraftServer server, UUID u) {
		int waves = match.cleared();
		if (waves <= 0) {
			return;
		}
		String name = NAMES.getOrDefault(u, u.toString());
		Season.Entry e = new Season.Entry(u, name, waves, match.clearedTicks(), System.currentTimeMillis(),
				match.target());
		Fame.register(server, match.mode(), e);
		ServerPlayer p = server.getPlayerList().getPlayer(u);
		if (p != null) {
			for (String advancement : Marks.advancements(match.mode(), waves, match.clearedTicks(), match.target())) {
				Fame.grant(server, p, advancement);
			}
		}
	}

	// --- cada tick ---

	static void tick(MinecraftServer server) {
		if (match.state() == Match.State.FREE) {
			return;
		}
		Zone z = Arena.zone();
		ServerLevel level = Arena.arenaLevel();
		if (z == null || level == null) {
			finish(null, null, "sin arena");
			return;
		}
		boolean counted = match.state() == Match.State.COUNTDOWN;
		switch (match.tick()) {
			case SECOND -> second(level, z, counted);
			case WAVE_STARTS -> {
				if (counted && !matchStarts(level, z)) {
					return;
				}
				waveStarts(level, z);
			}
			case NOTHING -> {
			}
		}
		int t = server.getTickCount();
		if (match.state() == Match.State.WAVE && t % SPAWN_EVERY == 0) {
			spawn(level, z);
		}
		if (t % SWEEP_EVERY == 0) {
			sweep(server, level, z);
		}
	}

	private static void second(ServerLevel level, Zone z, boolean counted) {
		if (!counted && match.mode() != Mode.COOP) {
			return;                          // pausas cortas o sin pausa: sin aviso por segundo
		}
		int s = match.seconds();
		for (ServerPlayer p : inRing(level, z)) {
			if (counted) {
				title(p, Component.literal(String.valueOf(s)).withStyle(ChatFormatting.GOLD), Texts.t("heraldia.arena.cuenta"));
			} else {
				p.sendOverlayMessage(Texts.t("heraldia.arena.oleada.siguiente", s));
			}
		}
		if (counted) {
			level.playSound(null, z.centerX(), z.minY() + 2, z.centerZ(), SoundEvents.NOTE_BLOCK_HAT.value(), SoundSource.BLOCKS, 2f, 1f);
		}
	}

	/** Fin de la cuenta atrás: juegan los que están en el ruedo. Falso (y se acaba) si no hay nadie. */
	private static boolean matchStarts(ServerLevel level, Zone z) {
		List<UUID> inside = inRing(level, z).stream().map(Entity::getUUID).toList();
		if (!match.participants(inside)) {
			match.finish();      // vuelve a LIBRE sin oleadas
			gate(level, z, false);
			for (ServerPlayer p : level.players()) {
				if (z.near(p.getBlockX(), p.getBlockY(), p.getBlockZ(), BAR_RADIUS)) {
					p.sendOverlayMessage(Texts.t("heraldia.arena.sin_participantes"));
				}
			}
			LOGGER.info("Heraldia: arena: nadie en el ruedo al acabar la cuenta atrás");
			return false;
		}
		if (match.mode() == Mode.COOP) {
			ArenaScoreboard.show(level.getServer());   // el marcador vanilla es el récord del cooperativo
		}
		for (ServerPlayer p : inRing(level, z)) {
			NAMES.put(p.getUUID(), p.getGameProfile().name());
		}
		LOGGER.info("Heraldia: arena: partida empieza con {} participantes (modo {})", inside.size(), match.mode().id());
		return true;
	}

	private static void waveStarts(ServerLevel level, Zone z) {
		int n = match.wave();
		leftPlayers = 0;
		xpVanilla = xpGiven = 0;
		Component sub = match.mode() == Mode.TIME_TRIAL ? Texts.t("heraldia.arena.oleada.de", n, match.target())
				: Waves.withBoss(n)
				? Texts.t("heraldia.arena.oleada.jefe", Texts.t("heraldia.arena.jefe." + Waves.boss(n).index()))
				: Texts.t("heraldia.arena.oleada.mobs", match.total());
		for (ServerPlayer p : participants(level)) {
			title(p, (n == 1 ? Texts.t("heraldia.arena.lucha") : Texts.t("heraldia.arena.oleada", n)).withStyle(ChatFormatting.RED),
					n == 1 ? Texts.t("heraldia.arena.oleada", n) : sub);
		}
		level.playSound(null, z.centerX(), z.minY() + 2, z.centerZ(), SoundEvents.RAID_HORN.value(), SoundSource.HOSTILE, 2f, 1.2f);
		LOGGER.info("Heraldia: arena: oleada {}: {} enemigos ({}), vida y daño x{}", n, match.total(), Waves.batch(n),
				String.format(java.util.Locale.ROOT, "%.2f", Waves.stats(n, statsPct)));
	}

	/** Saca la siguiente tanda (sin pasar de arena.max_mobs_vivos vivos). */
	private static void spawn(ServerLevel level, Zone z) {
		int n = match.spawn(maxAlive);
		if (n == 0) {
			return;
		}
		int wave = match.wave();
		List<String> types = Waves.types(wave, mobsPct);
		List<ServerPlayer> players = participants(level);
		int finished = 0;
		for (int i = 0; i < n; i++) {
			boolean boss = match.takeBoss();
			String type = boss ? Waves.boss(wave).mob() : types.get(Math.min(leftPlayers++, types.size() - 1));
			int[] p = z.point(level.getRandom().nextInt(z.points()));
			if (create(level, type, p, wave, boss, players)) {
				finished++;
			} else {
				match.fail();
			}
		}
		LOGGER.info("Heraldia: arena: salen {} enemigos ({} vivos, {} por salir)", finished, match.alive(), match.pending());
	}

	private static boolean create(ServerLevel level, String type, int[] p, int wave, boolean boss, List<ServerPlayer> players) {
		Identifier id = Identifier.tryParse(type);
		EntityType<?> et = id == null ? null : BuiltInRegistries.ENTITY_TYPE.getOptional(id).orElse(null);
		if (et == null || !(et.create(level, EntitySpawnReason.STRUCTURE) instanceof Mob mob)) {
			LOGGER.warn("Heraldia: arena: mob {} desconocido", type);
			return false;
		}
		// Antes de finalizeSpawn, como los refuerzos de los jefes: adultos (ZombieMixin...) y con la etiqueta de la arena
		mob.addTag(Arena.TAG);
		mob.addTag(Heraldia.ADULT);
		if (boss) {
			mob.addTag(Phases.GUARDIAN);          // fases, refuerzos y barra de los jefes (jefes/)
		}
		double x = p[0] + 0.5, y = p[1], zz = p[2] + 0.5;
		mob.snapTo(x, y, zz, level.getRandom().nextFloat() * 360f, 0f);
		mob.finalizeSpawn(level, level.getCurrentDifficultyAt(BlockPos.containing(x, y, zz)), EntitySpawnReason.STRUCTURE, null);
		mob.ejectPassengers();
		mob.stopRiding();
		if (boss) {
			Waves.Boss j = Waves.boss(wave);
			Item weapon = BuiltInRegistries.ITEM.getOptional(Identifier.parse(j.weapon())).orElse(Items.IRON_SWORD);
			mob.setItemSlot(EquipmentSlot.MAINHAND, new ItemStack(weapon));
			mob.setCustomName(Texts.t("heraldia.arena.jefe." + j.index()).withStyle(ChatFormatting.RED));
			mob.setCustomNameVisible(true);
		}
		prepare(mob, wave, boss);
		if (!NO_SUN.contains(type) && mob.getItemBySlot(EquipmentSlot.HEAD).isEmpty()) {
			mob.setItemSlot(EquipmentSlot.HEAD, new ItemStack(Items.IRON_HELMET));    // que no ardan al sol
		}
		ServerPlayer target = nearest(mob, players);
		if (target != null) {
			mob.setTarget(target);
		}
		MOBS.put(mob.getUUID(), mob);
		if (!level.addFreshEntity(mob)) {
			MOBS.remove(mob.getUUID());
			return false;
		}
		level.sendParticles(ParticleTypes.LARGE_SMOKE, x, y + 0.8, zz, 12, 0.3, 0.6, 0.3, 0.02);
		level.sendParticles(ParticleTypes.FLAME, x, y + 0.2, zz, 8, 0.3, 0.1, 0.3, 0.02);
		if (boss) {
			level.playSound(null, x, y, zz, SoundEvents.RAVAGER_ROAR, SoundSource.HOSTILE, 2f, 0.8f);
			LOGGER.info("Heraldia: arena: mini-jefe {} en la oleada {} (vida {})", type, wave, mob.getMaxHealth());
		}
		return true;
	}

	/** Vida y daño de la oleada (y del mini-jefe), sin soltar nada y sin desaparecer. */
	private static void prepare(Mob mob, int wave, boolean boss) {
		double mod = Waves.modifier(wave, statsPct);
		MobDifficulty.put(mob.getAttribute(Attributes.MAX_HEALTH), HEALTH, mod);
		MobDifficulty.put(mob.getAttribute(Attributes.ATTACK_DAMAGE), DAMAGE, mod);
		if (boss) {
			MobDifficulty.put(mob.getAttribute(Attributes.MAX_HEALTH), BOSS_HEALTH, Waves.BOSS_HEALTH);
			MobDifficulty.put(mob.getAttribute(Attributes.ATTACK_DAMAGE), BOSS_DAMAGE, Waves.BOSS_DAMAGE);
		}
		mob.setHealth(mob.getMaxHealth());
		for (EquipmentSlot s : EquipmentSlot.values()) {
			mob.setDropChance(s, 0f);
		}
		mob.setCanPickUpLoot(false);
		mob.setPersistenceRequired();
	}

	/** Una vez por segundo: participantes, mobs (fuera del ruedo, muertos sin aviso, sin objetivo) y barra. */
	private static void sweep(MinecraftServer server, ServerLevel level, Zone z) {
		if (match.inGame()) {
			for (UUID u : match.participants()) {
				ServerPlayer p = server.getPlayerList().getPlayer(u);
				if (p == null || p.isRemoved() || !p.isAlive() || p.level() != level || p.isSpectator()
						|| !z.inRing(p.getX(), p.getY(), p.getZ())) {
					if (p != null && p.isAlive()) {
						warn(level, z, Texts.t("heraldia.arena.sale", p.getDisplayName()));
					}
					outcome(level, z, u, p == null ? u.toString() : p.getGameProfile().name(), "sale");
					if (match.state() == Match.State.FREE) {
						return;
					}
				}
			}
		}
		List<ServerPlayer> players = participants(level);
		for (Mob m : List.copyOf(MOBS.values())) {
			if (m.isRemoved()) {
				Entity.RemovalReason r = m.getRemovalReason();
				if (r == Entity.RemovalReason.UNLOADED_TO_CHUNK || r == Entity.RemovalReason.UNLOADED_WITH_PLAYER) {
					continue;                 // sigue en su chunk: vuelve con ENTITY_LOAD
				}
				MOBS.remove(m.getUUID());     // quitado sin morir (no debería pasar): cuenta como uno menos
				if (match.dies()) {
					cleared(level, z);
					if (match.state() == Match.State.FREE) {
						return;                   // el contrarreloj acabó con esta oleada
					}
				}
				continue;
			}
			if (!m.isAlive()) {
				continue;                     // muriendo: AFTER_DEATH lo cuenta
			}
			if (!z.inRing(m.getX(), m.getY(), m.getZ())) {
				int[] p = z.point(level.getRandom().nextInt(z.points()));
				m.teleportTo(p[0] + 0.5, p[1], p[2] + 0.5);
				LOGGER.info("Heraldia: arena: un mob se salió del ruedo y vuelve a su punto");
			}
			if (m.getTarget() == null || !m.getTarget().isAlive()) {
				ServerPlayer o = nearest(m, players);
				if (o != null) {
					m.setTarget(o);
				}
			}
		}
		bar(level, z);
	}

	private static void bar(ServerLevel level, Zone z) {
		if (bar == null) {
			bar = new ServerBossEvent(UUID.randomUUID(), Component.empty(), BossEvent.BossBarColor.RED,
					BossEvent.BossBarOverlay.PROGRESS);
		}
		switch (match.state()) {
			case COUNTDOWN -> {
				bar.setName(Texts.t("heraldia.arena.barra.cuenta", match.seconds()));
				bar.setProgress(1f);
				bar.setColor(BossEvent.BossBarColor.YELLOW);
			}
			case PAUSE -> {
				bar.setName(Texts.t("heraldia.arena.barra.pausa", match.wave()));
				bar.setProgress(1f);
				bar.setColor(BossEvent.BossBarColor.GREEN);
			}
			default -> {
				bar.setName(switch (match.mode()) {
					case TIME_TRIAL -> Texts.t("heraldia.arena.barra.contrarreloj", match.wave(), match.target(),
							match.remaining(), Marks.time(match.ticks()));
					case SURVIVAL -> Texts.t("heraldia.arena.barra.supervivencia", match.wave(), match.remaining());
					default -> Texts.t("heraldia.arena.barra", match.wave(), match.remaining());
				});
				bar.setProgress(match.total() > 0 ? Math.clamp((float) match.remaining() / match.total(), 0f, 1f) : 0f);
				bar.setColor(Waves.withBoss(match.wave()) ? BossEvent.BossBarColor.PURPLE : BossEvent.BossBarColor.RED);
			}
		}
		int before = bar.getPlayers().size();
		for (ServerPlayer p : level.players()) {
			if (z.near(p.getBlockX(), p.getBlockY(), p.getBlockZ(), BAR_RADIUS)) {
				bar.addPlayer(p);
			} else {
				bar.removePlayer(p);
			}
		}
		for (ServerPlayer p : List.copyOf(bar.getPlayers())) {
			if (p.level() != level || p.hasDisconnected()) {
				bar.removePlayer(p);
			}
		}
		if (bar.getPlayers().size() != before) {
			LOGGER.info("Heraldia: arena: barra para {} jugadores ({})", bar.getPlayers().size(), bar.getName().getString());
		}
	}

	// --- eventos ---

	/** Muere una entidad: un mob de la partida (cuenta) o un participante (cae). */
	static void onDeath(LivingEntity e) {
		Zone z = Arena.zone();
		ServerLevel level = Arena.arenaLevel();
		if (match.state() == Match.State.FREE || z == null || level == null) {
			return;
		}
		if (e instanceof Mob m && MOBS.remove(m.getUUID()) != null) {
			if (match.dies()) {
				cleared(level, z);
			}
		} else if (e instanceof ServerPlayer p && match.participates(p.getUUID())) {
			warn(level, z, Texts.t("heraldia.arena.cae", p.getDisplayName(), match.wave()));
			outcome(level, z, p.getUUID(), p.getGameProfile().name(), "cae");
		}
	}

	/** Al cargarse una entidad: los mobs de la arena que no son de esta partida se quitan; los refuerzos del mini-jefe se suman. */
	static void onLoad(Entity e, ServerLevel level) {
		if (!(e instanceof Mob m)) {
			return;
		}
		Set<String> tags = m.entityTags();
		if (tags.isEmpty()) {
			return;
		}
		if (tags.contains(Arena.TAG)) {
			Mob ours = MOBS.get(m.getUUID());
			if (ours == null) {
				m.discard();
				LOGGER.info("Heraldia: arena: quitado un mob de arena de una partida anterior ({})",
						BuiltInRegistries.ENTITY_TYPE.getKey(m.getType()).getPath());
			} else if (ours != m) {
				MOBS.put(m.getUUID(), m);     // se recargó su chunk
			}
			return;
		}
		Zone z = Arena.zone();
		if (tags.contains(Phases.REINFORCEMENT) && match.state() == Match.State.WAVE && z != null && level == Arena.arenaLevel()
				&& z.inRing(m.getX(), m.getY(), m.getZ())) {
			m.addTag(Arena.TAG);
			prepare(m, match.wave(), false);
			MOBS.put(m.getUUID(), m);
			match.extra();
			LOGGER.info("Heraldia: arena: un refuerzo del mini-jefe entra en la oleada");
		}
	}

	private static void outcome(ServerLevel level, Zone z, UUID u, String name, String as) {
		LOGGER.info("Heraldia: arena: {} {} en la oleada {}", name, as, match.wave());
		if (match.participates(u) && match.inGame()) {
			mark(level.getServer(), u);
		}
		if (match.outcome(u)) {
			finish(level, z, "sin participantes");
		}
	}

	/** Se supera la oleada: récords, recompensas, logros y pausa. */
	private static void cleared(ServerLevel level, Zone z) {
		int n = match.wave();
		LOGGER.info("Heraldia: arena: oleada {} superada (experiencia: {} de vanilla, {} dada, al {} %)", n, xpVanilla, xpGiven, xpPct);
		int tier = Waves.reward(n);
		Component sub = match.completed() ? Texts.t("heraldia.arena.tiempo", Marks.time(match.clearedTicks()))
				: match.mode() == Mode.SURVIVAL ? Texts.t("heraldia.arena.sin_pausa")
				: Texts.t("heraldia.arena.oleada.siguiente", match.seconds());
		for (ServerPlayer p : participants(level)) {
			title(p, Texts.t("heraldia.arena.oleada.superada", n).withStyle(ChatFormatting.GREEN), sub);
			if (match.mode() == Mode.COOP) {
				ArenaScoreboard.cleared(level.getServer(), p, n);   // el récord de siempre (marcador vanilla), solo del cooperativo
			}
			io.github.albertosa23.heraldia.quests.Quests.waveCleared(p, n);   // encargos del tablón (T38)
			if (tier > 0) {
				reward(level, p, n, tier);
			}
			if (Waves.advancement(n)) {
				AdvancementHolder a = level.getServer().getAdvancements().get(Heraldia.id("arena/oleada_" + n));
				if (a != null) {
					p.getAdvancements().award(a, "oleada");
				}
			}
		}
		level.playSound(null, z.centerX(), z.minY() + 2, z.centerZ(), SoundEvents.PLAYER_LEVELUP, SoundSource.PLAYERS, 1.5f, 1f);
		if (match.completed()) {
			LOGGER.info("Heraldia: arena: contrarreloj completado: {} oleadas en {} ticks ({})", n, match.clearedTicks(),
					Marks.time(match.clearedTicks()));
			finish(level, z, "contrarreloj completado");
		}
	}

	private static void reward(ServerLevel level, ServerPlayer p, int wave, int tier) {
		ResourceKey<LootTable> key = ResourceKey.create(Registries.LOOT_TABLE, Heraldia.id("arena/recompensa_" + tier));
		LootTable table = level.getServer().reloadableRegistries().getLootTable(key);
		LootParams params = new LootParams.Builder(level).withParameter(LootContextParams.ORIGIN, p.position())
				.withParameter(LootContextParams.THIS_ENTITY, p).create(LootContextParamSets.CHEST);
		int n = 0;
		for (ItemStack s : table.getRandomItems(params)) {
			KeyCommand.give(p, s);
			n++;
		}
		p.sendSystemMessage(Texts.t("heraldia.arena.recompensa", wave).withStyle(ChatFormatting.GOLD));
		LOGGER.info("Heraldia: arena: recompensa {} ({} objetos) para {} en la oleada {}", tier, n, p.getGameProfile().name(), wave);
	}

	// --- muerte en el ruedo: se conserva el inventario y la experiencia ---

	/** Llamado por PlayerArenaMixin al soltar el equipo al morir: ¿lo conserva? (cae en el ruedo durante una partida). */
	static boolean keepsOnDeath(Player player) {
		Zone z = Arena.zone();
		if (!(player instanceof ServerPlayer p) || z == null || p.level() != Arena.arenaLevel() || !match.inGame()
				|| !match.participates(p.getUUID()) || !z.inRing(p.getX(), p.getY(), p.getZ())) {
			if (player.hasAttached(Saved.Type.KEEP)) {
				player.removeAttached(Saved.Type.KEEP);   // de una caída anterior sin reaparición vanilla
			}
			return false;
		}
		p.setAttached(Saved.Type.KEEP, Boolean.TRUE);
		LOGGER.info("Heraldia: arena: {} cae en el ruedo y conserva su inventario y su experiencia", p.getGameProfile().name());
		return true;
	}

	/** ¿Está conservando (no suelta experiencia)? */
	static boolean keeping(Player player) {
		return Boolean.TRUE.equals(player.getAttached(Saved.Type.KEEP));
	}

	/** Al reaparecer (COPY_FROM): le devuelve lo que llevaba. */
	static void copy(ServerPlayer oldValue, ServerPlayer newValue, boolean alive) {
		if (alive || !keeping(oldValue)) {
			return;
		}
		newValue.getInventory().replaceWith(oldValue.getInventory());
		newValue.experienceLevel = oldValue.experienceLevel;
		newValue.totalExperience = oldValue.totalExperience;
		newValue.experienceProgress = oldValue.experienceProgress;
		newValue.removeAttached(Saved.Type.KEEP);
		RESPAWN.add(newValue.getUUID());
		newValue.sendSystemMessage(Texts.t("heraldia.arena.conservado").withStyle(ChatFormatting.GOLD));
	}

	/** Tras reaparecer: a la entrada de la arena. */
	static void respawn(ServerPlayer newValue) {
		Zone z = Arena.zone();
		ServerLevel level = Arena.arenaLevel();
		if (!RESPAWN.remove(newValue.getUUID()) || z == null || level == null) {
			return;
		}
		int[] r = z.respawn();
		newValue.teleportTo(level, r[0] + 0.5, r[1], r[2] + 0.5, Set.of(), 180f, 0f, false);
		LOGGER.info("Heraldia: arena: {} reaparece en la entrada de la arena", newValue.getGameProfile().name());
	}

	/** /heraldia arena leave. */
	static boolean leave(ServerPlayer p) {
		Zone z = Arena.zone();
		ServerLevel level = Arena.arenaLevel();
		if (z == null || level == null || !match.participates(p.getUUID())) {
			return false;
		}
		int[] r = z.respawn();
		p.teleportTo(level, r[0] + 0.5, r[1], r[2] + 0.5, Set.of(), 180f, 0f, false);
		warn(level, z, Texts.t("heraldia.arena.sale", p.getDisplayName()));
		outcome(level, z, p.getUUID(), p.getGameProfile().name(), "sale");
		return true;
	}

	// --- utilidades ---

	/** Cierra (rejas) o abre (aire) la puerta del ruedo. */
	static void gate(ServerLevel level, Zone z, boolean close) {
		int[] a = z.gateMin(), b = z.gateMax();
		BlockState s = close ? Blocks.IRON_BARS.defaultBlockState() : Blocks.AIR.defaultBlockState();
		BlockPos.MutableBlockPos pos = new BlockPos.MutableBlockPos();
		for (int x = a[0]; x <= b[0]; x++) {
			for (int y = a[1]; y <= b[1]; y++) {
				for (int zz = a[2]; zz <= b[2]; zz++) {
					BlockState actual = level.getBlockState(pos.set(x, y, zz));
					if (close ? actual.isAir() : actual.is(Blocks.IRON_BARS)) {
						level.setBlock(pos, s, net.minecraft.world.level.block.Block.UPDATE_ALL);
					}
				}
			}
		}
		level.playSound(null, (a[0] + b[0]) / 2.0 + 0.5, a[1], (a[2] + b[2]) / 2.0 + 0.5,
				close ? SoundEvents.IRON_DOOR_CLOSE : SoundEvents.IRON_DOOR_OPEN, SoundSource.BLOCKS, 1.5f, 0.8f);
	}

	static AABB box(Zone z) {
		return new AABB(z.minX(), z.minY(), z.minZ(), z.maxX() + 1, z.maxY() + 1, z.maxZ() + 1);
	}

	static List<ServerPlayer> inRing(ServerLevel level, Zone z) {
		List<ServerPlayer> out = new ArrayList<>();
		for (ServerPlayer p : level.players()) {
			if (!p.isSpectator() && p.isAlive() && z.inRing(p.getX(), p.getY(), p.getZ())) {
				out.add(p);
			}
		}
		return out;
	}

	private static List<ServerPlayer> participants(ServerLevel level) {
		List<ServerPlayer> out = new ArrayList<>();
		for (UUID u : match.participants()) {
			ServerPlayer p = level.getServer().getPlayerList().getPlayer(u);
			if (p != null && p.isAlive()) {
				out.add(p);
			}
		}
		return out;
	}

	private static @Nullable ServerPlayer nearest(Mob m, List<ServerPlayer> players) {
		ServerPlayer best = null;
		double d = Double.MAX_VALUE;
		for (ServerPlayer p : players) {
			double dd = p.distanceToSqr(m);
			if (dd < d && p.canBeSeenAsEnemy()) {
				d = dd;
				best = p;
			}
		}
		return best;
	}

	private static void warn(ServerLevel level, Zone z, Component c) {
		for (ServerPlayer p : level.players()) {
			if (z.near(p.getBlockX(), p.getBlockY(), p.getBlockZ(), BAR_RADIUS)) {
				p.sendSystemMessage(c);
			}
		}
	}

	static void title(ServerPlayer p, Component title, Component subtitle) {
		p.connection.send(new ClientboundSetTitlesAnimationPacket(5, 30, 10));
		p.connection.send(new ClientboundSetSubtitleTextPacket(subtitle));
		p.connection.send(new ClientboundSetTitleTextPacket(title));
	}

	/** Al pararse el servidor: la partida se acaba limpia (mobs fuera, puerta abierta). */
	static void onStop() {
		finish(Arena.arenaLevel(), Arena.zone(), "el servidor se para");
		RESPAWN.clear();
	}
}
