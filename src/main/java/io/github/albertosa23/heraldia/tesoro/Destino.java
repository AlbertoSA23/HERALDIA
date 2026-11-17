package io.github.albertosa23.heraldia.tesoro;

import java.util.Locale;
import net.minecraft.nbt.CompoundTag;

/**
 * Un paso de la cadena: el sitio que marca el mapa. {@code estructura}: el id de la estructura (heraldia:medianas/...,
 * heraldia:minas/...) o vacío en el tesoro; {@code generada}: si la estructura ya estaba generada al elegirla (si no,
 * prevista: un chunk sin generar donde la generación la pondrá); {@code bioma}: el id del bioma del sitio (para la pista).
 */
public record Destino(Tipo tipo, String estructura, int x, int z, boolean generada, String bioma) {
	public enum Tipo {
		MEDIANA, MINA, TESORO;

		public String id() {
			return name().toLowerCase(Locale.ROOT);
		}

		static Tipo de(String id) {
			return valueOf(id.toUpperCase(Locale.ROOT));
		}
	}

	public long distanciaSq(int px, int pz) {
		long dx = x - px, dz = z - pz;
		return dx * dx + dz * dz;
	}

	CompoundTag aTag() {
		CompoundTag t = new CompoundTag();
		t.putString("tipo", tipo.id());
		if (!estructura.isEmpty()) {
			t.putString("estructura", estructura);
		}
		t.putInt("x", x);
		t.putInt("z", z);
		t.putBoolean("generada", generada);
		t.putString("bioma", bioma);
		return t;
	}

	static Destino deTag(CompoundTag t) {
		return new Destino(Tipo.de(t.getStringOr("tipo", "tesoro")), t.getStringOr("estructura", ""), t.getIntOr("x", 0),
				t.getIntOr("z", 0), t.getBooleanOr("generada", false), t.getStringOr("bioma", "minecraft:plains"));
	}
}
