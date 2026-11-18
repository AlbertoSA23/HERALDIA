package io.github.albertosa23.heraldia.loot;

import java.util.Optional;
import net.minecraft.nbt.CompoundTag;
import org.jspecify.annotations.Nullable;

/**
 * Pure logic of the restocking loot (options botin.reponer.*), without world classes: which tables restock, what is
 * saved in the chest and when it is time to refill it. {@link RestockedLoot} applies it when the chest is opened.
 *
 * <p>The only thing saved is in the block's custom_data: {@code heraldia_botin: {tabla: "<id>", saqueado: <clock>}},
 * with the overworld clock ({@code getOverworldClockTime}, the one /time add moves) of the last looting.
 */
public final class Restock {
	/** Key of the record in the chest's custom_data. */
	public static final String KEY = "heraldia_botin";
	static final String TABLE = "tabla", LOOTED = "saqueado";
	/** One game day, in world-clock ticks. */
	public static final long DAY = 24000L;
	/** Radius (blocks) in which another player prevents the chest from restocking. */
	public static final double PLAYER_RADIUS = 32;
	/** "Nearly empty": at most this many occupied slots (out of 27). Whatever is there stays: the loot goes into the free ones. */
	public static final int MAX_OCCUPIED = 3;
	private static final String NS = "heraldia:";
	private static final String[] PREFIXES = {"cofres/", "unicas/", "medianas/", "minas/", "costa/"};

	private Restock() {
	}

	/** What to do with a chest when it is opened. */
	public enum Decision {
		/** It is not a known Heraldia chest (or it does not restock): nothing. */
		NOTHING,
		/** It still has its unopened table: the table is recorded and that it is looted now. */
		RECORD,
		/** Not yet (too few days, another player nearby or the chest has things). */
		WAIT,
		/** Due: its table is set again (the game opens it in this same use). */
		RESTOCK,
		/** The clock has gone backwards (/time set): the count starts over. */
		RESET
	}

	/**
	 * Does a chest with this table restock? Only the village chest tables ({@code heraldia:cofres/}), the mediums, the
	 * mine entrances ({@code heraldia:minas/}), the lighthouses and shipwrecks ({@code heraldia:costa/}) and the uniques;
	 * never the trophies (nor anything that is not Heraldia's).
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
	 * Decision when a chest is opened.
	 *
	 * @param pending   table the chest has not opened yet (or null)
	 * @param ledger    what is saved in the chest ({@link #ledger}), if any
	 * @param now       world clock
	 * @param days      botin.reponer.dias
	 * @param others    players within {@link #PLAYER_RADIUS} blocks, not counting the one opening it
	 * @param occupied  slots with something in them
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

	/** Table the premium chest of a cleared unique restocks with (botin.reponer.premium_vencido_modesto; generator: chest_loot.cleared_premium). */
	public static final String CLEARED_PREMIUM = "heraldia:botin/premium_vencido";
	/** Option: the premium chest of a unique whose guardian has fallen restocks with {@link #CLEARED_PREMIUM}. */
	public static final String CLEARED_PREMIUM_OPTION = "botin.reponer.premium_vencido_modesto";

	/**
	 * The unique structure id of a premium chest table ({@code heraldia:unicas/<id>/premium} gives {@code <id>}), or null for any
	 * other table (minor chests, treasure rooms, villages...).
	 */
	public static @Nullable String premiumOf(@Nullable String table) {
		String prefix = NS + "unicas/", suffix = "/premium";
		if (table == null || !table.startsWith(prefix) || !table.endsWith(suffix)) {
			return null;
		}
		String sid = table.substring(prefix.length(), table.length() - suffix.length());
		return sid.isEmpty() || sid.contains("/") ? null : sid;
	}

	/**
	 * Table a due chest is refilled with: its own, except the premium chest of a cleared unique with the option on, which gets
	 * {@link #CLEARED_PREMIUM}. The record keeps the original table either way, so turning the option off restores the full
	 * premium on the next refill. {@code cleared} is only asked for premium tables (it looks up the structure).
	 */
	public static String refillTable(String table, boolean option, java.util.function.Predicate<String> cleared) {
		String sid = option ? premiumOf(table) : null;
		return sid != null && cleared.test(sid) ? CLEARED_PREMIUM : table;
	}

	/** What is saved in a chest: its original table and the clock of the last looting. */
	public record Ledger(String table, long looted) {
		CompoundTag tag() {
			CompoundTag t = new CompoundTag();
			t.putString(TABLE, table);
			t.putLong(LOOTED, looted);
			return t;
		}
	}

	/** The record from a chest's custom_data, if it has one and it is valid. */
	public static Optional<Ledger> ledger(CompoundTag customData) {
		return customData.getCompound(KEY).flatMap(t -> {
			String table = t.getStringOr(TABLE, "");
			Optional<Long> lootedAt = t.getLong(LOOTED);
			return table.isEmpty() || lootedAt.isEmpty() ? Optional.empty() : Optional.of(new Ledger(table, lootedAt.get()));
		});
	}

	/** Writes the record into a copy of the custom_data (does not touch the other keys, e.g. those of other systems). */
	public static CompoundTag withLedger(CompoundTag customData, Ledger r) {
		CompoundTag out = customData.copy();
		out.put(KEY, r.tag());
		return out;
	}
}
