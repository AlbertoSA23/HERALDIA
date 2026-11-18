package io.github.albertosa23.heraldia.maps;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import io.github.albertosa23.heraldia.command.State;
import io.github.albertosa23.heraldia.command.Texts;
import java.util.EnumSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import org.junit.jupiter.api.Test;

/** Qué marcadores salen y cómo (posición, capa, nombre, descripción, icono), el filtro de solo descubiertas y su actualización. */
class MarkersTest {
	static final Map<String, String> STYLES = Map.of("llanura", "llanuras", "taiga", "taiga");
	static final Map<String, String> ES = Texts.texts("es_es"), EN = Texts.texts("en_us");
	static final Markers.Options ALL = new Markers.Options(true, false, EnumSet.allOf(Layer.class));
	static final Markers.Options DISCOVERED = new Markers.Options(true, true, EnumSet.allOf(Layer.class));

	static List<Site> sites() {
		return List.of(
				Site.of("unicas/castillo", STYLES, 1000, 70, -2000),
				Site.of("unicas/castillo", STYLES, -5000, 80, 3000),
				Site.of("llanura_grande", STYLES, 120, 64, 340),
				Site.of("taiga", STYLES, -800, 70, 90),
				Site.of("medianas/posada/llanura", STYLES, 400, 66, 400),
				Site.of("medianas/ermita/taiga", STYLES, 500, 66, 500),
				Site.of("minas/grande/llanura", STYLES, 600, 60, 600));
	}

	static State.Achievements advancements(String... finished) {
		State.Achievements l = new State.Achievements();
		for (String h : finished) {
			l.add(h, true, List.of());
		}
		return l;
	}

	@Test
	void buildsEachMarkerWithPositionLayerAndName() {
		List<MapMarker> ms = Markers.build(sites(), new int[]{10, 65, 20}, advancements(), ALL, ES);
		assertEquals(8, ms.size());
		MapMarker castle = ms.get(0);
		assertEquals(Layer.UNIQUES, castle.layer());
		assertEquals(List.of(1000, 70, -2000), List.of(castle.x(), castle.y(), castle.z()));
		assertEquals(ES.get("heraldia.unicas.castillo.nombre"), castle.name());
		assertEquals(ES.get("heraldia.mapas_web.descripcion.unicas"), castle.description());
		assertEquals("unicas/castillo@1000,70,-2000", castle.id());
		MapMarker village = ms.stream().filter(m -> m.layer() == Layer.VILLAGES && m.x() == 120).findFirst().orElseThrow();
		assertEquals("Aldea: " + ES.get("heraldia.familia.llanuras"), village.name());
		MapMarker inn = ms.stream().filter(m -> m.layer() == Layer.MEDIUMS && m.x() == 400).findFirst().orElseThrow();
		assertEquals(ES.get("heraldia.medianas.posada.nombre"), inn.name());
		MapMarker mine = ms.stream().filter(m -> m.layer() == Layer.MINES).findFirst().orElseThrow();
		assertEquals(ES.get("heraldia.minas.grande.nombre"), mine.name());
		MapMarker arena = ms.get(ms.size() - 1);
		assertEquals(Layer.ARENA, arena.layer());
		assertEquals(List.of(10, 65, 20), List.of(arena.x(), arena.y(), arena.z()));
		assertEquals(ES.get("heraldia.arena.nombre"), arena.name());
	}

	@Test
	void allTextsExistInSpanishAndEnglish() {
		for (Map<String, String> t : List.of(ES, EN)) {
			for (MapMarker m : Markers.build(sites(), new int[]{0, 0, 0}, advancements(), ALL, t)) {
				assertFalse(m.name().startsWith("heraldia."), m.name());
				assertFalse(m.description().startsWith("heraldia."), m.description());
			}
			Markers.layerNames(t).values().forEach(n -> assertFalse(n.startsWith("heraldia."), n));
		}
		assertEquals("Village: " + EN.get("heraldia.familia.taiga"), Markers.name(Layer.VILLAGES, "taiga", EN));
	}

	@Test
	void onlyDiscoveredUsesStatusAdvancements() {
		assertEquals(List.of(Layer.ARENA), Markers.build(sites(), new int[]{0, 0, 0}, advancements(), DISCOVERED, ES)
				.stream().map(MapMarker::layer).toList(), "sin descubrir nada solo sale la arena");
		State.Achievements l = advancements("heraldia:unicas/castillo/descubrir", "heraldia:aldeas/taiga", "heraldia:minas/pequena");
		l.add("heraldia:medianas/todas", false, List.of("ermita"));
		List<MapMarker> ms = Markers.build(sites(), null, l, DISCOVERED, ES);
		assertEquals(List.of("unicas/castillo@-5000,80,3000", "unicas/castillo@1000,70,-2000", "taiga@-800,70,90",
				"medianas/ermita/taiga@500,66,500"), ms.stream().map(MapMarker::id).sorted(MarkersTest::byLayerAndId).toList());
	}

	private static int byLayerAndId(String a, String b) {
		return a.compareTo(b) * -1 == 0 ? 0 : order(a) != order(b) ? Integer.compare(order(a), order(b)) : a.compareTo(b);
	}

	private static int order(String id) {
		return id.startsWith("unicas") ? 0 : id.startsWith("medianas") ? 2 : 1;
	}

	@Test
	void newAdvancementUpdatesMarkers() {
		State.Achievements l = advancements();
		assertTrue(Markers.build(sites(), null, l, DISCOVERED, ES).isEmpty());
		// lo que hace MapasWeb.alConseguir: el criterio recién conseguido se suma a los logros conocidos
		l.add("heraldia:medianas/todas", false, List.of("posada"));
		assertEquals(List.of("medianas/posada/llanura@400,66,400"),
				Markers.build(sites(), null, l, DISCOVERED, ES).stream().map(MapMarker::id).toList());
		l.add("heraldia:aldeas/llanuras", true, List.of("llanuras"));
		assertEquals(2, Markers.build(sites(), null, l, DISCOVERED, ES).size());
		// un criterio sin terminar el logro no basta para aldeas, únicas ni minas
		l.add("heraldia:unicas/castillo/descubrir", false, List.of("descubrir"));
		assertEquals(2, Markers.build(sites(), null, l, DISCOVERED, ES).size());
	}

	@Test
	void layersAndMasterSwitch() {
		assertTrue(Markers.build(sites(), new int[]{0, 0, 0}, advancements(), new Markers.Options(false, false,
				EnumSet.allOf(Layer.class)), ES).isEmpty());
		Markers.Options onlyMines = new Markers.Options(true, false, EnumSet.of(Layer.MINES));
		List<MapMarker> ms = Markers.build(sites(), new int[]{0, 0, 0}, advancements(), onlyMines, ES);
		assertEquals(List.of(Layer.MINES), ms.stream().map(MapMarker::layer).toList());
		Map<Layer, List<MapMarker>> byLayer = Markers.byLayer(ms, onlyMines);
		assertEquals(Set.of(Layer.MINES), byLayer.keySet(), "las capas apagadas no salen (el mapa las quita)");
		Map<Layer, List<MapMarker>> empties = Markers.byLayer(List.of(), ALL);
		assertEquals(EnumSet.allOf(Layer.class), empties.keySet(), "las capas activadas salen aunque estén vacías");
		assertTrue(Markers.byLayer(List.of(), new Markers.Options(false, false, EnumSet.allOf(Layer.class))).isEmpty());
		assertTrue(Markers.build(sites(), new int[]{0, 0, 0}, advancements(),
				new Markers.Options(true, false, EnumSet.complementOf(EnumSet.of(Layer.ARENA))), ES)
				.stream().noneMatch(m -> m.layer() == Layer.ARENA));
	}

	@Test
	void discoveryRulesOfEachLayer() {
		State.Achievements l = advancements("heraldia:aldeas/llanuras", "heraldia:unicas/faro/descubrir", "heraldia:minas/grande", "heraldia:costa/faro");
		l.add("heraldia:medianas/todas", false, List.of("molino"));
		assertTrue(Markers.discovered(Layer.VILLAGES, "llanuras", l));
		assertFalse(Markers.discovered(Layer.VILLAGES, "taiga", l));
		assertTrue(Markers.discovered(Layer.UNIQUES, "faro", l));
		assertFalse(Markers.discovered(Layer.UNIQUES, "castillo", l));
		assertTrue(Markers.discovered(Layer.MEDIUMS, "molino", l));
		assertFalse(Markers.discovered(Layer.MEDIUMS, "posada", l));
		assertTrue(Markers.discovered(Layer.MINES, "grande", l));
		assertFalse(Markers.discovered(Layer.MINES, "pequena", l));
		assertTrue(Markers.discovered(Layer.COAST, "faro", l));
		assertFalse(Markers.discovered(Layer.COAST, "naufragio", l), "cada tipo con su logro");
		assertTrue(Markers.discovered(Layer.ARENA, "", new State.Achievements()));
	}

	@Test
	void escapedHtml() {
		MapMarker m = new MapMarker("x", Layer.UNIQUES, 0, 0, 0, "<script>&\"'", "a<b");
		assertEquals("<b>&lt;script&gt;&amp;&quot;&#39;</b><br>a&lt;b", m.html());
	}

	@Test
	void missingTextReturnsKey() {
		assertEquals("heraldia.unicas.nada.nombre", Markers.name(Layer.UNIQUES, "nada", Map.of()));
		assertEquals("Aldea (x)", Markers.name(Layer.VILLAGES, "f", Map.of("heraldia.mapas_web.aldea", "Aldea (x)",
				"heraldia.familia.f", "F")).replace(" F", ""));
	}

	@Test
	void markerLanguage() {
		assertEquals("es_es", WebMaps.language("auto", Locale.of("es", "ES")));
		assertEquals("fr_ca", WebMaps.language("auto", Locale.of("fr", "CA")));
		assertEquals("gl_es", WebMaps.language("gl_es", Locale.US));
		// un idioma del sistema que el .jar no trae: el de su lengua o el inglés (Textos.codigo)
		assertEquals(Texts.texts("fr_fr"), Texts.texts(WebMaps.language("auto", Locale.of("fr", "CA"))));
		assertEquals(EN, Texts.texts(WebMaps.language("auto", Locale.of("ja", "JP"))));
	}
}
