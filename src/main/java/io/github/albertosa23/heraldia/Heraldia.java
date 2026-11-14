package io.github.albertosa23.heraldia;

import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.minecraft.core.registries.Registries;
import net.minecraft.server.MinecraftServer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/** Punto de entrada. El contenido es de datos (data/heraldia); aquí solo se informa de lo cargado. */
public final class Heraldia implements ModInitializer {
	public static final String MOD_ID = "heraldia";
	private static final Logger LOGGER = LoggerFactory.getLogger(MOD_ID);

	@Override
	public void onInitialize() {
		ServerLifecycleEvents.SERVER_STARTED.register(Heraldia::logRegisteredStructures);
	}

	/** Deja en el log cuántas estructuras del mod están en el registro, para comprobar la carga sin entrar al juego. */
	private static void logRegisteredStructures(MinecraftServer server) {
		long count = server.registryAccess().lookupOrThrow(Registries.STRUCTURE).keySet().stream()
				.filter(id -> MOD_ID.equals(id.getNamespace()))
				.count();
		LOGGER.info("Heraldia: {} estructuras registradas", count);
	}
}
