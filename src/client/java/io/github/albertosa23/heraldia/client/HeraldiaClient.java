package io.github.albertosa23.heraldia.client;

import io.github.albertosa23.heraldia.comando.RecargarCommand;
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
 * Punto de entrada del cliente (solo se carga en el cliente: el servidor dedicado nunca ve este source set).
 * En un jugador la configuración se lee al arrancar el juego ({@code Heraldia.onInitialize}); para que lo guardado en la
 * pantalla se aplique al volver a abrir un mundo sin reiniciar el juego, se vuelve a leer al cerrar el servidor
 * integrado y, si no hay ninguno abierto, nada más guardar; con uno abierto, al guardar se recarga en caliente lo que no
 * afecta a la generación (como /heraldia recargar).
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
	 * Tras guardar: si no hay un mundo de un jugador abierto, la configuración nueva pasa a estar en uso ya. Si lo hay, el
	 * mismo camino que /heraldia recargar (en el hilo de su servidor): se aplican ya las opciones que no afectan a la
	 * generación y el informe sale en el chat; las demás esperan a volver a abrir el mundo.
	 */
	static void applyIfIdle(Minecraft minecraft) {
		IntegratedServer server = minecraft.getSingleplayerServer();
		if (server == null) {
			HeraldiaConfig.load(configFile());
			return;
		}
		server.execute(() -> {
			List<Component> lines = RecargarCommand.aplicar(server);
			server.getPlayerList().getPlayers().forEach(p -> lines.forEach(p::sendSystemMessage));
		});
	}
}
