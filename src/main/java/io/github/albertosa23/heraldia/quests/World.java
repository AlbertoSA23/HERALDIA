package io.github.albertosa23.heraldia.quests;

import com.mojang.serialization.Codec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import java.util.ArrayList;
import java.util.List;

/**
 * Lo que se guarda de los encargos en el mundo principal (adjunto persistente de Fabric en el {@code ServerLevel}):
 * cuántos se han entregado entre todos (para /heraldia status) y dónde han caído los guardianes desde que hay encargos
 * (para no pedir vencer a uno que ya no está desde el periodo siguiente). Inmutable.
 */
public record World(int completed, List<Fallen> fallen) {
	/** Guardianes caídos que se recuerdan: uno por única, de sobra. */
	public static final int MAX_FALLEN = 1000;
	public static final World EMPTY = new World(0, List.of());

	/** Un guardián caído: su única, dónde y cuándo (tick del mundo). */
	public record Fallen(String unique, int x, int z, long tick) {
		public static final Codec<Fallen> CODEC = RecordCodecBuilder.create(i -> i.group(
				Codec.STRING.fieldOf("unica").forGetter(Fallen::unique),
				Codec.INT.fieldOf("x").forGetter(Fallen::x),
				Codec.INT.fieldOf("z").forGetter(Fallen::z),
				Codec.LONG.optionalFieldOf("tick", 0L).forGetter(Fallen::tick)).apply(i, Fallen::new));
	}

	public static final Codec<World> CODEC = RecordCodecBuilder.create(i -> i.group(
			Codec.INT.optionalFieldOf("completados", 0).forGetter(World::completed),
			Fallen.CODEC.listOf().optionalFieldOf("caidos", List.of()).forGetter(World::fallen)).apply(i, World::new));

	public World {
		fallen = List.copyOf(fallen);
	}

	public World isCompleted() {
		return new World(completed + 1, fallen);
	}

	public World falls(String unique, int x, int z, long tick) {
		if (hasFallen(unique, x, z)) {
			return this;
		}
		List<Fallen> l = new ArrayList<>(fallen);
		l.add(new Fallen(unique, x, z, tick));
		while (l.size() > MAX_FALLEN) {
			l.remove(0);
		}
		return new World(completed, l);
	}

	/** ¿Ha caído ya el guardián de esa única en (x, z)? (a menos de {@link Objectives#GUARDIAN_RADIUS}) */
	public boolean hasFallen(String unique, int x, int z) {
		return fellBefore(unique, x, z, Long.MAX_VALUE);
	}

	/**
	 * ¿Cayó antes del tick {@code before}? El tablón de un periodo solo descarta los guardianes caídos antes de que
	 * empezara: así no cambia a mitad de periodo (los ids de sus encargos son su hueco) y el caído deja de salir en el
	 * siguiente.
	 */
	public boolean fellBefore(String unique, int x, int z, long before) {
		for (Fallen c : fallen) {
			if (c.tick() < before && c.unique().equals(unique) && Objectives.near(x, z, c.x(), c.z(), Objectives.GUARDIAN_RADIUS)) {
				return true;
			}
		}
		return false;
	}
}
