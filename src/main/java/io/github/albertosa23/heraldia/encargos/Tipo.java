package io.github.albertosa23.heraldia.encargos;

import com.mojang.serialization.Codec;
import java.util.Locale;

/**
 * Tipos de encargo del tablón (T38). El id es el que se guarda en los datos del jugador y el que forma la clave de su
 * texto ({@code heraldia.encargos.tipo.<id>}); no se renombra un id publicado.
 */
public enum Tipo {
	/** Traer N objetos al alguacil (comida, materiales del bioma, menas moderadas): se comprueban al entregar. */
	TRAER(10),
	/** Vencer al guardián de una estructura única concreta (cercana o lejana). */
	GUARDIAN(30),
	/** Llegar a una estructura mediana o a una entrada de mina concreta (pista de rumbo y distancia, sin coordenadas). */
	EXPLORAR(15),
	/** Superar la oleada N en la arena. */
	ARENA(20),
	/** Llevar un mensaje a una aldea vecina por el camino (llegar a ella). */
	VIAJE(15);

	/** Reputación que da con la aldea que lo encarga. */
	public final int reputacion;

	Tipo(int reputacion) {
		this.reputacion = reputacion;
	}

	public String id() {
		return name().toLowerCase(Locale.ROOT);
	}

	public static Tipo de(String id) {
		return valueOf(id.toUpperCase(Locale.ROOT));
	}

	public static final Codec<Tipo> CODEC = Codec.STRING.xmap(Tipo::de, Tipo::id);
}
