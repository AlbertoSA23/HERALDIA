package io.github.albertosa23.heraldia.comando;

import net.fabricmc.fabric.api.command.v2.CommandRegistrationCallback;
import net.minecraft.commands.Commands;

/**
 * Herramientas de administración: /heraldia revisar (ruta guiada de revisión, operadores), /heraldia estado (resumen
 * del servidor, todos; los operadores ven más) y /heraldia recargar (recarga en caliente, operadores). Una línea en
 * Heraldia.onInitialize.
 */
public final class Admin {
	private Admin() {
	}

	public static void register() {
		CommandRegistrationCallback.EVENT.register((dispatcher, access, environment) -> dispatcher.register(Commands.literal("heraldia")
				.then(RevisarCommand.nodo())
				.then(EstadoCommand.nodo())
				.then(RecargarCommand.nodo())));
		RevisarCommand.registrarEventos();
	}
}
