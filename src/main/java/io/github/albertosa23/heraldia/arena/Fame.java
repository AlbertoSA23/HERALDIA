package io.github.albertosa23.heraldia.arena;

import com.mojang.brigadier.arguments.IntegerArgumentType;
import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;
import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.command.Texts;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import java.time.DayOfWeek;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.AbstractMap;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import net.fabricmc.fabric.api.attachment.v1.AttachmentRegistry;
import net.fabricmc.fabric.api.attachment.v1.AttachmentType;
import net.minecraft.ChatFormatting;
import net.minecraft.advancements.AdvancementHolder;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.StandingSignBlock;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.entity.SignBlockEntity;
import net.minecraft.world.level.block.entity.SignText;
import net.minecraft.world.level.block.entity.SignTextSlot;
import net.minecraft.world.item.DyeColor;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.scores.Objective;
import net.minecraft.world.scores.PlayerScoreEntry;
import org.jspecify.annotations.Nullable;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Weekly leaderboard, records and champions of the arena (T41). The state ({@link Season}) lives in the overworld
 * (persistent attachment heraldia:arena_temporada); the pure logic is in {@link Season}, {@link Week} and
 * {@link Marks}.
 * <ul>
 * <li>The week closes on day arena.temporada.dia_reinicio at hour arena.temporada.hora_reinicio (server
 * time; also if the server was off: at startup) or with /heraldia arena season reset: it goes to the history
 * (arena.temporada.historico weeks), its champions are announced in the chat and earn their advancement (those absent,
 * when they join). It is checked at startup, once per minute (one comparison) and before recording a mark.</li>
 * <li>The previous week's champions appear in the hall of fame: the arena signs (on the walkway, next to the
 * entrance: the blueprint says where; in an already placed arena they are only put if their spot is free) and two
 * pages of the Guide.</li>
 * <li>On the first startup with T41 the vanilla scoreboard record (coop) is copied to the records.</li>
 * </ul>
 */
public final class Fame {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	private static final int CHECK_EVERY = 1200;
	private static final DateTimeFormatter DATE = DateTimeFormatter.ofPattern("dd/MM/yyyy", Locale.ROOT);

	private static DayOfWeek day = DayOfWeek.MONDAY;
	private static int hour, history = 8;
	/** The server's time zone (the pure logic tests use others). */
	private static ZoneId zone = ZoneId.systemDefault();
	/** When the current week ends (epoch ms); Long.MAX_VALUE without a server. */
	private static long next = Long.MAX_VALUE;
	private static boolean signs;

	private Fame() {
	}

	/** The attachment, kept apart so the tests register nothing when Fame loads. */
	static final class Type {
		static final AttachmentType<Season> SEASON = AttachmentRegistry.create(Heraldia.id("arena_temporada"),
				b -> b.persistent(Season.CODEC));

		private Type() {
		}
	}

	static void registerAttachment() {
		LOGGER.debug("Heraldia: adjunto {} registrado", Type.SEASON.identifier());
	}

	/** Reads arena.temporada.* (at startup and on /heraldia reload; applies even during a match). */
	static void configure(HeraldiaConfig cfg) {
		day = Week.day(cfg.getString("arena.temporada.dia_reinicio"));
		hour = cfg.getInt("arena.temporada.hora_reinicio");
		history = cfg.getInt("arena.temporada.historico");
	}

	static Season read(MinecraftServer server) {
		return Optional.ofNullable(server.overworld().getAttached(Type.SEASON)).orElse(Season.EMPTY);
	}

	private static void save(MinecraftServer server, Season t) {
		server.overworld().setAttached(Type.SEASON, t);
	}

	static LocalDate currentStart() {
		return Week.start(Instant.now(), zone, day, hour);
	}

	// --- startup, reload and tick ---

	/** At startup (with the arena enabled): scoreboard migration, week close if the reset has passed, and signs. */
	static void onStart(MinecraftServer server) {
		Season t = read(server);
		if (!t.migrated()) {
			Map<String, Integer> points = scoreboardPoints(server);
			t = t.migrate(points, ArenaScoreboard.SERVER, System.currentTimeMillis());
			Optional<Season.Entry> r = t.record(Mode.COOP);
			LOGGER.info("Heraldia: arena: récords migrados del marcador ({} jugadores; cooperativo: {})", points.size(),
					r.map(e -> e.name() + " " + e.waves()).orElse("ninguno"));
		}
		t = t.trim(history);
		save(server, t);
		check(server);
		signs = true;
	}

	/** /heraldia reload: arena.temporada.* (the history is trimmed now; the day and hour count from now). */
	static void reload(MinecraftServer server) {
		save(server, read(server).trim(history));
		check(server);
		signs = true;
	}

	static void onStop() {
		next = Long.MAX_VALUE;
		signs = false;
	}

	/** Once per minute: has the reset passed? Signs to place (their chunk loaded)? Cheap early exit. */
	static void tick(MinecraftServer server) {
		if (server.getTickCount() % CHECK_EVERY != 0) {
			return;
		}
		if (System.currentTimeMillis() >= next) {
			check(server);
		}
		if (signs) {
			signs(server);
		}
	}

	/** Closes the saved week if it is no longer the current one (and announces its champions); computes the next reset. */
	static void check(MinecraftServer server) {
		Instant now = Instant.now();
		LocalDate ini = Week.start(now, zone, day, hour);
		Season.Closing c = read(server).advance(ini, day, history);
		save(server, c.season());
		next = Week.nextReset(now, zone, day, hour).toEpochMilli();
		if (c.closed() != null) {
			closed(server, c, ini);
		}
	}

	/** /heraldia arena season reset: closes the current week now. */
	static Season.Closed force(MinecraftServer server) {
		Instant now = Instant.now();
		LocalDate ini = Week.start(now, zone, day, hour);
		Season.Closing c = read(server).force(now.atZone(zone).toLocalDate(), ini, history);
		save(server, c.season());
		closed(server, c, ini);
		return c.closed();
	}

	private static void closed(MinecraftServer server, Season.Closing c, LocalDate ini) {
		Season.Closed w = c.closed();
		Map<Mode, Season.Entry> champions = c.season().champions(ini);
		List<String> log = new ArrayList<>();
		champions.forEach((m, e) -> log.add(m.id() + "=" + e.name()));
		LOGGER.info("Heraldia: arena: semana del {} cerrada; campeones: {}", date(w.start()),
				log.isEmpty() ? "ninguno" : String.join(", ", log));
		server.getPlayerList().broadcastSystemMessage(Texts.t("heraldia.arena.semana.cerrada", date(w.start()))
				.withStyle(ChatFormatting.GOLD), false);
		if (champions.isEmpty()) {
			server.getPlayerList().broadcastSystemMessage(Texts.t("heraldia.arena.semana.sin_campeones")
					.withStyle(ChatFormatting.GRAY), false);
		}
		champions.forEach((m, e) -> {
			server.getPlayerList().broadcastSystemMessage(Texts.t("heraldia.arena.semana.campeon", Texts.t(m.text()),
					e.name(), points(m, e)).withStyle(ChatFormatting.YELLOW), false);
			ServerPlayer p = server.getPlayerList().getPlayer(e.player());
			if (p != null) {
				grant(server, p, Marks.championAdvancement(m));
			}
		});
		signs = true;
		signs(server);
	}

	// --- marks ---

	/** A mark from a finished match (first, in case the reset has just passed and has not been checked yet). */
	static void register(MinecraftServer server, Mode m, Season.Entry e) {
		if (System.currentTimeMillis() >= next) {
			check(server);
		}
		Season before = read(server);
		boolean record = Season.best(e, before.record(m).orElse(null));
		Season t = before.register(m, e);
		save(server, t);
		int place = t.ranking(m).indexOf(e) + 1;
		LOGGER.info("Heraldia: arena: marca de {} en {}: {} oleadas en {} ticks (puesto {} de la semana{})", e.name(), m.id(),
				e.waves(), e.ticks(), place <= 0 ? "-" : place, record ? ", récord" : "");
		if (record && m != Mode.COOP) {          // the coop one is already announced by the scoreboard (ArenaScoreboard)
			server.getPlayerList().broadcastSystemMessage(Texts.t("heraldia.arena.record.modo", e.name(), Texts.t(m.text()),
					points(m, e)).withStyle(ChatFormatting.GOLD), false);
		}
	}

	/** When a player joins: the advancements of the weeks they won and do not have (they were offline at the close). */
	static void onJoin(ServerPlayer p) {
		MinecraftServer server = p.level().getServer();
		for (Mode m : read(server).won(p.getUUID())) {
			grant(server, p, Marks.championAdvancement(m));
		}
	}

	static void grant(MinecraftServer server, ServerPlayer p, String advancement) {
		AdvancementHolder a = server.getAdvancements().get(Heraldia.id(advancement));
		if (a != null && !p.getAdvancements().getOrStartProgress(a).isDone()) {
			p.getAdvancements().award(a, "logro");
			LOGGER.info("Heraldia: arena: logro {} para {}", advancement, p.getGameProfile().name());
		}
	}

	/** The mark to show it (in the .jar's default language or in that of {@code texts}). */
	static MutableComponent points(Map<String, String> texts, Mode m, Season.Entry e) {
		Object[] p = Marks.points(m, e);
		Object[] args = new Object[p.length - 1];
		System.arraycopy(p, 1, args, 0, args.length);
		return Texts.t(texts, (String) p[0], args);
	}

	static MutableComponent points(Mode m, Season.Entry e) {
		Object[] p = Marks.points(m, e);
		Object[] args = new Object[p.length - 1];
		System.arraycopy(p, 1, args, 0, args.length);
		return Texts.t((String) p[0], args);
	}

	static String date(long epochDay) {
		return epochDay == Season.NO_WEEK ? "-" : LocalDate.ofEpochDay(epochDay).format(DATE);
	}

	private static Map<String, Integer> scoreboardPoints(MinecraftServer server) {
		Map<String, Integer> out = new HashMap<>();
		Objective obj = server.getScoreboard().getObjective(ArenaScoreboard.OBJECTIVE);
		if (obj != null) {
			for (PlayerScoreEntry s : server.getScoreboard().listPlayerScores(obj)) {
				out.put(s.owner(), s.value());
			}
		}
		return out;
	}

	// --- hall of fame signs ---

	/**
	 * Writes the previous week's champion of each mode on the arena signs (one per mode, in the order of
	 * {@link Mode}). Only if its chunk is loaded (if not, it stays pending and is checked every minute); in an arena placed
	 * before T41 it puts the sign if its spot is empty and has ground, and if there is something else, it touches nothing.
	 */
	static void signs(MinecraftServer server) {
		Zone z = Arena.zone();
		ServerLevel level = Arena.arenaLevel();
		if (z == null || level == null) {
			signs = false;
			return;
		}
		List<int[]> sites = z.plan().fame();
		if (sites.isEmpty()) {
			signs = false;
			return;
		}
		Map<Mode, Season.Entry> champions = read(server).champions(currentStart());
		long week = read(server).closed(1).map(Season.Closed::start).orElse(Season.NO_WEEK);
		Mode[] modes = Mode.values();
		for (int i = 0; i < Math.min(sites.size(), modes.length); i++) {
			BlockPos pos = BlockPos.containing(z.world(sites.get(i))[0], z.world(sites.get(i))[1], z.world(sites.get(i))[2]);
			if (!level.isLoaded(pos)) {
				return;                          // still pending
			}
			Mode m = modes[i];
			signpost(level, pos, z.plan().fameRotation(), lines(m, champions.get(m), week));
		}
		signs = false;
		LOGGER.info("Heraldia: arena: carteles del salón de la fama al día ({} campeones)", champions.size());
	}

	/**
	 * The 4 lines of a mode's sign: title, mode, champion (or nobody) and their mark (a finished time trial, only its
	 * time: "m:ss (10 waves)" does not fit in 90 px) or, without a champion, the date of the previous week.
	 */
	static Component[] lines(Mode m, Season.@Nullable Entry e, long week) {
		return new Component[] {
				Texts.t("heraldia.arena.cartel.titulo").withStyle(ChatFormatting.DARK_RED, ChatFormatting.BOLD),
				Texts.t(m.text()).withStyle(ChatFormatting.BLACK),
				e == null ? Texts.t("heraldia.arena.cartel.nadie").withStyle(ChatFormatting.DARK_GRAY)
						: Component.literal(e.name()).withStyle(ChatFormatting.DARK_BLUE),
				e == null ? Component.literal(week == Season.NO_WEEK ? "" : date(week)).withStyle(ChatFormatting.DARK_GRAY)
						: (e.complete() ? Component.literal(Marks.time(e.ticks())) : points(m, e)).withStyle(ChatFormatting.BLACK)};
	}

	private static void signpost(ServerLevel level, BlockPos pos, int rotation, Component[] lines) {
		BlockState st = level.getBlockState(pos);
		if (st.isAir()) {
			if (!level.getBlockState(pos.below()).isFaceSturdy(level, pos.below(), Direction.UP)) {
				LOGGER.info("Heraldia: arena: sin suelo para el cartel del salón de la fama en {}", pos.toShortString());
				return;
			}
			st = Blocks.CRIMSON_SIGN.defaultBlockState().setValue(StandingSignBlock.ROTATION, Math.floorMod(rotation, 16));
			level.setBlock(pos, st, Block.UPDATE_ALL);
			LOGGER.info("Heraldia: arena: cartel del salón de la fama puesto en {}", pos.toShortString());
		}
		BlockEntity be = level.getBlockEntity(pos);
		if (!(be instanceof SignBlockEntity sign)) {
			LOGGER.info("Heraldia: arena: el sitio del cartel del salón de la fama ({}) está ocupado: no se toca", pos.toShortString());
			return;
		}
		List<Component> l = List.of(lines);
		sign.setText(new SignText(l, l, DyeColor.BLACK, false), SignTextSlot.FRONT);
		sign.setWaxed(true);
		sign.setChanged();
		level.sendBlockUpdated(pos, st, st, Block.UPDATE_ALL);
	}

	// --- the Guide ---

	/**
	 * The hall of fame pages for the Guide (title and body; {@code command/Guide} adds them after the journal summary):
	 * the previous week's champions and the records of each enabled mode. Empty without the arena enabled.
	 */
	public static List<Map.Entry<String, Component>> pages(MinecraftServer server, Map<String, String> texts) {
		if (!Arena.turnedOn()) {
			return List.of();
		}
		return pages(read(server), currentStart(), Game.modes(), texts);
	}

	/** The same with the given state (the tests check it: the text and what fits). */
	static List<Map.Entry<String, Component>> pages(Season t, LocalDate currentStart, List<Mode> modes, Map<String, String> texts) {
		Map<Mode, Season.Entry> champions = t.champions(currentStart);
		MutableComponent fame = Component.empty();
		if (champions.isEmpty()) {
			fame.append(Texts.t(texts, "heraldia.guia.fama.ninguno"));
		} else {
			fame.append(Texts.t(texts, "heraldia.guia.fama.semana", date(t.history().get(0).start())));
			for (Mode m : modes) {
				Season.Entry e = champions.get(m);
				fame.append("\n").append(e == null ? Texts.t(texts, "heraldia.guia.fama.vacio", Texts.t(texts, m.text()))
						: Texts.t(texts, "heraldia.guia.fama.entrada", Texts.t(texts, m.text()), e.name(), points(texts, m, e)));
			}
		}
		MutableComponent records = Component.empty().append(Texts.t(texts, "heraldia.guia.records.intro"));
		for (Mode m : modes) {
			Season.Entry e = t.record(m).orElse(null);
			records.append("\n").append(e == null ? Texts.t(texts, "heraldia.guia.fama.vacio", Texts.t(texts, m.text()))
					: Texts.t(texts, "heraldia.guia.fama.entrada", Texts.t(texts, m.text()), e.name(), points(texts, m, e)));
		}
		return List.of(new AbstractMap.SimpleImmutableEntry<>("heraldia.guia.fama.titulo", fame),
				new AbstractMap.SimpleImmutableEntry<>("heraldia.guia.records.titulo", records));
	}

	// --- commands ---

	/** /heraldia arena leaderboard [coop|timeattack|survival [week]] (any player). */
	static LiteralArgumentBuilder<CommandSourceStack> leaderboard() {
		LiteralArgumentBuilder<CommandSourceStack> n = Commands.literal("leaderboard").executes(ctx -> ranking(ctx, null, 0));
		for (Mode m : Mode.values()) {
			n.then(Commands.literal(m.id()).executes(ctx -> ranking(ctx, m, 0))
					.then(Commands.argument("week", IntegerArgumentType.integer(0, Season.MAX_HISTORY))
							.executes(ctx -> ranking(ctx, m, IntegerArgumentType.getInteger(ctx, "week")))));
		}
		return n;
	}

	/** /heraldia arena season [reset] (operators): the current week and the next reset; reset closes it now. */
	static LiteralArgumentBuilder<CommandSourceStack> season() {
		return Commands.literal("season").requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))
				.executes(ctx -> {
					if (!checkEnabled(ctx.getSource())) {
						return 0;
					}
					Season t = read(ctx.getSource().getServer());
					String nxt = Instant.ofEpochMilli(next).atZone(zone).toLocalDateTime().format(
							DateTimeFormatter.ofPattern("dd/MM/yyyy HH:mm", Locale.ROOT));
					ctx.getSource().sendSuccess(() -> Texts.t("heraldia.arena.temporada.info", date(t.week()), nxt,
							zone.getId(), t.history().size()), false);
					return 1;
				})
				.then(Commands.literal("reset").executes(ctx -> {
					if (!checkEnabled(ctx.getSource())) {
						return 0;
					}
					Season.Closed c = force(ctx.getSource().getServer());
					ctx.getSource().sendSuccess(() -> Texts.t("heraldia.arena.temporada.reiniciada", date(c.start())), true);
					return 1;
				}));
	}

	private static boolean checkEnabled(CommandSourceStack src) {
		if (!Arena.turnedOn()) {
			src.sendFailure(Texts.t("heraldia.arena.desactivada"));
			return false;
		}
		return true;
	}

	private static int ranking(CommandContext<CommandSourceStack> ctx, @Nullable Mode mode, int ago) {
		CommandSourceStack src = ctx.getSource();
		if (!checkEnabled(src)) {
			return 0;
		}
		Season t = read(src.getServer());
		Map<String, String> texts = src.getPlayer() != null ? Texts.language(src.getPlayer())
				: Texts.texts("es_es");
		Map<String, List<Season.Entry>> rk;
		long start;
		if (ago == 0) {
			rk = t.actual();
			start = t.week();
		} else {
			Optional<Season.Closed> c = t.closed(ago);
			if (c.isEmpty()) {
				src.sendFailure(Texts.t(texts, "heraldia.arena.clasificacion.sin_semana", t.history().size()));
				return 0;
			}
			rk = c.get().ranking();
			start = c.get().start();
		}
		List<Mode> modes = mode != null ? List.of(mode) : Game.modes();
		int max = mode != null ? Season.MAX_PER_MODE : 3;
		String header = ago == 0 ? "heraldia.arena.clasificacion.actual" : "heraldia.arena.clasificacion.pasada";
		src.sendSuccess(() -> Texts.t(texts, header, date(start)).withStyle(ChatFormatting.GOLD), false);
		for (Mode m : modes) {
			List<Season.Entry> l = rk.getOrDefault(m.id(), List.of());
			src.sendSuccess(() -> Texts.t(texts, m.text()).withStyle(ChatFormatting.YELLOW, ChatFormatting.BOLD), false);
			if (l.isEmpty()) {
				src.sendSuccess(() -> Texts.t(texts, "heraldia.arena.clasificacion.vacia").withStyle(ChatFormatting.GRAY), false);
			}
			for (int i = 0; i < Math.min(max, l.size()); i++) {
				Season.Entry e = l.get(i);
				int place = i + 1;
				src.sendSuccess(() -> Texts.t(texts, "heraldia.arena.clasificacion.linea", place, e.name(), points(texts, m, e)), false);
			}
			t.record(m).ifPresent(r -> src.sendSuccess(() -> Texts.t(texts, "heraldia.arena.clasificacion.record", r.name(),
					points(texts, m, r)).withStyle(ChatFormatting.AQUA), false));
		}
		return 1;
	}
}
