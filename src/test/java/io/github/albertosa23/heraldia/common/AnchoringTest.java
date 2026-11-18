package io.github.albertosa23.heraldia.common;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Stream;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.NbtAccounter;
import net.minecraft.nbt.NbtIo;
import net.minecraft.nbt.Tag;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/**
 * Mobs anclados: la lógica de {@link Anchoring} y, sobre las plantillas generadas (build/generated), que todo guardián
 * final y todo zombi o esqueleto lleva la etiqueta, que cada única tiene su guardián anclado y que ningún aldeano la
 * lleva (deben seguir recogiendo cosechas).
 */
class AnchoringTest {
	private static final String GUARDIAN = "heraldia_guardian";
	/** Tipos de core.RECOGE_BOTIN (los que el juego deja recoger objetos al colocarlos). */
	private static final Set<String> PICKS_UP = Set.of("zombie", "husk", "drowned", "zombie_villager", "zombified_piglin",
			"skeleton", "stray", "bogged", "wither_skeleton", "parched", "piglin", "piglin_brute");
	/** (plantilla, NBT) de cada entidad de las plantillas generadas. */
	private static final List<Map.Entry<String, CompoundTag>> ENTITIES = new ArrayList<>();

	@BeforeAll
	static void read() throws IOException {
		Path root = Path.of(System.getProperty("heraldia.generated"), "data/heraldia/structure");
		List<Path> files = new ArrayList<>();
		try (Stream<Path> s = Files.walk(root)) {
			s.filter(p -> p.toString().endsWith(".nbt")).forEach(files::add);
		}
		for (Path f : files) {
			CompoundTag t = NbtIo.readCompressed(f, NbtAccounter.unlimitedHeap());
			for (Tag e : t.getListOrEmpty("entities")) {
				ENTITIES.add(Map.entry(root.relativize(f).toString(), ((CompoundTag) e).getCompoundOrEmpty("nbt")));
			}
		}
	}

	private static Set<String> tags(CompoundTag nbt) {
		Set<String> out = new HashSet<>();
		ListTag list = nbt.getListOrEmpty("Tags");
		for (Tag t : list) {
			t.asString().ifPresent(out::add);
		}
		return out;
	}

	private static String type(CompoundTag nbt) {
		return nbt.getStringOr("id", "").replace("minecraft:", "");
	}

	@Test
	void tag() {
		assertTrue(Anchoring.anchored(Set.of(Anchoring.TAG)));
		assertTrue(Anchoring.anchored(Set.of(GUARDIAN, "heraldia_adulto", Anchoring.TAG)));
		assertFalse(Anchoring.anchored(Set.of()));
		assertFalse(Anchoring.anchored(Set.of(GUARDIAN, "heraldia_adulto")));
		assertFalse(Anchoring.anchored(Set.of("heraldia_anclado.x", "heraldia_anclad")));
	}

	@Test
	void still() {
		assertEquals(Anchoring.STILL, Anchoring.still(0));
		assertEquals(Anchoring.STILL, Anchoring.still(99));
		assertEquals(Anchoring.STILL, Anchoring.still(Anchoring.STILL));
		assertEquals(5000, Anchoring.still(5000));
		assertEquals(100, Anchoring.STILL, "RandomStrollGoal.canUse exige getNoActionTime() < 100 (26.3)");
	}

	@Test
	void stillUntilCombat() {
		assertTrue(Anchoring.still(false, Anchoring.STILL));
		assertTrue(Anchoring.still(false, 5000));
		assertFalse(Anchoring.still(true, Anchoring.STILL), "con objetivo: combate");
		assertFalse(Anchoring.still(false, 0), "recién golpeado: noActionTime a 0");
		assertFalse(Anchoring.still(false, Anchoring.STILL - 1));
	}

	@Test
	void sameTagAsTheGenerator() throws IOException {
		String core = Files.readString(Path.of("tools/gen/core.py"));
		Matcher m = Pattern.compile("^ANCLADO_TAG = \"([^\"]+)\"", Pattern.MULTILINE).matcher(core);
		assertTrue(m.find(), "core.ANCLADO_TAG");
		assertEquals(m.group(1), Anchoring.TAG);
		for (String mob : PICKS_UP) {
			assertTrue(core.contains('"' + mob + '"'), mob + " no está en core.RECOGE_BOTIN");
		}
	}

	@Test
	void guardiansAndPickersAnchored() {
		assertFalse(ENTITIES.isEmpty());
		List<String> sin = new ArrayList<>();
		for (Map.Entry<String, CompoundTag> e : ENTITIES) {
			Set<String> tags = tags(e.getValue());
			if ((tags.contains(GUARDIAN) || PICKS_UP.contains(type(e.getValue()))) && !tags.contains(Anchoring.TAG)) {
				sin.add(e.getKey() + " (" + type(e.getValue()) + ")");
			}
		}
		assertTrue(sin.isEmpty(), "sin " + Anchoring.TAG + ": " + sin);
	}

	@Test
	void eachUniqueWithItsAnchoredGuardian() throws IOException {
		Map<String, Integer> perUnique = new HashMap<>();
		for (Map.Entry<String, CompoundTag> e : ENTITIES) {
			Set<String> tags = tags(e.getValue());
			if (tags.contains(GUARDIAN) && tags.contains(Anchoring.TAG) && e.getKey().startsWith("unicas")) {
				perUnique.merge(e.getKey().split("[/\\\\]")[1].replace(".nbt", ""), 1, Integer::sum);
			}
		}
		Set<String> uniques = new HashSet<>();
		try (Stream<Path> s = Files.list(Path.of(System.getProperty("heraldia.generated"), "data/heraldia/worldgen/structure/unicas"))) {
			s.forEach(p -> uniques.add(p.getFileName().toString().replace(".json", "")));
		}
		assertFalse(uniques.isEmpty());
		assertEquals(uniques, perUnique.keySet(), "únicas sin guardián anclado");
		perUnique.forEach((id, n) -> assertEquals(1, n, id + ": un solo guardián"));
	}

	@Test
	void villagersNotAnchored() {
		int villagers = 0;
		for (Map.Entry<String, CompoundTag> e : ENTITIES) {
			if (type(e.getValue()).equals("villager")) {
				villagers++;
				assertFalse(tags(e.getValue()).contains(Anchoring.TAG), e.getKey() + ": un aldeano debe poder recoger cosechas");
			}
		}
		assertTrue(villagers > 0);
	}
}
