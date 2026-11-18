package io.github.albertosa23.heraldia.quests;

import com.mojang.serialization.Codec;
import com.mojang.serialization.codecs.RecordCodecBuilder;

/**
 * Un encargo del tablón de una aldea (inmutable). Se guarda entero en los datos del jugador al aceptarlo, así que
 * sobrevive a la rotación del tablón y a los cambios del mundo.
 *
 * @param aldeaX     chunk del inicio de la aldea que lo encarga (su clave, ver {@link Reputation#key})
 * @param aldeaZ     ídem
 * @param periodo    periodo de rotación en que salió ({@link Generator#period})
 * @param hueco      posición en el tablón (0..3)
 * @param tipo       qué hay que hacer
 * @param objetivo   objeto (traer: «minecraft:bread»), única (guardián: «castillo»), estructura (explorar:
 *                   «heraldia:medianas/posada/llanuras»), nombre de la aldea vecina (viaje) o vacío (arena)
 * @param cantidad   objetos que traer u oleada que superar (0 en los demás)
 * @param x          bloque del objetivo (guardián, explorar, viaje; 0 en los demás)
 * @param z          ídem
 * @param esmeraldas recompensa
 * @param experiencia recompensa (puntos)
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

	/** Id estable: aldea, periodo y hueco («12.-40.7.1»). Dos jugadores con el mismo encargo tienen el mismo id. */
	public String id() {
		return villageX + "." + villageZ + "." + period + "." + gap;
	}

	public String village() {
		return Reputation.key(villageX, villageZ);
	}

	/** Reputación que da con su aldea al entregarlo. */
	public int reputation() {
		return type.reputation;
	}

	/** ¿Tiene un sitio al que ir (y una pista de rumbo)? */
	public boolean withPlace() {
		return type == Type.GUARDIAN || type == Type.EXPLORE || type == Type.JOURNEY;
	}
}
