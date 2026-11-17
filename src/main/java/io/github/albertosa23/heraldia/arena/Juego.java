package io.github.albertosa23.heraldia.arena;

import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.comando.LlaveCommand;
import io.github.albertosa23.heraldia.comando.Textos;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.dificultad.DificultadMobs;
import io.github.albertosa23.heraldia.jefes.Fases;
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
 * La partida en marcha: mueve la {@link Partida} cada tick (salida temprana si no hay ninguna), saca los mobs por
 * tandas en los puntos de aparición, los mantiene en el ruedo, lleva la barra de jefe, los títulos, los récords
 * ({@link Marcador}), las recompensas y los logros, y cierra y abre la puerta del ruedo. Los mobs de la arena llevan la
 * etiqueta {@link Arena#TAG}; solo cuentan los de esta partida (en memoria): los demás se quitan al cargarse.
 */
final class Juego {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	/** Modificadores propios (se suman a los de la dificultad y los jefes sin pisarlos). */
	static final Identifier VIDA = Heraldia.id("arena_vida"), DANO = Heraldia.id("arena_dano"),
			JEFE_VIDA = Heraldia.id("arena_jefe_vida"), JEFE_DANO = Heraldia.id("arena_jefe_dano");
	private static final int CADA_APARICION = 10, CADA_REPASO = 20, RADIO_BARRA = 24;
	private static final Set<String> SIN_SOL = Set.of("minecraft:husk", "minecraft:creeper", "minecraft:spider",
			"minecraft:cave_spider", "minecraft:vindicator", "minecraft:witch", "minecraft:wither_skeleton");

	private static Partida partida = new Partida(50);
	private static final Map<UUID, Mob> MOBS = new HashMap<>();
	/** Jugadores que reaparecen en la arena (cayeron en el ruedo); en memoria, se usa en el mismo tick. */
	private static final Set<UUID> REAPARECER = new HashSet<>();
	private static @Nullable ServerBossEvent barra;
	private static int salidos;
	/** Experiencia de la oleada en curso: la que daría vanilla y la que se da (para el log). */
	private static long xpVanilla, xpDada;
	private static int mobsPct = 50, statsPct = 10, maxVivos = 20, xpPct = 15;

	private Juego() {
	}

	/** Lee la configuración (al arrancar) y deja la arena sin partida. */
	static void configurar(HeraldiaConfig cfg) {
		mobsPct = cfg.getInt("arena.oleada.mobs_incremento");
		int pedido = cfg.getInt("arena.oleada.stats_incremento");
		statsPct = Oleadas.statsEfectivo(mobsPct, pedido);
		if (statsPct != pedido) {
			LOGGER.warn("Heraldia: arena: arena.oleada.stats_incremento={} es mayor que mobs_incremento={}: se usa {} "
					+ "(los mobs crecen más que su vida y daño)", pedido, mobsPct, statsPct);
		}
		maxVivos = cfg.getInt("arena.max_mobs_vivos");
		xpPct = cfg.getInt("arena.experiencia_porcentaje");
		partida = new Partida(mobsPct);
		MOBS.clear();
	}

	static Partida partida() {
		return partida;
	}

	static int experienciaPct() {
		return xpPct;
	}

	static void sumarExperiencia(int vanilla, int dada) {
		xpVanilla += vanilla;
		xpDada += dada;
	}

	// --- empezar y acabar ---

	/** Alguien toca la campana. */
	static void campana(ServerPlayer p, Zona z) {
		if (partida.estado() != Partida.Estado.LIBRE) {
			p.sendOverlayMessage(Textos.t("heraldia.arena.en_marcha"));
			return;
		}
		empezar((ServerLevel) p.level(), z, p.getGameProfile().name());
	}

	/** Empieza la cuenta atrás (con la campana o con /heraldia arena start). Falso si ya hay partida. */
	static boolean empezar(ServerLevel level, Zona z, String quien) {
		if (!partida.empezar()) {
			return false;
		}
		puerta(level, z, true);
		LOGGER.info("Heraldia: arena: cuenta atrás (la empieza {})", quien);
		for (ServerPlayer p : enRuedo(level, z)) {
			titulo(p, Component.literal(String.valueOf(partida.segundos())).withStyle(ChatFormatting.GOLD),
					Textos.t("heraldia.arena.cuenta"));
		}
		level.playSound(null, z.centroX(), z.minY() + 2, z.centroZ(), SoundEvents.RAID_HORN.value(), SoundSource.HOSTILE, 2f, 1f);
		return true;
	}

	/** Acaba la partida: quita sus mobs, abre la puerta, quita la barra y avisa. */
	static void terminar(@Nullable ServerLevel level, @Nullable Zona z, String motivo) {
		if (partida.estado() == Partida.Estado.LIBRE) {
			return;
		}
		int superadas = partida.superadas();
		for (Mob m : MOBS.values()) {
			m.discard();
		}
		MOBS.clear();
		if (level != null && z != null) {
			// también los que se hubieran quedado fuera de la cuenta (refuerzos, mobs recargados)
			for (Mob m : level.getEntitiesOfClass(Mob.class, caja(z), m -> m.entityTags().contains(Arena.TAG))) {
				m.discard();
			}
			puerta(level, z, false);
			Component fin = Textos.t("heraldia.arena.fin", superadas).withStyle(ChatFormatting.GOLD);
			for (ServerPlayer p : level.players()) {
				if (z.cerca(p.getBlockX(), p.getBlockY(), p.getBlockZ(), RADIO_BARRA)) {
					p.sendSystemMessage(fin);
				}
			}
			Marcador.ocultar(level.getServer());
		}
		if (barra != null) {
			barra.removeAllPlayers();
			barra = null;
		}
		partida.terminar();
		LOGGER.info("Heraldia: arena: partida terminada ({}) con {} oleadas superadas", motivo, superadas);
	}

	// --- cada tick ---

	static void tick(MinecraftServer server) {
		if (partida.estado() == Partida.Estado.LIBRE) {
			return;
		}
		Zona z = Arena.zona();
		ServerLevel level = Arena.nivel();
		if (z == null || level == null) {
			terminar(null, null, "sin arena");
			return;
		}
		boolean enCuenta = partida.estado() == Partida.Estado.CUENTA_ATRAS;
		switch (partida.tick()) {
			case SEGUNDO -> segundo(level, z, enCuenta);
			case EMPIEZA_OLEADA -> {
				if (enCuenta && !empiezaPartida(level, z)) {
					return;
				}
				empiezaOleada(level, z);
			}
			case NADA -> {
			}
		}
		int t = server.getTickCount();
		if (partida.estado() == Partida.Estado.OLEADA && t % CADA_APARICION == 0) {
			aparecer(level, z);
		}
		if (t % CADA_REPASO == 0) {
			repasar(server, level, z);
		}
	}

	private static void segundo(ServerLevel level, Zona z, boolean enCuenta) {
		int s = partida.segundos();
		for (ServerPlayer p : enRuedo(level, z)) {
			if (enCuenta) {
				titulo(p, Component.literal(String.valueOf(s)).withStyle(ChatFormatting.GOLD), Textos.t("heraldia.arena.cuenta"));
			} else {
				p.sendOverlayMessage(Textos.t("heraldia.arena.oleada.siguiente", s));
			}
		}
		if (enCuenta) {
			level.playSound(null, z.centroX(), z.minY() + 2, z.centroZ(), SoundEvents.NOTE_BLOCK_HAT.value(), SoundSource.BLOCKS, 2f, 1f);
		}
	}

	/** Fin de la cuenta atrás: juegan los que están en el ruedo. Falso (y se acaba) si no hay nadie. */
	private static boolean empiezaPartida(ServerLevel level, Zona z) {
		List<UUID> dentro = enRuedo(level, z).stream().map(Entity::getUUID).toList();
		if (!partida.participantes(dentro)) {
			partida.terminar();      // vuelve a LIBRE sin oleadas
			puerta(level, z, false);
			for (ServerPlayer p : level.players()) {
				if (z.cerca(p.getBlockX(), p.getBlockY(), p.getBlockZ(), RADIO_BARRA)) {
					p.sendOverlayMessage(Textos.t("heraldia.arena.sin_participantes"));
				}
			}
			LOGGER.info("Heraldia: arena: nadie en el ruedo al acabar la cuenta atrás");
			return false;
		}
		Marcador.mostrar(level.getServer());
		LOGGER.info("Heraldia: arena: partida empieza con {} participantes", dentro.size());
		return true;
	}

	private static void empiezaOleada(ServerLevel level, Zona z) {
		int n = partida.oleada();
		salidos = 0;
		xpVanilla = xpDada = 0;
		Component sub = Oleadas.conJefe(n)
				? Textos.t("heraldia.arena.oleada.jefe", Textos.t("heraldia.arena.jefe." + Oleadas.jefe(n).indice()))
				: Textos.t("heraldia.arena.oleada.mobs", partida.total());
		for (ServerPlayer p : participantes(level)) {
			titulo(p, (n == 1 ? Textos.t("heraldia.arena.lucha") : Textos.t("heraldia.arena.oleada", n)).withStyle(ChatFormatting.RED),
					n == 1 ? Textos.t("heraldia.arena.oleada", n) : sub);
		}
		level.playSound(null, z.centroX(), z.minY() + 2, z.centroZ(), SoundEvents.RAID_HORN.value(), SoundSource.HOSTILE, 2f, 1.2f);
		LOGGER.info("Heraldia: arena: oleada {}: {} enemigos ({}), vida y daño x{}", n, partida.total(), Oleadas.tanda(n),
				String.format(java.util.Locale.ROOT, "%.2f", Oleadas.stats(n, statsPct)));
	}

	/** Saca la siguiente tanda (sin pasar de arena.max_mobs_vivos vivos). */
	private static void aparecer(ServerLevel level, Zona z) {
		int n = partida.aparecer(maxVivos);
		if (n == 0) {
			return;
		}
		int oleada = partida.oleada();
		List<String> tipos = Oleadas.tipos(oleada, mobsPct);
		List<ServerPlayer> jugadores = participantes(level);
		int hechos = 0;
		for (int i = 0; i < n; i++) {
			boolean jefe = partida.tomarJefe();
			String tipo = jefe ? Oleadas.jefe(oleada).mob() : tipos.get(Math.min(salidos++, tipos.size() - 1));
			int[] p = z.punto(level.getRandom().nextInt(z.puntos()));
			if (crear(level, tipo, p, oleada, jefe, jugadores)) {
				hechos++;
			} else {
				partida.fallo();
			}
		}
		LOGGER.info("Heraldia: arena: salen {} enemigos ({} vivos, {} por salir)", hechos, partida.vivos(), partida.pendientes());
	}

	private static boolean crear(ServerLevel level, String tipo, int[] p, int oleada, boolean jefe, List<ServerPlayer> jugadores) {
		Identifier id = Identifier.tryParse(tipo);
		EntityType<?> et = id == null ? null : BuiltInRegistries.ENTITY_TYPE.getOptional(id).orElse(null);
		if (et == null || !(et.create(level, EntitySpawnReason.STRUCTURE) instanceof Mob mob)) {
			LOGGER.warn("Heraldia: arena: mob {} desconocido", tipo);
			return false;
		}
		// Antes de finalizeSpawn, como los refuerzos de los jefes: adultos (ZombieMixin...) y con la etiqueta de la arena
		mob.addTag(Arena.TAG);
		mob.addTag(Heraldia.ADULTO);
		if (jefe) {
			mob.addTag(Fases.GUARDIAN);          // fases, refuerzos y barra de los jefes (jefes/)
		}
		double x = p[0] + 0.5, y = p[1], zz = p[2] + 0.5;
		mob.snapTo(x, y, zz, level.getRandom().nextFloat() * 360f, 0f);
		mob.finalizeSpawn(level, level.getCurrentDifficultyAt(BlockPos.containing(x, y, zz)), EntitySpawnReason.STRUCTURE, null);
		mob.ejectPassengers();
		mob.stopRiding();
		if (jefe) {
			Oleadas.Jefe j = Oleadas.jefe(oleada);
			Item arma = BuiltInRegistries.ITEM.getOptional(Identifier.parse(j.arma())).orElse(Items.IRON_SWORD);
			mob.setItemSlot(EquipmentSlot.MAINHAND, new ItemStack(arma));
			mob.setCustomName(Textos.t("heraldia.arena.jefe." + j.indice()).withStyle(ChatFormatting.RED));
			mob.setCustomNameVisible(true);
		}
		preparar(mob, oleada, jefe);
		if (!SIN_SOL.contains(tipo) && mob.getItemBySlot(EquipmentSlot.HEAD).isEmpty()) {
			mob.setItemSlot(EquipmentSlot.HEAD, new ItemStack(Items.IRON_HELMET));    // que no ardan al sol
		}
		ServerPlayer objetivo = cercano(mob, jugadores);
		if (objetivo != null) {
			mob.setTarget(objetivo);
		}
		MOBS.put(mob.getUUID(), mob);
		if (!level.addFreshEntity(mob)) {
			MOBS.remove(mob.getUUID());
			return false;
		}
		level.sendParticles(ParticleTypes.LARGE_SMOKE, x, y + 0.8, zz, 12, 0.3, 0.6, 0.3, 0.02);
		level.sendParticles(ParticleTypes.FLAME, x, y + 0.2, zz, 8, 0.3, 0.1, 0.3, 0.02);
		if (jefe) {
			level.playSound(null, x, y, zz, SoundEvents.RAVAGER_ROAR, SoundSource.HOSTILE, 2f, 0.8f);
			LOGGER.info("Heraldia: arena: mini-jefe {} en la oleada {} (vida {})", tipo, oleada, mob.getMaxHealth());
		}
		return true;
	}

	/** Vida y daño de la oleada (y del mini-jefe), sin soltar nada y sin desaparecer. */
	private static void preparar(Mob mob, int oleada, boolean jefe) {
		double mod = Oleadas.modificador(oleada, statsPct);
		DificultadMobs.poner(mob.getAttribute(Attributes.MAX_HEALTH), VIDA, mod);
		DificultadMobs.poner(mob.getAttribute(Attributes.ATTACK_DAMAGE), DANO, mod);
		if (jefe) {
			DificultadMobs.poner(mob.getAttribute(Attributes.MAX_HEALTH), JEFE_VIDA, Oleadas.JEFE_VIDA);
			DificultadMobs.poner(mob.getAttribute(Attributes.ATTACK_DAMAGE), JEFE_DANO, Oleadas.JEFE_DANO);
		}
		mob.setHealth(mob.getMaxHealth());
		for (EquipmentSlot s : EquipmentSlot.values()) {
			mob.setDropChance(s, 0f);
		}
		mob.setCanPickUpLoot(false);
		mob.setPersistenceRequired();
	}

	/** Una vez por segundo: participantes, mobs (fuera del ruedo, muertos sin aviso, sin objetivo) y barra. */
	private static void repasar(MinecraftServer server, ServerLevel level, Zona z) {
		if (partida.enJuego()) {
			for (UUID u : partida.participantes()) {
				ServerPlayer p = server.getPlayerList().getPlayer(u);
				if (p == null || p.isRemoved() || !p.isAlive() || p.level() != level || p.isSpectator()
						|| !z.enRuedo(p.getX(), p.getY(), p.getZ())) {
					if (p != null && p.isAlive()) {
						avisar(level, z, Textos.t("heraldia.arena.sale", p.getDisplayName()));
					}
					sale(level, z, u, p == null ? u.toString() : p.getGameProfile().name(), "sale");
					if (partida.estado() == Partida.Estado.LIBRE) {
						return;
					}
				}
			}
		}
		List<ServerPlayer> jugadores = participantes(level);
		for (Mob m : List.copyOf(MOBS.values())) {
			if (m.isRemoved()) {
				Entity.RemovalReason r = m.getRemovalReason();
				if (r == Entity.RemovalReason.UNLOADED_TO_CHUNK || r == Entity.RemovalReason.UNLOADED_WITH_PLAYER) {
					continue;                 // sigue en su chunk: vuelve con ENTITY_LOAD
				}
				MOBS.remove(m.getUUID());     // quitado sin morir (no debería pasar): cuenta como uno menos
				if (partida.muere()) {
					superada(level, z);
				}
				continue;
			}
			if (!m.isAlive()) {
				continue;                     // muriendo: AFTER_DEATH lo cuenta
			}
			if (!z.enRuedo(m.getX(), m.getY(), m.getZ())) {
				int[] p = z.punto(level.getRandom().nextInt(z.puntos()));
				m.teleportTo(p[0] + 0.5, p[1], p[2] + 0.5);
				LOGGER.info("Heraldia: arena: un mob se salió del ruedo y vuelve a su punto");
			}
			if (m.getTarget() == null || !m.getTarget().isAlive()) {
				ServerPlayer o = cercano(m, jugadores);
				if (o != null) {
					m.setTarget(o);
				}
			}
		}
		barra(level, z);
	}

	private static void barra(ServerLevel level, Zona z) {
		if (barra == null) {
			barra = new ServerBossEvent(UUID.randomUUID(), Component.empty(), BossEvent.BossBarColor.RED,
					BossEvent.BossBarOverlay.PROGRESS);
		}
		switch (partida.estado()) {
			case CUENTA_ATRAS -> {
				barra.setName(Textos.t("heraldia.arena.barra.cuenta", partida.segundos()));
				barra.setProgress(1f);
				barra.setColor(BossEvent.BossBarColor.YELLOW);
			}
			case PAUSA -> {
				barra.setName(Textos.t("heraldia.arena.barra.pausa", partida.oleada()));
				barra.setProgress(1f);
				barra.setColor(BossEvent.BossBarColor.GREEN);
			}
			default -> {
				barra.setName(Textos.t("heraldia.arena.barra", partida.oleada(), partida.restantes()));
				barra.setProgress(partida.total() > 0 ? Math.clamp((float) partida.restantes() / partida.total(), 0f, 1f) : 0f);
				barra.setColor(Oleadas.conJefe(partida.oleada()) ? BossEvent.BossBarColor.PURPLE : BossEvent.BossBarColor.RED);
			}
		}
		int antes = barra.getPlayers().size();
		for (ServerPlayer p : level.players()) {
			if (z.cerca(p.getBlockX(), p.getBlockY(), p.getBlockZ(), RADIO_BARRA)) {
				barra.addPlayer(p);
			} else {
				barra.removePlayer(p);
			}
		}
		for (ServerPlayer p : List.copyOf(barra.getPlayers())) {
			if (p.level() != level || p.hasDisconnected()) {
				barra.removePlayer(p);
			}
		}
		if (barra.getPlayers().size() != antes) {
			LOGGER.info("Heraldia: arena: barra para {} jugadores ({})", barra.getPlayers().size(), barra.getName().getString());
		}
	}

	// --- eventos ---

	/** Muere una entidad: un mob de la partida (cuenta) o un participante (cae). */
	static void alMorir(LivingEntity e) {
		Zona z = Arena.zona();
		ServerLevel level = Arena.nivel();
		if (partida.estado() == Partida.Estado.LIBRE || z == null || level == null) {
			return;
		}
		if (e instanceof Mob m && MOBS.remove(m.getUUID()) != null) {
			if (partida.muere()) {
				superada(level, z);
			}
		} else if (e instanceof ServerPlayer p && partida.participa(p.getUUID())) {
			avisar(level, z, Textos.t("heraldia.arena.cae", p.getDisplayName(), partida.oleada()));
			sale(level, z, p.getUUID(), p.getGameProfile().name(), "cae");
		}
	}

	/** Al cargarse una entidad: los mobs de la arena que no son de esta partida se quitan; los refuerzos del mini-jefe se suman. */
	static void alCargar(Entity e, ServerLevel level) {
		if (!(e instanceof Mob m)) {
			return;
		}
		Set<String> tags = m.entityTags();
		if (tags.isEmpty()) {
			return;
		}
		if (tags.contains(Arena.TAG)) {
			Mob nuestro = MOBS.get(m.getUUID());
			if (nuestro == null) {
				m.discard();
				LOGGER.info("Heraldia: arena: quitado un mob de arena de una partida anterior ({})",
						BuiltInRegistries.ENTITY_TYPE.getKey(m.getType()).getPath());
			} else if (nuestro != m) {
				MOBS.put(m.getUUID(), m);     // se recargó su chunk
			}
			return;
		}
		Zona z = Arena.zona();
		if (tags.contains(Fases.REFUERZO) && partida.estado() == Partida.Estado.OLEADA && z != null && level == Arena.nivel()
				&& z.enRuedo(m.getX(), m.getY(), m.getZ())) {
			m.addTag(Arena.TAG);
			preparar(m, partida.oleada(), false);
			MOBS.put(m.getUUID(), m);
			partida.extra();
			LOGGER.info("Heraldia: arena: un refuerzo del mini-jefe entra en la oleada");
		}
	}

	private static void sale(ServerLevel level, Zona z, UUID u, String nombre, String como) {
		LOGGER.info("Heraldia: arena: {} {} en la oleada {}", nombre, como, partida.oleada());
		if (partida.sale(u)) {
			terminar(level, z, "sin participantes");
		}
	}

	/** Se supera la oleada: récords, recompensas, logros y pausa. */
	private static void superada(ServerLevel level, Zona z) {
		int n = partida.oleada();
		LOGGER.info("Heraldia: arena: oleada {} superada (experiencia: {} de vanilla, {} dada, al {} %)", n, xpVanilla, xpDada, xpPct);
		int nivel = Oleadas.recompensa(n);
		for (ServerPlayer p : participantes(level)) {
			titulo(p, Textos.t("heraldia.arena.oleada.superada", n).withStyle(ChatFormatting.GREEN),
					Textos.t("heraldia.arena.oleada.siguiente", partida.segundos()));
			Marcador.superada(level.getServer(), p, n);
			io.github.albertosa23.heraldia.encargos.Encargos.oleadaSuperada(p, n);   // encargos del tablón (T38)
			if (nivel > 0) {
				recompensa(level, p, n, nivel);
			}
			if (Oleadas.logro(n)) {
				AdvancementHolder a = level.getServer().getAdvancements().get(Heraldia.id("arena/oleada_" + n));
				if (a != null) {
					p.getAdvancements().award(a, "oleada");
				}
			}
		}
		level.playSound(null, z.centroX(), z.minY() + 2, z.centroZ(), SoundEvents.PLAYER_LEVELUP, SoundSource.PLAYERS, 1.5f, 1f);
	}

	private static void recompensa(ServerLevel level, ServerPlayer p, int oleada, int nivel) {
		ResourceKey<LootTable> key = ResourceKey.create(Registries.LOOT_TABLE, Heraldia.id("arena/recompensa_" + nivel));
		LootTable tabla = level.getServer().reloadableRegistries().getLootTable(key);
		LootParams params = new LootParams.Builder(level).withParameter(LootContextParams.ORIGIN, p.position())
				.withParameter(LootContextParams.THIS_ENTITY, p).create(LootContextParamSets.CHEST);
		int n = 0;
		for (ItemStack s : tabla.getRandomItems(params)) {
			LlaveCommand.give(p, s);
			n++;
		}
		p.sendSystemMessage(Textos.t("heraldia.arena.recompensa", oleada).withStyle(ChatFormatting.GOLD));
		LOGGER.info("Heraldia: arena: recompensa {} ({} objetos) para {} en la oleada {}", nivel, n, p.getGameProfile().name(), oleada);
	}

	// --- muerte en el ruedo: se conserva el inventario y la experiencia ---

	/** Llamado por PlayerArenaMixin al soltar el equipo al morir: ¿lo conserva? (cae en el ruedo durante una partida). */
	static boolean conservaAlMorir(Player player) {
		Zona z = Arena.zona();
		if (!(player instanceof ServerPlayer p) || z == null || p.level() != Arena.nivel() || !partida.enJuego()
				|| !partida.participa(p.getUUID()) || !z.enRuedo(p.getX(), p.getY(), p.getZ())) {
			if (player.hasAttached(Guardada.Tipo.CONSERVAR)) {
				player.removeAttached(Guardada.Tipo.CONSERVAR);   // de una caída anterior sin reaparición vanilla
			}
			return false;
		}
		p.setAttached(Guardada.Tipo.CONSERVAR, Boolean.TRUE);
		LOGGER.info("Heraldia: arena: {} cae en el ruedo y conserva su inventario y su experiencia", p.getGameProfile().name());
		return true;
	}

	/** ¿Está conservando (no suelta experiencia)? */
	static boolean conservando(Player player) {
		return Boolean.TRUE.equals(player.getAttached(Guardada.Tipo.CONSERVAR));
	}

	/** Al reaparecer (COPY_FROM): le devuelve lo que llevaba. */
	static void copiar(ServerPlayer viejo, ServerPlayer nuevo, boolean vivo) {
		if (vivo || !conservando(viejo)) {
			return;
		}
		nuevo.getInventory().replaceWith(viejo.getInventory());
		nuevo.experienceLevel = viejo.experienceLevel;
		nuevo.totalExperience = viejo.totalExperience;
		nuevo.experienceProgress = viejo.experienceProgress;
		nuevo.removeAttached(Guardada.Tipo.CONSERVAR);
		REAPARECER.add(nuevo.getUUID());
		nuevo.sendSystemMessage(Textos.t("heraldia.arena.conservado").withStyle(ChatFormatting.GOLD));
	}

	/** Tras reaparecer: a la entrada de la arena. */
	static void reaparecer(ServerPlayer nuevo) {
		Zona z = Arena.zona();
		ServerLevel level = Arena.nivel();
		if (!REAPARECER.remove(nuevo.getUUID()) || z == null || level == null) {
			return;
		}
		int[] r = z.reaparicion();
		nuevo.teleportTo(level, r[0] + 0.5, r[1], r[2] + 0.5, Set.of(), 180f, 0f, false);
		LOGGER.info("Heraldia: arena: {} reaparece en la entrada de la arena", nuevo.getGameProfile().name());
	}

	/** /heraldia arena leave. */
	static boolean salir(ServerPlayer p) {
		Zona z = Arena.zona();
		ServerLevel level = Arena.nivel();
		if (z == null || level == null || !partida.participa(p.getUUID())) {
			return false;
		}
		int[] r = z.reaparicion();
		p.teleportTo(level, r[0] + 0.5, r[1], r[2] + 0.5, Set.of(), 180f, 0f, false);
		avisar(level, z, Textos.t("heraldia.arena.sale", p.getDisplayName()));
		sale(level, z, p.getUUID(), p.getGameProfile().name(), "sale");
		return true;
	}

	// --- utilidades ---

	/** Cierra (rejas) o abre (aire) la puerta del ruedo. */
	static void puerta(ServerLevel level, Zona z, boolean cerrar) {
		int[] a = z.puertaMin(), b = z.puertaMax();
		BlockState s = cerrar ? Blocks.IRON_BARS.defaultBlockState() : Blocks.AIR.defaultBlockState();
		BlockPos.MutableBlockPos pos = new BlockPos.MutableBlockPos();
		for (int x = a[0]; x <= b[0]; x++) {
			for (int y = a[1]; y <= b[1]; y++) {
				for (int zz = a[2]; zz <= b[2]; zz++) {
					BlockState actual = level.getBlockState(pos.set(x, y, zz));
					if (cerrar ? actual.isAir() : actual.is(Blocks.IRON_BARS)) {
						level.setBlock(pos, s, net.minecraft.world.level.block.Block.UPDATE_ALL);
					}
				}
			}
		}
		level.playSound(null, (a[0] + b[0]) / 2.0 + 0.5, a[1], (a[2] + b[2]) / 2.0 + 0.5,
				cerrar ? SoundEvents.IRON_DOOR_CLOSE : SoundEvents.IRON_DOOR_OPEN, SoundSource.BLOCKS, 1.5f, 0.8f);
	}

	static AABB caja(Zona z) {
		return new AABB(z.minX(), z.minY(), z.minZ(), z.maxX() + 1, z.maxY() + 1, z.maxZ() + 1);
	}

	static List<ServerPlayer> enRuedo(ServerLevel level, Zona z) {
		List<ServerPlayer> out = new ArrayList<>();
		for (ServerPlayer p : level.players()) {
			if (!p.isSpectator() && p.isAlive() && z.enRuedo(p.getX(), p.getY(), p.getZ())) {
				out.add(p);
			}
		}
		return out;
	}

	private static List<ServerPlayer> participantes(ServerLevel level) {
		List<ServerPlayer> out = new ArrayList<>();
		for (UUID u : partida.participantes()) {
			ServerPlayer p = level.getServer().getPlayerList().getPlayer(u);
			if (p != null && p.isAlive()) {
				out.add(p);
			}
		}
		return out;
	}

	private static @Nullable ServerPlayer cercano(Mob m, List<ServerPlayer> jugadores) {
		ServerPlayer mejor = null;
		double d = Double.MAX_VALUE;
		for (ServerPlayer p : jugadores) {
			double dd = p.distanceToSqr(m);
			if (dd < d && p.canBeSeenAsEnemy()) {
				d = dd;
				mejor = p;
			}
		}
		return mejor;
	}

	private static void avisar(ServerLevel level, Zona z, Component c) {
		for (ServerPlayer p : level.players()) {
			if (z.cerca(p.getBlockX(), p.getBlockY(), p.getBlockZ(), RADIO_BARRA)) {
				p.sendSystemMessage(c);
			}
		}
	}

	static void titulo(ServerPlayer p, Component titulo, Component subtitulo) {
		p.connection.send(new ClientboundSetTitlesAnimationPacket(5, 30, 10));
		p.connection.send(new ClientboundSetSubtitleTextPacket(subtitulo));
		p.connection.send(new ClientboundSetTitleTextPacket(titulo));
	}

	/** Al pararse el servidor: la partida se acaba limpia (mobs fuera, puerta abierta). */
	static void alParar() {
		terminar(Arena.nivel(), Arena.zona(), "el servidor se para");
		REAPARECER.clear();
	}
}
