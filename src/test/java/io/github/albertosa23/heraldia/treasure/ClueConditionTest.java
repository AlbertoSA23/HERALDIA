package io.github.albertosa23.heraldia.treasure;

import static org.junit.jupiter.api.Assertions.assertEquals;

import com.google.gson.JsonParser;
import com.mojang.serialization.JsonOps;
import org.junit.jupiter.api.Test;

/** The fragment's probability (the same computation as tools/gen/treasure.probability) and the condition's format. */
class ClueConditionTest {
	@Test
	void probability() {
		assertEquals(0.03, ClueCondition.probability(3, 1), 1e-12);
		assertEquals(0.015, ClueCondition.probability(3, 0.5), 1e-12);
		assertEquals(0.15, ClueCondition.probability(3, 5), 1e-12);
		assertEquals(0, ClueCondition.probability(0, 5), 1e-12);
		assertEquals(1, ClueCondition.probability(100, 5), 1e-12);
		assertEquals(0, ClueCondition.probability(-1, 1), 1e-12);
	}

	@Test
	void readsFactorWithDefault() {
		ClueCondition c = ClueCondition.CODEC.codec().parse(JsonOps.INSTANCE, JsonParser.parseString("{\"factor\": 0.5}")).getOrThrow();
		assertEquals(0.5, c.factor());
		assertEquals(1.0, ClueCondition.CODEC.codec().parse(JsonOps.INSTANCE, JsonParser.parseString("{}")).getOrThrow().factor());
	}

	@Test
	void optionsAreReloadableNotGeneration() {
		for (String k : new String[]{ClueCondition.ENABLED, ClueCondition.PROBABILITY, ClueCondition.RADIUS}) {
			assertEquals(true, io.github.albertosa23.heraldia.config.Reload.reloadable(k), k);
		}
	}
}
