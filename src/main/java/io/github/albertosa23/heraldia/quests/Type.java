package io.github.albertosa23.heraldia.quests;

import com.mojang.serialization.Codec;
import java.util.Locale;

/**
 * Board quest types (T38). The id is what is saved in the player's data and what forms the key of its
 * text ({@code heraldia.encargos.tipo.<id>}); a published id is never renamed.
 */
public enum Type {
	/** Bring N items to the bailiff (food, biome materials, moderate ores): checked on delivery. */
	BRING("traer", 10),
	/** Defeat the guardian of a specific unique structure (near or far). */
	GUARDIAN("guardian", 30),
	/** Reach a specific medium structure or mine entrance (heading and distance hint, no coordinates). */
	EXPLORE("explorar", 15),
	/** Clear wave N in the arena. */
	ARENA("arena", 20),
	/** Take a message to a neighboring village along the road (reach it). */
	JOURNEY("viaje", 15);

	/** Reputation it gives with the village that gives it. */
	public final int reputation;

	/** Saved id (NBT, JSON and translation keys): never renamed. */
	private final String id;

	Type(String id, int reputation) {
		this.id = id;
		this.reputation = reputation;
	}

	public String id() {
		return id;
	}

	public static Type of(String id) {
		for (Type t : values()) {
			if (t.id.equalsIgnoreCase(id)) {
				return t;
			}
		}
		throw new IllegalArgumentException("No quest type " + id);
	}

	public static final Codec<Type> CODEC = Codec.STRING.xmap(Type::of, Type::id);
}
