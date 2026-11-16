package io.github.albertosa23.heraldia.comun;

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
 * Mobs anclados: la lógica de {@link Anclaje} y, sobre las plantillas generadas (build/generated), que todo guardián
 * final y todo zombi o esqueleto lleva la etiqueta, que cada única tiene su guardián anclado y que ningún aldeano la
 * lleva (deben seguir recogiendo cosechas).
 */
class AnclajeTest {
	private static final String GUARDIAN = "heraldia_guardian";
	/** Tipos de core.RECOGE_BOTIN (los que el juego deja recoger objetos al colocarlos). */
	private static final Set<String> RECOGE = Set.of("zombie", "husk", "drowned", "zombie_villager", "zombified_piglin",
			"skeleton", "stray", "bogged", "wither_skeleton", "parched", "piglin", "piglin_brute");
	/** (plantilla, NBT) de cada entidad de las plantillas generadas. */
	private static final List<Map.Entry<String, CompoundTag>> ENTIDADES = new ArrayList<>();

	@BeforeAll
	static void leer() throws IOException {
		Path root = Path.of(System.getProperty("heraldia.generated"), "data/heraldia/structure");
		List<Path> files = new ArrayList<>();
		try (Stream<Path> s = Files.walk(root)) {
			s.filter(p -> p.toString().endsWith(".nbt")).forEach(files::add);
		}
		for (Path f : files) {
			CompoundTag t = NbtIo.readCompressed(f, NbtAccounter.unlimitedHeap());
			for (Tag e : t.getListOrEmpty("entities")) {
				ENTIDADES.add(Map.entry(root.relativize(f).toString(), ((CompoundTag) e).getCompoundOrEmpty("nbt")));
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

	private static String tipo(CompoundTag nbt) {
		return nbt.getStringOr("id", "").replace("minecraft:", "");
	}

	@Test
	void etiqueta() {
		assertTrue(Anclaje.anclado(Set.of(Anclaje.TAG)));
		assertTrue(Anclaje.anclado(Set.of(GUARDIAN, "heraldia_adulto", Anclaje.TAG)));
		assertFalse(Anclaje.anclado(Set.of()));
		assertFalse(Anclaje.anclado(Set.of(GUARDIAN, "heraldia_adulto")));
		assertFalse(Anclaje.anclado(Set.of("heraldia_anclado.x", "heraldia_anclad")));
	}

	@Test
	void quieto() {
		assertEquals(Anclaje.QUIETO, Anclaje.quieto(0));
		assertEquals(Anclaje.QUIETO, Anclaje.quieto(99));
		assertEquals(Anclaje.QUIETO, Anclaje.quieto(Anclaje.QUIETO));
		assertEquals(5000, Anclaje.quieto(5000));
		assertEquals(100, Anclaje.QUIETO, "RandomStrollGoal.canUse exige getNoActionTime() < 100 (26.3)");
	}

	@Test
	void quietoHastaElCombate() {
		assertTrue(Anclaje.quieto(false, Anclaje.QUIETO));
		assertTrue(Anclaje.quieto(false, 5000));
		assertFalse(Anclaje.quieto(true, Anclaje.QUIETO), "con objetivo: combate");
		assertFalse(Anclaje.quieto(false, 0), "recién golpeado: noActionTime a 0");
		assertFalse(Anclaje.quieto(false, Anclaje.QUIETO - 1));
	}

	@Test
	void mismaEtiquetaQueElGenerador() throws IOException {
		String core = Files.readString(Path.of("tools/gen/core.py"));
		Matcher m = Pattern.compile("^ANCLADO_TAG = \"([^\"]+)\"", Pattern.MULTILINE).matcher(core);
		assertTrue(m.find(), "core.ANCLADO_TAG");
		assertEquals(m.group(1), Anclaje.TAG);
		for (String mob : RECOGE) {
			assertTrue(core.contains('"' + mob + '"'), mob + " no está en core.RECOGE_BOTIN");
		}
	}

	@Test
	void guardianesYRecogedoresAnclados() {
		assertFalse(ENTIDADES.isEmpty());
		List<String> sin = new ArrayList<>();
		for (Map.Entry<String, CompoundTag> e : ENTIDADES) {
			Set<String> tags = tags(e.getValue());
			if ((tags.contains(GUARDIAN) || RECOGE.contains(tipo(e.getValue()))) && !tags.contains(Anclaje.TAG)) {
				sin.add(e.getKey() + " (" + tipo(e.getValue()) + ")");
			}
		}
		assertTrue(sin.isEmpty(), "sin " + Anclaje.TAG + ": " + sin);
	}

	@Test
	void cadaUnicaConSuGuardianAnclado() throws IOException {
		Map<String, Integer> porUnica = new HashMap<>();
		for (Map.Entry<String, CompoundTag> e : ENTIDADES) {
			Set<String> tags = tags(e.getValue());
			if (tags.contains(GUARDIAN) && tags.contains(Anclaje.TAG) && e.getKey().startsWith("unicas")) {
				porUnica.merge(e.getKey().split("[/\\\\]")[1].replace(".nbt", ""), 1, Integer::sum);
			}
		}
		Set<String> unicas = new HashSet<>();
		try (Stream<Path> s = Files.list(Path.of(System.getProperty("heraldia.generated"), "data/heraldia/worldgen/structure/unicas"))) {
			s.forEach(p -> unicas.add(p.getFileName().toString().replace(".json", "")));
		}
		assertFalse(unicas.isEmpty());
		assertEquals(unicas, porUnica.keySet(), "únicas sin guardián anclado");
		porUnica.forEach((id, n) -> assertEquals(1, n, id + ": un solo guardián"));
	}

	@Test
	void aldeanosSinAnclar() {
		int aldeanos = 0;
		for (Map.Entry<String, CompoundTag> e : ENTIDADES) {
			if (tipo(e.getValue()).equals("villager")) {
				aldeanos++;
				assertFalse(tags(e.getValue()).contains(Anclaje.TAG), e.getKey() + ": un aldeano debe poder recoger cosechas");
			}
		}
		assertTrue(aldeanos > 0);
	}
}
