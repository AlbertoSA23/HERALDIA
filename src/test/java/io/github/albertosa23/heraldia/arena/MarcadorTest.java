package io.github.albertosa23.heraldia.arena;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import io.github.albertosa23.heraldia.dificultad.Dificultad;
import java.util.Set;
import org.junit.jupiter.api.Test;

/** Récords y la dificultad de los mobs de la arena (dificultad.nivel se respeta y suma). */
class MarcadorTest {
	@Test
	void records() {
		assertTrue(Marcador.mejora(0, 1));
		assertTrue(Marcador.mejora(4, 5));
		assertFalse(Marcador.mejora(5, 5), "igualar no es batir");
		assertFalse(Marcador.mejora(7, 5));
		assertFalse(Marcador.SERVIDOR.matches("[A-Za-z0-9_]{3,16}"), "el récord del servidor no puede ser el nombre de un jugador");
	}

	@Test
	void laDificultadSeAplicaALosMobsDeLaArena() {
		assertEquals(Arena.TAG, Dificultad.ARENA);
		assertTrue(Dificultad.aplica(Set.of(Arena.TAG, "heraldia_adulto"), true));
		assertFalse(Dificultad.aplica(Set.of(Arena.TAG), false), "solo a los hostiles");
		assertFalse(Dificultad.aplica(Set.of("heraldia_adulto"), true));
	}
}
