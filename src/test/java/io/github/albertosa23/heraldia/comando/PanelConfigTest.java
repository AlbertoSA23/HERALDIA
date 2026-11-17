package io.github.albertosa23.heraldia.comando;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonPrimitive;
import io.github.albertosa23.heraldia.config.ConfigOption;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.config.Menus;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import net.minecraft.SharedConstants;
import net.minecraft.network.chat.ClickEvent;
import net.minecraft.server.Bootstrap;
import net.minecraft.server.dialog.ActionButton;
import net.minecraft.server.dialog.MultiActionDialog;
import net.minecraft.server.dialog.action.CommandTemplate;
import net.minecraft.server.dialog.action.StaticAction;
import net.minecraft.server.dialog.input.BooleanInput;
import net.minecraft.server.dialog.input.NumberRangeInput;
import net.minecraft.server.dialog.input.SingleOptionInput;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/**
 * Panel de configuración en diálogos (T46): orden de los diálogos y de sus botones, opciones reales en cada submenú (5
 * a 8), controles con el valor actual, lectura de lo que devuelve el diálogo y preferencia de idioma.
 */
class PanelConfigTest {
	@BeforeAll
	static void bootstrap() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	static Map<String, ConfigOption> opciones() {
		Map<String, ConfigOption> m = new LinkedHashMap<>();
		HeraldiaConfig.options().forEach(o -> m.put(o.key(), o));
		return m;
	}

	static String comando(ActionButton b) {
		return ((ClickEvent.RunCommand) ((StaticAction) b.action().orElseThrow()).value()).command();
	}

	@Test
	void ordenDeLosMenus() {
		assertEquals(List.of("mundo", "aldeas", "combate", "botin", "arena", "jugadores", "avanzado"),
				Menus.MENUS.stream().map(Menus.Menu::id).toList());
		assertEquals(List.of("casual", "estandar", "hardcore"), Menus.PERFILES);
	}

	@Test
	void cadaMenuTieneDeCincoAOchoOpcionesRealesSinRepetir() {
		Map<String, ConfigOption> o = opciones();
		Set<String> vistas = new HashSet<>();
		for (Menus.Menu m : Menus.MENUS) {
			assertTrue(m.claves().size() >= Menus.MIN_OPCIONES && m.claves().size() <= Menus.MAX_OPCIONES, m.id());
			for (String k : m.claves()) {
				assertTrue(o.containsKey(k), k);
				assertTrue(vistas.add(k), "repetida " + k);
				assertTrue(o.get(k).pattern() == null, k);
			}
		}
		assertTrue(Menus.menu("avanzado").orElseThrow().claves().contains("actualizar.margen_bloques"));
	}

	@Test
	void dialogoPrincipalEnOrden() {
		Map<String, String> l = Textos.idioma("es_es");
		MultiActionDialog d = PanelConfig.principal(l, "estandar", "estandar");
		List<String> cmds = d.actions().stream().map(PanelConfigTest::comando).toList();
		assertEquals(PanelConfig.accionesPrincipal(), cmds);
		assertEquals("heraldia config profile casual", cmds.get(0));
		assertEquals("heraldia config menu mundo", cmds.get(3));
		assertEquals("heraldia config menu avanzado", cmds.getLast());
		assertTrue(d.actions().get(1).button().label().getString().startsWith("✔"));   // el perfil elegido
		assertEquals("Configuración de Heraldia", d.common().title().getString());
		assertTrue(d.exitAction().isPresent());
	}

	@Test
	void submenuConSusControlesYLaPlantilla() {
		Map<String, ConfigOption> o = opciones();
		Map<String, JsonPrimitive> v = HeraldiaConfig.defaults();
		Menus.Menu combate = Menus.menu("combate").orElseThrow();
		MultiActionDialog d = PanelConfig.submenu(Textos.idioma("en_us"), combate, o, v, "estandar");
		assertEquals(combate.claves().size(), d.common().inputs().size());
		assertEquals(combate.claves().size(), d.common().body().size());
		assertTrue(d.common().inputs().get(0).control() instanceof SingleOptionInput s
				&& s.entries().stream().filter(SingleOptionInput.Entry::initial).findFirst().orElseThrow().id().equals("normal"));
		assertTrue(d.common().inputs().get(1).control() instanceof BooleanInput);
		assertTrue(d.common().inputs().get(4).control() instanceof NumberRangeInput n && n.rangeInfo().end() == 300f);
		CommandTemplate t = (CommandTemplate) d.actions().get(0).action().orElseThrow();
		Map<String, String> vals = new LinkedHashMap<>();
		for (int i = 0; i < combate.claves().size(); i++) {
			vals.put("o" + i, "v" + i);
		}
		assertEquals("heraldia config save combate v0 v1 v2 v3 v4 v5", t.template().instantiate(vals));
		assertEquals("heraldia config", comando(d.actions().get(1)));
		// la frase de cada opción lleva su recomendado; la generación avisa de reinicio, el combate no
		assertFalse(d.common().body().get(0).toString().contains("heraldia.panel.reinicio"));
		MultiActionDialog mundo = PanelConfig.submenu(Textos.idioma("en_us"), Menus.menu("mundo").orElseThrow(), o, v, "estandar");
		assertTrue(mundo.common().body().get(0).toString().contains("heraldia.panel.reinicio"));
	}

	@Test
	void pasoDelDeslizadorYLectura() {
		Map<String, ConfigOption> o = opciones();
		ConfigOption sep = o.get("aldeas.separacion_bloques");      // 1000..10000
		assertEquals(100, Menus.paso(sep));
		assertEquals(1, Menus.paso(o.get("aldeas.caminos.ancho")));
		assertEquals(0.1, Menus.paso(o.get("minas.vanilla.multiplicador")));
		// 1550 no cae en la rejilla de 100: si el diálogo devuelve el ajustado (1600), se conserva el que había
		assertEquals(Optional.of(new JsonPrimitive(1550)), Menus.leer(sep, "1600.0", new JsonPrimitive(1550)));
		assertEquals(Optional.of(new JsonPrimitive(2000)), Menus.leer(sep, "2000", new JsonPrimitive(1550)));
		assertEquals(Optional.empty(), Menus.leer(sep, "20000", null));
		assertEquals(Optional.of(new JsonPrimitive(2.5)), Menus.leer(o.get("minas.vanilla.multiplicador"), "2.5", new JsonPrimitive(2.0)));
		assertEquals(Optional.of(new JsonPrimitive(false)), Menus.leer(o.get("medianas.activadas"), "false", new JsonPrimitive(true)));
		assertEquals(Optional.of(new JsonPrimitive("heroica")), Menus.leer(o.get("dificultad.nivel"), "heroica", null));
		assertEquals(Optional.empty(), Menus.leer(o.get("dificultad.nivel"), "imposible", null));
		Menus.Leidos r = Menus.leer(Menus.menu("combate").orElseThrow(), List.of("dificil", "true", "x", "false", "120", "true"), o,
				HeraldiaConfig.defaults());
		assertEquals(List.of("jefes.fases.activado"), r.invalidas());
		assertEquals(new JsonPrimitive("dificil"), r.valores().get("dificultad.nivel"));
		assertEquals(new JsonPrimitive(120), r.valores().get("jefes.refuerzos.porcentaje"));
	}

	@Test
	void preferenciaDeIdioma() {
		List<String> hay = new ArrayList<>(Textos.idiomas());
		assertEquals(8, hay.size());
		assertEquals(Optional.of(Optional.of("fr_fr")), Preferencias.elegir("FR_fr", hay));
		assertEquals(Optional.of(Optional.empty()), Preferencias.elegir("auto", hay));
		assertEquals(Optional.empty(), Preferencias.elegir("klingon", hay));
	}
}
