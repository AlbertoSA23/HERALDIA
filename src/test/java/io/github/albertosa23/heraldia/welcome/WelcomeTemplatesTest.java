package io.github.albertosa23.heraldia.welcome;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.mojang.serialization.JsonOps;
import io.github.albertosa23.heraldia.welcome.Spots.Piece;
import io.github.albertosa23.heraldia.welcome.Spots.Spot;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Stream;
import net.minecraft.SharedConstants;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.NbtAccounter;
import net.minecraft.nbt.NbtIo;
import net.minecraft.nbt.Tag;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.level.block.Blocks;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/**
 * The spots against the real generated templates of every style: each decoration goes on a cell its template leaves to the
 * terrain or fills with air (never on one of the village's own blocks), and leans on a real block of that template. If a
 * generator change moves a gate's wall or the fountain, this test says which spot is now wrong.
 */
class WelcomeTemplatesTest {
	@BeforeAll
	static void bootstrap() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	/** Template blocks by local position "x,y,z" → block id, from the .nbt as the generator wrote it. */
	static Map<String, String> blocks(Path f) throws IOException {
		CompoundTag t = NbtIo.readCompressed(f, NbtAccounter.unlimitedHeap());
		ListTag palette = t.getListOrEmpty("palette");
		Map<String, String> m = new HashMap<>();
		for (Tag b : t.getListOrEmpty("blocks")) {
			CompoundTag c = (CompoundTag) b;
			ListTag pos = c.getListOrEmpty("pos");
			CompoundTag entry = palette.getCompoundOrEmpty(c.getIntOr("state", 0));
			String name = entry.getStringOr("id", entry.getStringOr("Name", ""));   // 26.3 writes "id"
			m.put(pos.getIntOr(0, 0) + "," + pos.getIntOr(1, 0) + "," + pos.getIntOr(2, 0), name);
		}
		return m;
	}

	static boolean empty(String id) {
		return id == null || id.equals("minecraft:air") || id.equals("minecraft:structure_void");
	}

	@Test
	void everySpotFitsEveryStyle() throws IOException {
		Path root = Path.of(System.getProperty("heraldia.generated"), "data/heraldia/structure");
		List<Path> files = new ArrayList<>();
		try (Stream<Path> s = Files.walk(root)) {
			s.filter(p -> p.toString().endsWith(".nbt")).forEach(files::add);
		}
		Map<Piece, Integer> checked = new HashMap<>();
		List<String> bad = new ArrayList<>();
		for (Path f : files) {
			String rel = root.relativize(f).toString().replace('\\', '/');
			Piece piece = Piece.of(rel.substring(0, rel.length() - ".nbt".length()));
			if (piece == null || rel.startsWith("unicas/") || rel.startsWith("medianas/")) {
				continue;
			}
			Map<String, String> b = blocks(f);
			for (Spot s : Spots.of(piece)) {
				String at = b.get(s.x() + "," + s.y() + "," + s.z());
				if (!empty(at)) {
					bad.add(rel + ": " + s.item() + " at " + s.x() + "," + s.y() + "," + s.z() + " is on the template's " + at);
				}
				if (s.templateSupport()) {
					String sup = b.get(s.sx() + "," + s.sy() + "," + s.sz());
					if (empty(sup) || sup.endsWith("jigsaw") || sup.contains("water") || sup.contains("lantern")) {
						bad.add(rel + ": " + s.item() + " at " + s.x() + "," + s.y() + "," + s.z() + " has no support (" + sup + ")");
					}
				}
			}
			checked.merge(piece, 1, Integer::sum);
		}
		assertTrue(bad.isEmpty(), "spots that do not fit:\n" + String.join("\n", bad));
		// 36 styles: one gate, two towers, two squares and one job board each
		assertEquals(36, checked.getOrDefault(Piece.GATE, 0), checked.toString());
		assertEquals(72, checked.getOrDefault(Piece.TOWER, 0), checked.toString());
		assertEquals(72, checked.getOrDefault(Piece.PLAZA, 0), checked.toString());
		assertEquals(36, checked.getOrDefault(Piece.BOARD, 0), checked.toString());
	}

	@Test
	void everyGateHasABannerToTakeTheColourFrom() throws IOException {
		Path root = Path.of(System.getProperty("heraldia.generated"), "data/heraldia/structure");
		try (Stream<Path> s = Files.walk(root)) {
			for (Path f : s.filter(p -> p.toString().endsWith("/terminators/gate.nbt")).toList()) {
				assertTrue(blocks(f).values().stream().anyMatch(id -> Spots.bannerColour(id) != null), f.toString());
			}
		}
	}

	@Test
	void theRecordSurvivesSavingAndLoading() {
		Shown s = Shown.EMPTY;
		List<String> changed = new ArrayList<>();
		s = s.sync("uuid-a", Map.of("3,-4", 80, "10,10", -20), changed);
		assertEquals(2, changed.size());
		Shown.Village v = s.village("3,-4").with(Map.of(42L, Blocks.LANTERN.defaultBlockState()), List.of(), List.of(7L));
		s = s.with("3,-4", v);
		Shown back = Shown.CODEC.parse(JsonOps.INSTANCE, Shown.CODEC.encodeStart(JsonOps.INSTANCE, s).getOrThrow()).getOrThrow();
		assertEquals(s, back);
		assertEquals(Blocks.LANTERN.defaultBlockState(), back.village("3,-4").placedAt(42L));
		assertTrue(back.village("3,-4").isDeclined(7L));
		assertEquals(80, back.village("3,-4").points().get("uuid-a"));
		// syncing the same reputation again changes nothing; a reputation back to 0 leaves no trace
		changed.clear();
		assertEquals(s, s.sync("uuid-a", Map.of("3,-4", 80, "10,10", -20), changed));
		assertTrue(changed.isEmpty());
		Shown zero = s.sync("uuid-a", Map.of("10,10", 0), changed);
		assertTrue(zero.villages().get("10,10") == null, "a village with nothing left is not kept");
		// a removal drops what was placed
		Shown.Village after = back.village("3,-4").with(Map.of(), List.of(42L), List.of());
		assertEquals(null, after.placedAt(42L));
	}
}
