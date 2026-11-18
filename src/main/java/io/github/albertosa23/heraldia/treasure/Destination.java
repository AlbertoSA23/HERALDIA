package io.github.albertosa23.heraldia.treasure;

import java.util.Locale;
import net.minecraft.nbt.CompoundTag;

/**
 * Un paso de la cadena: el sitio que marca el mapa. {@code structure}: el id de la estructura (heraldia:medianas/...,
 * heraldia:minas/...) o vacío en el tesoro; {@code generated}: si la estructura ya estaba generada al elegirla (si no,
 * prevista: un chunk sin generar donde la generación la pondrá); {@code biome}: el id del bioma del sitio (para la pista).
 */
public record Destination(Type type, String structure, int x, int z, boolean generated, String biome) {
	public enum Type {
		MEDIUM, MINE, TREASURE;

		public String id() {
			return name().toLowerCase(Locale.ROOT);
		}

		static Type of(String id) {
			return valueOf(id.toUpperCase(Locale.ROOT));
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
