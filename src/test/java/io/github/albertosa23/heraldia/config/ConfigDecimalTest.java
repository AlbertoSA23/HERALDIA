package io.github.albertosa23.heraldia.config;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonParser;
import com.google.gson.JsonPrimitive;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Optional;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/** Opciones con decimales (el valor por defecto con punto en el esquema, como minas.vanilla.multiplicador = 2.0). */
class ConfigDecimalTest {
	private static final ConfigOption DECIMAL = ConfigOption.of(JsonParser.parseString("""
			{"clave": "m.x", "defecto": 2.0, "min": 1, "max": 5, "ayuda": "k", "seccion": "s", "nombre": "n"}""").getAsJsonObject());
	private static final ConfigOption INTEGER = ConfigOption.of(JsonParser.parseString("""
			{"clave": "m.y", "defecto": 2, "min": 1, "max": 5, "ayuda": "k", "seccion": "s", "nombre": "n"}""").getAsJsonObject());

	@TempDir
	Path dir;

	@AfterEach
	void restore() {
		HeraldiaConfig.load(null);
	}

	@Test
	void tellsDecimalsFromIntegers() {
		assertTrue(DECIMAL.decimal());
		assertFalse(INTEGER.decimal());
		assertFalse(DECIMAL.isBoolean());
	}

	@Test
	void acceptsDecimalsInRange() {
		assertEquals(Optional.of(new JsonPrimitive(1.5)), DECIMAL.accept(new JsonPrimitive(1.5)));
		assertEquals(Optional.of(new JsonPrimitive(5.0)), DECIMAL.accept(new JsonPrimitive(5)));
		assertTrue(DECIMAL.accept(new JsonPrimitive(5.01)).isEmpty());
		assertTrue(DECIMAL.accept(new JsonPrimitive(0.99)).isEmpty());
		assertTrue(DECIMAL.accept(new JsonPrimitive(Double.NaN)).isEmpty());
		assertTrue(DECIMAL.accept(new JsonPrimitive("2")).isEmpty() || DECIMAL.accept(new JsonPrimitive("2")).isPresent());
		assertTrue(INTEGER.accept(new JsonPrimitive(1.5)).isEmpty(), "las enteras siguen sin admitir decimales");
	}

	@Test
	void screenReadsDecimals() {
		assertEquals(Optional.of(new JsonPrimitive(2.5)), DECIMAL.parse(" 2.5 "));
		assertEquals(Optional.of(new JsonPrimitive(3.0)), DECIMAL.parse("3"));
		for (String bad : new String[] {"", "2,5", "1e3", "6", "0.5", "abc", "2.", ".5"}) {
			assertTrue(DECIMAL.parse(bad).isEmpty(), bad);
		}
		assertTrue(INTEGER.parse("2.5").isEmpty());
	}

	@Test
	void minesMultiplierIsDecimal() throws IOException {
		ConfigOption o = HeraldiaConfig.options().stream().filter(x -> x.key().equals("minas.vanilla.multiplicador")).findFirst().orElseThrow();
		assertTrue(o.decimal());
		assertEquals(2.0, o.defaultValue().getAsDouble());
		assertEquals(1, o.min());
		assertEquals(5, o.max());
		Path f = dir.resolve("heraldia.json");
		Files.writeString(f, "{\"minas\": {\"vanilla\": {\"multiplicador\": 1.25}}}");
		assertEquals(1.25, HeraldiaConfig.load(f).getDouble("minas.vanilla.multiplicador"));
		assertTrue(Files.readString(f).contains("1.25"), "se reescribe con su valor");
	}
}
