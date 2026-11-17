package io.github.albertosa23.heraldia.arena;

import com.mojang.brigadier.arguments.IntegerArgumentType;
import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;
import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.comando.Textos;
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
 * Clasificación semanal, récords y campeones de la arena (T41). El estado ({@link Temporada}) va en el mundo principal
 * (adjunto persistente heraldia:arena_temporada); la lógica pura está en {@link Temporada}, {@link Semana} y
 * {@link Marcas}.
 * <ul>
 * <li>La semana se cierra el día arena.temporada.dia_reinicio a la hora arena.temporada.hora_reinicio (hora del
 * servidor; también si el servidor estaba apagado: al arrancar) o con /heraldia arena season reset: pasa al histórico
 * (arena.temporada.historico semanas), se anuncian sus campeones en el chat y ganan su logro (los que no están, al
 * entrar). Se comprueba al arrancar, una vez por minuto (una comparación) y antes de apuntar una marca.</li>
 * <li>Los campeones de la semana anterior salen en el salón de la fama: los carteles de la arena (en el paseo, junto a la
 * entrada: el plano dice dónde; en una arena ya colocada se ponen solo si su sitio está libre) y dos páginas de la Guía.</li>
 * <li>Al arrancar por primera vez con T41 se copia el récord del marcador vanilla (cooperativo) a los récords.</li>
 * </ul>
 */
public final class Fama {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	private static final int CADA_COMPROBACION = 1200;
	private static final DateTimeFormatter FECHA = DateTimeFormatter.ofPattern("dd/MM/yyyy", Locale.ROOT);

	private static DayOfWeek dia = DayOfWeek.MONDAY;
	private static int hora, historico = 8;
	/** La zona horaria del servidor (los tests de la lógica pura usan otras). */
	private static ZoneId zona = ZoneId.systemDefault();
	/** Cuándo acaba la semana en curso (epoch ms); Long.MAX_VALUE sin servidor. */
	private static long proximo = Long.MAX_VALUE;
	private static boolean carteles;

	private Fama() {
	}

	/** El adjunto, aparte para que los tests no registren nada al cargar Fama. */
	static final class Tipo {
		static final AttachmentType<Temporada> TEMPORADA = AttachmentRegistry.create(Heraldia.id("arena_temporada"),
				b -> b.persistent(Temporada.CODEC));

		private Tipo() {
		}
	}

	static void registrarAdjunto() {
		LOGGER.debug("Heraldia: adjunto {} registrado", Tipo.TEMPORADA.identifier());
	}

	/** Lee arena.temporada.* (al arrancar y con /heraldia reload; se aplica aunque haya partida). */
	static void configurar(HeraldiaConfig cfg) {
		dia = Semana.dia(cfg.getString("arena.temporada.dia_reinicio"));
		hora = cfg.getInt("arena.temporada.hora_reinicio");
		historico = cfg.getInt("arena.temporada.historico");
	}

	static Temporada leer(MinecraftServer server) {
		return Optional.ofNullable(server.overworld().getAttached(Tipo.TEMPORADA)).orElse(Temporada.VACIA);
	}

	private static void guardar(MinecraftServer server, Temporada t) {
		server.overworld().setAttached(Tipo.TEMPORADA, t);
	}

	static LocalDate inicioActual() {
		return Semana.inicio(Instant.now(), zona, dia, hora);
	}

	// --- arranque, recarga y tick ---

	/** Al arrancar (con la arena activada): migración del marcador, cierre de la semana si pasó el reinicio y carteles. */
	static void alArrancar(MinecraftServer server) {
		Temporada t = leer(server);
		if (!t.migrada()) {
			Map<String, Integer> puntos = puntosMarcador(server);
			t = t.migrar(puntos, Marcador.SERVIDOR, System.currentTimeMillis());
			Optional<Temporada.Entrada> r = t.record(Modo.COOPERATIVO);
			LOGGER.info("Heraldia: arena: récords migrados del marcador ({} jugadores; cooperativo: {})", puntos.size(),
					r.map(e -> e.nombre() + " " + e.oleadas()).orElse("ninguno"));
		}
		t = t.recortar(historico);
		guardar(server, t);
		comprobar(server);
		carteles = true;
	}

	/** /heraldia reload: arena.temporada.* (el histórico se recorta ya; el día y la hora cuentan desde ahora). */
	static void recargar(MinecraftServer server) {
		guardar(server, leer(server).recortar(historico));
		comprobar(server);
		carteles = true;
	}

	static void alParar() {
		proximo = Long.MAX_VALUE;
		carteles = false;
	}

	/** Una vez por minuto: ¿ha pasado el reinicio? ¿Carteles por poner (su chunk se cargó)? Salida temprana barata. */
	static void tick(MinecraftServer server) {
		if (server.getTickCount() % CADA_COMPROBACION != 0) {
			return;
		}
		if (System.currentTimeMillis() >= proximo) {
			comprobar(server);
		}
		if (carteles) {
			carteles(server);
		}
	}

	/** Cierra la semana guardada si ya no es la en curso (y anuncia sus campeones); calcula el próximo reinicio. */
	static void comprobar(MinecraftServer server) {
		Instant ahora = Instant.now();
		LocalDate ini = Semana.inicio(ahora, zona, dia, hora);
		Temporada.Cierre c = leer(server).avanzar(ini, dia, historico);
		guardar(server, c.temporada());
		proximo = Semana.proximoReinicio(ahora, zona, dia, hora).toEpochMilli();
		if (c.cerrada() != null) {
			cerrada(server, c, ini);
		}
	}

	/** /heraldia arena season reset: cierra ya la semana en curso. */
	static Temporada.Cerrada forzar(MinecraftServer server) {
		Instant ahora = Instant.now();
		LocalDate ini = Semana.inicio(ahora, zona, dia, hora);
		Temporada.Cierre c = leer(server).forzar(ahora.atZone(zona).toLocalDate(), ini, historico);
		guardar(server, c.temporada());
		cerrada(server, c, ini);
		return c.cerrada();
	}

	private static void cerrada(MinecraftServer server, Temporada.Cierre c, LocalDate ini) {
		Temporada.Cerrada w = c.cerrada();
		Map<Modo, Temporada.Entrada> campeones = c.temporada().campeones(ini);
		List<String> log = new ArrayList<>();
		campeones.forEach((m, e) -> log.add(m.id() + "=" + e.nombre()));
		LOGGER.info("Heraldia: arena: semana del {} cerrada; campeones: {}", fecha(w.inicio()),
				log.isEmpty() ? "ninguno" : String.join(", ", log));
		server.getPlayerList().broadcastSystemMessage(Textos.t("heraldia.arena.semana.cerrada", fecha(w.inicio()))
				.withStyle(ChatFormatting.GOLD), false);
		if (campeones.isEmpty()) {
			server.getPlayerList().broadcastSystemMessage(Textos.t("heraldia.arena.semana.sin_campeones")
					.withStyle(ChatFormatting.GRAY), false);
		}
		campeones.forEach((m, e) -> {
			server.getPlayerList().broadcastSystemMessage(Textos.t("heraldia.arena.semana.campeon", Textos.t(m.texto()),
					e.nombre(), puntos(m, e)).withStyle(ChatFormatting.YELLOW), false);
			ServerPlayer p = server.getPlayerList().getPlayer(e.jugador());
			if (p != null) {
				conceder(server, p, Marcas.logroCampeon(m));
			}
		});
		carteles = true;
		carteles(server);
	}

	// --- marcas ---

	/** Una marca de una partida terminada (antes, por si acaba de pasar el reinicio y aún no se ha comprobado). */
	static void registrar(MinecraftServer server, Modo m, Temporada.Entrada e) {
		if (System.currentTimeMillis() >= proximo) {
			comprobar(server);
		}
		Temporada antes = leer(server);
		boolean record = Temporada.mejor(e, antes.record(m).orElse(null));
		Temporada t = antes.registrar(m, e);
		guardar(server, t);
		int puesto = t.clasificacion(m).indexOf(e) + 1;
		LOGGER.info("Heraldia: arena: marca de {} en {}: {} oleadas en {} ticks (puesto {} de la semana{})", e.nombre(), m.id(),
				e.oleadas(), e.ticks(), puesto <= 0 ? "-" : puesto, record ? ", récord" : "");
		if (record && m != Modo.COOPERATIVO) {          // el del cooperativo ya lo anuncia el marcador (Marcador)
			server.getPlayerList().broadcastSystemMessage(Textos.t("heraldia.arena.record.modo", e.nombre(), Textos.t(m.texto()),
					puntos(m, e)).withStyle(ChatFormatting.GOLD), false);
		}
	}

	/** Al entrar un jugador: los logros de las semanas que ganó y no tiene (estaba desconectado al cerrarse). */
	static void alEntrar(ServerPlayer p) {
		MinecraftServer server = p.level().getServer();
		for (Modo m : leer(server).ganadas(p.getUUID())) {
			conceder(server, p, Marcas.logroCampeon(m));
		}
	}

	static void conceder(MinecraftServer server, ServerPlayer p, String logro) {
		AdvancementHolder a = server.getAdvancements().get(Heraldia.id(logro));
		if (a != null && !p.getAdvancements().getOrStartProgress(a).isDone()) {
			p.getAdvancements().award(a, "logro");
			LOGGER.info("Heraldia: arena: logro {} para {}", logro, p.getGameProfile().name());
		}
	}

	/** La marca para enseñarla (en el idioma por defecto del .jar o en el de {@code textos}). */
	static MutableComponent puntos(Map<String, String> textos, Modo m, Temporada.Entrada e) {
		Object[] p = Marcas.puntos(m, e);
		Object[] args = new Object[p.length - 1];
		System.arraycopy(p, 1, args, 0, args.length);
		return Textos.t(textos, (String) p[0], args);
	}

	static MutableComponent puntos(Modo m, Temporada.Entrada e) {
		Object[] p = Marcas.puntos(m, e);
		Object[] args = new Object[p.length - 1];
		System.arraycopy(p, 1, args, 0, args.length);
		return Textos.t((String) p[0], args);
	}

	static String fecha(long epochDay) {
		return epochDay == Temporada.SIN_SEMANA ? "-" : LocalDate.ofEpochDay(epochDay).format(FECHA);
	}

	private static Map<String, Integer> puntosMarcador(MinecraftServer server) {
		Map<String, Integer> out = new HashMap<>();
		Objective obj = server.getScoreboard().getObjective(Marcador.OBJETIVO);
		if (obj != null) {
			for (PlayerScoreEntry s : server.getScoreboard().listPlayerScores(obj)) {
				out.put(s.owner(), s.value());
			}
		}
		return out;
	}

	// --- carteles del salón de la fama ---

	/**
	 * Escribe en los carteles de la arena el campeón de la semana anterior de cada modo (uno por modo, en el orden de
	 * {@link Modo}). Solo si su chunk está cargado (si no, queda pendiente y se mira cada minuto); en una arena colocada
	 * antes de T41 pone el cartel si su sitio está vacío y con suelo, y si hay otra cosa, no toca nada.
	 */
	static void carteles(MinecraftServer server) {
		Zona z = Arena.zona();
		ServerLevel level = Arena.nivel();
		if (z == null || level == null) {
			carteles = false;
			return;
		}
		List<int[]> sitios = z.plano().fama();
		if (sitios.isEmpty()) {
			carteles = false;
			return;
		}
		Map<Modo, Temporada.Entrada> campeones = leer(server).campeones(inicioActual());
		long semana = leer(server).cerrada(1).map(Temporada.Cerrada::inicio).orElse(Temporada.SIN_SEMANA);
		Modo[] modos = Modo.values();
		for (int i = 0; i < Math.min(sitios.size(), modos.length); i++) {
			BlockPos pos = BlockPos.containing(z.mundo(sitios.get(i))[0], z.mundo(sitios.get(i))[1], z.mundo(sitios.get(i))[2]);
			if (!level.isLoaded(pos)) {
				return;                          // sigue pendiente
			}
			Modo m = modos[i];
			cartel(level, pos, z.plano().famaRotacion(), lineas(m, campeones.get(m), semana));
		}
		carteles = false;
		LOGGER.info("Heraldia: arena: carteles del salón de la fama al día ({} campeones)", campeones.size());
	}

	/**
	 * Las 4 líneas del cartel de un modo: título, modo, campeón (o nadie) y su marca (el contrarreloj acabado, solo su
	 * tiempo: «m:ss (10 oleadas)» no cabe en 90 px) o, sin campeón, la fecha de la semana anterior.
	 */
	static Component[] lineas(Modo m, Temporada.@Nullable Entrada e, long semana) {
		return new Component[] {
				Textos.t("heraldia.arena.cartel.titulo").withStyle(ChatFormatting.DARK_RED, ChatFormatting.BOLD),
				Textos.t(m.texto()).withStyle(ChatFormatting.BLACK),
				e == null ? Textos.t("heraldia.arena.cartel.nadie").withStyle(ChatFormatting.DARK_GRAY)
						: Component.literal(e.nombre()).withStyle(ChatFormatting.DARK_BLUE),
				e == null ? Component.literal(semana == Temporada.SIN_SEMANA ? "" : fecha(semana)).withStyle(ChatFormatting.DARK_GRAY)
						: (e.completa() ? Component.literal(Marcas.tiempo(e.ticks())) : puntos(m, e)).withStyle(ChatFormatting.BLACK)};
	}

	private static void cartel(ServerLevel level, BlockPos pos, int rotacion, Component[] lineas) {
		BlockState st = level.getBlockState(pos);
		if (st.isAir()) {
			if (!level.getBlockState(pos.below()).isFaceSturdy(level, pos.below(), Direction.UP)) {
				LOGGER.info("Heraldia: arena: sin suelo para el cartel del salón de la fama en {}", pos.toShortString());
				return;
			}
			st = Blocks.CRIMSON_SIGN.defaultBlockState().setValue(StandingSignBlock.ROTATION, Math.floorMod(rotacion, 16));
			level.setBlock(pos, st, Block.UPDATE_ALL);
			LOGGER.info("Heraldia: arena: cartel del salón de la fama puesto en {}", pos.toShortString());
		}
		BlockEntity be = level.getBlockEntity(pos);
		if (!(be instanceof SignBlockEntity sign)) {
			LOGGER.info("Heraldia: arena: el sitio del cartel del salón de la fama ({}) está ocupado: no se toca", pos.toShortString());
			return;
		}
		List<Component> l = List.of(lineas);
		sign.setText(new SignText(l, l, DyeColor.BLACK, false), SignTextSlot.FRONT);
		sign.setWaxed(true);
		sign.setChanged();
		level.sendBlockUpdated(pos, st, st, Block.UPDATE_ALL);
	}

	// --- la Guía ---

	/**
	 * Las páginas del salón de la fama para la Guía (título y cuerpo; las pone {@code comando/Guia} tras el resumen del
	 * diario): los campeones de la semana anterior y los récords de cada modo activado. Vacío sin arena activada.
	 */
	public static List<Map.Entry<String, Component>> paginas(MinecraftServer server, Map<String, String> textos) {
		if (!Arena.activada()) {
			return List.of();
		}
		return paginas(leer(server), inicioActual(), Juego.modos(), textos);
	}

	/** Lo mismo con el estado dado (lo prueban los tests: el texto y lo que cabe). */
	static List<Map.Entry<String, Component>> paginas(Temporada t, LocalDate inicioActual, List<Modo> modos, Map<String, String> textos) {
		Map<Modo, Temporada.Entrada> campeones = t.campeones(inicioActual);
		MutableComponent fama = Component.empty();
		if (campeones.isEmpty()) {
			fama.append(Textos.t(textos, "heraldia.guia.fama.ninguno"));
		} else {
			fama.append(Textos.t(textos, "heraldia.guia.fama.semana", fecha(t.historico().get(0).inicio())));
			for (Modo m : modos) {
				Temporada.Entrada e = campeones.get(m);
				fama.append("\n").append(e == null ? Textos.t(textos, "heraldia.guia.fama.vacio", Textos.t(textos, m.texto()))
						: Textos.t(textos, "heraldia.guia.fama.entrada", Textos.t(textos, m.texto()), e.nombre(), puntos(textos, m, e)));
			}
		}
		MutableComponent records = Component.empty().append(Textos.t(textos, "heraldia.guia.records.intro"));
		for (Modo m : modos) {
			Temporada.Entrada e = t.record(m).orElse(null);
			records.append("\n").append(e == null ? Textos.t(textos, "heraldia.guia.fama.vacio", Textos.t(textos, m.texto()))
					: Textos.t(textos, "heraldia.guia.fama.entrada", Textos.t(textos, m.texto()), e.nombre(), puntos(textos, m, e)));
		}
		return List.of(new AbstractMap.SimpleImmutableEntry<>("heraldia.guia.fama.titulo", fama),
				new AbstractMap.SimpleImmutableEntry<>("heraldia.guia.records.titulo", records));
	}

	// --- comandos ---

	/** /heraldia arena leaderboard [coop|timeattack|survival [week]] (cualquier jugador). */
	static LiteralArgumentBuilder<CommandSourceStack> leaderboard() {
		LiteralArgumentBuilder<CommandSourceStack> n = Commands.literal("leaderboard").executes(ctx -> clasificacion(ctx, null, 0));
		for (Modo m : Modo.values()) {
			n.then(Commands.literal(m.id()).executes(ctx -> clasificacion(ctx, m, 0))
					.then(Commands.argument("week", IntegerArgumentType.integer(0, Temporada.MAX_HISTORICO))
							.executes(ctx -> clasificacion(ctx, m, IntegerArgumentType.getInteger(ctx, "week")))));
		}
		return n;
	}

	/** /heraldia arena season [reset] (operadores): la semana en curso y el próximo reinicio; reset la cierra ya. */
	static LiteralArgumentBuilder<CommandSourceStack> season() {
		return Commands.literal("season").requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))
				.executes(ctx -> {
					if (!comprobarActivada(ctx.getSource())) {
						return 0;
					}
					Temporada t = leer(ctx.getSource().getServer());
					String prox = Instant.ofEpochMilli(proximo).atZone(zona).toLocalDateTime().format(
							DateTimeFormatter.ofPattern("dd/MM/yyyy HH:mm", Locale.ROOT));
					ctx.getSource().sendSuccess(() -> Textos.t("heraldia.arena.temporada.info", fecha(t.semana()), prox,
							zona.getId(), t.historico().size()), false);
					return 1;
				})
				.then(Commands.literal("reset").executes(ctx -> {
					if (!comprobarActivada(ctx.getSource())) {
						return 0;
					}
					Temporada.Cerrada c = forzar(ctx.getSource().getServer());
					ctx.getSource().sendSuccess(() -> Textos.t("heraldia.arena.temporada.reiniciada", fecha(c.inicio())), true);
					return 1;
				}));
	}

	private static boolean comprobarActivada(CommandSourceStack src) {
		if (!Arena.activada()) {
			src.sendFailure(Textos.t("heraldia.arena.desactivada"));
			return false;
		}
		return true;
	}

	private static int clasificacion(CommandContext<CommandSourceStack> ctx, @Nullable Modo modo, int hace) {
		CommandSourceStack src = ctx.getSource();
		if (!comprobarActivada(src)) {
			return 0;
		}
		Temporada t = leer(src.getServer());
		Map<String, String> textos = src.getPlayer() != null ? Textos.idioma(src.getPlayer().clientInformation().language())
				: Textos.textos("es_es");
		Map<String, List<Temporada.Entrada>> clas;
		long inicio;
		if (hace == 0) {
			clas = t.actual();
			inicio = t.semana();
		} else {
			Optional<Temporada.Cerrada> c = t.cerrada(hace);
			if (c.isEmpty()) {
				src.sendFailure(Textos.t(textos, "heraldia.arena.clasificacion.sin_semana", t.historico().size()));
				return 0;
			}
			clas = c.get().clasificacion();
			inicio = c.get().inicio();
		}
		List<Modo> modos = modo != null ? List.of(modo) : Juego.modos();
		int max = modo != null ? Temporada.MAX_POR_MODO : 3;
		String cabecera = hace == 0 ? "heraldia.arena.clasificacion.actual" : "heraldia.arena.clasificacion.pasada";
		src.sendSuccess(() -> Textos.t(textos, cabecera, fecha(inicio)).withStyle(ChatFormatting.GOLD), false);
		for (Modo m : modos) {
			List<Temporada.Entrada> l = clas.getOrDefault(m.id(), List.of());
			src.sendSuccess(() -> Textos.t(textos, m.texto()).withStyle(ChatFormatting.YELLOW, ChatFormatting.BOLD), false);
			if (l.isEmpty()) {
				src.sendSuccess(() -> Textos.t(textos, "heraldia.arena.clasificacion.vacia").withStyle(ChatFormatting.GRAY), false);
			}
			for (int i = 0; i < Math.min(max, l.size()); i++) {
				Temporada.Entrada e = l.get(i);
				int puesto = i + 1;
				src.sendSuccess(() -> Textos.t(textos, "heraldia.arena.clasificacion.linea", puesto, e.nombre(), puntos(textos, m, e)), false);
			}
			t.record(m).ifPresent(r -> src.sendSuccess(() -> Textos.t(textos, "heraldia.arena.clasificacion.record", r.nombre(),
					puntos(textos, m, r)).withStyle(ChatFormatting.AQUA), false));
		}
		return 1;
	}
}
