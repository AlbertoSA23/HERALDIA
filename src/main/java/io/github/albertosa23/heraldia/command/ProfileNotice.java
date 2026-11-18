package io.github.albertosa23.heraldia.command;

import com.mojang.serialization.Codec;
import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.config.ProfileAdvice;
import io.github.albertosa23.heraldia.config.Profiles;
import io.github.albertosa23.heraldia.update.Updater;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import net.fabricmc.fabric.api.attachment.v1.AttachmentRegistry;
import net.fabricmc.fabric.api.attachment.v1.AttachmentType;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.fabricmc.fabric.api.networking.v1.ServerPlayConnectionEvents;
import net.minecraft.ChatFormatting;
import net.minecraft.network.chat.ClickEvent;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.HoverEvent;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.permissions.Permissions;
import org.jspecify.annotations.Nullable;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * The light profile's notices at startup ({@link ProfileAdvice} decides):
 * <ul>
 * <li>First start (the file does not say which profile to use): one line in the log with the memory and cores the JVM sees
 * and the suggested profile; if it is not the one in use, each operator gets it in the chat on joining, with a button that
 * runs /heraldia config profile ligero (which, in a world already started, first asks for confirmation). It only suggests:
 * nothing changes unless an operator chooses it. Once a profile is in the file (the mod writes it on startup), it is quiet.</li>
 * <li>Seams: the generation options in use are saved in the world (attachment heraldia:generacion_mundo); if they changed
 * since the previous start in a world already played, a warning in the log with what changed, and each operator gets it
 * in the chat on joining (once per server session).</li>
 * </ul>
 * Nothing per tick: one look at startup and one per operator joining. One line in Heraldia.onInitialize.
 */
public final class ProfileNotice {
	private static final Logger LOGGER = LoggerFactory.getLogger(Heraldia.MOD_ID);
	private static volatile @Nullable String suggested;
	private static volatile @Nullable String seams;
	private static volatile String memory = "?";
	private static volatile int cores;
	private static final Map<UUID, Boolean> NOTIFIED = new ConcurrentHashMap<>();

	private ProfileNotice() {
	}

	/** The world's generation options at its last start (new data in the world, absent in worlds from before). */
	static final class Type {
		static final AttachmentType<Map<String, String>> GENERATION = AttachmentRegistry.create(Heraldia.id("generacion_mundo"),
				b -> b.persistent(Codec.unboundedMap(Codec.STRING, Codec.STRING)));

		private Type() {
		}
	}

	public static void register() {
		Type.GENERATION.identifier();
		ServerLifecycleEvents.SERVER_STARTED.register(ProfileNotice::onStart);
		ServerPlayConnectionEvents.JOIN.register((handler, sender, server) -> server.schedule(server.wrapRunnable(() -> {
			if (!handler.player.hasDisconnected()) {
				onJoin(handler.player);
			}
		})));
	}

	private static void onStart(MinecraftServer server) {
		NOTIFIED.clear();
		HeraldiaConfig cfg = HeraldiaConfig.get();
		Profiles ps = HeraldiaConfig.profiles();
		// suggestion (first start)
		suggested = null;
		if (!cfg.profileInFile()) {
			Runtime rt = Runtime.getRuntime();
			memory = ProfileAdvice.gb(rt.maxMemory());
			cores = rt.availableProcessors();
			Optional<String> s = ProfileAdvice.suggest(rt.maxMemory(), cores);
			String chosen = cfg.profile().chosen();
			if (s.isPresent() && !s.get().equals(chosen)) {
				suggested = s.get();
				LOGGER.info("Heraldia: perfil: no está elegido en config/heraldia.json; la JVM tiene {} GB y {} núcleos: se sugiere el perfil {} "
						+ "(generación más ligera; /heraldia config profile {} o \"perfil\": \"{}\" en el fichero). Se sigue con {}.",
						memory, cores, s.get(), s.get(), s.get(), chosen);
			} else {
				LOGGER.info("Heraldia: perfil: no está elegido en config/heraldia.json; la JVM tiene {} GB y {} núcleos: el perfil {} va bien en este equipo",
						memory, cores, chosen);
			}
		}
		// seams (generation changed in a world already played)
		ServerLevel ow = server.overworld();
		Map<String, String> stored = ow.getAttached(Type.GENERATION);
		Map<String, String> now = ProfileAdvice.fingerprint(cfg.values(), ps.generation());
		boolean started = ow.getGameTime() >= Updater.NEW_WORLD_TICKS;
		seams = null;
		boolean generationProfile = ps.touchesGeneration(cfg.profile().chosen());
		Map<String, String[]> fromDefaults = stored == null ? ProfileAdvice.defaultChanges(now, cfg.profile().pinned().keySet()) : Map.of();
		if (ProfileAdvice.warnSeams(stored, now, started, generationProfile, fromDefaults)) {
			List<String> what = new ArrayList<>();
			if (stored == null) {
				if (generationProfile) {
					what.add("perfil=" + cfg.profile().chosen());
				}
				fromDefaults.forEach((k, v) -> what.add(k + " " + v[0] + " → " + v[1]));
			} else {
				ProfileAdvice.changed(stored, now).forEach((k, v) -> what.add(k + " " + v[0] + " → " + v[1]));
			}
			seams = String.join(", ", what);
			LOGGER.warn("Heraldia: la generación del mundo ha cambiado desde el último arranque ({}). Lo ya generado no cambia: solo los "
					+ "chunks nuevos siguen la configuración nueva, y junto a lo ya explorado puede haber costuras (una zona densa junto a "
					+ "otra vacía, caminos que acaban en el borde, medianas que /locate ya no encuentra). Ver docs/CONFIGURATION.md, «Light profile».", seams);
		}
		ow.setAttached(Type.GENERATION, Map.copyOf(now));
	}

	/** When an operator joins: the suggestion and the seam warning of this server session, once each. */
	private static void onJoin(ServerPlayer player) {
		String s = suggested, c = seams;
		if (s == null && c == null || !player.permissions().hasPermission(Permissions.COMMANDS_GAMEMASTER)
				|| NOTIFIED.putIfAbsent(player.getUUID(), Boolean.TRUE) != null) {
			return;
		}
		message(Texts.language(player), s, memory, cores, c).forEach(player::sendSystemMessage);
	}

	/** The chat lines for an operator (public for the tests): the suggestion with its button, and the seam warning. */
	public static List<Component> message(Map<String, String> l, @Nullable String suggestion, String memory, int cores, @Nullable String seams) {
		List<Component> out = new ArrayList<>();
		if (suggestion != null) {
			String cmd = "/" + ConfigPanel.CMD + " profile " + suggestion;
			out.add(Texts.t(l, "heraldia.ligero.sugerencia", memory, cores).withStyle(ChatFormatting.GOLD));
			out.add(Texts.t(l, "heraldia.ligero.sugerencia.boton").withStyle(st -> st.withColor(ChatFormatting.GREEN).withUnderlined(true)
					.withClickEvent(new ClickEvent.RunCommand(cmd))
					.withHoverEvent(new HoverEvent.ShowText(Texts.t(l, "heraldia.ligero.sugerencia.ayuda")))));
			out.add(Texts.t(l, "heraldia.ligero.sugerencia.ignorar").withStyle(ChatFormatting.GRAY));
		}
		if (seams != null) {
			out.add(Texts.t(l, "heraldia.ligero.costuras", seams).withStyle(ChatFormatting.YELLOW));
		}
		return out;
	}
}
