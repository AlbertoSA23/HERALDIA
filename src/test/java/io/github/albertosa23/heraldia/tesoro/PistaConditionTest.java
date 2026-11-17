package io.github.albertosa23.heraldia.tesoro;

import static org.junit.jupiter.api.Assertions.assertEquals;

import com.google.gson.JsonParser;
import com.mojang.serialization.JsonOps;
import org.junit.jupiter.api.Test;

/** La probabilidad del fragmento (la misma cuenta que tools/gen/tesoro.probabilidad) y el formato de la condición. */
class PistaConditionTest {
	@Test
	void probabilidad() {
		assertEquals(0.03, PistaCondition.probabilidad(3, 1), 1e-12);
		assertEquals(0.015, PistaCondition.probabilidad(3, 0.5), 1e-12);
		assertEquals(0.15, PistaCondition.probabilidad(3, 5), 1e-12);
		assertEquals(0, PistaCondition.probabilidad(0, 5), 1e-12);
		assertEquals(1, PistaCondition.probabilidad(100, 5), 1e-12);
		assertEquals(0, PistaCondition.probabilidad(-1, 1), 1e-12);
	}

	@Test
	void leeElFactorConValorPorDefecto() {
		PistaCondition c = PistaCondition.CODEC.codec().parse(JsonOps.INSTANCE, JsonParser.parseString("{\"factor\": 0.5}")).getOrThrow();
		assertEquals(0.5, c.factor());
		assertEquals(1.0, PistaCondition.CODEC.codec().parse(JsonOps.INSTANCE, JsonParser.parseString("{}")).getOrThrow().factor());
	}

	@Test
	void lasOpcionesSonRecargablesYNoDeGeneracion() {
		for (String k : new String[]{PistaCondition.ACTIVADO, PistaCondition.PROBABILIDAD, PistaCondition.RADIO}) {
			assertEquals(true, io.github.albertosa23.heraldia.config.Recarga.recargable(k), k);
		}
	}
}
