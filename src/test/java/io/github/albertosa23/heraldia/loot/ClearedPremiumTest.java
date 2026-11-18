package io.github.albertosa23.heraldia.loot;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.config.Menus;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.TreeSet;
import java.util.stream.Stream;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.NbtAccounter;
import net.minecraft.nbt.NbtIo;
import net.minecraft.nbt.Tag;
import org.junit.jupiter.api.Test;

/**
 * Premium chest of a cleared unique (botin.reponer.premium_vencido_modesto): which tables count as premium, which table a due
 * chest is refilled with, and that the modest table really is modest.
 */
class ClearedPremiumTest {
	private static final String PREMIUM = "heraldia:unicas/castillo/premium";

	@Test
	void premiumTables() {
		assertEquals("castillo", Restock.premiumOf(PREMIUM));
		assertEquals("atlantida", Restock.premiumOf("heraldia:unicas/atlantida/premium"));
		for (String t : List.of("heraldia:unicas/castillo/armeria", "heraldia:unicas/castillo/premium_vistoso",
				"heraldia:unicas/monasterio/sub/premium", "heraldia:unicas//premium", "heraldia:cofres/premium",
				"heraldia:medianas/posada/premium", "heraldia:chozas_mago/malvado_premium", "otro:unicas/castillo/premium", "")) {
			assertNull(Restock.premiumOf(t), t);
		}
		assertNull(Restock.premiumOf(null));
	}

	@Test
	void onlyTheClearedPremiumGetsTheModestTable() {
		List<String> asked = new ArrayList<>();
		// guardian alive: the full premium, as always
		assertEquals(PREMIUM, Restock.refillTable(PREMIUM, true, sid -> { asked.add(sid); return false; }));
		assertEquals(List.of("castillo"), asked);
		// guardian fallen: the modest table
		assertEquals(Restock.CLEARED_PREMIUM, Restock.refillTable(PREMIUM, true, sid -> true));
		// option off: the full premium, and the structure is not even looked up
		assertEquals(PREMIUM, Restock.refillTable(PREMIUM, false, sid -> { throw new AssertionError("no debe buscar"); }));
		// any other chest of a cleared unique (and any other table) keeps its own, without looking anything up
		for (String t : List.of("heraldia:unicas/castillo/armeria", "heraldia:cofres/herreria", "heraldia:medianas/posada/despensa")) {
			assertEquals(t, Restock.refillTable(t, true, sid -> { throw new AssertionError("no debe buscar: " + t); }));
		}
	}

	@Test
	void theModestTableIsNeverRecordedAsTheChestsOwn() {
		// if the chest is left unopened with the modest table, the next opening must not adopt it as its table:
		// the record keeps the premium, so turning the option off brings the full premium back
		assertFalse(Restock.tableRestocks(Restock.CLEARED_PREMIUM));
		assertEquals(Restock.Decision.NOTHING, Restock.decide(Restock.CLEARED_PREMIUM,
				java.util.Optional.of(new Restock.Ledger(PREMIUM, 0)), 100 * Restock.DAY, 7, 0, 0));
	}

	@Test
	void optionOnByDefaultAndInThePanel() {
		assertTrue(HeraldiaConfig.defaults().get(Restock.CLEARED_PREMIUM_OPTION).getAsBoolean());
		assertTrue(Menus.menu("botin").orElseThrow().keys().contains(Restock.CLEARED_PREMIUM_OPTION));
	}

	/** The generated table: only emeralds (1-2, at most every other refill) and a rare modest book (enchanting-table only). */
	@Test
	void theModestTableIsModest() throws IOException {
		Path f = Path.of(System.getProperty("heraldia.generated"), "data/heraldia/loot_table/botin/premium_vencido.json");
		JsonObject t = JsonParser.parseString(Files.readString(f)).getAsJsonObject();
		assertEquals("minecraft:chest", t.get("type").getAsString());
		String text = t.toString();
		for (String bad : List.of("netherite", "elytra", "diamond", "mending", "treasure", "on_random_loot", "enchanted_golden_apple", "totem")) {
			assertFalse(text.contains(bad), bad);
		}
		TreeSet<String> items = new TreeSet<>();
		for (JsonElement p : t.getAsJsonArray("pools")) {
			JsonObject pool = p.getAsJsonObject();
			assertEquals(1, pool.get("rolls").getAsInt(), "una tirada por grupo");
			int total = 0, nonEmpty = 0;
			for (JsonElement e : pool.getAsJsonArray("entries")) {
				JsonObject entry = e.getAsJsonObject();
				int w = entry.get("weight").getAsInt();
				total += w;
				if (entry.has("name")) {
					items.add(entry.get("name").getAsString());
					nonEmpty += w;
				}
			}
			assertTrue(nonEmpty * 2 <= total, "como mucho la mitad de las veces: " + pool);
		}
		assertEquals(new TreeSet<>(List.of("minecraft:book", "minecraft:emerald")), items);
		assertTrue(text.contains("in_enchanting_table"), "libro solo con encantamientos de mesa");
	}

	/** Every unique's premium chest in the templates is recognised (a renamed premium table would silently skip the rule). */
	@Test
	void templatePremiumChestsAreRecognised() throws IOException {
		Path root = Path.of(System.getProperty("heraldia.generated"), "data/heraldia/structure/unicas");
		List<Path> files = new ArrayList<>();
		try (Stream<Path> s = Files.walk(root)) {
			s.filter(p -> p.toString().endsWith(".nbt")).forEach(files::add);
		}
		TreeSet<String> uniques = new TreeSet<>();
		for (Path f : files) {
			CompoundTag t = NbtIo.readCompressed(f, NbtAccounter.unlimitedHeap());
			for (Tag b : t.getListOrEmpty("blocks")) {
				String sid = Restock.premiumOf(((CompoundTag) b).getCompoundOrEmpty("nbt").getStringOr("LootTable", ""));
				if (sid != null) {
					uniques.add(sid);
				}
			}
		}
		assertTrue(uniques.size() >= 15, "pocas únicas con cofre premium reconocido: " + uniques);
	}
}
