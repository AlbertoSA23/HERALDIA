package io.github.albertosa23.heraldia.loot;

import java.util.Optional;
import net.minecraft.nbt.CompoundTag;

/**
 * Lógica pura del botín que se repone (opciones botin.reponer.*), sin clases del mundo: qué tablas se reponen, qué se
 * guarda en el cofre y cuándo toca volver a llenarlo. La aplica {@link BotinRepuesto} al abrir el cofre.
 *
 * <p>Lo único que se guarda está en el custom_data del bloque: {@code heraldia_botin: {tabla: "<id>", saqueado: <reloj>}},
 * con el reloj del mundo principal ({@code getOverworldClockTime}, el que mueve /time add) del último saqueo.
 */
public final class Reposicion {
	/** Clave del registro en el custom_data del cofre. */
	public static final String CLAVE = "heraldia_botin";
	static final String TABLA = "tabla", SAQUEADO = "saqueado";
	/** Un día de juego, en ticks del reloj del mundo. */
	public static final long DIA = 24000L;
	/** Radio (bloques) en el que otro jugador impide reponer el cofre. */
	public static final double RADIO_JUGADORES = 32;
	/** «Casi vacío»: como mucho tantas casillas ocupadas (de 27). Lo que haya se queda: el botín va a las libres. */
	public static final int MAX_OCUPADAS = 3;
	private static final String NS = "heraldia:";
	private static final String[] PREFIJOS = {"cofres/", "unicas/", "medianas/"};

	private Reposicion() {
	}

	/** Qué hacer con un cofre al abrirlo. */
	public enum Decision {
		/** No es un cofre de Heraldia conocido (o no se repone): nada. */
		NADA,
		/** Aún tiene su tabla sin abrir: se apunta la tabla y que se saquea ahora. */
		APUNTAR,
		/** Aún no toca (pocos días, otro jugador cerca o el cofre tiene cosas). */
		ESPERAR,
		/** Toca: vuelve a ponerse su tabla (el juego la abre en este mismo uso). */
		REPONER,
		/** El reloj ha ido hacia atrás (/time set): la cuenta empieza de nuevo. */
		REINICIAR
	}

	/**
	 * ¿Se repone un cofre con esta tabla? Solo las de cofre de las aldeas ({@code heraldia:cofres/}), las medianas y las
	 * únicas; nunca los trofeos (ni nada que no sea de Heraldia).
	 */
	public static boolean tablaRepone(String tabla) {
		if (tabla == null || !tabla.startsWith(NS) || tabla.contains("trofeo")) {
			return false;
		}
		String path = tabla.substring(NS.length());
		for (String p : PREFIJOS) {
			if (path.startsWith(p) && path.length() > p.length()) {
				return true;
			}
		}
		return false;
	}

	/**
	 * Decisión al abrir un cofre.
	 *
	 * @param pendiente   tabla que el cofre aún no ha abierto (o null)
	 * @param registro    lo guardado en el cofre ({@link #registro}), si lo hay
	 * @param ahora       reloj del mundo
	 * @param dias        botin.reponer.dias
	 * @param otros       jugadores a {@link #RADIO_JUGADORES} bloques, sin contar al que abre
	 * @param ocupadas    casillas con algo
	 */
	public static Decision decidir(String pendiente, Optional<Registro> registro, long ahora, int dias, int otros, int ocupadas) {
		if (pendiente != null) {
			return tablaRepone(pendiente) ? Decision.APUNTAR : Decision.NADA;
		}
		if (registro.isEmpty() || !tablaRepone(registro.get().tabla())) {
			return Decision.NADA;
		}
		long desde = registro.get().saqueado();
		if (ahora < desde) {
			return Decision.REINICIAR;
		}
		if (ahora - desde < dias * DIA || otros > 0 || ocupadas > MAX_OCUPADAS) {
			return Decision.ESPERAR;
		}
		return Decision.REPONER;
	}

	/** Lo guardado en un cofre: su tabla original y el reloj del último saqueo. */
	public record Registro(String tabla, long saqueado) {
		CompoundTag tag() {
			CompoundTag t = new CompoundTag();
			t.putString(TABLA, tabla);
			t.putLong(SAQUEADO, saqueado);
			return t;
		}
	}

	/** El registro del custom_data de un cofre, si lo tiene y es válido. */
	public static Optional<Registro> registro(CompoundTag customData) {
		return customData.getCompound(CLAVE).flatMap(t -> {
			String tabla = t.getStringOr(TABLA, "");
			Optional<Long> saq = t.getLong(SAQUEADO);
			return tabla.isEmpty() || saq.isEmpty() ? Optional.empty() : Optional.of(new Registro(tabla, saq.get()));
		});
	}

	/** Escribe el registro en una copia del custom_data (no toca el resto de claves, p. ej. las de otros sistemas). */
	public static CompoundTag conRegistro(CompoundTag customData, Registro r) {
		CompoundTag out = customData.copy();
		out.put(CLAVE, r.tag());
		return out;
	}
}
