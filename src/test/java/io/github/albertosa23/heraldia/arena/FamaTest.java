package io.github.albertosa23.heraldia.arena;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import io.github.albertosa23.heraldia.comando.Textos;
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
class FamaTest {
	private static final UUID A = UUID.randomUUID(), B = UUID.randomUUID();
	private static final LocalDate L16 = LocalDate.of(2026, 11, 16), L23 = LocalDate.of(2026, 11, 23);
	private static Map<String, String> es, en;

	@BeforeAll
	static void bootstrap() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
		es = Textos.idioma("es_es");
		en = Textos.idioma("en_us");
	}

	private static Temporada conCampeones() {
		Temporada t = Temporada.VACIA.avanzar(L16, DayOfWeek.MONDAY, 8).temporada()
				.registrar(Modo.COOPERATIVO, new Temporada.Entrada(A, "Ana", 12, 9000, 1, 0))
				.registrar(Modo.CONTRARRELOJ, new Temporada.Entrada(B, "Bea", 10, (4 * 60 + 32) * 20, 2, 10));
		return t.avanzar(L23, DayOfWeek.MONDAY, 8).temporada();
	}

	@Test
	void paginasSinCampeones() {
		List<Map.Entry<String, Component>> p = Fama.paginas(Temporada.VACIA, L23, List.of(Modo.values()), es);
		assertEquals(2, p.size());
		assertEquals("heraldia.guia.fama.titulo", p.get(0).getKey());
		assertEquals("heraldia.guia.records.titulo", p.get(1).getKey());
		assertTrue(p.get(0).getValue().getString().startsWith("Aún no hay campeones"), p.get(0).getValue().getString());
		String records = p.get(1).getValue().getString();
		assertTrue(records.contains("• Cooperativo: nadie") && records.contains("• Contrarreloj: nadie")
				&& records.contains("• Supervivencia: nadie"), records);
	}

	@Test
	void paginasConCampeones() {
		List<Map.Entry<String, Component>> p = Fama.paginas(conCampeones(), L23, List.of(Modo.values()), es);
		String fama = p.get(0).getValue().getString();
		assertTrue(fama.startsWith("Campeones de la arena de la semana del 16/11/2026:"), fama);
		assertTrue(fama.contains("• Cooperativo: Ana, oleada 12"), fama);
		assertTrue(fama.contains("• Contrarreloj: Bea, 4:32 (10 oleadas)"), fama);
		assertTrue(fama.contains("• Supervivencia: nadie"), fama);
		String records = p.get(1).getValue().getString();
		assertTrue(records.contains("• Cooperativo: Ana, oleada 12") && records.contains("Bea, 4:32"), records);
		// en inglés, con el respaldo inglés
		String en1 = Fama.paginas(conCampeones(), L23, List.of(Modo.values()), en).get(0).getValue().getString();
		assertTrue(en1.contains("• Time attack: Bea, 4:32 (10 waves)") && en1.contains("• Co-op: Ana, wave 12"), en1);
		// solo los modos activados
		String solo = Fama.paginas(conCampeones(), L23, List.of(Modo.CONTRARRELOJ), es).get(0).getValue().getString();
		assertTrue(!solo.contains("Cooperativo") && solo.contains("Bea"), solo);
		// la semana siguiente ya no son los de la semana anterior
		String despues = Fama.paginas(conCampeones(), L23.plusWeeks(1), List.of(Modo.values()), es).get(0).getValue().getString();
		assertTrue(despues.startsWith("Aún no hay campeones"), despues);
	}

	@Test
	void lineasDelCartel() {
		Temporada.Entrada bea = new Temporada.Entrada(B, "Bea", 10, (4 * 60 + 32) * 20, 2, 10);
		Component[] l = Fama.lineas(Modo.CONTRARRELOJ, bea, L16.toEpochDay());
		assertEquals(4, l.length);
		assertEquals(List.of("Campeón", "Contrarreloj", "Bea", "4:32"), List.of(l).stream().map(Component::getString).toList());
		Component[] medias = Fama.lineas(Modo.CONTRARRELOJ, new Temporada.Entrada(B, "Bea", 7, 900, 2, 10), L16.toEpochDay());
		assertEquals("7/10 oleadas", medias[3].getString());
		Component[] sup = Fama.lineas(Modo.SUPERVIVENCIA, new Temporada.Entrada(A, "Ana", 17, 900, 2, 0), L16.toEpochDay());
		assertEquals("oleada 17", sup[3].getString());
		Component[] nadie = Fama.lineas(Modo.COOPERATIVO, null, L16.toEpochDay());
		assertEquals(List.of("Campeón", "Cooperativo", "Sin campeón", "16/11/2026"), List.of(nadie).stream().map(Component::getString).toList());
		assertEquals("", Fama.lineas(Modo.COOPERATIVO, null, Temporada.SIN_SEMANA)[3].getString());
	}

	@Test
	void fechas() {
		assertEquals("16/11/2026", Fama.fecha(L16.toEpochDay()));
		assertEquals("-", Fama.fecha(Temporada.SIN_SEMANA));
	}

	@Test
	void planoConCarteles() {
		String json = ZonaTest.JSON.replace("\"jefes\": 4}", "\"jefes\": 4, \"fama\": [[31, 8, 52], [32, 8, 52], [33, 8, 52]], \"fama_rotacion\": 0}");
		Plano p = Plano.leer(new StringReader(json));
		assertEquals(3, p.fama().size());
		assertEquals(List.of(31, 8, 52), java.util.Arrays.stream(p.fama().get(0)).boxed().toList());
		assertEquals(0, p.famaRotacion());
		Zona z = new Zona(100, 60, -200, p);
		assertTrue(z.contiene(z.mundo(p.fama().get(2))[0], z.mundo(p.fama().get(2))[1], z.mundo(p.fama().get(2))[2]),
				"los carteles están dentro de la caja protegida");
		// un plano de antes de T41 (sin carteles) se sigue leyendo
		Plano viejo = ZonaTest.plano();
		assertTrue(viejo.fama().isEmpty());
		assertEquals(0, viejo.famaRotacion());
	}
}
