package io.github.albertosa23.heraldia.encargos;

import com.mojang.serialization.Codec;
import com.mojang.serialization.codecs.RecordCodecBuilder;

/**
 * Un encargo del tablón de una aldea (inmutable). Se guarda entero en los datos del jugador al aceptarlo, así que
 * sobrevive a la rotación del tablón y a los cambios del mundo.
 *
 * @param aldeaX     chunk del inicio de la aldea que lo encarga (su clave, ver {@link Reputacion#clave})
 * @param aldeaZ     ídem
 * @param periodo    periodo de rotación en que salió ({@link Generador#periodo})
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
public record Encargo(int aldeaX, int aldeaZ, long periodo, int hueco, Tipo tipo, String objetivo, int cantidad, int x, int z,
					  int esmeraldas, int experiencia) {
	public static final Codec<Encargo> CODEC = RecordCodecBuilder.create(i -> i.group(
			Codec.INT.fieldOf("aldea_x").forGetter(Encargo::aldeaX),
			Codec.INT.fieldOf("aldea_z").forGetter(Encargo::aldeaZ),
			Codec.LONG.fieldOf("periodo").forGetter(Encargo::periodo),
			Codec.INT.fieldOf("hueco").forGetter(Encargo::hueco),
			Tipo.CODEC.fieldOf("tipo").forGetter(Encargo::tipo),
			Codec.STRING.optionalFieldOf("objetivo", "").forGetter(Encargo::objetivo),
			Codec.INT.optionalFieldOf("cantidad", 0).forGetter(Encargo::cantidad),
			Codec.INT.optionalFieldOf("x", 0).forGetter(Encargo::x),
			Codec.INT.optionalFieldOf("z", 0).forGetter(Encargo::z),
			Codec.INT.optionalFieldOf("esmeraldas", 0).forGetter(Encargo::esmeraldas),
			Codec.INT.optionalFieldOf("experiencia", 0).forGetter(Encargo::experiencia)).apply(i, Encargo::new));

	/** Id estable: aldea, periodo y hueco («12.-40.7.1»). Dos jugadores con el mismo encargo tienen el mismo id. */
	public String id() {
		return aldeaX + "." + aldeaZ + "." + periodo + "." + hueco;
	}

	public String aldea() {
		return Reputacion.clave(aldeaX, aldeaZ);
	}

	/** Reputación que da con su aldea al entregarlo. */
	public int reputacion() {
		return tipo.reputacion;
	}

	/** ¿Tiene un sitio al que ir (y una pista de rumbo)? */
	public boolean conLugar() {
		return tipo == Tipo.GUARDIAN || tipo == Tipo.EXPLORAR || tipo == Tipo.VIAJE;
	}
}
