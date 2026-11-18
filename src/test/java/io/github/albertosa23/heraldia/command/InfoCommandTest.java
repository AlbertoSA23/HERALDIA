package io.github.albertosa23.heraldia.command;

import static org.junit.jupiter.api.Assertions.assertEquals;

import net.minecraft.SharedConstants;
import net.minecraft.server.Bootstrap;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/** 8-point heading of /heraldia info nearby (north = -z, as in the game). */
class InfoCommandTest {
	@BeforeAll
	static void bootstrap() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	@Test
	void cardinalAndDiagonalPoints() {
		assertEquals("n", InfoCommand.direction(0, -100));
		assertEquals("s", InfoCommand.direction(0, 100));
		assertEquals("e", InfoCommand.direction(100, 0));
		assertEquals("o", InfoCommand.direction(-100, 0));
		assertEquals("ne", InfoCommand.direction(70, -70));
		assertEquals("no", InfoCommand.direction(-70, -70));
		assertEquals("se", InfoCommand.direction(70, 70));
		assertEquals("so", InfoCommand.direction(-70, 70));
	}

	@Test
	void sectorsOf45Degrees() {
		// each heading covers ±22.5°: at 20° from north it is still north; at 25°, northeast
		assertEquals("n", InfoCommand.direction(36, -100)); // ~19.8°
		assertEquals("ne", InfoCommand.direction(47, -100)); // ~25.2°
		assertEquals("e", InfoCommand.direction(100, 36));
		assertEquals("s", InfoCommand.direction(0, 0)); // no offset: atan2(0, 0) = 0, south
	}

	@Test
	void halfGeneratedSavedChunkDoesNotCountAsGenerated() {
		assertFalse(InfoCommand.withStructures("minecraft:empty"));
		assertTrue(InfoCommand.withStructures("minecraft:structure_starts"));
		assertTrue(InfoCommand.withStructures("minecraft:features"));
		assertTrue(InfoCommand.withStructures("minecraft:full"));
		assertTrue(InfoCommand.withStructures(""), "sin estado, como antes");
	}
}
