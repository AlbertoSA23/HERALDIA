package io.github.albertosa23.heraldia.update;

import com.mojang.serialization.Codec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.version.Version;
import java.util.Optional;
import net.fabricmc.fabric.api.attachment.v1.AttachmentRegistry;
import net.fabricmc.fabric.api.attachment.v1.AttachmentType;

/**
 * Mod version the world was generated with and the last one it was opened with (T46), saved in the overworld
 * (Fabric API persistent attachment on the {@code ServerLevel}, like the arena). A world that already existed before the mod
 * saved this (or before the mod was installed) is recorded as generated with {@link #PREVIOUS}: which one is unknown.
 *
 * @param generated  version the world was created with, or {@link #PREVIOUS}
 * @param latest     last version it was opened with (the current one after startup)
 * @param fixesLevel the fix level ({@link Fixes}) of the version it was generated with (0 if it is {@link #PREVIOUS}): the
 *                   chunks and mobs of a world with a lower level may need fixes
 */
public record WorldVersion(String generated, String latest, int fixesLevel) {
	public static final String PREVIOUS = "anterior";
	public static final Codec<WorldVersion> CODEC = RecordCodecBuilder.create(i -> i.group(
			Codec.STRING.fieldOf("generado").forGetter(WorldVersion::generated),
			Codec.STRING.fieldOf("ultima").forGetter(WorldVersion::latest),
			Codec.INT.optionalFieldOf("nivel_arreglos", 0).forGetter(WorldVersion::fixesLevel)).apply(i, WorldVersion::new));

	/**
	 * What is saved at startup with version {@code actual} (pure logic): if there was nothing, a new world
	 * (with less than {@code newTicks} of play) is treated as generated with the current one and an old one with {@link #PREVIOUS}; if
	 * there was, the generation one is kept and the current one is set as latest.
	 */
	public static WorldVersion onStart(Optional<WorldVersion> saved, String actual, long gameTime, long newTicks, int tier) {
		if (saved.isEmpty()) {
			boolean newValue = gameTime < newTicks;
			return new WorldVersion(newValue ? actual : PREVIOUS, actual, newValue ? tier : 0);
		}
		WorldVersion g = saved.get();
		return new WorldVersion(g.generated(), actual, g.fixesLevel());
	}

	/** Is it opened with an older version than the last one it was opened with? (logged as a warning). */
	public static boolean backsOff(Optional<WorldVersion> saved, String actual) {
		if (saved.isEmpty()) {
			return false;
		}
		Optional<Version> before = Version.of(saved.get().latest()), now = Version.of(actual);
		return before.isPresent() && now.isPresent() && now.get().compareTo(before.get()) < 0;
	}

	/** The attachment, kept apart so the tests register nothing when the class loads. */
	static final class Type {
		static final AttachmentType<WorldVersion> VERSION = AttachmentRegistry.create(Heraldia.id("version_mundo"), b -> b.persistent(CODEC));

		private Type() {
		}
	}
}
