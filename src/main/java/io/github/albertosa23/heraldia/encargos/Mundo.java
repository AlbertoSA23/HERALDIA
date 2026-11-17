package io.github.albertosa23.heraldia.encargos;

import com.mojang.serialization.Codec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import java.util.ArrayList;
import java.util.List;

/**
 * Lo que se guarda de los encargos en el mundo principal (adjunto persistente de Fabric en el {@code ServerLevel}):
 * cuántos se han entregado entre todos (para /heraldia status) y dónde han caído los guardianes desde que hay encargos
 * (para no pedir vencer a uno que ya no está desde el periodo siguiente). Inmutable.
 */
public record Mundo(int completados, List<Caido> caidos) {
	/** Guardianes caídos que se recuerdan: uno por única, de sobra. */
	public static final int MAX_CAIDOS = 1000;
	public static final Mundo VACIO = new Mundo(0, List.of());

	/** Un guardián caído: su única, dónde y cuándo (tick del mundo). */
	public record Caido(String unica, int x, int z, long tick) {
		public static final Codec<Caido> CODEC = RecordCodecBuilder.create(i -> i.group(
				Codec.STRING.fieldOf("unica").forGetter(Caido::unica),
				Codec.INT.fieldOf("x").forGetter(Caido::x),
				Codec.INT.fieldOf("z").forGetter(Caido::z),
				Codec.LONG.optionalFieldOf("tick", 0L).forGetter(Caido::tick)).apply(i, Caido::new));
	}

	public static final Codec<Mundo> CODEC = RecordCodecBuilder.create(i -> i.group(
			Codec.INT.optionalFieldOf("completados", 0).forGetter(Mundo::completados),
			Caido.CODEC.listOf().optionalFieldOf("caidos", List.of()).forGetter(Mundo::caidos)).apply(i, Mundo::new));

	public Mundo {
		caidos = List.copyOf(caidos);
	}

	public Mundo completado() {
		return new Mundo(completados + 1, caidos);
	}

	public Mundo cae(String unica, int x, int z, long tick) {
		if (caido(unica, x, z)) {
			return this;
		}
		List<Caido> l = new ArrayList<>(caidos);
		l.add(new Caido(unica, x, z, tick));
		while (l.size() > MAX_CAIDOS) {
			l.remove(0);
		}
		return new Mundo(completados, l);
	}

	/** ¿Ha caído ya el guardián de esa única en (x, z)? (a menos de {@link Objetivos#RADIO_GUARDIAN}) */
	public boolean caido(String unica, int x, int z) {
		return caidoAntes(unica, x, z, Long.MAX_VALUE);
	}

	/**
	 * ¿Cayó antes del tick {@code antes}? El tablón de un periodo solo descarta los guardianes caídos antes de que
	 * empezara: así no cambia a mitad de periodo (los ids de sus encargos son su hueco) y el caído deja de salir en el
	 * siguiente.
	 */
	public boolean caidoAntes(String unica, int x, int z, long antes) {
		for (Caido c : caidos) {
			if (c.tick() < antes && c.unica().equals(unica) && Objetivos.cerca(x, z, c.x(), c.z(), Objetivos.RADIO_GUARDIAN)) {
				return true;
			}
		}
		return false;
	}
}
