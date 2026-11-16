package io.github.albertosa23.heraldia.comando;

import static org.junit.jupiter.api.Assertions.assertEquals;

import net.minecraft.SharedConstants;
import net.minecraft.server.Bootstrap;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/** Rumbo de 8 puntos de /heraldia info cerca (norte = -z, como en el juego). */
class InfoCommandTest {
	@BeforeAll
	static void bootstrap() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	@Test
	void puntosCardinalesYDiagonales() {
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
	void sectoresDe45Grados() {
		// cada rumbo cubre ±22,5°: a 20° del norte sigue siendo norte; a 25°, noreste
		assertEquals("n", InfoCommand.direction(36, -100)); // ~19,8°
		assertEquals("ne", InfoCommand.direction(47, -100)); // ~25,2°
		assertEquals("e", InfoCommand.direction(100, 36));
		assertEquals("s", InfoCommand.direction(0, 0)); // sin desplazamiento: atan2(0, 0) = 0, el sur
	}
}
