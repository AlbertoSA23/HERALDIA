package io.github.albertosa23.heraldia.quests;

import com.mojang.serialization.Codec;
import com.mojang.serialization.codecs.RecordCodecBuilder;

/**
 * A quest from a village's board (immutable). It is saved whole in the player's data when accepted, so it
 * survives the board's rotation and changes in the world.
 *
 * @param villageX   chunk of the start of the village that gives it (its key, see {@link Reputation#key})
 * @param villageZ   likewise
 * @param period     rotation period it came out in ({@link Generator#period})
 * @param gap        position on the board (0..3)
 * @param type       what has to be done
 * @param target     item (bring: "minecraft:bread"), unique (guardian: "castillo"), structure (explore:
 *                   "heraldia:medianas/posada/llanuras"), name of the neighboring village (journey) or empty (arena)
 * @param amount     items to bring or wave to clear (0 in the others)
 * @param x          block of the target (guardian, explore, journey; 0 in the others)
 * @param z          likewise
 * @param emeralds   reward
 * @param experience reward (points)
 */
public record Quest(int villageX, int villageZ, long period, int gap, Type type, String target, int amount, int x, int z,
					  int emeralds, int experience) {
	public static final Codec<Quest> CODEC = RecordCodecBuilder.create(i -> i.group(
			Codec.INT.fieldOf("aldea_x").forGetter(Quest::villageX),
			Codec.INT.fieldOf("aldea_z").forGetter(Quest::villageZ),
			Codec.LONG.fieldOf("periodo").forGetter(Quest::period),
			Codec.INT.fieldOf("hueco").forGetter(Quest::gap),
			Type.CODEC.fieldOf("tipo").forGetter(Quest::type),
			Codec.STRING.optionalFieldOf("objetivo", "").forGetter(Quest::target),
			Codec.INT.optionalFieldOf("cantidad", 0).forGetter(Quest::amount),
			Codec.INT.optionalFieldOf("x", 0).forGetter(Quest::x),
			Codec.INT.optionalFieldOf("z", 0).forGetter(Quest::z),
			Codec.INT.optionalFieldOf("esmeraldas", 0).forGetter(Quest::emeralds),
			Codec.INT.optionalFieldOf("experiencia", 0).forGetter(Quest::experience)).apply(i, Quest::new));

	/** Stable id: village, period and gap ("12.-40.7.1"). Two players with the same quest have the same id. */
	public String id() {
		return villageX + "." + villageZ + "." + period + "." + gap;
	}

	public String village() {
		return Reputation.key(villageX, villageZ);
	}

	/** Reputation it gives with its village on delivery. */
	public int reputation() {
		return type.reputation;
	}

	/** Does it have a site to go to (and a heading hint)? */
	public boolean withPlace() {
		return type == Type.GUARDIAN || type == Type.EXPLORE || type == Type.JOURNEY;
	}
}
