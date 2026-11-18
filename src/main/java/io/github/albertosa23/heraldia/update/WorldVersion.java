package io.github.albertosa23.heraldia.update;

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
 * guardara esto (o antes de instalar el mod) queda como generado con {@link #PREVIOUS}: no se sabe con cuál.
 *
 * @param generado      versión con la que se creó el mundo, o {@link #PREVIOUS}
 * @param ultima        última versión con la que se abrió (la de ahora tras arrancar)
 * @param nivelArreglos el {@link Fixes#NIVEL} de la versión con que se generó (0 si es {@link #PREVIOUS}): los
 *                      chunks y mobs de un mundo de un nivel menor pueden necesitar arreglos
 */
public record WorldVersion(String generated, String latest, int fixesLevel) {
	public static final String PREVIOUS = "anterior";
	public static final Codec<WorldVersion> CODEC = RecordCodecBuilder.create(i -> i.group(
			Codec.STRING.fieldOf("generado").forGetter(WorldVersion::generated),
			Codec.STRING.fieldOf("ultima").forGetter(WorldVersion::latest),
			Codec.INT.optionalFieldOf("nivel_arreglos", 0).forGetter(WorldVersion::fixesLevel)).apply(i, WorldVersion::new));

	/**
	 * Lo que queda guardado al arrancar con la versión {@code actual} (lógica pura): si no había nada, un mundo nuevo
	 * (con menos de {@code newTicks} de juego) se da por generado con la actual y uno viejo con {@link #PREVIOUS}; si
	 * había, se conserva la de generación y se pone la actual como última.
	 */
	public static WorldVersion onStart(Optional<WorldVersion> saved, String actual, long gameTime, long newTicks, int tier) {
		if (saved.isEmpty()) {
			boolean newValue = gameTime < newTicks;
			return new WorldVersion(newValue ? actual : PREVIOUS, actual, newValue ? tier : 0);
		}
		WorldVersion g = saved.get();
		return new WorldVersion(g.generated(), actual, g.fixesLevel());
	}

	/** ¿Se abre con una versión más antigua que la última con la que se abrió? (se avisa en el log). */
	public static boolean backsOff(Optional<WorldVersion> saved, String actual) {
		if (saved.isEmpty()) {
			return false;
		}
		Optional<Version> before = Version.of(saved.get().latest()), now = Version.of(actual);
		return before.isPresent() && now.isPresent() && now.get().compareTo(before.get()) < 0;
	}

	/** El adjunto, aparte para que los tests no registren nada al cargar la clase. */
	static final class Type {
		static final AttachmentType<WorldVersion> VERSION = AttachmentRegistry.create(Heraldia.id("version_mundo"), b -> b.persistent(CODEC));

		private Type() {
		}
	}
}
