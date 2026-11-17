package io.github.albertosa23.heraldia.arena;

import java.util.Locale;
import java.util.Optional;

/**
 * Modos de partida de la arena (T41), sin clases del juego. Se eligen al empezar (campana o
 * /heraldia arena start &lt;modo&gt;); todos guardan las reglas de siempre (sin botín, experiencia reducida, inventario
 * conservado, mini-jefe cada 5 oleadas, dificultad y perfil):
 * <ul>
 * <li>{@link #COOPERATIVO}: el de siempre (T31), sin cambios: oleadas hasta que caen todos, con pausa entre ellas; puntúa
 * la oleada superada (y su récord sigue en el marcador vanilla).</li>
 * <li>{@link #CONTRARRELOJ}: N oleadas fijas (arena.modos.oleadas_contrarreloj) contra el reloj, con una pausa corta;
 * acaba al superar la última y puntúa el tiempo.</li>
 * <li>{@link #SUPERVIVENCIA}: oleadas sin pausa entre ellas hasta que caen todos; puntúa la oleada más alta superada.</li>
 * </ul>
 * El {@link #id()} es el argumento del comando (inglés, minúsculas, ASCII); {@link #clave()}, el de la configuración
 * (arena.modos.&lt;clave&gt;) y los textos (heraldia.arena.modo.&lt;id&gt;).
 */
public enum Modo {
	COOPERATIVO("coop", "cooperativo", Partida.PAUSA_TICKS),
	CONTRARRELOJ("timeattack", "contrarreloj", 100),
	SUPERVIVENCIA("survival", "supervivencia", 0);

	private final String id, clave;
	private final int pausa;

	Modo(String id, String clave, int pausa) {
		this.id = id;
		this.clave = clave;
		this.pausa = pausa;
	}

	/** Argumento del comando y clave de los datos guardados (no cambia). */
	public String id() {
		return id;
	}

	/** Nombre en la configuración (arena.modos.&lt;clave&gt;). */
	public String clave() {
		return clave;
	}

	/** Ticks de pausa entre oleadas (0: la siguiente empieza en el tick siguiente al superar la anterior). */
	public int pausa() {
		return pausa;
	}

	public String opcion() {
		return "arena.modos." + clave;
	}

	public String texto() {
		return "heraldia.arena.modo." + id;
	}

	/** El modo de un id del comando o de los datos guardados ({@code coop}, {@code timeattack}, {@code survival}). */
	public static Optional<Modo> deId(String id) {
		if (id == null) {
			return Optional.empty();
		}
		String s = id.toLowerCase(Locale.ROOT);
		for (Modo m : values()) {
			if (m.id.equals(s)) {
				return Optional.of(m);
			}
		}
		return Optional.empty();
	}
}
