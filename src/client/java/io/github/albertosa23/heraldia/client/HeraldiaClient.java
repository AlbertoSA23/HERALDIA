package io.github.albertosa23.heraldia.client;

import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import java.nio.file.Path;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.api.EnvType;
import net.fabricmc.api.Environment;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.fabricmc.loader.api.FabricLoader;
import net.minecraft.client.Minecraft;

/**
 * Punto de entrada del cliente (solo se carga en el cliente: el servidor dedicado nunca ve este source set).
 * En un jugador la configuración se lee al arrancar el juego ({@code Heraldia.onInitialize}); para que lo guardado en la
 * pantalla se aplique al volver a abrir un mundo sin reiniciar el juego, se vuelve a leer al cerrar el servidor
 * integrado y, si no hay ninguno abierto, nada más guardar.
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

	/** Tras guardar: si no hay un mundo de un jugador abierto, la configuración nueva pasa a estar en uso ya. */
	static void applyIfIdle(Minecraft minecraft) {
		if (minecraft.getSingleplayerServer() == null) {
			HeraldiaConfig.load(configFile());
		}
	}
}
