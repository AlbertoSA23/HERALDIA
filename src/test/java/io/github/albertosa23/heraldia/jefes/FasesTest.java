package io.github.albertosa23.heraldia.jefes;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.HashSet;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.Test;

/** Lógica pura de las fases: umbrales, idempotencia por fase (etiquetas), límite de refuerzos, opciones y barra. */
class FasesTest {
	private static final Set<String> GUARDIAN = Set.of(Fases.GUARDIAN, "heraldia_guardian.castillo", "heraldia_anclado");

	@Test
	void umbrales() {
		assertEquals(1, Fases.faseDeVida(100, 100));
		assertEquals(1, Fases.faseDeVida(66, 100));          // «bajar del 66 %»: en el 66 justo aún no
		assertEquals(2, Fases.faseDeVida(65.9f, 100));
		assertEquals(2, Fases.faseDeVida(33, 100));
		assertEquals(3, Fases.faseDeVida(32.9f, 100));
		assertEquals(3, Fases.faseDeVida(0.5f, 100));
		assertEquals(2, Fases.faseDeVida(39, 60));           // 65 %
		assertEquals(1, Fases.faseDeVida(10, 0));            // vida máxima rara: sin fases
		assertEquals(1, Fases.faseDeVida(10, Float.NaN));
	}

	@Test
	void reconoceGuardianYUnica() {
		assertTrue(Fases.esGuardian(GUARDIAN));
		assertFalse(Fases.esGuardian(Set.of()));
		assertFalse(Fases.esGuardian(Set.of("heraldia_guardian.castillo")));   // solo la de la única no basta
		assertFalse(Fases.esGuardian(Set.of(Fases.REFUERZO, "heraldia_anclado")));
		assertEquals("castillo", Fases.unica(GUARDIAN));
		assertNull(Fases.unica(Set.of(Fases.GUARDIAN)));                    // guardián de un mundo viejo sin id
		assertNull(Fases.unica(Set.of(Fases.GUARDIAN, Fases.UNICA)));
	}

	@Test
	void pendientesEnOrdenYUnaVez() {
		Set<String> tags = new HashSet<>(GUARDIAN);
		assertEquals(List.of(), Fases.pendientes(tags, 80, 100, true, true));
		assertEquals(List.of(2), Fases.pendientes(tags, 60, 100, true, true));
		tags.add(Fases.FASE + 2);
		assertEquals(2, Fases.alcanzada(tags));
		// ya en la fase 2: otro golpe en la misma franja no la repite (tampoco tras curarse por encima del 66 %)
		assertEquals(List.of(), Fases.pendientes(tags, 50, 100, true, true));
		assertEquals(List.of(), Fases.pendientes(tags, 90, 100, true, true));
		assertEquals(List.of(3), Fases.pendientes(tags, 20, 100, true, true));
		tags.add(Fases.FASE + 3);
		assertEquals(3, Fases.alcanzada(tags));
		assertEquals(List.of(), Fases.pendientes(tags, 1, 100, true, true));
	}

	@Test
	void unGolpeGrandeDaLasDosFases() {
		assertEquals(List.of(2, 3), Fases.pendientes(GUARDIAN, 10, 100, true, false));
		assertEquals(List.of(3), Fases.pendientes(Set.of(Fases.GUARDIAN, Fases.FASE + 2), 10, 100, false, true));
		// un guardián cargado con la etiqueta de la fase 3 pero no la de la 2 (fichero editado): solo falta la 2
		assertEquals(List.of(2), Fases.pendientes(Set.of(Fases.GUARDIAN, Fases.FASE + 3), 10, 100, true, true));
		assertEquals(3, Fases.alcanzada(Set.of(Fases.FASE + 3)));
	}

	@Test
	void opcionesDesactivadasYMuerto() {
		assertEquals(List.of(), Fases.pendientes(GUARDIAN, 10, 100, false, false));
		assertEquals(List.of(), Fases.pendientes(GUARDIAN, 0, 100, true, true));      // el golpe que lo mata
		assertEquals(List.of(), Fases.pendientes(GUARDIAN, -3, 100, true, true));
		assertEquals(List.of(2, 3), Fases.pendientes(GUARDIAN, 10, 100, false, true));  // solo refuerzos
		assertEquals(List.of(2, 3), Fases.pendientes(GUARDIAN, 10, 100, true, false));  // solo fases
	}

	@Test
	void limiteDeRefuerzosVivos() {
		assertEquals(3, Fases.cuantos(3, 0));
		assertEquals(2, Fases.cuantos(2, 0));
		assertEquals(1, Fases.cuantos(3, 3));
		assertEquals(0, Fases.cuantos(3, Fases.MAX_VIVOS));
		assertEquals(0, Fases.cuantos(3, Fases.MAX_VIVOS + 5));
		assertEquals(0, Fases.cuantos(0, 0));
		// dos fases seguidas con 3 refuerzos cada una: nunca más de MAX_VIVOS
		int vivos = 0;
		for (int f = 0; f < 2; f++) {
			vivos += Fases.cuantos(3, vivos);
		}
		assertEquals(Fases.MAX_VIVOS, vivos);
	}

	@Test
	void mensajes() {
		assertEquals("heraldia.jefes.fase.2", Fases.clave(2, true, 0));
		assertEquals("heraldia.jefes.fase.2.refuerzos", Fases.clave(2, true, 3));
		assertEquals("heraldia.jefes.fase.3.refuerzos", Fases.clave(3, true, 1));
		assertEquals("heraldia.jefes.refuerzos", Fases.clave(3, false, 2));
		assertNull(Fases.clave(2, false, 0));
	}

	@Test
	void barra() {
		assertEquals(Boolean.TRUE, Fases.ve(0));
		assertEquals(Boolean.TRUE, Fases.ve(32.0 * 32));
		assertNull(Fases.ve(40.0 * 40));                     // entre los dos radios: se queda como estaba
		assertEquals(Boolean.FALSE, Fases.ve(48.1 * 48.1));
		assertEquals(1f, Fases.progreso(100, 100));
		assertEquals(0.5f, Fases.progreso(30, 60));
		assertEquals(0f, Fases.progreso(5, 0));
		assertEquals(1f, Fases.progreso(120, 100));
		assertEquals(net.minecraft.world.BossEvent.BossBarColor.YELLOW, Barras.color(1));
		assertEquals(net.minecraft.world.BossEvent.BossBarColor.RED, Barras.color(2));
		assertEquals(net.minecraft.world.BossEvent.BossBarColor.PURPLE, Barras.color(3));
	}
}
