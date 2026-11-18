package io.github.albertosa23.heraldia.quests;

import com.mojang.serialization.Codec;
import java.util.Locale;

/**
 * Tipos de encargo del tablón (T38). El id es el que se guarda en los datos del jugador y el que forma la clave de su
 * texto ({@code heraldia.encargos.type.<id>}); no se renombra un id publicado.
 */
public enum Type {
	/** Traer N objetos al alguacil (comida, materiales del bioma, menas moderadas): se comprueban al entregar. */
	BRING(10),
	/** Vencer al guardián de una estructura única concreta (cercana o lejana). */
	GUARDIAN(30),
	/** Llegar a una estructura mediana o a una entrada de mina concreta (pista de rumbo y distancia, sin coordenadas). */
	EXPLORE(15),
	/** Superar la oleada N en la arena. */
	ARENA(20),
	/** Llevar un mensaje a una aldea vecina por el camino (llegar a ella). */
	JOURNEY(15);

	/** Reputación que da con la aldea que lo encarga. */
	public final int reputation;

	Type(int reputation) {
		this.reputation = reputation;
	}

	public String id() {
		return name().toLowerCase(Locale.ROOT);
	}

	public static Type of(String id) {
		return valueOf(id.toUpperCase(Locale.ROOT));
	}

	public static final Codec<Type> CODEC = Codec.STRING.xmap(Type::of, Type::id);
}
