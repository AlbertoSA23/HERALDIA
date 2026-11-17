package io.github.albertosa23.heraldia.comando;

import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.version.Avisados;
import io.github.albertosa23.heraldia.version.Publicaciones;
import io.github.albertosa23.heraldia.version.Publicaciones.Publicacion;
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
 * ({@link Publicaciones}: semver, sin pre-publicaciones salvo update_check.prereleases; el Minecraft de cada publicación
 * sale del gradle.properties de su etiqueta). Si la hay, lo dice en la consola y en el chat a cada operador al entrar,
 * una vez por sesión del servidor ({@link Avisados}), en su idioma, con el enlace a la descarga y la recomendación de
 * hacer antes una copia de seguridad. /heraldia update check (operadores) lo comprueba en el momento.
 * <p>Sin telemetría: una petición GET sin datos del servidor ni del jugador, con un User-Agent genérico y tiempos de
 * espera cortos. Sin red, o con una respuesta rara, solo deja una línea en el log. Opción update_check.activado; la
 * propiedad del sistema heraldia.update_check.url cambia la dirección (las pruebas apuntan a un servidor local).
 */
public final class AvisoVersion {
	private static final Logger LOGGER = LoggerFactory.getLogger(Heraldia.MOD_ID);
	public static final String OPCION = "update_check.activado", OPCION_PRE = "update_check.prereleases";
	/** Releases de GitHub del repositorio del mod (contact.sources de fabric.mod.json). */
	static final String URL = "https://api.github.com/repos/AlbertoSA23/HERALDIA/releases?per_page=20";
	static final String PROPIEDAD_URL = "heraldia.update_check.url";
	static final String USER_AGENT = "Heraldia-update-check";
	static final Duration CONEXION = Duration.ofSeconds(5), RESPUESTA = Duration.ofSeconds(10);
	static final long PERIODO_H = 24;
	/** Lo más que se lee de una respuesta (la de GitHub con 20 publicaciones y su registro de cambios ocupa unos cientos de kB). */
	static final int MAX_BYTES = 4 << 20;
	private static final Avisados AVISADOS = new Avisados();
	private static volatile Publicacion nueva;
	private static ScheduledExecutorService hilo;

	private AvisoVersion() {
	}

	public static void registrar() {
		ServerLifecycleEvents.SERVER_STARTED.register(AvisoVersion::arrancar);
		ServerLifecycleEvents.SERVER_STOPPING.register(server -> parar());
		ServerPlayConnectionEvents.JOIN.register((handler, sender, server) -> server.schedule(server.wrapRunnable(() -> {
			if (!handler.player.hasDisconnected()) {
				alEntrar(handler.player);
			}
		})));
	}

	/** /heraldia update check (operadores): comprueba ahora, aunque update_check.activado esté desactivada. */
	static LiteralArgumentBuilder<CommandSourceStack> nodo() {
		return Commands.literal("update")
				.requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))
				.then(Commands.literal("check").executes(ctx -> {
					CommandSourceStack src = ctx.getSource();
					src.sendSuccess(() -> Textos.t("heraldia.version.comprobando"), false);
					MinecraftServer server = src.getServer();
					Thread t = new Thread(() -> comprobar(server, src), "Heraldia update check");
					t.setDaemon(true);
					t.start();
					return 1;
				}));
	}

	private static synchronized void arrancar(MinecraftServer server) {
		parar();
		nueva = null;
		if (!HeraldiaConfig.get().getBool(OPCION)) {
			LOGGER.info("Heraldia: aviso de versión nueva desactivado ({} = false)", OPCION);
			return;
		}
		hilo = Executors.newSingleThreadScheduledExecutor(r -> {
			Thread t = new Thread(r, "Heraldia update check");
			t.setDaemon(true);
			t.setPriority(Thread.MIN_PRIORITY);
			return t;
		});
		hilo.scheduleAtFixedRate(() -> comprobar(server, null), 0, PERIODO_H, TimeUnit.HOURS);
	}

	private static synchronized void parar() {
		if (hilo != null) {
			hilo.shutdownNow();
			hilo = null;
		}
	}

	/** En el hilo propio: pregunta y pasa el resultado al hilo del servidor. Nunca lanza. */
	private static void comprobar(MinecraftServer server, CommandSourceStack quien) {
		long t0 = System.nanoTime();
		String actual = version(), mc = SharedConstants.getCurrentVersion().name();
		try {
			Optional<Version> va = Version.de(actual);
			if (va.isEmpty()) {
				throw new IOException("la versión instalada «" + actual + "» no es una versión");
			}
			Optional<Publicacion> p = consultar(url(), va.get(), mc, HeraldiaConfig.get().getBool(OPCION_PRE));
			long ms = (System.nanoTime() - t0) / 1_000_000;
			LOGGER.info("Heraldia: comprobación de versión nueva ({} para Minecraft {}): {} en {} ms", actual, mc,
					p.map(x -> x.version().toString()).orElse("ninguna"), ms);
			server.execute(() -> resultado(server, p.orElse(null), actual, mc, quien));
		} catch (Exception e) {
			LOGGER.info("Heraldia: no se pudo comprobar si hay una versión nueva ({}: {})", e.getClass().getSimpleName(), e.getMessage());
			if (quien != null) {
				server.execute(() -> quien.sendFailure(Textos.t("heraldia.version.sin_respuesta")));
			}
		}
	}

	static String url() {
		String u = System.getProperty(PROPIEDAD_URL);
		return u == null || u.isBlank() ? URL : u;
	}

	/** Pide la lista y elige; para las de GitHub, el Minecraft de cada candidata sale del gradle.properties de su etiqueta. */
	static Optional<Publicacion> consultar(String url, Version actual, String mc, boolean pre) throws IOException, InterruptedException {
		HttpClient cliente = HttpClient.newBuilder().connectTimeout(CONEXION).followRedirects(HttpClient.Redirect.NORMAL).build();
		List<Publicacion> todas = Publicaciones.leer(pedir(cliente, url, "application/vnd.github+json, application/json"));
		return Publicaciones.elegir(todas, actual, mc, pre, p -> {
			String props = propiedades(url, p.etiqueta());
			if (props == null) {
				return Optional.empty();
			}
			try {
				return Publicaciones.minecraftDePropiedades(pedir(cliente, props, "application/vnd.github.raw"));
			} catch (IOException e) {
				LOGGER.info("Heraldia: no se pudo leer el Minecraft de la {} ({})", p.etiqueta(), e.getMessage());
				return Optional.empty();
			} catch (InterruptedException e) {
				Thread.currentThread().interrupt();
				return Optional.empty();
			}
		});
	}

	/** .../repos/&lt;dueño&gt;/&lt;repo&gt;/releases?... -> .../repos/&lt;dueño&gt;/&lt;repo&gt;/contents/gradle.properties?ref=&lt;etiqueta&gt;. */
	static String propiedades(String url, String etiqueta) {
		int i = url.indexOf("/releases");
		if (i < 0 || etiqueta == null || etiqueta.isEmpty()) {
			return null;
		}
		return url.substring(0, i) + "/contents/gradle.properties?ref=" + URLEncoder.encode(etiqueta, StandardCharsets.UTF_8);
	}

	private static String pedir(HttpClient cliente, String url, String accept) throws IOException, InterruptedException {
		HttpRequest req = HttpRequest.newBuilder(URI.create(url)).timeout(RESPUESTA).header("User-Agent", USER_AGENT)
				.header("Accept", accept).GET().build();
		HttpResponse<InputStream> r = cliente.send(req, HttpResponse.BodyHandlers.ofInputStream());
		try (InputStream in = r.body()) {
			if (r.statusCode() != 200) {
				throw new IOException("HTTP " + r.statusCode() + " de " + URI.create(url).getHost());
			}
			byte[] datos = in.readNBytes(MAX_BYTES + 1);
			if (datos.length > MAX_BYTES) {
				throw new IOException("respuesta demasiado grande");
			}
			return new String(datos, StandardCharsets.UTF_8);
		}
	}

	/** En el hilo del servidor. */
	private static void resultado(MinecraftServer server, Publicacion p, String actual, String mc, CommandSourceStack quien) {
		Publicacion antes = nueva;
		nueva = p;
		if (p != null && (antes == null || !antes.version().equals(p.version()))) {
			Map<String, String> en = Textos.idioma(Textos.EN);
			LOGGER.warn("Heraldia: {} {}: {}. {}", formato(en, "heraldia.version.nueva", p.version(), actual, mc),
					en.get("heraldia.version.descargar"), p.url(), en.get("heraldia.version.copia"));
			for (ServerPlayer jugador : new ArrayList<>(server.getPlayerList().getPlayers())) {
				if (quien == null || jugador != quien.getPlayer()) {
					alEntrar(jugador);
				}
			}
		}
		if (quien != null) {
			if (p == null) {
				quien.sendSuccess(() -> Textos.t("heraldia.version.al_dia", actual, mc), false);
			} else {
				mensaje(p, actual, mc, Textos.idioma(quien.getPlayer() != null ? quien.getPlayer().clientInformation().language() : Textos.ES))
						.forEach(m -> quien.sendSystemMessage(m));
				if (quien.getPlayer() != null) {
					AVISADOS.marcar(quien.getPlayer().getUUID(), p.version().toString());
				}
			}
		}
	}

	/** Al entrar un jugador (y al encontrar una versión nueva, a los conectados): si es operador y aún no se le ha dicho. */
	private static void alEntrar(ServerPlayer jugador) {
		Publicacion p = nueva;
		if (p == null || !jugador.permissions().hasPermission(Permissions.COMMANDS_GAMEMASTER)
				|| !AVISADOS.marcar(jugador.getUUID(), p.version().toString())) {
			return;
		}
		mensaje(p, version(), SharedConstants.getCurrentVersion().name(), Textos.idioma(jugador.clientInformation().language()))
				.forEach(jugador::sendSystemMessage);
		LOGGER.info("Heraldia: aviso de la versión {} a {}", p.version(), jugador.getGameProfile().name());
	}

	/** Las líneas del aviso en el chat: la versión nueva, el enlace clicable y la copia de seguridad. */
	static List<Component> mensaje(Publicacion p, String actual, String mc, Map<String, String> textos) {
		MutableComponent enlace = Textos.t(textos, "heraldia.version.descargar").withStyle(s -> s.withColor(ChatFormatting.GREEN)
				.withUnderlined(true).withClickEvent(new ClickEvent.OpenUrl(URI.create(p.url())))
				.withHoverEvent(new HoverEvent.ShowText(Component.literal(p.url()))));
		return List.of(
				Textos.t(textos, "heraldia.version.nueva", p.version().toString(), actual, mc).withStyle(ChatFormatting.GOLD)
						.append(" ").append(enlace),
				Textos.t(textos, "heraldia.version.copia").withStyle(ChatFormatting.YELLOW));
	}

	private static String formato(Map<String, String> textos, String clave, Object... args) {
		String t = textos.getOrDefault(clave, clave);
		return String.format(Locale.ROOT, t, args);
	}

	static String version() {
		return FabricLoader.getInstance().getModContainer(Heraldia.MOD_ID)
				.map(c -> c.getMetadata().getVersion().getFriendlyString()).orElse("?");
	}
}
