package io.github.albertosa23.heraldia.arena;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import io.github.albertosa23.heraldia.difficulty.ModDifficulty;
import java.util.Set;
import org.junit.jupiter.api.Test;

/** Records and the difficulty of the arena mobs (dificultad.nivel is respected and adds up). */
class ArenaScoreboardTest {
	@Test
	void records() {
		assertTrue(ArenaScoreboard.improves(0, 1));
		assertTrue(ArenaScoreboard.improves(4, 5));
		assertFalse(ArenaScoreboard.improves(5, 5), "igualar no es batir");
		assertFalse(ArenaScoreboard.improves(7, 5));
		assertFalse(ArenaScoreboard.SERVER.matches("[A-Za-z0-9_]{3,16}"), "el récord del servidor no puede ser el nombre de un jugador");
	}

	@Test
	void difficultyAppliesToArenaMobs() {
		assertEquals(Arena.TAG, ModDifficulty.ARENA);
		assertTrue(ModDifficulty.applies(Set.of(Arena.TAG, "heraldia_adulto"), true));
		assertFalse(ModDifficulty.applies(Set.of(Arena.TAG), false), "solo a los hostiles");
		assertFalse(ModDifficulty.applies(Set.of("heraldia_adulto"), true));
	}
}
