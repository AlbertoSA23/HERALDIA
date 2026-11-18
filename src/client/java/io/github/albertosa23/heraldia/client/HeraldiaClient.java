package io.github.albertosa23.heraldia.client;

import io.github.albertosa23.heraldia.command.ReloadCommand;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import java.nio.file.Path;
import java.util.List;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.api.EnvType;
import net.fabricmc.api.Environment;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.fabricmc.loader.api.FabricLoader;
import net.minecraft.client.Minecraft;
import net.minecraft.client.server.IntegratedServer;
import net.minecraft.network.chat.Component;

/**
 * Client entry point (only loaded on the client: the dedicated server never sees this source set).
 * In single player the configuration is read when the game starts ({@code Heraldia.onInitialize}); so that what the
 * screen saves applies when a world is reopened without restarting the game, it is read again when the integrated server
 * closes and, if none is open, right after saving; with one open, saving hot-reloads what does not affect generation
 * (like /heraldia reload).
 */
@Environment(EnvType.CLIENT)
public final class HeraldiaClient implements ClientModInitializer {
	@Override
	public void onInitializeClient() {
		ServerLifecycleEvents.SERVER_STOPPED.register(server -> HeraldiaConfig.load(configFile()));
	}

	static Path configFile() {
		return FabricLoader.getInstance().getConfigDir().resolve("heraldia.json");
	}

	/**
	 * After saving: if no single-player world is open, the new configuration is in use right away. If one is, the same path
	 * as /heraldia reload (on its server thread): the options that do not affect generation apply now and the report goes
	 * to the chat; the others wait until the world is reopened.
	 */
	static void applyIfIdle(Minecraft minecraft) {
		IntegratedServer server = minecraft.getSingleplayerServer();
		if (server == null) {
			HeraldiaConfig.load(configFile());
			return;
		}
		server.execute(() -> {
			List<Component> lines = ReloadCommand.apply(server);
			server.getPlayerList().getPlayers().forEach(p -> lines.forEach(p::sendSystemMessage));
		});
	}
}
