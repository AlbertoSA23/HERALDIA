package io.github.albertosa23.heraldia.command;

import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.version.Notified;
import io.github.albertosa23.heraldia.version.Releases;
import io.github.albertosa23.heraldia.version.Releases.Release;
import io.github.albertosa23.heraldia.version.Version;
import java.io.IOException;
import java.io.InputStream;
import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.fabricmc.fabric.api.networking.v1.ServerPlayConnectionEvents;
import net.fabricmc.loader.api.FabricLoader;
import net.minecraft.ChatFormatting;
import net.minecraft.SharedConstants;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.network.chat.ClickEvent;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.HoverEvent;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.permissions.Permissions;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Aviso de versión nueva. Al arrancar y cada 24 h, en un hilo propio (nunca en el del servidor ni retrasando el
 * arranque), pregunta a la API de GitHub Releases, donde publica .github/workflows/publish.yml (en main; también publica
 * en CurseForge, cuya API pide una clave), si hay una versión del mod más nueva para el Minecraft del servidor
 * ({@link Releases}: semver, sin pre-publicaciones salvo update_check.prereleases; el Minecraft de cada publicación
 * sale del gradle.properties de su etiqueta). Si la hay, lo dice en la consola y en el chat a cada operador al entrar,
 * una vez por sesión del servidor ({@link Notified}), en su idioma, con el enlace a la descarga y la recomendación de
 * hacer antes una copia de seguridad. /heraldia update check (operadores) lo comprueba en el momento.
 * <p>Sin telemetría: una petición GET sin datos del servidor ni del jugador, con un User-Agent genérico y tiempos de
 * espera cortos. Sin red, o con una respuesta rara, solo deja una línea en el log. Opción update_check.activado; la
 * propiedad del sistema heraldia.update_check.url cambia la dirección (las pruebas apuntan a un servidor local).
 */
public final class VersionNotice {
	private static final Logger LOGGER = LoggerFactory.getLogger(Heraldia.MOD_ID);
	public static final String OPTION = "update_check.activado", PRE_OPTION = "update_check.prereleases";
	/** Releases de GitHub del repositorio del mod (contact.sources de fabric.mod.json). */
	static final String URL = "https://api.github.com/repos/AlbertoSA23/HERALDIA/releases?per_page=20";
	static final String URL_PROPERTY = "heraldia.update_check.url";
	static final String USER_AGENT = "Heraldia-update-check";
	static final Duration CONNECTION = Duration.ofSeconds(5), RESPONSE = Duration.ofSeconds(10);
	static final long PERIOD_H = 24;
	/** Lo más que se lee de una respuesta (la de GitHub con 20 publicaciones y su registro de cambios ocupa unos cientos de kB). */
	static final int MAX_BYTES = 4 << 20;
	private static final Notified NOTIFIED = new Notified();
	private static volatile Release fresh;
	private static ScheduledExecutorService thread;

	private VersionNotice() {
	}

	public static void register() {
		ServerLifecycleEvents.SERVER_STARTED.register(VersionNotice::start);
		ServerLifecycleEvents.SERVER_STOPPING.register(server -> stop());
		ServerPlayConnectionEvents.JOIN.register((handler, sender, server) -> server.schedule(server.wrapRunnable(() -> {
			if (!handler.player.hasDisconnected()) {
				onJoin(handler.player);
			}
		})));
	}

	/** /heraldia update check (operadores): comprueba ahora, aunque update_check.activado esté desactivada. */
	static LiteralArgumentBuilder<CommandSourceStack> node() {
		return Commands.literal("update")
				.requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))
				.then(Commands.literal("check").executes(ctx -> {
					CommandSourceStack src = ctx.getSource();
					src.sendSuccess(() -> Texts.t("heraldia.version.comprobando"), false);
					MinecraftServer server = src.getServer();
					Thread t = new Thread(() -> check(server, src), "Heraldia update check");
					t.setDaemon(true);
					t.start();
					return 1;
				}));
	}

	private static synchronized void start(MinecraftServer server) {
		stop();
		fresh = null;
		if (!HeraldiaConfig.get().getBool(OPTION)) {
			LOGGER.info("Heraldia: aviso de versión nueva desactivado ({} = false)", OPTION);
			return;
		}
		thread = Executors.newSingleThreadScheduledExecutor(r -> {
			Thread t = new Thread(r, "Heraldia update check");
			t.setDaemon(true);
			t.setPriority(Thread.MIN_PRIORITY);
			return t;
		});
		thread.scheduleAtFixedRate(() -> check(server, null), 0, PERIOD_H, TimeUnit.HOURS);
	}

	private static synchronized void stop() {
		if (thread != null) {
			thread.shutdownNow();
			thread = null;
		}
	}

	/** En el hilo propio: pregunta y pasa el resultado al hilo del servidor. Nunca lanza. */
	private static void check(MinecraftServer server, CommandSourceStack who) {
		long t0 = System.nanoTime();
		String actual = version(), mc = SharedConstants.getCurrentVersion().name();
		try {
			Optional<Version> va = Version.of(actual);
			if (va.isEmpty()) {
				throw new IOException("la versión instalada «" + actual + "» no es una versión");
			}
			Optional<Release> p = query(url(), va.get(), mc, HeraldiaConfig.get().getBool(PRE_OPTION));
			long ms = (System.nanoTime() - t0) / 1_000_000;
			LOGGER.info("Heraldia: comprobación de versión nueva ({} para Minecraft {}): {} en {} ms", actual, mc,
					p.map(x -> x.version().toString()).orElse("ninguna"), ms);
			server.execute(() -> result(server, p.orElse(null), actual, mc, who));
		} catch (Exception e) {
			LOGGER.info("Heraldia: no se pudo comprobar si hay una versión nueva ({}: {})", e.getClass().getSimpleName(), e.getMessage());
			if (who != null) {
				server.execute(() -> who.sendFailure(Texts.t("heraldia.version.sin_respuesta")));
			}
		}
	}

	static String url() {
		String u = System.getProperty(URL_PROPERTY);
		return u == null || u.isBlank() ? URL : u;
	}

	/** Pide la lista y elige; para las de GitHub, el Minecraft de cada candidata sale del gradle.properties de su etiqueta. */
	static Optional<Release> query(String url, Version actual, String mc, boolean pre) throws IOException, InterruptedException {
		HttpClient client = HttpClient.newBuilder().connectTimeout(CONNECTION).followRedirects(HttpClient.Redirect.NORMAL).build();
		List<Release> all = Releases.read(request(client, url, "application/vnd.github+json, application/json"));
		return Releases.choose(all, actual, mc, pre, p -> {
			String props = properties(url, p.tag());
			if (props == null) {
				return Optional.empty();
			}
			try {
				return Releases.minecraftFromProperties(request(client, props, "application/vnd.github.raw"));
			} catch (IOException e) {
				LOGGER.info("Heraldia: no se pudo leer el Minecraft de la {} ({})", p.tag(), e.getMessage());
				return Optional.empty();
			} catch (InterruptedException e) {
				Thread.currentThread().interrupt();
				return Optional.empty();
			}
		});
	}

	/** .../repos/&lt;dueño&gt;/&lt;repo&gt;/releases?... -> .../repos/&lt;dueño&gt;/&lt;repo&gt;/contents/gradle.properties?ref=&lt;etiqueta&gt;. */
	static String properties(String url, String tag) {
		int i = url.indexOf("/releases");
		if (i < 0 || tag == null || tag.isEmpty()) {
			return null;
		}
		return url.substring(0, i) + "/contents/gradle.properties?ref=" + URLEncoder.encode(tag, StandardCharsets.UTF_8);
	}

	private static String request(HttpClient client, String url, String accept) throws IOException, InterruptedException {
		HttpRequest req = HttpRequest.newBuilder(URI.create(url)).timeout(RESPONSE).header("User-Agent", USER_AGENT)
				.header("Accept", accept).GET().build();
		HttpResponse<InputStream> r = client.send(req, HttpResponse.BodyHandlers.ofInputStream());
		try (InputStream in = r.body()) {
			if (r.statusCode() != 200) {
				throw new IOException("HTTP " + r.statusCode() + " de " + URI.create(url).getHost());
			}
			byte[] data = in.readNBytes(MAX_BYTES + 1);
			if (data.length > MAX_BYTES) {
				throw new IOException("respuesta demasiado grande");
			}
			return new String(data, StandardCharsets.UTF_8);
		}
	}

	/** En el hilo del servidor. */
	private static void result(MinecraftServer server, Release p, String actual, String mc, CommandSourceStack who) {
		Release before = fresh;
		fresh = p;
		if (p != null && (before == null || !before.version().equals(p.version()))) {
			Map<String, String> en = Texts.language(Texts.EN);
			LOGGER.warn("Heraldia: {} {}: {}. {}", format(en, "heraldia.version.nueva", p.version(), actual, mc),
					en.get("heraldia.version.descargar"), p.url(), en.get("heraldia.version.copia"));
			for (ServerPlayer player : new ArrayList<>(server.getPlayerList().getPlayers())) {
				if (who == null || player != who.getPlayer()) {
					onJoin(player);
				}
			}
		}
		if (who != null) {
			if (p == null) {
				who.sendSuccess(() -> Texts.t("heraldia.version.al_dia", actual, mc), false);
			} else {
				message(p, actual, mc, (who.getPlayer() != null ? Texts.language(who.getPlayer()) : Texts.language(Texts.ES)))
						.forEach(m -> who.sendSystemMessage(m));
				if (who.getPlayer() != null) {
					NOTIFIED.markStop(who.getPlayer().getUUID(), p.version().toString());
				}
			}
		}
	}

	/** Al entrar un jugador (y al encontrar una versión nueva, a los conectados): si es operador y aún no se le ha dicho. */
	private static void onJoin(ServerPlayer player) {
		Release p = fresh;
		if (p == null || !player.permissions().hasPermission(Permissions.COMMANDS_GAMEMASTER)
				|| !NOTIFIED.markStop(player.getUUID(), p.version().toString())) {
			return;
		}
		message(p, version(), SharedConstants.getCurrentVersion().name(), Texts.language(player))
				.forEach(player::sendSystemMessage);
		LOGGER.info("Heraldia: aviso de la versión {} a {}", p.version(), player.getGameProfile().name());
	}

	/** Las líneas del aviso en el chat: la versión nueva, el enlace clicable y la copia de seguridad. */
	static List<Component> message(Release p, String actual, String mc, Map<String, String> texts) {
		MutableComponent link = Texts.t(texts, "heraldia.version.descargar").withStyle(s -> s.withColor(ChatFormatting.GREEN)
				.withUnderlined(true).withClickEvent(new ClickEvent.OpenUrl(URI.create(p.url())))
				.withHoverEvent(new HoverEvent.ShowText(Component.literal(p.url()))));
		return List.of(
				Texts.t(texts, "heraldia.version.nueva", p.version().toString(), actual, mc).withStyle(ChatFormatting.GOLD)
						.append(" ").append(link),
				Texts.t(texts, "heraldia.version.copia").withStyle(ChatFormatting.YELLOW));
	}

	private static String format(Map<String, String> texts, String key, Object... args) {
		String t = texts.getOrDefault(key, key);
		return String.format(Locale.ROOT, t, args);
	}

	static String version() {
		return FabricLoader.getInstance().getModContainer(Heraldia.MOD_ID)
				.map(c -> c.getMetadata().getVersion().getFriendlyString()).orElse("?");
	}
}
