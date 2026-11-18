package io.github.albertosa23.heraldia.command;

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
 * Dialog configuration panel (T46): order of the dialogs and their buttons, real options in each submenu (5
 * to 8), controls with the current value, reading what the dialog returns and language preference.
 */
class ConfigPanelTest {
	@BeforeAll
	static void bootstrap() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	static Map<String, ConfigOption> options() {
		Map<String, ConfigOption> m = new LinkedHashMap<>();
		HeraldiaConfig.options().forEach(o -> m.put(o.key(), o));
		return m;
	}

	static String command(ActionButton b) {
		return ((ClickEvent.RunCommand) ((StaticAction) b.action().orElseThrow()).value()).command();
	}

	@Test
	void menuOrder() {
		assertEquals(List.of("mundo", "aldeas", "combate", "botin", "arena", "jugadores", "avanzado"),
				Menus.MENUS.stream().map(Menus.Menu::id).toList());
		assertEquals(List.of("casual", "estandar", "hardcore"), Menus.PROFILES);
	}

	@Test
	void eachMenuHasFiveToEightRealOptionsWithoutRepeats() {
		Map<String, ConfigOption> o = options();
		Set<String> seen = new HashSet<>();
		for (Menus.Menu m : Menus.MENUS) {
			assertTrue(m.keys().size() >= Menus.MIN_OPTIONS && m.keys().size() <= Menus.MAX_OPTIONS, m.id());
			for (String k : m.keys()) {
				assertTrue(o.containsKey(k), k);
				assertTrue(seen.add(k), "repetida " + k);
				assertTrue(o.get(k).pattern() == null, k);
			}
		}
		assertTrue(Menus.menu("avanzado").orElseThrow().keys().contains("actualizar.margen_bloques"));
	}

	@Test
	void mainDialogInOrder() {
		Map<String, String> l = Texts.language("es_es");
		MultiActionDialog d = ConfigPanel.main(l, "estandar", "estandar");
		List<String> cmds = d.actions().stream().map(ConfigPanelTest::command).toList();
		assertEquals(ConfigPanel.mainActions(), cmds);
		assertEquals("heraldia config profile casual", cmds.get(0));
		assertEquals("heraldia config menu mundo", cmds.get(3));
		assertEquals("heraldia config menu avanzado", cmds.getLast());
		assertTrue(d.actions().get(1).button().label().getString().startsWith("✔"));   // the chosen profile
		assertEquals("Configuración de Heraldia", d.common().title().getString());
		assertTrue(d.exitAction().isPresent());
	}

	@Test
	void submenuWithItsControlsAndTemplate() {
		Map<String, ConfigOption> o = options();
		Map<String, JsonPrimitive> v = HeraldiaConfig.defaults();
		Menus.Menu combat = Menus.menu("combate").orElseThrow();
		MultiActionDialog d = ConfigPanel.submenu(Texts.language("en_us"), combat, o, v, "estandar");
		assertEquals(combat.keys().size(), d.common().inputs().size());
		assertEquals(combat.keys().size(), d.common().body().size());
		assertTrue(d.common().inputs().get(0).control() instanceof SingleOptionInput s
				&& s.entries().stream().filter(SingleOptionInput.Entry::initial).findFirst().orElseThrow().id().equals("normal"));
		assertTrue(d.common().inputs().get(1).control() instanceof BooleanInput);
		assertTrue(d.common().inputs().get(4).control() instanceof NumberRangeInput n && n.rangeInfo().end() == 300f);
		CommandTemplate t = (CommandTemplate) d.actions().get(0).action().orElseThrow();
		Map<String, String> vals = new LinkedHashMap<>();
		for (int i = 0; i < combat.keys().size(); i++) {
			vals.put("o" + i, "v" + i);
		}
		assertEquals("heraldia config save combate v0 v1 v2 v3 v4 v5", t.template().instantiate(vals));
		assertEquals("heraldia config", command(d.actions().get(1)));
		// each option's sentence carries its recommended value; generation warns about a restart, combat does not
		assertFalse(d.common().body().get(0).toString().contains("heraldia.panel.reinicio"));
		MultiActionDialog world = ConfigPanel.submenu(Texts.language("en_us"), Menus.menu("mundo").orElseThrow(), o, v, "estandar");
		assertTrue(world.common().body().get(0).toString().contains("heraldia.panel.reinicio"));
	}

	@Test
	void sliderStepAndReading() {
		Map<String, ConfigOption> o = options();
		ConfigOption sep = o.get("aldeas.separacion_bloques");      // 1000..10000
		assertEquals(100, Menus.step(sep));
		assertEquals(1, Menus.step(o.get("aldeas.caminos.ancho")));
		assertEquals(0.1, Menus.step(o.get("minas.vanilla.multiplicador")));
		// 1550 does not fall on the grid of 100: if the dialog returns the snapped one (1600), the existing one is kept
		assertEquals(Optional.of(new JsonPrimitive(1550)), Menus.read(sep, "1600.0", new JsonPrimitive(1550)));
		assertEquals(Optional.of(new JsonPrimitive(2000)), Menus.read(sep, "2000", new JsonPrimitive(1550)));
		assertEquals(Optional.empty(), Menus.read(sep, "20000", null));
		assertEquals(Optional.of(new JsonPrimitive(2.5)), Menus.read(o.get("minas.vanilla.multiplicador"), "2.5", new JsonPrimitive(2.0)));
		assertEquals(Optional.of(new JsonPrimitive(false)), Menus.read(o.get("medianas.activadas"), "false", new JsonPrimitive(true)));
		assertEquals(Optional.of(new JsonPrimitive("heroica")), Menus.read(o.get("dificultad.nivel"), "heroica", null));
		assertEquals(Optional.empty(), Menus.read(o.get("dificultad.nivel"), "imposible", null));
		Menus.Loaded r = Menus.read(Menus.menu("combate").orElseThrow(), List.of("dificil", "true", "x", "false", "120", "true"), o,
				HeraldiaConfig.defaults());
		assertEquals(List.of("jefes.fases.activado"), r.invalid());
		assertEquals(new JsonPrimitive("dificil"), r.optionValues().get("dificultad.nivel"));
		assertEquals(new JsonPrimitive(120), r.optionValues().get("jefes.refuerzos.porcentaje"));
	}

	@Test
	void languagePreference() {
		List<String> there = new ArrayList<>(Texts.languages());
		assertEquals(8, there.size());
		assertEquals(Optional.of(Optional.of("fr_fr")), Preferences.choose("FR_fr", there));
		assertEquals(Optional.of(Optional.empty()), Preferences.choose("auto", there));
		assertEquals(Optional.empty(), Preferences.choose("klingon", there));
	}
}
