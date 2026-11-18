package io.github.albertosa23.heraldia.config;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonParser;
import com.google.gson.JsonPrimitive;
import java.util.Optional;
import org.junit.jupiter.api.Test;

/** ConfigOption leída del esquema (ConfigOption.of) y su validación, sin depender de las opciones reales. */
class ConfigOptionTest {
	private static ConfigOption of(String json) {
		return ConfigOption.of(JsonParser.parseString(json).getAsJsonObject());
	}

	private static final ConfigOption RANGE = of("""
			{"clave": "a.b", "defecto": 5, "min": -3, "max": 10, "ayuda": "k.ayuda", "args": ["x"], "seccion": "s",
			 "nombre": "k.nombre", "patron": "a.<p>", "args_nombre": [null, "k.arg"]}""");
	private static final ConfigOption YESNO = of("""
			{"clave": "a.c", "defecto": true, "ayuda": "k", "seccion": "s", "nombre": "n"}""");

	private static final ConfigOption LIST = of("""
			{"clave": "a.d", "defecto": "normal", "valores": ["facil", "normal", "dificil"], "ayuda": "k", "seccion": "s",
			 "nombre": "n", "nombres_valores": ["k.facil", "k.normal", "k.dificil"]}""");

	@Test
	void listOption() {
		assertTrue(LIST.isChoice() && !LIST.isBoolean() && LIST.min() == null);
		assertEquals(java.util.List.of("facil", "normal", "dificil"), LIST.values());
		assertEquals(java.util.List.of("k.facil", "k.normal", "k.dificil"), LIST.valueNames());
		assertEquals(Optional.of(new JsonPrimitive("dificil")), LIST.accept(new JsonPrimitive("dificil")));
		for (JsonPrimitive bad : new JsonPrimitive[]{new JsonPrimitive("Dificil"), new JsonPrimitive("heroica"), new JsonPrimitive(1),
				new JsonPrimitive(true), new JsonPrimitive("")}) {
			assertTrue(LIST.accept(bad).isEmpty(), bad.toString());
		}
		assertEquals(Optional.of(new JsonPrimitive("facil")), LIST.parse(" facil "));
		assertTrue(LIST.parse("1").isEmpty());
		assertTrue(!RANGE.isChoice() && !YESNO.isChoice() && RANGE.values().isEmpty());
	}

	@Test
	void readsAllFields() {
		assertEquals("a.b", RANGE.key());
		assertEquals(-3, RANGE.min());
		assertEquals(10, RANGE.max());
		assertEquals("a.<p>", RANGE.pattern());
		assertEquals(java.util.Arrays.asList(null, "k.arg"), RANGE.argNames());
		assertEquals(java.util.List.of("x"), RANGE.args());
		assertTrue(YESNO.isBoolean() && YESNO.min() == null && YESNO.pattern() == null && YESNO.args().isEmpty());
	}

	@Test
	void acceptsIntegersInRangeAndNormalizes() {
		assertEquals(Optional.of(new JsonPrimitive(-3)), RANGE.accept(new JsonPrimitive(-3)));
		assertEquals(Optional.of(new JsonPrimitive(10)), RANGE.accept(new JsonPrimitive(10.0)));
		for (JsonPrimitive bad : new JsonPrimitive[]{new JsonPrimitive(11), new JsonPrimitive(-4), new JsonPrimitive(2.5),
				new JsonPrimitive(true), new JsonPrimitive("5")}) {
			assertTrue(RANGE.accept(bad).isEmpty(), bad.toString());
		}
		assertTrue(YESNO.accept(new JsonPrimitive(1)).isEmpty() && YESNO.accept(new JsonPrimitive(false)).isPresent());
	}

	@Test
	void screenText() {
		assertEquals(Optional.of(new JsonPrimitive(-3)), RANGE.parse("-3"));
		assertEquals(Optional.of(new JsonPrimitive(7)), RANGE.parse("\t7 "));
		for (String bad : new String[]{"-4", "11", "0x5", "5.", "", " ", "--1", "123456789012"}) {
			assertTrue(RANGE.parse(bad).isEmpty(), bad);
		}
		assertTrue(YESNO.parse("True").isEmpty() && YESNO.parse("true").isPresent());
	}
}
