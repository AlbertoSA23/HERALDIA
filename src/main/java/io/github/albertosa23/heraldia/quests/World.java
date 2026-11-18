package io.github.albertosa23.heraldia.quests;

import com.mojang.serialization.Codec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import java.util.ArrayList;
import java.util.List;

/**
 * What is saved of the quests in the overworld (Fabric persistent attachment on the {@code ServerLevel}):
 * how many have been delivered by everyone (for /heraldia status) and where the guardians have fallen since there are quests
 * (so as not to ask for defeating one that is no longer there from the next period on). Immutable.
 */
public record World(int completed, List<Fallen> fallen) {
	/** Fallen guardians that are remembered: one per unique, more than enough. */
	public static final int MAX_FALLEN = 1000;
	public static final World EMPTY = new World(0, List.of());

	/** A fallen guardian: its unique, where and when (world tick). */
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

	/** Has the guardian of that unique at (x, z) already fallen? (within {@link Objectives#GUARDIAN_RADIUS}) */
	public boolean hasFallen(String unique, int x, int z) {
		return fellBefore(unique, x, z, Long.MAX_VALUE);
	}

	/**
	 * Did it fall before tick {@code before}? A period's board only discards the guardians fallen before it
	 * started: so it does not change mid-period (the ids of its quests are their gap) and the fallen one stops showing in the
	 * next one.
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
