package io.github.albertosa23.heraldia.actualizar;

import com.mojang.serialization.Codec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.version.Version;
import java.util.Optional;
import net.fabricmc.fabric.api.attachment.v1.AttachmentRegistry;
import net.fabricmc.fabric.api.attachment.v1.AttachmentType;

/**
 * Versión del mod con la que se generó el mundo y la última con la que se abrió (T46), guardadas en el mundo principal
 * (adjunto persistente de Fabric API en el {@code ServerLevel}, como la arena). Un mundo que ya existía antes de que el mod
 * guardara esto (o antes de instalar el mod) queda como generado con {@link #ANTERIOR}: no se sabe con cuál.
 *
 * @param generado      versión con la que se creó el mundo, o {@link #ANTERIOR}
 * @param ultima        última versión con la que se abrió (la de ahora tras arrancar)
 * @param nivelArreglos el {@link Arreglos#NIVEL} de la versión con que se generó (0 si es {@link #ANTERIOR}): los
 *                      chunks y mobs de un mundo de un nivel menor pueden necesitar arreglos
 */
public record VersionMundo(String generado, String ultima, int nivelArreglos) {
	public static final String ANTERIOR = "anterior";
	public static final Codec<VersionMundo> CODEC = RecordCodecBuilder.create(i -> i.group(
			Codec.STRING.fieldOf("generado").forGetter(VersionMundo::generado),
			Codec.STRING.fieldOf("ultima").forGetter(VersionMundo::ultima),
			Codec.INT.optionalFieldOf("nivel_arreglos", 0).forGetter(VersionMundo::nivelArreglos)).apply(i, VersionMundo::new));

	/**
	 * Lo que queda guardado al arrancar con la versión {@code actual} (lógica pura): si no había nada, un mundo nuevo
	 * (con menos de {@code nuevoTicks} de juego) se da por generado con la actual y uno viejo con {@link #ANTERIOR}; si
	 * había, se conserva la de generación y se pone la actual como última.
	 */
	public static VersionMundo alArrancar(Optional<VersionMundo> guardada, String actual, long gameTime, long nuevoTicks, int nivel) {
		if (guardada.isEmpty()) {
			boolean nuevo = gameTime < nuevoTicks;
			return new VersionMundo(nuevo ? actual : ANTERIOR, actual, nuevo ? nivel : 0);
		}
		VersionMundo g = guardada.get();
		return new VersionMundo(g.generado(), actual, g.nivelArreglos());
	}

	/** ¿Se abre con una versión más antigua que la última con la que se abrió? (se avisa en el log). */
	public static boolean retrocede(Optional<VersionMundo> guardada, String actual) {
		if (guardada.isEmpty()) {
			return false;
		}
		Optional<Version> antes = Version.de(guardada.get().ultima()), ahora = Version.de(actual);
		return antes.isPresent() && ahora.isPresent() && ahora.get().compareTo(antes.get()) < 0;
	}

	/** El adjunto, aparte para que los tests no registren nada al cargar la clase. */
	static final class Tipo {
		static final AttachmentType<VersionMundo> VERSION = AttachmentRegistry.create(Heraldia.id("version_mundo"), b -> b.persistent(CODEC));

		private Tipo() {
		}
	}
}
