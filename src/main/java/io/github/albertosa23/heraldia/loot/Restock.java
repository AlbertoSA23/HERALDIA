package io.github.albertosa23.heraldia.loot;

import java.util.Optional;
import net.minecraft.nbt.CompoundTag;

/**
 * Lógica pura del botín que se repone (opciones botin.reponer.*), sin clases del mundo: qué tablas se reponen, qué se
 * guarda en el cofre y cuándo toca volver a llenarlo. La aplica {@link RestockedLoot} al abrir el cofre.
 *
 * <p>Lo único que se guarda está en el custom_data del bloque: {@code heraldia_botin: {table: "<id>", looted: <reloj>}},
 * con el reloj del mundo principal ({@code getOverworldClockTime}, el que mueve /time add) del último saqueo.
 */
public final class Restock {
	/** Clave del registro en el custom_data del cofre. */
	public static final String CLAVE = "heraldia_botin";
	static final String TABLE = "tabla", LOOTED = "saqueado";
	/** Un día de juego, en ticks del reloj del mundo. */
	public static final long DAY = 24000L;
	/** Radio (bloques) en el que otro jugador impide reponer el cofre. */
	public static final double PLAYER_RADIUS = 32;
	/** «Casi vacío»: como mucho tantas casillas ocupadas (de 27). Lo que haya se queda: el botín va a las libres. */
	public static final int MAX_OCCUPIED = 3;
	private static final String NS = "heraldia:";
	private static final String[] PREFIXES = {"cofres/", "unicas/", "medianas/", "minas/", "costa/"};

	private Restock() {
	}

	/** Qué hacer con un cofre al abrirlo. */
	public enum Decision {
		/** No es un cofre de Heraldia conocido (o no se repone): nada. */
		NOTHING,
		/** Aún tiene su tabla sin abrir: se apunta la tabla y que se saquea ahora. */
		RECORD,
		/** Aún no toca (pocos días, otro jugador cerca o el cofre tiene cosas). */
		WAIT,
		/** Toca: vuelve a ponerse su tabla (el juego la abre en este mismo uso). */
		RESTOCK,
		/** El reloj ha ido hacia atrás (/time set): la cuenta empieza de nuevo. */
		RESET
	}

	/**
	 * ¿Se repone un cofre con esta tabla? Solo las de cofre de las aldeas ({@code heraldia:cofres/}), las medianas, las
	 * entradas a mina ({@code heraldia:mines/}), los faros y naufragios ({@code heraldia:coast/}) y las únicas; nunca los trofeos (ni nada que no sea de Heraldia).
	 */
	public static boolean tableRestocks(String table) {
		if (table == null || !table.startsWith(NS) || table.contains("trofeo")) {
			return false;
		}
		String path = table.substring(NS.length());
		for (String p : PREFIXES) {
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
	 * @param registro    lo guardado en el cofre ({@link #ledger}), si lo hay
	 * @param ahora       reloj del mundo
	 * @param dias        botin.reponer.dias
	 * @param otros       jugadores a {@link #PLAYER_RADIUS} bloques, sin contar al que abre
	 * @param ocupadas    casillas con algo
	 */
	public static Decision decide(String pending, Optional<Ledger> ledger, long now, int days, int others, int occupied) {
		if (pending != null) {
			return tableRestocks(pending) ? Decision.RECORD : Decision.NOTHING;
		}
		if (ledger.isEmpty() || !tableRestocks(ledger.get().table())) {
			return Decision.NOTHING;
		}
		long from = ledger.get().looted();
		if (now < from) {
			return Decision.RESET;
		}
		if (now - from < days * DAY || others > 0 || occupied > MAX_OCCUPIED) {
			return Decision.WAIT;
		}
		return Decision.RESTOCK;
	}

	/** Lo guardado en un cofre: su tabla original y el reloj del último saqueo. */
	public record Ledger(String table, long looted) {
		CompoundTag tag() {
			CompoundTag t = new CompoundTag();
			t.putString(TABLE, table);
			t.putLong(LOOTED, looted);
			return t;
		}
	}

	/** El registro del custom_data de un cofre, si lo tiene y es válido. */
	public static Optional<Ledger> ledger(CompoundTag customData) {
		return customData.getCompound(CLAVE).flatMap(t -> {
			String table = t.getStringOr(TABLE, "");
			Optional<Long> lootedAt = t.getLong(LOOTED);
			return table.isEmpty() || lootedAt.isEmpty() ? Optional.empty() : Optional.of(new Ledger(table, lootedAt.get()));
		});
	}

	/** Escribe el registro en una copia del custom_data (no toca el resto de claves, p. ej. las de otros sistemas). */
	public static CompoundTag withLedger(CompoundTag customData, Ledger r) {
		CompoundTag out = customData.copy();
		out.put(CLAVE, r.tag());
		return out;
	}
}
