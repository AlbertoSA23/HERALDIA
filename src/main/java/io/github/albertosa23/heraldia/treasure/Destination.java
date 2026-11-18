package io.github.albertosa23.heraldia.treasure;

import java.util.Locale;
import net.minecraft.nbt.CompoundTag;

/**
 * A step of the chain: the spot the map marks. {@code structure}: the structure's id (heraldia:medianas/...,
 * heraldia:minas/...) or empty for the treasure; {@code generated}: whether the structure was already generated when chosen (otherwise,
 * expected: an ungenerated chunk where generation will put it); {@code biome}: the id of the spot's biome (for the clue).
 */
public record Destination(Type type, String structure, int x, int z, boolean generated, String biome) {
	public enum Type {
		MEDIUM("mediana"), MINE("mina"), TREASURE("tesoro");

		/** Saved id (NBT): never renamed. */
		private final String id;

		Type(String id) {
			this.id = id;
		}

		public String id() {
			return id;
		}

		static Type of(String id) {
			for (Type t : values()) {
				if (t.id.equals(id)) {
					return t;
				}
			}
			throw new IllegalArgumentException("No destination type " + id);
		}
	}

	public long distanceSq(int px, int pz) {
		long dx = x - px, dz = z - pz;
		return dx * dx + dz * dz;
	}

	CompoundTag toTag() {
		CompoundTag t = new CompoundTag();
		t.putString("tipo", type.id());
		if (!structure.isEmpty()) {
			t.putString("estructura", structure);
		}
		t.putInt("x", x);
		t.putInt("z", z);
		t.putBoolean("generada", generated);
		t.putString("bioma", biome);
		return t;
	}

	static Destination fromTag(CompoundTag t) {
		return new Destination(Type.of(t.getStringOr("tipo", "tesoro")), t.getStringOr("estructura", ""), t.getIntOr("x", 0),
				t.getIntOr("z", 0), t.getBooleanOr("generada", false), t.getStringOr("bioma", "minecraft:plains"));
	}
}
