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

	private static final ConfigOption RANGO = of("""
			{"clave": "a.b", "defecto": 5, "min": -3, "max": 10, "ayuda": "k.ayuda", "args": ["x"], "seccion": "s",
			 "nombre": "k.nombre", "patron": "a.<p>", "args_nombre": [null, "k.arg"]}""");
	private static final ConfigOption SINO = of("""
			{"clave": "a.c", "defecto": true, "ayuda": "k", "seccion": "s", "nombre": "n"}""");

	private static final ConfigOption LISTA = of("""
			{"clave": "a.d", "defecto": "normal", "valores": ["facil", "normal", "dificil"], "ayuda": "k", "seccion": "s",
			 "nombre": "n", "nombres_valores": ["k.facil", "k.normal", "k.dificil"]}""");

	@Test
	void opcionDeLista() {
		assertTrue(LISTA.isChoice() && !LISTA.isBoolean() && LISTA.min() == null);
		assertEquals(java.util.List.of("facil", "normal", "dificil"), LISTA.values());
		assertEquals(java.util.List.of("k.facil", "k.normal", "k.dificil"), LISTA.valueNames());
		assertEquals(Optional.of(new JsonPrimitive("dificil")), LISTA.accept(new JsonPrimitive("dificil")));
		for (JsonPrimitive bad : new JsonPrimitive[]{new JsonPrimitive("Dificil"), new JsonPrimitive("heroica"), new JsonPrimitive(1),
				new JsonPrimitive(true), new JsonPrimitive("")}) {
			assertTrue(LISTA.accept(bad).isEmpty(), bad.toString());
		}
		assertEquals(Optional.of(new JsonPrimitive("facil")), LISTA.parse(" facil "));
		assertTrue(LISTA.parse("1").isEmpty());
		assertTrue(!RANGO.isChoice() && !SINO.isChoice() && RANGO.values().isEmpty());
	}

	@Test
	void leeTodosLosCampos() {
		assertEquals("a.b", RANGO.key());
		assertEquals(-3, RANGO.min());
		assertEquals(10, RANGO.max());
		assertEquals("a.<p>", RANGO.pattern());
		assertEquals(java.util.Arrays.asList(null, "k.arg"), RANGO.argNames());
		assertEquals(java.util.List.of("x"), RANGO.args());
		assertTrue(SINO.isBoolean() && SINO.min() == null && SINO.pattern() == null && SINO.args().isEmpty());
	}

	@Test
	void aceptaEnterosEnRangoYNormaliza() {
		assertEquals(Optional.of(new JsonPrimitive(-3)), RANGO.accept(new JsonPrimitive(-3)));
		assertEquals(Optional.of(new JsonPrimitive(10)), RANGO.accept(new JsonPrimitive(10.0)));
		for (JsonPrimitive bad : new JsonPrimitive[]{new JsonPrimitive(11), new JsonPrimitive(-4), new JsonPrimitive(2.5),
				new JsonPrimitive(true), new JsonPrimitive("5")}) {
			assertTrue(RANGO.accept(bad).isEmpty(), bad.toString());
		}
		assertTrue(SINO.accept(new JsonPrimitive(1)).isEmpty() && SINO.accept(new JsonPrimitive(false)).isPresent());
	}

	@Test
	void textoDeLaPantalla() {
		assertEquals(Optional.of(new JsonPrimitive(-3)), RANGO.parse("-3"));
		assertEquals(Optional.of(new JsonPrimitive(7)), RANGO.parse("\t7 "));
		for (String bad : new String[]{"-4", "11", "0x5", "5.", "", " ", "--1", "123456789012"}) {
			assertTrue(RANGO.parse(bad).isEmpty(), bad);
		}
		assertTrue(SINO.parse("True").isEmpty() && SINO.parse("true").isPresent());
	}
}
