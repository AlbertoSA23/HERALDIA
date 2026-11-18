package io.github.albertosa23.heraldia.arena;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import io.github.albertosa23.heraldia.command.Texts;
import java.io.StringReader;
import java.time.DayOfWeek;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import net.minecraft.SharedConstants;
import net.minecraft.network.chat.Component;
import net.minecraft.server.Bootstrap;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/**
 * El salón de la fama (T41) como lo ve un cliente sin el mod (cada traducible con su respaldo del .jar): las páginas de
 * la Guía con y sin campeones, en español y en inglés, y las líneas de los carteles; y el plano con sus carteles.
 */
class FameTest {
	private static final UUID A = UUID.randomUUID(), B = UUID.randomUUID();
	private static final LocalDate L16 = LocalDate.of(2026, 11, 16), L23 = LocalDate.of(2026, 11, 23);
	private static Map<String, String> es, en;

	@BeforeAll
	static void bootstrap() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
		es = Texts.language("es_es");
		en = Texts.language("en_us");
	}

	private static Season withChampions() {
		Season t = Season.EMPTY.advance(L16, DayOfWeek.MONDAY, 8).season()
				.register(Mode.COOP, new Season.Entry(A, "Ana", 12, 9000, 1, 0))
				.register(Mode.TIME_TRIAL, new Season.Entry(B, "Bea", 10, (4 * 60 + 32) * 20, 2, 10));
		return t.advance(L23, DayOfWeek.MONDAY, 8).season();
	}

	@Test
	void pagesWithoutChampions() {
		List<Map.Entry<String, Component>> p = Fame.pages(Season.EMPTY, L23, List.of(Mode.values()), es);
		assertEquals(2, p.size());
		assertEquals("heraldia.guia.fama.titulo", p.get(0).getKey());
		assertEquals("heraldia.guia.records.titulo", p.get(1).getKey());
		assertTrue(p.get(0).getValue().getString().startsWith("Aún no hay campeones"), p.get(0).getValue().getString());
		String records = p.get(1).getValue().getString();
		assertTrue(records.contains("• Cooperativo: nadie") && records.contains("• Contrarreloj: nadie")
				&& records.contains("• Supervivencia: nadie"), records);
	}

	@Test
	void pagesWithChampions() {
		List<Map.Entry<String, Component>> p = Fame.pages(withChampions(), L23, List.of(Mode.values()), es);
		String fame = p.get(0).getValue().getString();
		assertTrue(fame.startsWith("Campeones de la arena de la semana del 16/11/2026:"), fame);
		assertTrue(fame.contains("• Cooperativo: Ana, oleada 12"), fame);
		assertTrue(fame.contains("• Contrarreloj: Bea, 4:32 (10 oleadas)"), fame);
		assertTrue(fame.contains("• Supervivencia: nadie"), fame);
		String records = p.get(1).getValue().getString();
		assertTrue(records.contains("• Cooperativo: Ana, oleada 12") && records.contains("Bea, 4:32"), records);
		// en inglés, con el respaldo inglés
		String en1 = Fame.pages(withChampions(), L23, List.of(Mode.values()), en).get(0).getValue().getString();
		assertTrue(en1.contains("• Time attack: Bea, 4:32 (10 waves)") && en1.contains("• Co-op: Ana, wave 12"), en1);
		// solo los modos activados
		String alone = Fame.pages(withChampions(), L23, List.of(Mode.TIME_TRIAL), es).get(0).getValue().getString();
		assertTrue(!alone.contains("Cooperativo") && alone.contains("Bea"), alone);
		// la semana siguiente ya no son los de la semana anterior
		String after = Fame.pages(withChampions(), L23.plusWeeks(1), List.of(Mode.values()), es).get(0).getValue().getString();
		assertTrue(after.startsWith("Aún no hay campeones"), after);
	}

	@Test
	void signLines() {
		Season.Entry bea = new Season.Entry(B, "Bea", 10, (4 * 60 + 32) * 20, 2, 10);
		Component[] l = Fame.lines(Mode.TIME_TRIAL, bea, L16.toEpochDay());
		assertEquals(4, l.length);
		assertEquals(List.of("Campeón", "Contrarreloj", "Bea", "4:32"), List.of(l).stream().map(Component::getString).toList());
		Component[] halves = Fame.lines(Mode.TIME_TRIAL, new Season.Entry(B, "Bea", 7, 900, 2, 10), L16.toEpochDay());
		assertEquals("7/10 oleadas", halves[3].getString());
		Component[] sup = Fame.lines(Mode.SURVIVAL, new Season.Entry(A, "Ana", 17, 900, 2, 0), L16.toEpochDay());
		assertEquals("oleada 17", sup[3].getString());
		Component[] nobody = Fame.lines(Mode.COOP, null, L16.toEpochDay());
		assertEquals(List.of("Campeón", "Cooperativo", "Sin campeón", "16/11/2026"), List.of(nobody).stream().map(Component::getString).toList());
		assertEquals("", Fame.lines(Mode.COOP, null, Season.NO_WEEK)[3].getString());
	}

	@Test
	void dates() {
		assertEquals("16/11/2026", Fame.date(L16.toEpochDay()));
		assertEquals("-", Fame.date(Season.NO_WEEK));
	}

	@Test
	void planWithSigns() {
		String json = ZoneTest.JSON.replace("\"jefes\": 4}", "\"jefes\": 4, \"fama\": [[31, 8, 52], [32, 8, 52], [33, 8, 52]], \"fama_rotacion\": 0}");
		Blueprint p = Blueprint.read(new StringReader(json));
		assertEquals(3, p.fame().size());
		assertEquals(List.of(31, 8, 52), java.util.Arrays.stream(p.fame().get(0)).boxed().toList());
		assertEquals(0, p.fameRotation());
		Zone z = new Zone(100, 60, -200, p);
		assertTrue(z.mentions(z.world(p.fame().get(2))[0], z.world(p.fame().get(2))[1], z.world(p.fame().get(2))[2]),
				"los carteles están dentro de la caja protegida");
		// un plano de antes de T41 (sin carteles) se sigue leyendo
		Blueprint oldValue = ZoneTest.plan();
		assertTrue(oldValue.fame().isEmpty());
		assertEquals(0, oldValue.fameRotation());
	}
}
