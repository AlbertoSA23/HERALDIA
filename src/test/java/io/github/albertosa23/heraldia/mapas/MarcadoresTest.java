package io.github.albertosa23.heraldia.mapas;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import io.github.albertosa23.heraldia.comando.Estado;
import io.github.albertosa23.heraldia.comando.Textos;
import java.util.EnumSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import org.junit.jupiter.api.Test;

/** Qué marcadores salen y cómo (posición, capa, nombre, descripción, icono), el filtro de solo descubiertas y su actualización. */
class MarcadoresTest {
	static final Map<String, String> ESTILOS = Map.of("llanura", "llanuras", "taiga", "taiga");
	static final Map<String, String> ES = Textos.textos("es_es"), EN = Textos.textos("en_us");
	static final Marcadores.Opciones TODO = new Marcadores.Opciones(true, false, EnumSet.allOf(Capa.class));
	static final Marcadores.Opciones DESCUBIERTAS = new Marcadores.Opciones(true, true, EnumSet.allOf(Capa.class));

	static List<Sitio> sitios() {
		return List.of(
				Sitio.de("unicas/castillo", ESTILOS, 1000, 70, -2000),
				Sitio.de("unicas/castillo", ESTILOS, -5000, 80, 3000),
				Sitio.de("llanura_grande", ESTILOS, 120, 64, 340),
				Sitio.de("taiga", ESTILOS, -800, 70, 90),
				Sitio.de("medianas/posada/llanura", ESTILOS, 400, 66, 400),
				Sitio.de("medianas/ermita/taiga", ESTILOS, 500, 66, 500),
				Sitio.de("minas/grande/llanura", ESTILOS, 600, 60, 600));
	}

	static Estado.Logros logros(String... hechos) {
		Estado.Logros l = new Estado.Logros();
		for (String h : hechos) {
			l.sumar(h, true, List.of());
		}
		return l;
	}

	@Test
	void construyeCadaMarcadorConSuPosicionCapaYNombre() {
		List<Marcador> ms = Marcadores.construir(sitios(), new int[]{10, 65, 20}, logros(), TODO, ES);
		assertEquals(8, ms.size());
		Marcador castillo = ms.get(0);
		assertEquals(Capa.UNICAS, castillo.capa());
		assertEquals(List.of(1000, 70, -2000), List.of(castillo.x(), castillo.y(), castillo.z()));
		assertEquals(ES.get("heraldia.unicas.castillo.nombre"), castillo.nombre());
		assertEquals(ES.get("heraldia.mapas_web.descripcion.unicas"), castillo.descripcion());
		assertEquals("unicas/castillo@1000,70,-2000", castillo.id());
		Marcador aldea = ms.stream().filter(m -> m.capa() == Capa.ALDEAS && m.x() == 120).findFirst().orElseThrow();
		assertEquals("Aldea: " + ES.get("heraldia.familia.llanuras"), aldea.nombre());
		Marcador posada = ms.stream().filter(m -> m.capa() == Capa.MEDIANAS && m.x() == 400).findFirst().orElseThrow();
		assertEquals(ES.get("heraldia.medianas.posada.nombre"), posada.nombre());
		Marcador mina = ms.stream().filter(m -> m.capa() == Capa.MINAS).findFirst().orElseThrow();
		assertEquals(ES.get("heraldia.minas.grande.nombre"), mina.nombre());
		Marcador arena = ms.get(ms.size() - 1);
		assertEquals(Capa.ARENA, arena.capa());
		assertEquals(List.of(10, 65, 20), List.of(arena.x(), arena.y(), arena.z()));
		assertEquals(ES.get("heraldia.arena.nombre"), arena.nombre());
	}

	@Test
	void todosLosTextosExistenEnEspañolEInglés() {
		for (Map<String, String> t : List.of(ES, EN)) {
			for (Marcador m : Marcadores.construir(sitios(), new int[]{0, 0, 0}, logros(), TODO, t)) {
				assertFalse(m.nombre().startsWith("heraldia."), m.nombre());
				assertFalse(m.descripcion().startsWith("heraldia."), m.descripcion());
			}
			Marcadores.nombresCapas(t).values().forEach(n -> assertFalse(n.startsWith("heraldia."), n));
		}
		assertEquals("Village: " + EN.get("heraldia.familia.taiga"), Marcadores.nombre(Capa.ALDEAS, "taiga", EN));
	}

	@Test
	void soloDescubiertasUsaLosLogrosDeEstado() {
		assertEquals(List.of(Capa.ARENA), Marcadores.construir(sitios(), new int[]{0, 0, 0}, logros(), DESCUBIERTAS, ES)
				.stream().map(Marcador::capa).toList(), "sin descubrir nada solo sale la arena");
		Estado.Logros l = logros("heraldia:unicas/castillo/descubrir", "heraldia:aldeas/taiga", "heraldia:minas/pequena");
		l.sumar("heraldia:medianas/todas", false, List.of("ermita"));
		List<Marcador> ms = Marcadores.construir(sitios(), null, l, DESCUBIERTAS, ES);
		assertEquals(List.of("unicas/castillo@-5000,80,3000", "unicas/castillo@1000,70,-2000", "taiga@-800,70,90",
				"medianas/ermita/taiga@500,66,500"), ms.stream().map(Marcador::id).sorted(MarcadoresTest::porCapaEId).toList());
	}

	private static int porCapaEId(String a, String b) {
		return a.compareTo(b) * -1 == 0 ? 0 : orden(a) != orden(b) ? Integer.compare(orden(a), orden(b)) : a.compareTo(b);
	}

	private static int orden(String id) {
		return id.startsWith("unicas") ? 0 : id.startsWith("medianas") ? 2 : 1;
	}

	@Test
	void unLogroNuevoActualizaLosMarcadores() {
		Estado.Logros l = logros();
		assertTrue(Marcadores.construir(sitios(), null, l, DESCUBIERTAS, ES).isEmpty());
		// lo que hace MapasWeb.alConseguir: el criterio recién conseguido se suma a los logros conocidos
		l.sumar("heraldia:medianas/todas", false, List.of("posada"));
		assertEquals(List.of("medianas/posada/llanura@400,66,400"),
				Marcadores.construir(sitios(), null, l, DESCUBIERTAS, ES).stream().map(Marcador::id).toList());
		l.sumar("heraldia:aldeas/llanuras", true, List.of("llanuras"));
		assertEquals(2, Marcadores.construir(sitios(), null, l, DESCUBIERTAS, ES).size());
		// un criterio sin terminar el logro no basta para aldeas, únicas ni minas
		l.sumar("heraldia:unicas/castillo/descubrir", false, List.of("descubrir"));
		assertEquals(2, Marcadores.construir(sitios(), null, l, DESCUBIERTAS, ES).size());
	}

	@Test
	void lasCapasYElInterruptorGeneral() {
		assertTrue(Marcadores.construir(sitios(), new int[]{0, 0, 0}, logros(), new Marcadores.Opciones(false, false,
				EnumSet.allOf(Capa.class)), ES).isEmpty());
		Marcadores.Opciones soloMinas = new Marcadores.Opciones(true, false, EnumSet.of(Capa.MINAS));
		List<Marcador> ms = Marcadores.construir(sitios(), new int[]{0, 0, 0}, logros(), soloMinas, ES);
		assertEquals(List.of(Capa.MINAS), ms.stream().map(Marcador::capa).toList());
		Map<Capa, List<Marcador>> porCapa = Marcadores.porCapa(ms, soloMinas);
		assertEquals(Set.of(Capa.MINAS), porCapa.keySet(), "las capas apagadas no salen (el mapa las quita)");
		Map<Capa, List<Marcador>> vacias = Marcadores.porCapa(List.of(), TODO);
		assertEquals(EnumSet.allOf(Capa.class), vacias.keySet(), "las capas activadas salen aunque estén vacías");
		assertTrue(Marcadores.porCapa(List.of(), new Marcadores.Opciones(false, false, EnumSet.allOf(Capa.class))).isEmpty());
		assertTrue(Marcadores.construir(sitios(), new int[]{0, 0, 0}, logros(),
				new Marcadores.Opciones(true, false, EnumSet.complementOf(EnumSet.of(Capa.ARENA))), ES)
				.stream().noneMatch(m -> m.capa() == Capa.ARENA));
	}

	@Test
	void reglasDeDescubiertoDeCadaCapa() {
		Estado.Logros l = logros("heraldia:aldeas/llanuras", "heraldia:unicas/faro/descubrir", "heraldia:minas/grande");
		l.sumar("heraldia:medianas/todas", false, List.of("molino"));
		assertTrue(Marcadores.descubierto(Capa.ALDEAS, "llanuras", l));
		assertFalse(Marcadores.descubierto(Capa.ALDEAS, "taiga", l));
		assertTrue(Marcadores.descubierto(Capa.UNICAS, "faro", l));
		assertFalse(Marcadores.descubierto(Capa.UNICAS, "castillo", l));
		assertTrue(Marcadores.descubierto(Capa.MEDIANAS, "molino", l));
		assertFalse(Marcadores.descubierto(Capa.MEDIANAS, "posada", l));
		assertTrue(Marcadores.descubierto(Capa.MINAS, "grande", l));
		assertFalse(Marcadores.descubierto(Capa.MINAS, "pequena", l));
		assertTrue(Marcadores.descubierto(Capa.ARENA, "", new Estado.Logros()));
	}

	@Test
	void htmlEscapado() {
		Marcador m = new Marcador("x", Capa.UNICAS, 0, 0, 0, "<script>&\"'", "a<b");
		assertEquals("<b>&lt;script&gt;&amp;&quot;&#39;</b><br>a&lt;b", m.html());
	}

	@Test
	void textoQueFaltaDevuelveLaClave() {
		assertEquals("heraldia.unicas.nada.nombre", Marcadores.nombre(Capa.UNICAS, "nada", Map.of()));
		assertEquals("Aldea (x)", Marcadores.nombre(Capa.ALDEAS, "f", Map.of("heraldia.mapas_web.aldea", "Aldea (x)",
				"heraldia.familia.f", "F")).replace(" F", ""));
	}

	@Test
	void idiomaDeLosMarcadores() {
		assertEquals("es_es", MapasWeb.idioma("auto", Locale.of("es", "ES")));
		assertEquals("fr_ca", MapasWeb.idioma("auto", Locale.of("fr", "CA")));
		assertEquals("gl_es", MapasWeb.idioma("gl_es", Locale.US));
		// un idioma del sistema que el .jar no trae: el de su lengua o el inglés (Textos.codigo)
		assertEquals(Textos.textos("fr_fr"), Textos.textos(MapasWeb.idioma("auto", Locale.of("fr", "CA"))));
		assertEquals(EN, Textos.textos(MapasWeb.idioma("auto", Locale.of("ja", "JP"))));
	}
}
