package io.github.albertosa23.heraldia.loot;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import io.github.albertosa23.heraldia.loot.Restock.Decision;
import io.github.albertosa23.heraldia.loot.Restock.Ledger;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.TreeSet;
import java.util.stream.Stream;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.NbtAccounter;
import net.minecraft.nbt.NbtIo;
import net.minecraft.nbt.Tag;
import org.junit.jupiter.api.Test;

/** Restocking loot: when a chest restocks (days, players nearby, empty), which tables and what is saved. */
class RestockTest {
	private static final String VILLAGE = "heraldia:cofres/herreria", UNIQUE = "heraldia:unicas/castillo/armeria",
			MEDIUM = "heraldia:medianas/posada/despensa";
	private static final long DAY = Restock.DAY;

	private static Optional<Ledger> reg(String table, long t) {
		return Optional.of(new Ledger(table, t));
	}

	@Test
	void restockedTables() {
		for (String t : List.of(VILLAGE, UNIQUE, MEDIUM)) {
			assertTrue(Restock.tableRestocks(t), t);
		}
		for (String t : List.of("heraldia:trofeos/castillo", "heraldia:guardianes/castillo/zombie", "heraldia:llaves/castillo/llave",
				"heraldia:mapas/castillo", "heraldia:encargos/a", "heraldia:unicas/castillo/trofeo", "minecraft:chests/simple_dungeon",
				"heraldia:cofres/", "heraldia:unicas", "", "otro:cofres/x")) {
			assertFalse(Restock.tableRestocks(t), t);
		}
		assertFalse(Restock.tableRestocks(null));
	}

	@Test
	void pendingTableIsRecordedOnlyIfFromHeraldia() {
		assertEquals(Decision.RECORD, Restock.decide(VILLAGE, Optional.empty(), 0, 7, 0, 0));
		// also if there was already a record (it restocked and has not been opened yet, or the chest was refilled with /loot): it is recorded again
		assertEquals(Decision.RECORD, Restock.decide(UNIQUE, reg(UNIQUE, 5), 100 * DAY, 7, 3, 27));
		assertEquals(Decision.NOTHING, Restock.decide("minecraft:chests/simple_dungeon", Optional.empty(), 0, 7, 0, 0));
		assertEquals(Decision.NOTHING, Restock.decide("heraldia:trofeos/castillo", Optional.empty(), 0, 7, 0, 0));
	}

	@Test
	void withoutLedgerOrTableDoesNothing() {
		assertEquals(Decision.NOTHING, Restock.decide(null, Optional.empty(), 100 * DAY, 1, 0, 0));
		assertEquals(Decision.NOTHING, Restock.decide(null, reg("heraldia:trofeos/x", 0), 100 * DAY, 1, 0, 0));
	}

	@Test
	void waitsExactlyTheDays() {
		long t0 = 3 * DAY + 123;
		assertEquals(Decision.WAIT, Restock.decide(null, reg(VILLAGE, t0), t0, 7, 0, 0));
		assertEquals(Decision.WAIT, Restock.decide(null, reg(VILLAGE, t0), t0 + 7 * DAY - 1, 7, 0, 0));
		assertEquals(Decision.RESTOCK, Restock.decide(null, reg(VILLAGE, t0), t0 + 7 * DAY, 7, 0, 0));
		assertEquals(Decision.RESTOCK, Restock.decide(null, reg(VILLAGE, t0), t0 + 60 * DAY, 7, 0, 0));
		assertEquals(Decision.RESTOCK, Restock.decide(null, reg(VILLAGE, 0), DAY, 1, 0, 0));
		assertEquals(Decision.WAIT, Restock.decide(null, reg(VILLAGE, 0), 59 * DAY, 60, 0, 0));
	}

	@Test
	void anotherPlayerNearbyPreventsIt() {
		assertEquals(Decision.WAIT, Restock.decide(null, reg(MEDIUM, 0), 10 * DAY, 7, 1, 0));
		assertEquals(Decision.WAIT, Restock.decide(null, reg(MEDIUM, 0), 10 * DAY, 7, 4, 0));
		assertEquals(Decision.RESTOCK, Restock.decide(null, reg(MEDIUM, 0), 10 * DAY, 7, 0, 0));
	}

	@Test
	void onlyEmptyOrNearlyEmpty() {
		for (int n = 0; n <= Restock.MAX_OCCUPIED; n++) {
			assertEquals(Decision.RESTOCK, Restock.decide(null, reg(UNIQUE, 0), 10 * DAY, 7, 0, n), "ocupadas " + n);
		}
		for (int n = Restock.MAX_OCCUPIED + 1; n <= 27; n++) {
			assertEquals(Decision.WAIT, Restock.decide(null, reg(UNIQUE, 0), 10 * DAY, 7, 0, n), "ocupadas " + n);
		}
	}

	@Test
	void clockGoingBackResetsTheCount() {
		assertEquals(Decision.RESET, Restock.decide(null, reg(VILLAGE, 50 * DAY), 10 * DAY, 7, 0, 0));
	}

	@Test
	void ledgerRoundTripWithoutTouchingOtherKeys() {
		CompoundTag cd = new CompoundTag();
		cd.putString(PerPlayerChest.MARK + "_no", "x"); // any other key is kept
		assertTrue(Restock.ledger(cd).isEmpty());
		CompoundTag with = Restock.withLedger(cd, new Ledger(UNIQUE, 987654321L));
		assertEquals(Optional.of(new Ledger(UNIQUE, 987654321L)), Restock.ledger(with));
		assertEquals("x", with.getStringOr(PerPlayerChest.MARK + "_no", ""));
		assertFalse(cd.contains(Restock.KEY), "no modifica el original");
		// idempotent: writing it again leaves the same
		assertEquals(with, Restock.withLedger(with, new Ledger(UNIQUE, 987654321L)));
		// broken records: without a table or a time, they are ignored
		CompoundTag broken = new CompoundTag();
		CompoundTag r = new CompoundTag();
		r.putString("tabla", VILLAGE);
		broken.put(Restock.KEY, r);
		assertTrue(Restock.ledger(broken).isEmpty());
	}

	/**
	 * Every Heraldia loot table in a container of the generated templates (chests, barrels) restocks, with no
	 * exception: if a new generator places a chest with another table, this test says so (and one has to decide whether it restocks).
	 */
	@Test
	void templateTablesAreRestocked() throws IOException {
		Path root = Path.of(System.getProperty("heraldia.generated"), "data/heraldia/structure");
		List<Path> files = new ArrayList<>();
		try (Stream<Path> s = Files.walk(root)) {
			s.filter(p -> p.toString().endsWith(".nbt")).forEach(files::add);
		}
		TreeSet<String> seen = new TreeSet<>(), bad = new TreeSet<>();
		for (Path f : files) {
			CompoundTag t = NbtIo.readCompressed(f, NbtAccounter.unlimitedHeap());
			for (Tag b : t.getListOrEmpty("blocks")) {
				CompoundTag nbt = ((CompoundTag) b).getCompoundOrEmpty("nbt");
				String id = nbt.getStringOr("id", ""), table = nbt.getStringOr("LootTable", "");
				if (table.startsWith("heraldia:") && (id.endsWith("chest") || id.endsWith("barrel"))) {
					seen.add(table);
					if (!Restock.tableRestocks(table)) {
						bad.add(table + " (" + root.relativize(f) + ")");
					}
				}
			}
		}
		assertTrue(seen.size() > 50, "pocas tablas de cofre en las plantillas: " + seen.size());
		assertTrue(seen.stream().anyMatch(v -> v.startsWith("heraldia:cofres/")), "ninguna de aldea");
		assertTrue(seen.stream().anyMatch(v -> v.startsWith("heraldia:medianas/")), "ninguna de mediana");
		assertTrue(seen.stream().anyMatch(v -> v.startsWith("heraldia:unicas/")), "ninguna de única");
		assertTrue(seen.stream().anyMatch(v -> v.startsWith("heraldia:minas/")), "ninguna de entrada a mina");
		assertTrue(bad.isEmpty(), "tablas de cofre que no se repondrían: " + bad);
	}
}
